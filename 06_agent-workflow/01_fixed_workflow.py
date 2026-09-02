"""06 Agent Workflow의 출발점: 순서가 고정된 일반 Workflow입니다.

이 장은 ``고정 Workflow → 조건부 Workflow → 규칙 기반 Agent Loop →
LLM Tool 선택 → LLM 기반 AI Agent Loop`` 순서로 실행 구조를 확장합니다.

이번 파일에서 하는 일
----------------------
1. 개발자가 미리 정한 순서대로 날씨 Tool과 야외 장소 Tool을 호출합니다.
2. 각 단계의 결과를 trace에 기록합니다.
3. 날씨 결과가 다음 행동에 영향을 주지 않는 고정 Workflow의 특징을 확인합니다.

제주에 비가 와도 두 번째 행동은 항상 ``search_outdoor_places``입니다. 즉, Tool을
사용하지만 실행 중 판단하거나 경로를 변경하지 않습니다. 따라서 이 파일은 Agent나
AI Agent가 아니라, 이후 예제와 비교하기 위한 가장 단순한 Workflow입니다.
"""

from travel_tools import get_weather, search_outdoor_places


def run_workflow(city: str) -> dict:
    """개발자가 정한 두 Tool을 고정된 순서로 한 번씩 실행합니다.

    이 파일을 직접 실행할 때 ``__main__``에서 호출됩니다. 먼저 날씨를 조회하지만
    Result를 분기 조건으로 사용하지 않고 항상 야외 장소를 검색합니다.

    Args:
        city: 날씨와 장소를 조회할 도시 이름입니다.

    Returns:
        날씨·장소 Result, 완료 상태, 종료 이유와 단계별 Trace입니다.
    """
    trace = []
    weather = get_weather(city)
    trace.append({"step": 1, "action": "get_weather", "result": weather})
    # 비가 와도 다음 단계는 항상 야외 장소 검색으로 고정되어 있습니다.
    places = search_outdoor_places(city)
    trace.append({"step": 2, "action": "search_outdoor_places", "result": places})
    return {"type": "fixed_workflow", "city": city, "weather": weather, "places": places, "status": "completed", "termination_reason": "fixed_steps_completed", "trace": trace}


if __name__ == "__main__":
    result = run_workflow("제주")
    print("날씨:", result["weather"])
    print("추천 장소:", result["places"]["items"])
    print("종료 이유:", result["termination_reason"])
    print("\n비가 와도 야외 장소를 검색합니다. 다음 단계가 코드에 고정된 Workflow이기 때문입니다.")
