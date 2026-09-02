# 기존 Tool-calling Agent와 State 기반 AI Agent Loop 비교

이 문서의 핵심은 MCP와 일반 Python Tool의 차이가 아닙니다. **이전에 구현한 단순한 Tool-calling Agent와 이번 장에서 설계한 State 기반 AI Agent Loop가 무엇이 다르고, 왜 실행 구조가 달라졌는가**를 설명합니다.

```text
이전 Agent
= LLM이 필요한 Tool들을 선택
+ Tool을 모두 실행
+ Result를 LLM에 한 번 전달
+ 최종 답변

이번 Agent
= Goal과 실행 State
+ LLM의 다음 행동 판단
+ Tool 실행과 Result 관찰
+ 반복적인 LLM 재판단
+ 명시적인 완료·실패·안전 중단
```

두 구현 모두 LLM이 Tool을 선택하므로 넓은 의미에서는 AI Agent라고 볼 수 있습니다. 차이는 “AI Agent인가 아닌가”보다 **어느 정도까지 실행 상태와 반복을 애플리케이션이 명시적으로 관리하는가**에 있습니다.

## 1. 이전에 만든 Agent의 구조

이전 Agent의 대표적인 흐름은 다음과 같습니다.

```text
사용자 질문
  ↓
LLM 1회차 호출
  ↓
필요한 Tool Call 목록 생성
  ↓
선택된 Tool을 모두 실행
  ↓
모든 Tool Result를 LLM에 전달
  ↓
LLM 2회차 호출
  ↓
최종 답변 반환
```

코드 구조로 단순화하면 다음과 같습니다.

```python
response = call_llm(question, tools)
tool_calls = find_tool_calls(response)

tool_outputs = []
for call in tool_calls:
    result = execute_tool(call)
    tool_outputs.append(result)

final_response = call_llm(tool_outputs)
return final_response.output_text
```

이 구조의 중요한 특징은 **실행 순서가 두 번의 Model 호출로 거의 고정되어 있다는 것**입니다.

```text
첫 번째 LLM 호출 = 필요한 Tool 선택
두 번째 LLM 호출 = Tool Result를 종합한 최종 답변
```

첫 LLM 응답에서 날씨와 호텔 Tool을 동시에 선택할 수 있고, 각 Tool Result가 다른 Tool 선택에 영향을 주지 않는다면 이 구조로 충분합니다.

### 이전 Agent에도 상태는 있었다

이전 구현에 `state = {...}`가 없었다고 해서 상태가 없었던 것은 아닙니다. 다음 지역 변수가 실행 상태 역할을 했습니다.

```text
question       사용자 Goal
response       첫 번째 Model 판단
tool_calls     Model이 선택한 행동 목록
tool_outputs   Tool 실행 결과
final_response 최종 Model 답변
trace          실행한 Tool 기록
```

다만 이 정보가 하나의 State 계약으로 묶이지 않고 함수의 지역 변수와 OpenAI 응답 객체에 나뉘어 있었습니다. 이를 **암묵적 또는 분산된 실행 상태**라고 설명할 수 있습니다.

### 이전 구조가 적합한 경우

- 필요한 Tool들을 첫 판단에서 모두 선택할 수 있습니다.
- Tool들이 서로의 Result에 의존하지 않습니다.
- Tool 실행 이후 추가 Tool 선택이 필요하지 않습니다.
- 실행이 짧고 중단·재개가 필요하지 않습니다.
- 성공 결과와 간단한 예외만 구분하면 충분합니다.
- 실행 과정을 외부 서비스에서 계속 조회할 필요가 없습니다.

이 조건에서는 별도의 큰 State와 반복 Loop를 추가하는 것이 오히려 코드를 복잡하게 만들 수 있습니다.

## 2. 이전 Agent의 제한

다음 요청을 생각해 봅니다.

```text
제주 날씨를 확인하고 날씨에 맞는 장소를 추천해 줘.
```

어떤 장소 Tool을 호출할지는 날씨 Result를 보기 전에는 결정할 수 없습니다.

```text
날씨가 비
→ search_indoor_places 필요

날씨가 맑음
→ search_outdoor_places 필요
```

따라서 실행 흐름이 다음처럼 바뀝니다.

```text
LLM 1회차
→ get_weather 선택

Tool Result
→ 제주, 비

LLM 2회차
→ Result를 보고 search_indoor_places 선택

Tool Result
→ 제주현대미술관, 아쿠아플라넷

LLM 3회차
→ 추가 Tool이 필요 없다고 판단
→ 최종 답변
```

이 경우에는 “Tool을 한꺼번에 실행한 뒤 LLM을 한 번 더 호출”하는 고정 구조로 충분하지 않습니다. **이전 Tool Result를 관찰한 후 다음 Tool을 새로 선택하는 과정**이 필요합니다.

또한 다음 질문에도 답해야 합니다.

- LLM이 Tool을 계속 요청하면 언제 멈추는가?
- Model 호출이 실패하면 어떤 상태로 끝나는가?
- 잘못된 Tool 이름이나 arguments를 만들면 어떻게 처리하는가?
- 실제 Tool 실행이 실패하면 재시도하는가, 중단하는가?
- 최종 답변 없이 반복 제한에 도달하면 어떻게 표시하는가?
- 지금까지 Model과 Tool을 몇 번 호출했는가?
- 어떤 순서로 판단하고 실행했는가?

이번 Agent는 이 문제를 명시적으로 관리하기 위해 State와 반복 종료 정책을 도입합니다.

## 3. 이번에 만든 Agent의 구조

이번 장의 실제 AI Agent는 `06_openai_agent_loop.py`의 `run_openai_agent()`입니다.

```text
Agent
= Goal
+ State
+ LLM 판단
+ Tool 검증과 실행
+ Tool Result 관찰
+ 반복
+ 완료·실패·안전 중단 조건
```

전체 흐름은 다음과 같습니다.

```text
Initial State 생성
  ↓
LLM 최초 판단
  ↓
Function Call이 있는가?
  ├─ 없음 → 최종 답변 저장 → completed → return
  │
  └─ 있음
       ↓
     Tool Call 검증
       ↓
     Tool 실행
       ↓
     Tool Result와 Trace 기록
       ↓
     Result를 LLM에 전달
       ↓
     LLM 재판단
       └────────────── 반복
```

정상 실행 예시는 다음과 같습니다.

```text
1회차 LLM → get_weather 요청
Tool 실행 → 제주, 비

2회차 LLM → search_indoor_places 요청
Tool 실행 → 제주현대미술관, 아쿠아플라넷

3회차 LLM → Function Call 없음
최종 답변 → completed → return
```

핵심은 LLM 호출 횟수가 처음부터 두 번으로 고정되지 않는다는 것입니다. Model이 Goal을 달성했다고 판단하여 Function Call 없이 최종 답변을 반환할 때까지 필요한 만큼 반복합니다. 애플리케이션은 무한 반복을 막기 위해 최대 Tool 실행 라운드를 제한합니다.

## 4. 이번 Agent의 State

`run_openai_agent()`는 다음 State를 명시적으로 관리합니다.

```python
state = {
    "goal": question,
    "model": OPENAI_MODEL,
    "status": "running",
    "termination_reason": None,
    "llm_calls": 0,
    "tool_calls": 0,
    "trace": [],
    "answer": None,
}
```

각 항목의 역할은 다음과 같습니다.

| State | 역할 |
| --- | --- |
| `goal` | Agent가 달성해야 하는 사용자 요청 |
| `model` | 실행에 사용한 Model 식별 |
| `status` | 현재 실행 상태: `running`, `completed`, `failed`, `stopped` |
| `termination_reason` | 완료·실패·중단의 구체적인 이유 |
| `llm_calls` | Model 호출 횟수 |
| `tool_calls` | 실제 Tool 실행 횟수 |
| `trace` | 판단, Tool 실행, 오류와 종료의 순서 |
| `answer` | 정상 완료된 최종 답변 |

### State가 모든 데이터를 담는 것은 아니다

현재 예제에서는 OpenAI `response`, 현재 `calls`와 `tool_outputs`는 지역 변수로 관리합니다. 즉, 이번 구현도 모든 정보를 영속 State에 넣은 완전한 Workflow Runtime은 아닙니다.

```text
명시적인 운영 State
└─ 상태, 종료 이유, 호출 횟수, Trace, 최종 답변

한 실행 안의 임시 제어 데이터
└─ response, calls, tool_outputs
```

이 구분은 교육 예제를 단순하게 유지하면서도 Agent 실행을 관찰하고 통제하기 위한 것입니다. 이후 실행 중단과 재개가 필요하면 `response.id`, 대기 중인 Tool Call, 승인 대상 같은 값도 저장 가능한 State로 설계해야 합니다.

### OpenAI가 관리하는 대화 연결 상태

Tool Result 이후 다음 Model 호출은 `previous_response_id`로 직전 응답과 연결됩니다.

```python
continue_after_tools(
    client,
    previous_response_id=response.id,
    tool_outputs=tool_outputs,
)
```

따라서 상태는 두 층으로 나뉩니다.

```text
OpenAI Responses API
└─ 이전 Model 응답과 다음 호출의 대화 연결

Python Agent State
└─ 애플리케이션의 상태, 종료 이유, 호출 횟수, Trace와 답변
```

`previous_response_id`가 있다고 해서 애플리케이션의 운영 State가 자동으로 완성되는 것은 아닙니다. 반대로 State dict가 있다고 해서 Model의 대화 Context가 자동으로 이어지는 것도 아닙니다.

## 5. 두 Agent의 핵심 비교

| 기준 | 이전 단순 Tool-calling Agent | 이번 State 기반 Agent Loop |
| --- | --- | --- |
| 핵심 목적 | Tool 선택·실행·결과 종합 | Result를 보고 다음 행동을 반복 결정 |
| LLM 호출 흐름 | 보통 최초 판단 + 최종 답변 | 완료까지 동적 반복 |
| Tool 선택 | 첫 응답에서 필요한 Tool들을 선택 | 각 Result 이후 다음 Tool을 새로 선택 가능 |
| Tool 사이 의존성 | 서로 독립적인 경우에 적합 | 앞 Tool Result가 다음 행동을 바꾸는 경우 적합 |
| 실행 상태 | 지역 변수와 응답에 분산 | 운영 State dict로 명시 |
| 완료 판단 | 두 번째 응답 반환 | Function Call이 없을 때 완료 |
| 반복 제한 | Loop가 없으므로 불필요 | `MAX_STEPS`로 제한 |
| 오류 표현 | 주로 예외 발생 | `status`와 `termination_reason`으로 구조화 |
| Trace | Tool 실행 중심 | 단계, Tool, 오류와 종료까지 기록 |
| 호출 횟수 | 대체로 고정값 | 실제 호출할 때마다 누적 |
| 중단·재개 확장 | 별도 설계 필요 | 명시적 State를 확장하여 연결 가능 |
| 평가 | 최종 답변과 Tool 결과 확인 | 경로, 반복, 종료 이유까지 평가 가능 |

## 6. 판단 주체는 무엇이 달라졌는가?

두 Agent 모두 다음 행동 또는 Tool을 고르는 주체는 LLM입니다.

```text
이전 Agent
LLM이 첫 응답에서 필요한 Tool 목록 선택

이번 Agent
LLM이 매 Result 이후 다음 Tool 또는 종료 선택
```

이번 Agent에서 Python의 `for` 문이 Tool을 선택하는 것은 아닙니다. `for` 문은 **LLM에게 다시 판단할 기회를 제공하고 반복 횟수를 제한하는 실행 통제 구조**입니다.

```text
LLM
└─ 무엇을 할지 판단

Python Agent Loop
└─ 판단 → 검증 → 실행 → 관찰 → 재판단 순서와 한도를 통제

Backend
└─ Model이 요청한 Tool을 실제로 실행해도 되는지 검증
```

## 7. 정상 종료와 비정상 종료

### 정상 종료

Model이 Function Call 없이 최종 텍스트를 반환하면 목표를 달성한 것으로 처리합니다.

```text
function_calls(response) == []
→ status = completed
→ termination_reason = model_finished
→ answer 저장
→ return
```

### Model 호출 실패

```text
OpenAI 요청 중 예외
→ status = failed
→ termination_reason = model_error
→ return
```

### 잘못된 Tool Call

```text
Allowlist에 없는 Tool
또는 잘못된 JSON arguments
→ status = failed
→ termination_reason = invalid_tool_call
→ return
```

### Tool 실행 실패

```text
검증을 통과한 Tool의 실행 중 예외
→ status = failed
→ termination_reason = tool_error
→ return
```

### 최대 반복 초과

```text
최대 Tool 실행 라운드 이후에도 추가 Tool Call 요청
→ 추가 Tool은 실행하지 않음
→ status = stopped
→ termination_reason = max_steps_exceeded
→ return
```

`max_steps_exceeded`는 시스템 장애라기보다 무한 반복을 막기 위한 안전 중단이므로 `failed`와 구분합니다.

## 8. `openai_agent_backend.py`의 역할

현재 구조에서 `openai_agent_backend.py` 자체는 Agent가 아닙니다. 여러 예제가 공유하는 Model·Tool 연결 계층입니다.

```text
openai_agent_backend.py
├─ Agent Instructions
├─ OpenAI Function Tool Schema
├─ OpenAI Client 생성
├─ Function Call 추출
├─ Tool 이름과 arguments 검증
├─ 실제 Python Tool 실행
├─ 최초 Model 호출
└─ Tool Result 이후 Model 재호출
```

실제 Agent Loop는 `06_openai_agent_loop.py`에 있습니다.

```text
06_openai_agent_loop.py
├─ Goal과 State 생성
├─ Backend를 이용한 최초 LLM 판단
├─ Tool 실행과 Result 전달 반복
├─ 오류 상태 변환
├─ 최대 반복 통제
└─ 최종 완료·실패·중단 반환
```

두 파일의 관계는 다음과 같습니다.

```text
06_openai_agent_loop.py
└─ Agent의 전체 실행과 통제
     ↓ 사용
openai_agent_backend.py
└─ Model 호출과 Tool 검증·실행 기능
     ↓ 사용
travel_tools.py
└─ Tool 계약과 실제 Mock 함수
```

## 9. 왜 처음부터 복잡한 State를 사용하지 않았는가?

학습 순서상 처음에는 Tool Calling의 본질에 집중해야 합니다.

```text
사용자 질문
→ Model이 Tool 선택
→ Backend가 Tool 실행
→ Result를 Model에 전달
→ 답변
```

이 단계에서 상태 전이, 반복 제한, 오류 분류와 중단·재개를 모두 넣으면 Model Tool Calling과 Backend 실행 경계가 잘 보이지 않을 수 있습니다.

이번 장에서는 이미 Tool Calling을 이해했다는 전제에서 다음 문제로 확장합니다.

```text
Result에 따라 다음 행동이 달라지면?
몇 번 반복할지 미리 알 수 없다면?
실패와 안전 중단을 구분해야 한다면?
실행 경로를 평가해야 한다면?
나중에 승인 대기와 재개를 추가한다면?
```

따라서 State는 Agent를 만들기 위한 형식적 조건이 아니라, **복잡해진 Agent 실행을 통제하고 설명하기 위해 도입한 설계 수단**입니다.

## 10. 언제 어떤 구조를 선택하는가?

### 단순 Tool-calling 구조를 선택

```text
첫 판단에서 필요한 Tool을 모두 선택할 수 있다.
Tool Result가 다른 Tool 선택에 영향을 주지 않는다.
한 번의 Tool 실행 묶음 뒤 최종 답변이면 충분하다.
중단·재개와 세부 상태 조회가 필요하지 않다.
```

### State 기반 Agent Loop를 선택

```text
Tool Result를 본 뒤 다음 Tool을 결정해야 한다.
실행 횟수가 요청마다 달라진다.
완료, 실패와 반복 초과를 구분해야 한다.
판단과 실행 경로를 Trace하고 평가해야 한다.
승인 대기, 저장과 재개로 확장할 가능성이 있다.
```

복잡한 구조가 항상 더 좋은 것은 아닙니다. 필요한 실행 제어 수준에 맞는 가장 단순한 구조를 선택합니다.

## 11. 이후 Human Approval과 Multi-Agent로의 연결

명시적인 State는 다음 장의 Human Approval에서 더 중요해집니다.

```text
Agent가 변경 Tool 제안
→ 승인 대상과 현재 State 저장
→ status = waiting_approval
→ 실행 중단
→ 사용자 승인
→ 저장된 State에서 재개
→ 변경 Tool 실행
```

Multi AI Agent Orchestration에서는 State의 범위가 더 확장됩니다.

```text
공유 State
├─ 사용자 Goal
├─ 검증된 공통 Context
├─ 전체 진행 상태
└─ 전체 종료 이유

Agent 전용 State
├─ 역할별 입력과 결과
├─ Agent별 Tool 권한
├─ 개별 완료·실패 상태
└─ Handoff 정보
```

이번 Agent에서 State, 종료 이유와 Trace를 명시적으로 관리하는 것은 이후 승인·재개·평가와 Multi-Agent Orchestration으로 확장하기 위한 기초가 됩니다.

## 핵심 정리

```text
이전 Agent
= Tool Calling을 이해하기 위한 짧고 고정적인 실행 구조
= 필요한 Tool을 선택하고 모두 실행한 뒤 최종 답변
= 상태는 지역 변수와 Model 응답에 암묵적으로 존재

이번 Agent
= Tool Result 기반 재판단이 가능한 반복 실행 구조
= Goal, 상태, 호출 횟수, Trace와 종료 이유를 명시적으로 관리
= 완료, 오류와 최대 반복 초과를 구분

State가 있어서 Agent가 되는 것은 아니다.
Agent 실행이 복잡해졌기 때문에 State를 명시적으로 설계한 것이다.
```
