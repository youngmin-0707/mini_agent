"""규칙 기반 판단을 실제 OpenAI 모델의 Tool 선택으로 교체하는 중간 단계입니다.

01~04에서는 실행 순서나 다음 행동을 개발자 코드가 결정했습니다. 이번 파일부터는
사용자 질문, Agent 지침과 Tool Schema를 OpenAI 모델에 전달하고 모델이 어떤 Tool과
arguments가 필요한지 선택하게 합니다.

이번 파일에서 하는 일
----------------------
1. 공유 모듈에서 OpenAI client와 최초 Responses API 호출을 준비합니다.
2. 모델 응답 중 Function Call 항목만 추출합니다.
3. 모델이 선택한 Tool 이름과 arguments를 backend allowlist로 검증합니다.
4. 선택 결과를 출력하여 LLM이 행동을 결정했다는 사실을 관찰합니다.

중요하게도 이 파일은 Tool을 실제로 실행하지 않고 Tool Result도 모델에 돌려주지
않습니다. 따라서 완전한 Agent Loop가 아니라 LLM 기반 행동 선택 한 단계만 검사하는
예제입니다. 실제 Tool 실행과 재판단은 06에서 완성합니다.
"""

import json

from openai_agent_backend import OPENAI_MODEL, create_initial_response, function_calls, parse_and_validate_call, require_openai_client


def inspect_selection(question: str) -> dict:
    """OpenAI Model이 제안한 Tool Call을 실행하지 않고 검사합니다.

    ``__main__``에서 호출됩니다. 최초 Model 판단을 한 번 요청하고 Function Call을
    Backend 규칙으로 검증하지만 실제 Tool과 재판단 Loop는 실행하지 않습니다.

    Args:
        question: Model이 필요한 Tool을 판단할 사용자 요청입니다.

    Returns:
        Model, 선택된 Tool·arguments 또는 Tool이 없을 때의 직접 답변입니다.
    """
    client = require_openai_client()
    response = create_initial_response(client, question)
    selections = []
    for call in function_calls(response):
        tool_name, arguments = parse_and_validate_call(call)
        selections.append({"tool": tool_name, "arguments": arguments, "call_id": call.call_id})
    return {
        "question": question,
        "model": OPENAI_MODEL,
        "tool_calls": selections,
        "answer_if_no_tool": response.output_text if not selections else None,
    }


if __name__ == "__main__":
    result = inspect_selection("제주 날씨에 맞는 장소를 추천해 줘.")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("\n아직 Tool은 실행하지 않았습니다. Model이 만든 실행 제안만 확인했습니다.")
