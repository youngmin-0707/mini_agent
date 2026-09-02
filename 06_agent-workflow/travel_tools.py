"""06 Agent Workflow의 모든 예제가 공유하는 여행 mock Tool 계층입니다.

각 예제가 동일한 입력과 Tool Result를 사용하게 하여 Workflow/Agent 실행 구조의 차이에
집중하도록 만든 공용 모듈입니다. 외부 날씨·장소 API를 호출하지 않고 메모리의 고정
데이터를 반환하므로 비용과 네트워크 없이 반복 실행할 수 있습니다.

이번 파일이 제공하는 것
-----------------------
* ``get_weather``: 성공 또는 도시 없음 결과를 반환하는 읽기 전용 날씨 Tool
* ``search_indoor_places`` / ``search_outdoor_places``: 조건별 장소 검색 Tool
* ``TOOL_DEFINITIONS``: 이름·설명·입력 Schema·실행 함수를 묶은 단일 Tool 계약
* ``TOOLS``: 단일 계약에서 만든 Backend 실행 allowlist
* ``execute_tool``: Tool 이름과 arguments를 검증한 뒤 허용된 함수만 실행하는 dispatcher

이 파일은 판단하거나 다음 Tool을 선택하지 않으므로 Agent가 아닙니다. Workflow 또는
AI Agent가 선택한 행동을 실제 Python 함수로 수행하고 관찰 가능한 결과를 돌려주는
Tool 실행 계층입니다.
"""

from typing import Any

WEATHER = {"서울": {"condition": "맑음", "temperature_c": 24}, "제주": {"condition": "비", "temperature_c": 21}}
INDOOR_PLACES = {"서울": ["국립중앙박물관", "서울시립미술관"], "제주": ["제주현대미술관", "아쿠아플라넷"]}
OUTDOOR_PLACES = {"서울": ["서울숲", "북한산"], "제주": ["비자림", "성산일출봉"]}


def get_weather(city: str) -> dict[str, Any]:
    """도시의 날씨를 고정 데이터에서 조회하는 읽기 전용 Mock Tool입니다.

    Fixed·Conditional Workflow 또는 Agent가 ``get_weather`` 행동을 실행할 때 호출합니다.
    알려진 도시는 날씨 근거를, 없는 도시는 구조화된 실패를 반환합니다.

    Args:
        city: 날씨를 조회할 도시 이름입니다.

    Returns:
        성공 여부, 도시, 날씨와 Mock 출처 또는 도시 없음 오류입니다.
    """
    data = WEATHER.get(city)
    if data is None:
        return {"success": False, "error": "CITY_NOT_FOUND", "retryable": False, "city": city, "source": "mock-weather"}
    return {"success": True, "city": city, **data, "source": "mock-weather"}


def search_indoor_places(city: str) -> dict[str, Any]:
    """비 오는 날의 실내 장소 목록을 반환하는 Mock Tool입니다.

    날씨 Result가 비일 때 Workflow 규칙이나 Agent 판단에 의해 호출됩니다. 외부 검색을
    수행하지 않고 고정 장소 목록과 출처를 반환합니다.

    Args:
        city: 실내 장소를 검색할 도시 이름입니다.

    Returns:
        성공 여부, 도시, indoor category, 장소 목록과 Mock 출처입니다.
    """
    return {"success": True, "city": city, "category": "indoor", "items": INDOOR_PLACES.get(city, []), "source": "mock-places"}


def search_outdoor_places(city: str) -> dict[str, Any]:
    """비가 아닌 날의 야외 장소 목록을 반환하는 Mock Tool입니다.

    Fixed Workflow에서는 날씨와 무관하게, Conditional Workflow와 Agent에서는 날씨가
    비가 아닐 때 호출됩니다.

    Args:
        city: 야외 장소를 검색할 도시 이름입니다.

    Returns:
        성공 여부, 도시, outdoor category, 장소 목록과 Mock 출처입니다.
    """
    return {"success": True, "city": city, "category": "outdoor", "items": OUTDOOR_PLACES.get(city, []), "source": "mock-places"}


TOOL_DEFINITIONS: dict[str, dict[str, Any]] = {
    "get_weather": {
        "function": get_weather,
        "description": "도시의 현재 날씨를 조회합니다. 장소 추천 전에 먼저 사용합니다.",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string", "description": "조회할 한국 도시 이름"}},
            "required": ["city"],
            "additionalProperties": False,
        },
    },
    "search_indoor_places": {
        "function": search_indoor_places,
        "description": "비가 올 때 방문하기 좋은 실내 장소를 검색합니다.",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string", "description": "검색할 한국 도시 이름"}},
            "required": ["city"],
            "additionalProperties": False,
        },
    },
    "search_outdoor_places": {
        "function": search_outdoor_places,
        "description": "맑은 날 방문하기 좋은 야외 장소를 검색합니다.",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string", "description": "검색할 한국 도시 이름"}},
            "required": ["city"],
            "additionalProperties": False,
        },
    },
}

# Backend Allowlist도 같은 정의에서 생성하여 Model Schema와 이름이 어긋나지 않게 합니다.
TOOLS = {name: definition["function"] for name, definition in TOOL_DEFINITIONS.items()}


def execute_tool(tool_name: str, arguments: Any) -> dict[str, Any]:
    """Tool 이름과 arguments를 검증하고 Allowlist 함수만 실행합니다.

    Rule-based Agent, Tool Result Routing과 OpenAI Agent Backend가 선택한 행동을 실제
    함수로 바꾸는 시점에 호출합니다. 검증 실패도 예외 대신 구조화 Result로 반환합니다.

    Args:
        tool_name: 실행을 요청받은 Tool 이름입니다.
        arguments: Model 또는 Workflow가 만든 Tool 인자입니다.

    Returns:
        Tool 실행 Result 또는 허용·인자 검증 실패 Result입니다.
    """
    tool = TOOLS.get(tool_name)
    if tool is None:
        return {"success": False, "error": "TOOL_NOT_ALLOWED", "retryable": False}
    if not isinstance(arguments, dict):
        return {"success": False, "error": "INVALID_ARGUMENTS", "retryable": False}
    city = arguments.get("city")
    if not isinstance(city, str) or not city.strip():
        return {"success": False, "error": "INVALID_CITY", "retryable": False}
    return tool(city.strip())
