"""State를 사용하는 규칙 기반 Agent Loop를 구현합니다.

이 파일에서 Agent는 특정 객체나 함수 하나가 아니라 다음 요소를 결합한 전체 실행
구조입니다.

``Agent = Goal + State + decide() + execute_tool() + observe() + 반복 및 종료 조건``

코드에서는 ``state["goal"]``이 목표, ``state``가 현재 상태, ``decide``가 다음 행동
판단, ``execute_tool``이 행동, ``observe``가 Tool Result 관찰과 State 갱신을 담당합니다.
``run_agent``는 이 요소들을 Loop와 종료 조건으로 연결하여 Rule-based Agent를 실제로
구동하는 Runner입니다. 따라서 ``decide``나 ``run_agent`` 하나만 따로 Agent라기보다,
이 구성요소가 결합되어 동작하는 전체가 이 파일의 Agent입니다.

01과 02에서는 개발자가 작성한 Workflow가 한 방향으로 실행되었습니다. 이번 파일은
목표와 현재 State를 매 단계 다시 확인하며 ``판단(Reason) → 실행(Act) →
관찰(Observe)``을 반복하는 Agent Loop 구조를 처음 도입합니다.

이번 파일에서 하는 일
----------------------
1. ``create_state``가 목표, Tool 결과, 오류, 진행 상태와 trace를 만듭니다.
2. ``decide``가 현재 State를 보고 다음 행동, 완료 또는 중단을 선택합니다.
3. ``execute_tool``이 선택된 행동을 실행합니다.
4. ``observe``가 Tool Result를 State에 반영하여 다음 판단의 근거로 만듭니다.
5. ``run_agent``가 목표 달성, 실패 또는 최대 단계 도달까지 이 과정을 반복합니다.

구조적으로는 Agent Loop이지만 다음 행동을 정하는 주체는 Python if 문입니다. LLM이나
AI 모델이 판단하지 않으므로 이 예제는 AI Agent가 아니라 Rule-based/Mock Agent입니다.
06에서는 이 ``decide`` 역할을 OpenAI 모델이 수행하도록 교체합니다.
"""

from typing import Any
from travel_tools import execute_tool

MAX_STEPS = 5


def create_state(city: str) -> dict[str, Any]:
    """Rule-based Agent Loop가 사용할 최초 State를 생성합니다.

    ``run_agent``가 Loop에 진입하기 전에 한 번 호출합니다. 이후 ``observe``가 같은
    State를 갱신하고 ``decide``가 다음 행동의 근거로 사용합니다.

    Args:
        city: Agent가 처리할 도시 이름입니다.

    Returns:
        Goal, 관찰 결과, 진행 상태, 오류와 Trace를 담은 mutable State입니다.
    """
    # None은 아직 검색하지 않음, []는 검색했지만 결과 없음이라는 서로 다른 상태입니다.
    return {"goal": f"{city} 날씨에 맞는 장소 추천", "city": city, "weather": None, "places": None, "completed_actions": [], "status": "running", "termination_reason": None, "step": 0, "errors": [], "trace": []}


def decide(state: dict[str, Any]) -> dict[str, Any]:
    """현재 State를 읽고 다음 행동이나 종료를 규칙으로 결정합니다.

    ``run_agent``의 매 Loop 시작 시 호출됩니다. 날씨 조회, 실패 중단, 장소 검색 또는
    완료 중 하나를 선택하며 실제 LLM 판단 자리를 Python if 문으로 모사합니다.

    Args:
        state: 직전 Tool Result까지 반영된 Agent State입니다.

    Returns:
        다음 ``action``과 판단 근거인 ``reason_code``입니다.
    """
    if state["weather"] is None:
        return {"action": "get_weather", "reason_code": "WEATHER_REQUIRED"}
    if not state["weather"].get("success"):
        return {"action": "stop", "reason_code": "WEATHER_TOOL_FAILED"}
    if state["errors"]:
        return {"action": "stop", "reason_code": "TOOL_FAILED"}
    if state["places"] is None:
        action = "search_indoor_places" if state["weather"]["condition"] == "비" else "search_outdoor_places"
        return {"action": action, "reason_code": "PLACE_SEARCH_REQUIRED"}
    return {"action": "finish", "reason_code": "GOAL_COMPLETED"}


def observe(state: dict[str, Any], action: str, result: dict[str, Any]) -> None:
    """실행한 Tool Result를 다음 판단에 사용할 State로 반영합니다.

    ``run_agent``가 Tool을 실행한 직후 호출합니다. 날씨나 장소 결과, 완료 행동과 실패를
    누적하며 State를 직접 변경하므로 별도 반환값은 없습니다.

    Args:
        state: 갱신할 현재 Agent State입니다.
        action: 방금 실행한 Tool 이름입니다.
        result: Tool이 반환한 구조화된 Result입니다.
    """
    if action == "get_weather":
        state["weather"] = result
    elif action in {"search_indoor_places", "search_outdoor_places"}:
        state["places"] = result.get("items", [])
    state["completed_actions"].append(action)
    if not result.get("success"):
        state["errors"].append(result)


def run_agent(city: str) -> dict[str, Any]:
    """판단·실행·관찰을 완료 또는 제한까지 반복합니다.

    ``__main__``에서 호출됩니다. State 생성 후 매 단계 ``decide``를 호출하고 Tool
    행동이면 실행·관찰합니다. 완료·실패 또는 최대 단계 도달 시 최종 State를 반환합니다.

    Args:
        city: Agent가 처리할 도시 이름입니다.

    Returns:
        관찰 결과, 상태, 종료 이유, 오류와 전체 Trace가 들어 있는 State입니다.
    """
    state = create_state(city)
    for step in range(1, MAX_STEPS + 1):
        state["step"] = step
        decision = decide(state)
        action = decision["action"]
        state["trace"].append({"step": step, "stage": "reason", **decision})
        if action == "finish":
            state["status"] = "completed"
            state["termination_reason"] = "completed"
            return state
        if action == "stop":
            state["status"] = "stopped"
            state["termination_reason"] = decision["reason_code"].lower()
            return state
        result = execute_tool(action, {"city": state["city"]})
        state["trace"].append({"step": step, "stage": "act_and_observe", "tool": action, "result": result})
        observe(state, action, result)
    state["status"] = "stopped"
    state["termination_reason"] = "max_steps_exceeded"
    return state


if __name__ == "__main__":
    result = run_agent("제주")
    print("목표:", result["goal"])
    print("날씨:", result["weather"])
    print("장소:", result["places"])
    print("상태:", result["status"])
    print("종료 이유:", result["termination_reason"])
    print("실행 Trace:")
    for event in result["trace"]:
        print("-", event)
