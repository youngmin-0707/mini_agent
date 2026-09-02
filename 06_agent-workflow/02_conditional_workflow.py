"""고정 Workflow에 개발자 규칙에 의한 조건 분기를 추가합니다.

전체 학습 흐름에서 이 파일은 01의 고정 실행과 03의 반복 Agent Loop 사이에 있습니다.
실행 순서를 전부 고정하는 대신 날씨 Tool Result를 확인하여 실내 또는 야외 장소
Tool로 이동합니다.

이번 파일에서 하는 일
----------------------
1. ``run_workflow``로 항상 야외 장소를 찾는 고정 Workflow를 다시 실행합니다.
2. ``choose_action_by_rule``에서 날씨 결과를 Python if 문으로 판정합니다.
3. ``run_conditional_workflow``에서 판정 결과에 따라 다음 Tool을 선택합니다.
4. 두 결과를 나란히 출력하여 고정 순서와 조건부 라우팅을 비교합니다.

분기는 생겼지만 판단 주체는 LLM이 아니라 개발자가 작성한 규칙이며, 판단과 행동을
반복하는 Loop도 없습니다. 따라서 아직 AI Agent가 아니라 Conditional Workflow입니다.
"""

from travel_tools import get_weather, search_indoor_places, search_outdoor_places


def run_workflow(city: str) -> dict:
    """비교 기준이 되는 고정 Workflow를 실행합니다.

    ``__main__``에서 Conditional Workflow보다 먼저 호출됩니다. 날씨와 관계없이 야외
    장소 Tool을 실행하여 이후 규칙 기반 분기 결과와 비교할 기준을 만듭니다.

    Args:
        city: 조회할 도시 이름입니다.

    Returns:
        판단 주체, 날씨·장소 Result와 선택한 행동입니다.
    """
    weather = get_weather(city)
    places = search_outdoor_places(city)
    return {"decision_maker": "developer", "weather": weather, "places": places, "selected_action": "search_outdoor_places"}


def choose_action_by_rule(weather_result: dict) -> str:
    """날씨 Tool Result를 개발자 규칙으로 다음 행동 이름에 변환합니다.

    ``run_conditional_workflow``가 날씨를 조회한 직후 호출합니다. 조회가 실패하면
    ``stop``, 비이면 실내 검색, 그 외에는 야외 검색을 반환합니다.

    Args:
        weather_result: ``get_weather``가 반환한 성공 여부와 날씨 정보입니다.

    Returns:
        실행할 장소 Tool 이름 또는 중단을 뜻하는 ``stop``입니다.
    """
    if not weather_result.get("success"):
        return "stop"
    return "search_indoor_places" if weather_result["condition"] == "비" else "search_outdoor_places"


def run_conditional_workflow(city: str) -> dict:
    """날씨 Result에 따라 서로 다른 장소 Tool로 분기합니다.

    ``__main__``에서 고정 Workflow 다음에 호출됩니다. 날씨 조회 후 규칙 함수에 판단을
    위임하고 해당 Tool 하나를 실행합니다. 한 번 분기한 뒤 종료하므로 Agent Loop는 아닙니다.

    Args:
        city: 날씨와 장소를 조회할 도시 이름입니다.

    Returns:
        판단 주체, Tool Result와 선택한 행동입니다.
    """
    weather = get_weather(city)
    action = choose_action_by_rule(weather)
    if action == "search_indoor_places":
        places = search_indoor_places(city)
    elif action == "search_outdoor_places":
        places = search_outdoor_places(city)
    else:
        places = {"success": False, "error": "WEATHER_EVIDENCE_REQUIRED", "items": []}
    return {"decision_maker": "developer_rule", "weather": weather, "places": places, "selected_action": action}


if __name__ == "__main__":
    workflow = run_workflow("제주")
    conditional = run_conditional_workflow("제주")
    print("Workflow 선택:", workflow["selected_action"], workflow["places"]["items"])
    print("Conditional Workflow 선택:", conditional["selected_action"], conditional["places"]["items"])
    print("\n차이는 Tool 개수가 아니라 다음 행동을 언제, 어떤 근거로 선택하는가입니다.")
