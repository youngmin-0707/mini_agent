# 선택 학습 · 같은 OpenAI Agent를 LangGraph로 구현

이 예제는 `06_openai_agent_loop.py`와 동일한 OpenAI Model, instructions, Function Tool Schema와 mock Tool을 사용합니다. Function Call이 없으면 종료한다는 기본 조건도 같지만, 반복 제한과 오류를 상태로 변환하는 방식은 Python Loop와 LangGraph 예제에서 다릅니다.

```text
순수 Python OpenAI Agent
while → OpenAI Model → Function Call → Backend Tool → Result → Model

LangGraph 안의 OpenAI Agent
OpenAI Agent Node → Backend Tool Node → OpenAI Agent Node → END
```

| Agent 개념 | 순수 Python | LangGraph |
| --- | --- | --- |
| 실행 정보 | `state` 딕셔너리 | Graph State |
| Model 판단 | Responses API 호출 | OpenAI Agent Node |
| Tool 제안 | `function_call` | Agent Node 출력 |
| Tool 실행 | Python Loop 내부 | Backend Tool Node |
| Result 전달 | `function_call_output` | Tool Node에서 State 갱신 |
| 반복 | `for`·`while` | Edge로 Agent Node 복귀 |
| 종료 | Function Call 없음 | Conditional Edge → END |

```powershell
python .\10_optional_langgraph\01_same_openai_agent_with_langgraph.py
```

LangGraph가 Agent 판단을 대신하지 않습니다. `openai_agent_node()` 안의 OpenAI Model이 Tool과 종료를 선택하고, LangGraph는 State와 Node 이동을 관리합니다. `backend_tool_node()`는 Allowlist와 arguments를 검증한 뒤 실제 Tool을 실행합니다.

## 이 예제 State의 범위

이 코드는 순수 Python Loop와 Graph 구조를 쉽게 비교하기 위한 메모리 내 입문 예제입니다. 그래서 OpenAI 응답 객체를 그대로 State에 저장합니다.

운영 환경에서 Checkpoint와 영속화를 적용한다면 State에는 `previous_response_id`, Tool Result, 현재 단계와 같은 직렬화 가능한 구조화 데이터를 저장하도록 다시 설계해야 합니다. 이 예제의 State를 그대로 운영용 영속 State로 사용하지 않습니다.

Checkpoint와 사용자 승인 후 재개는 `07_human-approval-and-safety/10_optional_langgraph`에서 비교합니다. Reducer 심화, Streaming, Subgraph, Supervisor와 운영용 Checkpointer는 이 과정에서 다루지 않습니다.
