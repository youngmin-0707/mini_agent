# 06 Workflow와 AI Agent

이 장의 핵심은 **누가 다음 행동을 결정하는가**입니다.

```text
Workflow        개발자가 실행 경로를 설계한다.
Agent           목표와 상태를 보고 다음 행동을 선택하는 실행 주체다.
AI Agent        AI Model이 다음 행동이나 종료를 판단하는 Agent다.
LangGraph       Workflow와 Agent Loop를 State Graph로 표현하고 실행한다.
```

## 1. Workflow란 무엇인가?

Workflow는 입력을 처리하기 위한 **단계, 순서, 분기와 통제 지점을 개발자가 미리 설계한 실행 구조**입니다.

### Fixed Workflow

```text
입력 → 날씨 조회 → 야외 장소 검색 → 결과
```

실행 경로가 항상 같습니다. 비가 와도 다음 단계가 야외 장소 검색으로 고정되어 있다면 Tool Result가 경로를 바꾸지 않습니다.

### Conditional Workflow

```text
날씨 조회
  ├─ 비      → 실내 장소 검색
  ├─ 비 아님 → 야외 장소 검색
  └─ 실패    → 중단
```

결과에 따라 경로가 달라지지만 분기 규칙은 개발자가 작성합니다. Python `if` 문이 미리 정한 경로 중 하나를 선택한다면 Conditional Workflow입니다.

| 기준 | Fixed Workflow | Conditional Workflow |
| --- | --- | --- |
| 실행 순서 | 항상 동일 | 결과에 따라 분기 |
| 판단 주체 | 개발자 | 개발자 규칙 |
| 자율적 계획 | 없음 | 없음 |
| 예측 가능성 | 매우 높음 | 높음 |

> 관련 예제: `01_fixed_workflow.py`는 고정 경로를, `02_conditional_workflow.py`는 개발자 규칙에 따른 분기를 보여줍니다.

## 2. Agent와 AI Agent란 무엇인가?

Agent는 **목표와 현재 상태를 보고 다음 행동을 선택하고, 실행 결과를 관찰하면서 목표 달성을 시도하는 실행 주체**입니다.

```text
목표 확인 → 판단(Reason) → 실행(Act) → 관찰(Observe) → 재판단 또는 종료
```

Agent의 핵심 구성은 다음과 같습니다.

- 달성하려는 Goal
- 진행 상황을 담은 State
- 선택 가능한 Action 또는 Tool
- Result를 관찰하고 State에 반영하는 과정
- 완료·실패·최대 단계 같은 종료 조건

### Rule-based Agent

개발자가 작성한 규칙이 다음 행동을 판단합니다.

```python
if weather is None:
    action = "get_weather"
elif weather["condition"] == "비":
    action = "search_indoor_places"
else:
    action = "finish"
```

판단·실행·관찰을 반복하므로 Agent 구조이지만 AI Model을 사용하지 않으므로 엄밀하게는 AI Agent가 아닙니다. Mock Agent 또는 Rule-based Agent라고 부릅니다.

### LLM 기반 AI Agent

LLM이 사용자 목표, 지침, State와 Tool Schema를 보고 다음 행동을 판단합니다.

```text
사용자 목표 + Instructions + Tool Schema
  ↓
LLM
  ├─ Tool Call 선택
  └─ 최종 답변 선택
```

LLM은 판단 주체이고 Python Backend는 모델이 요청한 Tool을 검증하고 실행합니다.

> 관련 예제: `03_rule_based_agent_loop.py`는 규칙 기반 Agent Loop를 보여줍니다. `05_openai_tool_selection.py`부터 판단 주체가 Python 규칙에서 OpenAI Model로 바뀝니다.

## 3. Workflow, Rule-based Agent와 LLM 기반 AI Agent는 어떻게 다른가?

가장 중요한 기준은 **다음 행동의 판단 주체와 실행 경로가 언제 결정되는가**입니다.

| 기준 | Workflow | Rule-based Agent | LLM 기반 AI Agent |
| --- | --- | --- | --- |
| 다음 행동 판단 | 개발자가 설계한 경로 | 개발자의 규칙 | LLM |
| 실행 경로 | 실행 전에 대부분 결정 | State에 따라 규칙으로 선택 | 실행 중 Model이 동적으로 선택 |
| 반복 | 필요할 때 코드로 구현 | 판단·실행·관찰 반복 | Model·Tool·Result 반복 |
| 새로운 표현 대응 | 제한적 | 작성한 규칙 범위 | 자연어와 Context로 유연하게 대응 |
| 예측 가능성 | 높음 | 비교적 높음 | 상대적으로 낮음 |
| 비용과 지연 | 낮음 | 낮음 | Model 호출만큼 증가 |
| 적합한 문제 | 순서가 명확한 업무 | 규칙을 열거할 수 있는 판단 | 규칙으로 모두 작성하기 어려운 판단 |

Tool 사용 여부만으로는 구분할 수 없습니다. Workflow, Rule-based Agent와 AI Agent 모두 Tool을 사용할 수 있습니다.

`04_tool_result_routing.py`는 `03`에 포함된 **관찰 결과 → 다음 행동** 관계만 분리해 여러 결과와 실패 상황으로 확인합니다.

`05_openai_tool_selection.py`는 LLM이 Tool과 arguments를 선택하는 것까지만 관찰합니다. Tool 실행과 재판단이 없으므로 아직 완성된 Agent Loop는 아닙니다.

`06_openai_agent_loop.py`는 공용 Backend 함수들을 조합하여 전체 AI Agent Loop를 완성합니다.

이전에 만든 단순 Tool-calling Agent와 이번 State 기반 Agent Loop의 차이는
[`openai_agent_backend.md`](openai_agent_backend.md)에서 자세히 설명합니다.

```text
LLM 판단 → Tool Call → Backend 검증·실행 → Tool Result 전달
    ↑                                              ↓
    └──────── 추가 Tool Call 또는 최종 답변 ──────┘
```

> 관련 예제: `03`은 Rule-based Agent Loop, `04`는 Tool Result Routing, `05`는 LLM Tool 선택 관찰, `06`은 LLM 기반 AI Agent Loop입니다. `travel_tools.py`는 공용 Mock Tool 계층이며 Agent가 아닙니다.

## 4. Workflow 안에 AI Agent는 어떻게 들어가는가?

실무에서는 전체 시스템을 Agent에게 맡기기보다 **판단이 필요한 구간에 AI Agent를 넣고 결정적인 업무와 안전 통제는 Workflow와 Backend가 담당**하게 합니다.

```text
결정적 Workflow
├─ 입력 검증과 권한 확인
├─ AI Agent가 다음 행동 판단
│    ├─ Tool 제안
│    ├─ Result 관찰
│    └─ 추가 행동 또는 종료 선택
├─ Backend가 Tool Call 검증·실행
├─ 필요하면 사용자 승인
└─ 저장, 감사 로그와 응답 반환
```

| 구성요소 | 책임 |
| --- | --- |
| Workflow | 전체 단계, 통제 지점과 업무 순서 관리 |
| AI Agent | 모호한 요청 해석과 다음 행동 판단 |
| LLM | Tool Call 또는 답변 생성 |
| Backend | 권한·인자 검증과 실제 Tool 실행 |
| Tool | 조회, 검색, 저장 같은 한 가지 기능 수행 |
| Human approval | 결제·삭제·전송 같은 위험 행동 승인 |

Agent의 판단은 시스템 정책보다 우선하지 않습니다. Model이 Tool을 요청해도 Backend Allowlist, arguments 검증과 사용자 권한을 통과해야 실행됩니다.

> 관련 예제: `openai_agent_backend.py`는 OpenAI 호출과 Tool 검증·실행 함수를 제공합니다. `06_openai_agent_loop.py`의 `run_openai_agent()`가 이 함수들을 State, 반복과 종료 조건으로 연결한 실제 AI Agent Loop입니다.

## 5. LangGraph는 Workflow와 Agent를 어떻게 표현하는가?

LangGraph는 LLM이나 AI Agent 자체가 아닙니다. **Workflow와 Agent Loop의 State, 단계, 이동 경로, 반복과 종료를 Graph로 표현하는 저수준 Orchestration Framework**입니다.

```text
초기 LLM Application: Prompt → Model → Answer
Tool-using AI Agent:  Model → Tool → Result → Model → Tool 또는 Answer
```

Agent가 실제 업무를 수행하면서 상태 저장, 실패 후 재개, 사람 승인, 장시간 실행과 추적이 중요해졌습니다. LangGraph는 State Graph를 기반으로 이러한 실행을 관리하는 방향으로 발전했습니다.

| LangGraph 요소 | 의미 |
| --- | --- |
| State | Node 사이에서 공유하고 갱신하는 실행 정보 |
| Node | Model 호출, Tool 실행, 검증 같은 한 단계 |
| Edge | 다음 Node로 이동하는 경로 |
| Conditional Edge | State나 판단 결과에 따라 경로 선택 |
| Loop | Tool Result 이후 Agent Node로 돌아가 재판단 |
| `START` / `END` | Graph 시작과 종료 |

### Workflow를 Graph로 표현

```text
START → validate → search → answer → END
```

개발자가 다음 Node를 정하면 LangGraph로 작성했더라도 Workflow입니다.

### AI Agent를 Graph로 표현

```text
START → OpenAI Agent Node
                   ↓
             Tool Call이 있는가?
              ├─ 있음 → Backend Tool Node → Agent Node
              └─ 없음 → 최종 답변 → END
```

Agent Node 안의 LLM이 Tool과 종료를 판단합니다. Tool Node는 판단 주체가 아니라 선택된 Tool을 검증하고 실행합니다.

| Agent 개념 | 순수 Python | LangGraph |
| --- | --- | --- |
| 실행 정보 | `state` 딕셔너리 | Graph State |
| Model 판단 | Responses API 호출 | Agent Node |
| Tool 실행 | Loop 내부 함수 호출 | Backend Tool Node |
| Result 전달 | `function_call_output` | State 갱신 |
| 반복 | `for`·`while` | Agent Node로 돌아가는 Edge |
| 종료 | `if`와 `return` | Conditional Edge → `END` |

```text
LangGraph를 사용했다 = AI Agent다       X
Node가 여러 개다 = Multi-Agent다        X
LLM이 목표와 State로 행동을 판단한다    → AI Agent
```

> 관련 예제: `10_optional_langgraph/01_same_openai_agent_with_langgraph.py`는 `06`과 동일한 Model, Instructions, Tool Schema와 Mock Tool을 사용합니다. Function Call이 없으면 종료한다는 기본 조건은 같지만 반복 제한과 오류 처리 방식은 다릅니다. Agent가 달라진 것이 아니라 Python Loop를 State, Node와 Edge로 다시 표현한 것입니다.

최신 정의와 기능은 [LangGraph 공식 저장소](https://github.com/langchain-ai/langgraph)와 [공식 제품 구조 문서](https://docs.langchain.com/oss/python/concepts/products)를 참고합니다.

## 6. 이 과정에서 LangGraph를 어떻게 다루는가?

이 과정의 중심은 LangGraph 사용법이 아니라 **AI Agent와 Multi AI Agent Orchestration의 동작 원리**입니다. Agent의 Goal, State, Tool, Result, 반복과 종료를 먼저 순수 Python으로 구현하여 Framework 없이도 구조를 설명하고 수정할 수 있게 합니다.

```text
이 과정의 필수 학습
├─ LLM이 다음 행동을 판단하는 AI Agent
├─ Tool 실행과 Result 기반 재판단
├─ Agent의 State, 반복과 종료 조건
└─ 여러 Agent의 역할, 위임, Handoff, 실패 처리와 결과 통합

선택 비교 학습
└─ 같은 Agent Loop를 LangGraph의 State, Node와 Edge로 표현
```

Multi AI Agent Orchestration도 LangGraph 없이 구현할 수 있습니다. Python 함수, 상태 객체, Queue와 Backend Service만으로도 Agent 선택, 병렬 실행, Handoff와 결과 통합을 구성할 수 있습니다. 중요한 것은 특정 Framework가 아니라 다음 책임을 명확히 설계하는 것입니다.

- 어떤 Agent가 어떤 Goal과 역할을 가지는가?
- Supervisor 또는 Orchestrator가 누구에게 작업을 위임하는가?
- Agent 사이에 어떤 Context만 전달하는가?
- Tool 권한과 사용자 데이터는 어떻게 격리하는가?
- 일부 Agent가 실패하면 재시도, 대체 또는 중단 중 무엇을 선택하는가?
- 누가 전체 작업의 완료를 판단하고 결과를 통합하는가?

LangGraph는 이 구조를 State Graph로 표현하고 싶을 때 사용할 수 있는 **선택 도구**입니다. 복잡한 분기, Checkpoint, 중단 후 재개 같은 요구가 생기면 도움이 될 수 있지만, LangGraph를 사용해야만 AI Agent나 Multi AI Agent가 되는 것은 아닙니다.

> 관련 예제: 필수 예제인 `06_openai_agent_loop.py`는 순수 Python으로 AI Agent Loop를 구현합니다. `10_optional_langgraph`는 새로운 Agent를 만드는 과정이 아니라, 동일한 Agent를 Graph 형식으로 다시 표현해 보는 선택 비교 예제입니다.

## 핵심 정리

```text
Workflow
= 개발자가 실행 경로와 통제 지점을 설계한다.

Rule-based Agent
= 개발자 규칙이 State를 보고 다음 행동을 반복 선택한다.

LLM 기반 AI Agent
= LLM이 목표, State와 Tool Result로 다음 행동이나 종료를 판단한다.

LangGraph
= Workflow와 Agent Loop를 State Graph로 표현하고 운영하는 선택 Framework다.

Multi AI Agent Orchestration
= 서로 다른 목표·역할·전문 Context를 가진 여러 AI Agent의 선택, 위임, Handoff,
  실행 순서, 권한, 실패 처리, 결과 통합과 전체 종료를 연결하고 통제한다.
```

파일 순서를 외우기보다 **판단 주체가 개발자, 규칙 또는 LLM 중 누구인지 구분하는 것**이 이 장의 학습 목표입니다.
