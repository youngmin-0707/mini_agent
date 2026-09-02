"""06의 OpenAI AI Agent Loop를 선택 프레임워크인 LangGraph로 재구성합니다.

필수 학습인 06에서는 Python의 for 문과 조건문으로 ``LLM 판단 → Tool 실행 →
Tool Result 전달 → 재판단``을 구현했습니다. 이번 선택 예제는 새로운 Agent나 새로운
Tool을 만드는 것이 아니라, 같은 OpenAI Agent 실행 흐름을 State Graph의 Node와
Edge로 표현했을 때 코드 구조가 어떻게 달라지는지 비교합니다.

이번 파일에서 하는 일
----------------------
1. ``OpenAIAgentState``로 Node 사이에서 공유할 상태 계약을 정의합니다.
2. Agent Node에서 OpenAI 모델이 Tool Call 또는 최종 답변을 선택하게 합니다.
3. Backend Tool Node에서 모델 요청을 검증하고 allowlist Tool을 실행합니다.
4. 조건부 Edge로 Tool 실행, 모델 재판단 또는 종료 경로를 연결합니다.
5. 06과 동일한 backend 함수들을 재사용해 표현 방식만 공정하게 비교합니다.

전체 실행 흐름과 순서
---------------------
1. ``run``이 사용자 질문과 빈 Trace, 호출 횟수, 실행 상태로 Initial State를 만듭니다.
2. ``build_graph``가 Graph를 만들고 ``invoke``가 ``START``에서 실행을 시작합니다.
3. 첫 번째 ``openai_agent_node``는 질문, Instructions와 Tool Schema를 OpenAI에 보내
   최초 판단을 요청합니다.
4. Model 응답에 Function Call이 있으면 ``pending_calls``에 저장합니다.
5. ``route_after_agent``가 ``pending_calls`` 존재 여부를 확인합니다.
6. Tool Call이 있으면 Conditional Edge가 ``backend_tool_node``로 이동합니다.
7. Backend Tool Node가 Tool 이름과 arguments를 검증하고 Allowlist Tool을 실행한 뒤
   Function Call Output을 ``tool_outputs``에 저장합니다.
8. 일반 Edge가 다시 ``openai_agent_node``로 이동합니다.
9. Agent Node가 이전 OpenAI response id와 Tool Result를 Model에 전달하여 재판단을
   요청합니다. 추가 Tool이 필요하면 4~9번을 반복합니다.
10. Model이 Function Call 없이 최종 답변을 반환하면 ``status``를 completed로 바꾸고
    ``route_after_agent``가 ``finish``를 반환하여 ``END``로 이동합니다.
11. ``run``이 최종 Graph State에서 학습에 필요한 실행 결과만 추려 반환합니다.

Graph 경로를 한 줄로 표현하면 다음과 같습니다.

``START → OpenAI Agent → (Tool 필요) Backend Tools → OpenAI Agent → ...``
``→ (Tool 불필요) END``

LangGraph가 AI Agent를 자동으로 만들어 주는 것은 아닙니다. Agent의 판단 주체는 여전히
OpenAI 모델이고 Tool의 안전한 실행은 Python backend가 담당합니다. LangGraph는 State,
반복 경로와 종료 조건을 명시적인 Graph로 관리하는 Orchestration 수단입니다.
"""

import json
import sys
from pathlib import Path
from typing import Any, TypedDict

from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from openai_agent_backend import (  # noqa: E402
    OPENAI_MODEL,
    continue_after_tools,
    create_initial_response,
    execute_openai_call,
    function_calls,
    require_openai_client,
)


class OpenAIAgentState(TypedDict, total=False):
    """Graph의 모든 Node가 공유하고 부분 갱신하는 실행 State 계약입니다.

    LangGraph Node는 전체 State를 새로 만들지 않고 자신이 변경한 key만 dict로
    반환합니다. LangGraph가 그 결과를 기존 State에 병합하여 다음 Node에 전달합니다.

    Attributes:
        question: 사용자가 Agent에게 준 최초 Goal입니다.
        response: 직전 OpenAI Responses API 응답입니다. 다음 Model 호출을 연결합니다.
        pending_calls: Model이 요청했고 아직 Backend가 실행하지 않은 Function Call입니다.
        tool_outputs: Backend가 실행하여 다음 Model 호출에 전달할 Tool Result입니다.
        trace: Model 판단과 Tool 실행 순서를 관찰하기 위한 누적 기록입니다.
        llm_calls: OpenAI Model 호출 횟수입니다.
        tool_calls: Backend가 실제 실행한 Tool 횟수입니다.
        answer: Function Call이 없을 때 Model이 만든 최종 답변입니다.
        status: running 또는 completed로 표현하는 현재 실행 상태입니다.
        termination_reason: Graph가 종료된 이유입니다.
    """

    question: str
    response: Any
    pending_calls: list[Any]
    tool_outputs: list[dict[str, Any]]
    trace: list[dict[str, Any]]
    llm_calls: int
    tool_calls: int
    answer: str
    status: str
    termination_reason: str


def openai_agent_node(state: OpenAIAgentState) -> dict[str, Any]:
    """현재 State를 근거로 OpenAI Model의 다음 판단을 요청하는 Agent Node입니다.

    최초 실행에서는 ``question``을 Model에 전달합니다. Tool 실행 후 다시 들어온 경우에는
    직전 ``response.id``와 ``tool_outputs``를 전달해 이전 판단에 이어서 생각하게 합니다.

    Model 응답에 Function Call이 있으면 아직 실행하지 않고 ``pending_calls``에 저장합니다.
    실제 검증과 실행은 책임을 분리한 ``backend_tool_node``가 담당합니다. Function Call이
    없다면 Model이 목표를 달성했다고 보고 답변, 완료 상태와 종료 이유를 기록합니다.

    Args:
        state: 질문, 직전 Model 응답과 Tool Result가 들어 있는 현재 Graph State입니다.

    Returns:
        Model 응답, 대기 중 Tool Call, Trace와 호출 횟수 등 변경할 State key입니다.
        ``pending_calls``가 있으면 Tool Node로, 없으면 END로 라우팅됩니다.
    """
    client = require_openai_client()
    previous = state.get("response")
    tool_outputs = state.get("tool_outputs", [])

    try:
        if previous is None:
            response = create_initial_response(client, state["question"])
        else:
            response = continue_after_tools(client, previous.id, tool_outputs)
    except Exception as error:
        trace = list(state.get("trace", []))
        trace.append({"stage": "model_error", "error": str(error)})
        return {
            "pending_calls": [],
            "tool_outputs": [],
            "trace": trace,
            "status": "failed",
            "termination_reason": "model_error",
        }

    calls = function_calls(response)
    trace = list(state.get("trace", []))
    if not calls:
        trace.append({"stage": "model_final_answer", "text": response.output_text})
        return {
            "response": response,
            "pending_calls": [],
            "tool_outputs": [],
            "trace": trace,
            "llm_calls": state.get("llm_calls", 0) + 1,
            "answer": response.output_text,
            "status": "completed",
            "termination_reason": "model_finished",
        }

    trace.append({"stage": "model_requested_tools", "tools": [call.name for call in calls]})
    return {
        "response": response,
        "pending_calls": calls,
        "tool_outputs": [],
        "trace": trace,
        "llm_calls": state.get("llm_calls", 0) + 1,
        "status": "running",
    }


def backend_tool_node(state: OpenAIAgentState) -> dict[str, Any]:
    """Model이 제안한 Function Call을 검증하고 실제 Tool을 실행합니다.

    ``pending_calls``를 순회하며 ``execute_openai_call``에 전달합니다. 공유 Backend 함수는
    Tool 이름이 Allowlist에 있는지, arguments가 올바른 JSON Object인지 확인한 후에만
    Tool을 실행합니다. 실행 결과는 OpenAI가 이해하는 ``function_call_output`` 형식과
    사람이 확인할 Trace 형식으로 각각 저장합니다.

    이 Node는 다음 행동을 판단하지 않습니다. 안전하게 실행하고 관찰 결과를 만드는
    결정적 Backend 단계이며, 완료 후 Edge를 따라 Agent Node로 무조건 돌아갑니다.

    Args:
        state: Agent Node가 만든 ``pending_calls``와 지금까지의 Trace를 포함한 State입니다.

    Returns:
        다음 Model 판단에 전달할 ``tool_outputs``, 비운 ``pending_calls``, 갱신된 Trace와
        누적 Tool 호출 횟수입니다.
    """
    outputs = []
    trace = list(state.get("trace", []))
    for call in state.get("pending_calls", []):
        try:
            output, tool_trace = execute_openai_call(call)
        except (AttributeError, json.JSONDecodeError, TypeError, ValueError) as error:
            trace.append(
                {
                    "stage": "invalid_tool_call",
                    "tool": getattr(call, "name", None),
                    "error": str(error),
                }
            )
            return {
                "tool_outputs": [],
                "pending_calls": [],
                "trace": trace,
                "status": "failed",
                "termination_reason": "invalid_tool_call",
            }
        except Exception as error:
            trace.append(
                {
                    "stage": "tool_error",
                    "tool": getattr(call, "name", None),
                    "error": str(error),
                }
            )
            return {
                "tool_outputs": [],
                "pending_calls": [],
                "trace": trace,
                "status": "failed",
                "termination_reason": "tool_error",
            }
        outputs.append(output)
        trace.append({"stage": "tool_result", **tool_trace})
    return {
        "tool_outputs": outputs,
        "pending_calls": [],
        "trace": trace,
        "tool_calls": state.get("tool_calls", 0) + len(outputs),
    }


def route_after_agent(state: OpenAIAgentState) -> str:
    """Agent Node 실행 후 Tool 실행과 Graph 종료 중 다음 경로를 선택합니다.

    ``pending_calls``가 하나라도 있으면 ``tools``를 반환하여 Backend Tool Node로
    이동합니다. 비어 있으면 Model이 최종 답변을 반환한 것이므로 ``finish``를 반환해
    END로 이동합니다. 이 함수는 LLM 판단을 대신하지 않고 Model 응답을 Graph 경로로
    변환하는 Conditional Edge Router입니다.
    """
    if state.get("status") == "failed":
        return "finish"
    return "tools" if state.get("pending_calls") else "finish"


def route_after_tools(state: OpenAIAgentState) -> str:
    """Backend Tool Node 이후 재판단 또는 종료 경로를 선택합니다.

    ``backend_tool_node``가 Tool 실행 결과를 State에 반영한 직후 호출됩니다. Tool 검증
    또는 실행이 실패해 ``status=failed``가 되면 ``finish``를 반환해 END로 이동하고,
    성공하면 ``agent``를 반환해 OpenAI Agent Node가 Tool Result를 보고 재판단하게 합니다.

    Args:
        state: Backend Tool 실행 상태와 오류 정보가 반영된 Graph State입니다.

    Returns:
        실패 종료를 뜻하는 ``finish`` 또는 Model 재판단을 뜻하는 ``agent``입니다.
    """
    return "finish" if state.get("status") == "failed" else "agent"


def build_graph():
    """State 계약, Node와 Edge를 등록하고 실행 가능한 Graph를 만듭니다.

    Graph 구조는 ``START → openai_agent``로 시작합니다. Agent Node 뒤에는
    ``route_after_agent``를 조건부 Edge로 연결하여 Tool 요청이 있으면
    ``backend_tools``, 없으면 ``END``로 이동시킵니다. Backend Tool Node 뒤에는 항상
    Agent Node로 돌아가는 Edge를 연결해 Tool Result 기반 재판단 Loop를 만듭니다.

    Returns:
        ``invoke``할 수 있도록 compile된 LangGraph 실행 객체입니다.
    """
    builder = StateGraph(OpenAIAgentState)

    # 함수 하나를 Graph의 실행 단계 하나로 등록합니다.
    builder.add_node("openai_agent", openai_agent_node)
    builder.add_node("backend_tools", backend_tool_node)

    # Graph가 시작되면 항상 먼저 Model에게 다음 행동을 판단하게 합니다.
    builder.add_edge(START, "openai_agent")

    # Model 응답에 Tool Call이 있으면 Tool Node로, 없으면 END로 이동합니다.
    builder.add_conditional_edges(
        "openai_agent",
        route_after_agent,
        {"tools": "backend_tools", "finish": END},
    )

    # 성공한 Tool Result만 Model에 돌려주고, Backend 실패는 즉시 종료합니다.
    builder.add_conditional_edges(
        "backend_tools",
        route_after_tools,
        {"agent": "openai_agent", "finish": END},
    )
    return builder.compile()


def run(question: str, recursion_limit: int = 12) -> dict[str, Any]:
    """질문으로 Initial State를 만들고 Graph를 끝까지 실행합니다.

    ``invoke``는 START부터 END까지 Node와 Edge를 따라 동기적으로 실행합니다.
    ``recursion_limit``은 Agent와 Tool 사이의 잘못된 무한 반복을 제한하는 Graph 안전
    장치입니다. 실행이 끝나면 내부 OpenAI 응답 객체 등은 제외하고 학습자가 확인할
    질문, 상태, 종료 이유, 호출 횟수, Trace와 최종 답변만 반환합니다.

    Args:
        question: OpenAI Agent가 해결할 자연어 Goal입니다.

    Returns:
        Model 정보와 최종 상태, 실행 Trace, 호출 횟수 및 최종 답변을 담은 dict입니다.
    """
    initial_state: OpenAIAgentState = {
        "question": question,
        "trace": [],
        "llm_calls": 0,
        "tool_calls": 0,
        "status": "running",
    }
    try:
        result = build_graph().invoke(
            initial_state,
            config={"recursion_limit": recursion_limit},
        )
    except GraphRecursionError as error:
        return {
            "question": question,
            "model": OPENAI_MODEL,
            "status": "stopped",
            "termination_reason": "max_steps_exceeded",
            "llm_calls": None,
            "tool_calls": None,
            "trace": [{"stage": "max_steps_exceeded", "error": str(error)}],
            "answer": None,
        }
    return {
        "question": question,
        "model": OPENAI_MODEL,
        "status": result["status"],
        "termination_reason": result["termination_reason"],
        "llm_calls": result["llm_calls"],
        "tool_calls": result["tool_calls"],
        "trace": result["trace"],
        "answer": result.get("answer"),
    }


if __name__ == "__main__":
    print(json.dumps(run("제주 날씨에 맞는 장소를 추천해 줘."), ensure_ascii=False, indent=2))
