"""Tool Result가 다음 행동과 종료를 바꾸는 라우팅을 집중적으로 살펴봅니다.

이 파일은 Agent를 이용하는 예제가 아니라, Tool Result를 Python 규칙으로 확인하여
다음 행동을 선택하는 Conditional Workflow에 가깝습니다. ``weather``, ``decision``,
``places``와 ``trace`` 같은 실행 데이터는 있지만, 목표와 전체 State를 다시 확인하며
판단·실행·관찰을 반복하는 Agent Loop는 없습니다.

03의 Agent Loop 안에도 Tool Result 기반 분기가 포함되어 있습니다. 이번 파일은 전체
Loop보다 ``관찰한 결과 → 다음 행동 선택`` 관계에 집중할 수 있도록 그 부분을 떼어
제주, 서울, 없는 도시라는 서로 다른 입력으로 비교합니다.

이번 파일에서 하는 일
----------------------
1. 날씨 Tool을 먼저 실행하여 성공 여부와 날씨 조건을 얻습니다.
2. 실패하면 근거 부족으로 중단합니다.
3. 비가 오면 실내 장소 Tool, 그 외에는 야외 장소 Tool로 라우팅합니다.
4. 각 Tool Result와 결정 이유를 trace에 남깁니다.

이 파일은 정해진 두 단계만 실행하며 반복 State Loop가 없습니다. 또한 라우팅 판단도
개발자의 if 문이 수행합니다. 즉, 새로운 AI Agent 구현이 아니라 03에서 사용한
Tool-result routing과 안전한 종료 조건을 별도로 연습하는 예제입니다.
"""

from typing import Any
from travel_tools import execute_tool


def choose_place_tool(weather_result: dict[str, Any]) -> dict[str, str]:
    """날씨 Tool Result를 장소 Tool 또는 중단 경로로 변환합니다.

    ``run``이 날씨를 조회한 직후 한 번 호출합니다. Agent가 판단하는 것이 아니라
    개발자가 작성한 Python 규칙이 다음 Tool을 선택합니다. 결정적 Router이므로 LLM
    판단이나 반복적인 Agent Loop를 수행하지 않습니다.

    Args:
        weather_result: 날씨 조회의 성공 여부와 condition을 담은 Result입니다.

    Returns:
        선택한 ``action``과 선택 근거인 ``reason``입니다.
    """
    if not weather_result.get("success"):
        return {"action": "stop", "reason": "missing_weather_evidence"}
    if weather_result["condition"] == "비":
        return {"action": "search_indoor_places", "reason": "rain_detected"}
    return {"action": "search_outdoor_places", "reason": "clear_weather_detected"}


def run(city: str) -> dict[str, Any]:
    """한 도시의 날씨 Result에 따른 다음 행동과 종료를 실행합니다.

    ``__main__``에서 각 도시에 대해 호출됩니다. 날씨 Tool, 규칙 Router, 선택된 장소
    Tool 순서로 실행하며 날씨 근거가 없으면 장소 Tool 없이 중단합니다.

    Args:
        city: 라우팅 차이를 확인할 도시 이름입니다.

    Returns:
        날씨·장소 결과, 선택한 행동, 종료 이유와 Trace입니다.
    """
    trace = []
    weather = execute_tool("get_weather", {"city": city})
    trace.append({"stage": "tool_result", "tool": "get_weather", "data": weather})
    decision = choose_place_tool(weather)
    trace.append({"stage": "routing_decision", **decision})
    if decision["action"] == "stop":
        return {"city": city, "weather": weather, "places": [], "selected_action": "stop", "status": "stopped", "termination_reason": decision["reason"], "trace": trace}
    places = execute_tool(decision["action"], {"city": city})
    trace.append({"stage": "tool_result", "tool": decision["action"], "data": places})
    return {"city": city, "weather": weather, "places": places["items"], "selected_action": decision["action"], "status": "completed", "termination_reason": "completed", "trace": trace}


if __name__ == "__main__":
    for city in ("제주", "서울", "없는도시"):
        result = run(city)
        print(f"\n도시: {city}")
        print("날씨:", result["weather"])
        print("다음 행동:", result["selected_action"])
        print("장소:", result["places"])
        print("종료 이유:", result["termination_reason"])
