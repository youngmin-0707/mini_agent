"""05, 06과 선택 LangGraph 예제가 공유하는 OpenAI·Tool Backend입니다.

파일 이름의 backend는 FastAPI 웹 서버를 뜻하지 않습니다. 예제의 화면/진입점에서
분리한 공용 모듈이라는 뜻이며, Agent의 지침, Tool Schema, Model 호출, Tool 검증과
실행을 제공합니다. Agent Loop와 종료 정책은 이를 사용하는 실행 파일이 담당합니다.

주요 구성
---------
* ``INSTRUCTIONS``: 여행 AI Agent의 역할, 행동 순서와 근거 사용 규칙
* ``OPENAI_TOOLS``: 모델에 공개하는 Function Tool Schema
* ``require_openai_client``: API key를 확인하고 OpenAI client 생성
* ``parse_and_validate_call``: 모델의 Tool Call을 allowlist와 JSON 규칙으로 검증
* ``execute_openai_call``: 검증된 로컬 Tool을 실행하고 Function Call Output 생성
* ``create_initial_response``: 질문을 바탕으로 모델의 첫 판단 요청
* ``continue_after_tools``: Tool Result를 전달하여 모델의 다음 판단 요청

이 모듈 자체는 Agent Loop가 아닙니다. ``06_openai_agent_loop.py``가 이 함수들을
조합해 실제 AI Agent를 만들고, 선택 LangGraph 예제는 같은 함수들을 Graph Node에서
재사용합니다.
"""

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from travel_tools import TOOL_DEFINITIONS, TOOLS, execute_tool


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
INSTRUCTIONS = """당신은 한국 여행 AI Agent입니다.
사용자 목표를 달성하기 위해 제공된 Function Tool만 사용하세요.
날씨에 맞는 장소 추천 요청에서는 먼저 get_weather를 호출하세요.
날씨 Tool Result가 비이면 search_indoor_places를, 그렇지 않으면
search_outdoor_places를 호출하세요. Tool Result에 없는 사실을 만들지 마세요.
필요한 근거를 모두 얻었으면 추가 Tool 없이 간결한 한국어 최종 답변을 작성하세요.
최종 답변에는 Tool Result에 있는 날씨 값과 장소 이름만 사용하세요. 장소에 대한
특징·시설·활동 설명처럼 Tool Result에 없는 사실은 추측하거나 추가하지 마세요.
"""

OPENAI_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": name,
        "description": definition["description"],
        "parameters": definition["parameters"],
        "strict": True,
    }
    for name, definition in TOOL_DEFINITIONS.items()
]


def require_openai_client() -> OpenAI:
    """API key를 확인하고 Agent가 사용할 OpenAI Client를 생성합니다.

    `05`와 `06`, 선택 LangGraph 예제가 Model 호출 직전에 사용합니다. Key가 없으면
    외부 요청 전에 설정 오류를 발생시킵니다.

    Returns:
        환경변수의 인증 정보를 사용하는 OpenAI Client입니다.

    Raises:
        RuntimeError: ``OPENAI_API_KEY``가 설정되지 않은 경우입니다.
    """
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY가 필요합니다. 과정 루트의 .env에 "
            "OPENAI_API_KEY와 선택적으로 OPENAI_MODEL을 설정하세요."
        )
    return OpenAI()


def function_calls(response: Any) -> list[Any]:
    """Responses API 응답에서 Function Call 항목만 추출합니다.

    Model 응답 직후 Tool 선택 검사와 Agent Loop에서 호출합니다. 빈 목록은 Model이
    Tool 대신 최종 답변을 반환했다는 라우팅 근거가 됩니다.
    """
    return [item for item in response.output if item.type == "function_call"]


def parse_and_validate_call(call: Any) -> tuple[str, dict[str, Any]]:
    """Model의 Tool Call을 Backend가 실행 가능한 형태로 검증합니다.

    `05`에서는 표시 전, Agent Loop에서는 실행 직전에 호출합니다. Tool 이름이 Backend
    Allowlist에 있는지와 arguments가 JSON Object인지 다시 확인합니다.

    Args:
        call: OpenAI 응답의 Function Call 항목입니다.

    Returns:
        검증된 Tool 이름과 Python dict arguments입니다.

    Raises:
        ValueError: Tool 또는 arguments 계약이 잘못된 경우입니다.
    """
    if call.name not in TOOLS:
        raise ValueError(f"허용되지 않은 Tool입니다: {call.name}")
    arguments = json.loads(call.arguments)
    if not isinstance(arguments, dict):
        raise ValueError("Tool arguments는 JSON Object여야 합니다.")
    return call.name, arguments


def execute_openai_call(call: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    """Function Call을 검증·실행하고 Model 전달값과 Trace를 만듭니다.

    Python Agent Loop나 LangGraph Tool Node가 Model의 요청을 받은 뒤 호출합니다. 같은
    Result를 OpenAI용 ``function_call_output``과 관찰용 Trace 두 형식으로 반환합니다.

    Args:
        call: 실행하려는 OpenAI Function Call입니다.

    Returns:
        OpenAI에 전달할 output과 사람이 확인할 Tool Trace의 tuple입니다.
    """
    tool_name, arguments = parse_and_validate_call(call)
    result = execute_tool(tool_name, arguments)
    output = {
        "type": "function_call_output",
        "call_id": call.call_id,
        "output": json.dumps(result, ensure_ascii=False),
    }
    trace = {"tool": tool_name, "arguments": arguments, "result": result}
    return output, trace


def create_initial_response(client: OpenAI, question: str) -> Any:
    """사용자 질문으로 OpenAI Agent의 최초 판단을 요청합니다.

    `05`의 단일 선택 검사와 `06`·LangGraph Agent Loop의 첫 단계에서 호출합니다.
    Instructions와 Tool Schema를 제공하므로 Model은 Function Call이나 답변을 선택합니다.

    Args:
        client: 인증이 준비된 OpenAI Client입니다.
        question: Agent가 해결할 사용자 Goal입니다.

    Returns:
        Tool Call 또는 텍스트가 포함된 Responses API 응답입니다.
    """
    return client.responses.create(
        model=OPENAI_MODEL,
        instructions=INSTRUCTIONS,
        input=question,
        tools=OPENAI_TOOLS,
        tool_choice="auto",
        parallel_tool_calls=False,
    )

def continue_after_tools(client: OpenAI, previous_response_id: str, tool_outputs: list[dict[str, Any]]) -> Any:
    """Tool Result를 OpenAI에 전달하여 Agent의 재판단을 요청합니다.

    한 라운드의 Tool 실행 직후 호출합니다. 직전 response id와 Tool Result를 제공하여
    Model이 추가 Function Call 또는 최종 답변을 선택하게 합니다.

    Args:
        client: 인증이 준비된 OpenAI Client입니다.
        previous_response_id: Tool을 요청했던 직전 응답 ID입니다.
        tool_outputs: Function Call Output 형식의 Tool Result 목록입니다.

    Returns:
        Tool Result를 관찰한 다음 Responses API 응답입니다.
    """
    return client.responses.create(
        model=OPENAI_MODEL,
        instructions=INSTRUCTIONS,
        previous_response_id=previous_response_id,
        input=tool_outputs,
        tools=OPENAI_TOOLS,
        tool_choice="auto",
        parallel_tool_calls=False,
    )
