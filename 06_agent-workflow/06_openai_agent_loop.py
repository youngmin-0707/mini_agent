"""앞선 개념을 결합한 실제 OpenAI 기반 AI Agent Loop의 실행 진입점입니다.

이 장은 고정 Workflow, 조건 분기, State 기반 반복, Tool Result routing, LLM의 Tool
선택을 차례로 학습했습니다. 이번 파일은 이 요소들을 결합한 최종 필수 예제로,
OpenAI 모델이 목표와 Tool Result를 보고 다음 행동 또는 최종 답변을 결정합니다.

실행 흐름
---------
사용자 질문 → LLM 판단 → Tool Call → backend의 검증과 Tool 실행 → Tool Result 전달
→ LLM 재판단 → 추가 Tool Call 또는 최종 답변

이 파일의 ``run_openai_agent``가 State, 반복, 오류 처리와 종료 조건을 결합한 실제
AI Agent Loop입니다. ``openai_agent_backend.py``는 이 Loop가 공유하는 Agent 지침,
Tool Schema, OpenAI 호출과 안전한 Tool 실행 함수만 제공합니다.
"""

import json
import sys
from typing import Any

from openai_agent_backend import (
    OPENAI_MODEL,
    continue_after_tools,
    create_initial_response,
    execute_openai_call,
    function_calls,
    require_openai_client,
)


MAX_STEPS = 6


def run_openai_agent(question: str, max_steps: int = MAX_STEPS) -> dict[str, Any]:
    """OpenAI 판단과 Backend Tool 실행을 완료 또는 제한까지 반복합니다.

    이 파일의 ``__main__``에서 호출되는 실제 AI Agent Loop입니다. 최초 판단 이후
    Function Call 검증·실행, Result 전달과 재판단을 반복합니다. 최종 답변, 오류 또는
    반복 제한을 구조화된 상태와 Trace로 반환합니다.

    정상적인 반복과 종료 예시는 다음과 같습니다.

    ``1회차 LLM → get_weather 요청``
    ``Tool 실행 → 제주, 비``

    ``2회차 LLM → search_indoor_places 요청``
    ``Tool 실행 → 제주현대미술관, 아쿠아플라넷``

    ``3회차 LLM → Tool Call 없음``
    ``최종 답변 → '제주는 비가 오므로 ...' → return``

    즉, for 문은 Model이 Function Call을 반환하는 동안 Tool 실행과 재호출을 이어갑니다.
    Model이 Function Call 없이 최종 텍스트를 반환하면 ``function_calls(response)``가
    빈 목록이 되고, ``completed`` 상태와 최종 답변을 저장한 뒤 즉시 return합니다.

    비정상 상황에서는 다음과 같이 종료합니다.

    ``Model 호출 실패``
    ``→ status=failed → termination_reason=model_error → return``

    ``Model이 Allowlist에 없거나 잘못된 arguments의 Tool Call 생성``
    ``→ status=failed → termination_reason=invalid_tool_call → return``

    ``검증된 Tool의 실제 실행 중 예외 발생``
    ``→ status=failed → termination_reason=tool_error → return``

    ``최대 Tool 실행 라운드 이후에도 Model이 추가 Tool Call 요청``
    ``→ 추가 Tool은 실행하지 않음 → status=stopped``
    ``→ termination_reason=max_steps_exceeded → return``

    오류 상황은 같은 행동을 무의미하게 반복하지 않고 즉시 반환합니다. 최대 반복 초과는
    시스템 오류라기보다 무한 Loop를 막기 위한 안전 중단이므로 ``failed``가 아니라
    ``stopped``로 구분합니다. 모든 경우에 오류 또는 대기 Tool을 Trace에 기록합니다.

    Args:
        question: Agent가 해결할 자연어 Goal입니다.
        max_steps: 허용할 최대 Tool 실행 라운드 수입니다.

    Returns:
        상태, 종료 이유, 호출 횟수, Trace와 최종 답변을 담은 dict입니다.
    """
    client = require_openai_client()
    state: dict[str, Any] = {
        "goal": question,
        "model": OPENAI_MODEL,
        "status": "running",
        "termination_reason": None,
        "llm_calls": 0,
        "tool_calls": 0,
        "trace": [],
        "answer": None,
    }

    try:
        response = create_initial_response(client, question)
    except Exception as error:
        state["status"] = "failed"
        state["termination_reason"] = "model_error"
        state["trace"].append({"step": 0, "stage": "model_error", "error": str(error)})
        return state
    state["llm_calls"] += 1

    for step in range(1, max_steps + 1):
        calls = function_calls(response)
        if not calls:
            state["status"] = "completed"
            state["termination_reason"] = "model_finished"
            state["answer"] = response.output_text
            state["trace"].append(
                {"step": step, "stage": "model_final_answer", "text": response.output_text}
            )
            return state

        tool_outputs = []
        for call in calls:
            try:
                output, tool_trace = execute_openai_call(call)
            except (AttributeError, json.JSONDecodeError, TypeError, ValueError) as error:
                state["status"] = "failed"
                state["termination_reason"] = "invalid_tool_call"
                state["trace"].append(
                    {
                        "step": step,
                        "stage": "invalid_tool_call",
                        "tool": getattr(call, "name", None),
                        "error": str(error),
                    }
                )
                return state
            except Exception as error:
                state["status"] = "failed"
                state["termination_reason"] = "tool_error"
                state["trace"].append(
                    {
                        "step": step,
                        "stage": "tool_error",
                        "tool": getattr(call, "name", None),
                        "error": str(error),
                    }
                )
                return state
            state["tool_calls"] += 1
            state["trace"].append({"step": step, "stage": "model_tool_call", **tool_trace})
            tool_outputs.append(output)

        try:
            response = continue_after_tools(client, response.id, tool_outputs)
        except Exception as error:
            state["status"] = "failed"
            state["termination_reason"] = "model_error"
            state["trace"].append({"step": step, "stage": "model_error", "error": str(error)})
            return state
        state["llm_calls"] += 1

    # 마지막 Tool Result 뒤의 Model 응답도 확인합니다. 최종 답변이면 정상 완료하고,
    # 또 다른 Tool Call이면 실행하지 않은 채 반복 제한으로 안전하게 중단합니다.
    remaining_calls = function_calls(response)
    if not remaining_calls:
        state["status"] = "completed"
        state["termination_reason"] = "model_finished"
        state["answer"] = response.output_text
        state["trace"].append(
            {"step": max_steps + 1, "stage": "model_final_answer", "text": response.output_text}
        )
        return state

    state["status"] = "stopped"
    state["termination_reason"] = "max_steps_exceeded"
    state["trace"].append(
        {
            "step": max_steps + 1,
            "stage": "max_steps_exceeded",
            "pending_tools": [call.name for call in remaining_calls],
        }
    )
    return state


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "제주 날씨에 맞는 장소를 추천해 줘."
    result = run_openai_agent(question)
    print(json.dumps(result, ensure_ascii=False, indent=2))
