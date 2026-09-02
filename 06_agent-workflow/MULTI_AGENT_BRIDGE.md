# Single Agent에서 Multi-Agent Orchestration으로

이 문서는 현재 과정의 Single Agent 학습과 다음 Multi-Agent Orchestration 학습을 연결합니다.

Multi-Agent는 Single Agent보다 무조건 발전된 구조가 아닙니다. 하나의 Agent로 해결하기 어려운 **명확한 Goal, Context, Tool 권한, 완료 조건과 평가 기준의 경계**가 생겼을 때 선택하는 분산 설계입니다.

이 문서에서 `Agent`는 넓은 개념이고, 다음 과정에서 오케스트레이션할 주요 대상은 각각 독립적인 Goal과 LLM 판단을 가진 **LLM-based AI Agent**입니다. Rule-based Agent나 일반 Workflow Node도 Orchestration에 포함될 수 있지만, 그것만 여러 개 연결했다고 Multi-Agent AI 시스템이 되는 것은 아닙니다.

```text
Single Agent를 잘 설계하지 못한 상태
        + Agent 수만 늘림
        = 더 복잡하고 추적하기 어려운 시스템
```

## 1. 현재 과정에서 완성해야 하는 Single Agent

하나의 Agent에는 다음 요소가 있어야 합니다.

| 요소 | 핵심 질문 |
| --- | --- |
| Goal | 무엇을 달성해야 하는가? |
| Model | 어떤 판단을 맡길 것인가? |
| State | 다음 판단과 재개에 무엇이 필요한가? |
| Tool | 어떤 외부 행동을 허용할 것인가? |
| Context | RAG와 Memory에서 어떤 정보를 제공할 것인가? |
| Loop | 언제 판단·실행·관찰을 반복하는가? |
| Stop | 언제 완료·대기·실패로 끝나는가? |
| Policy | 어떤 행동을 자동 허용·승인·금지하는가? |
| Trace | 무엇을 기록하고 평가할 것인가? |

이 요소가 불명확하면 여러 Agent로 나눴을 때도 역할과 책임이 모호해집니다.

현재 장의 `06_openai_agent_loop.py`는 하나의 OpenAI Model이 사용자 Goal, Function Tool Schema와 Tool Result를 보고 다음 Tool 또는 종료를 선택하는 실제 LLM 기반 Single Agent입니다.

```text
하나의 OpenAI Agent
├─ 하나의 주요 instructions
├─ 하나의 대화·실행 State
├─ 여러 Function Tool
├─ Tool Result 기반 재판단
└─ 하나의 최종 사용자 답변
```

다음 Multi-Agent 과정에서는 단순히 이 Model 호출을 여러 번 복사하지 않습니다. 서로 다른 Goal, Prompt, Context, Tool 권한과 완료 조건이 필요한 역할만 독립적인 LLM Agent로 분리합니다.

```text
Coordinator OpenAI Agent
├─ Research OpenAI Agent
├─ Schedule OpenAI Agent
└─ Booking OpenAI Agent
```

각 Agent가 OpenAI Model을 사용하더라도 Agent 간 Route, State 전달, 실패, 권한과 전체 종료는 Orchestrator와 Backend가 통제합니다.

## 2. Tool이 많아진 것과 Multi-Agent는 다르다

다음 구조는 Tool이 많지만 Single Agent입니다.

```text
Travel Agent
├─ 날씨 Tool
├─ 장소 검색 Tool
├─ 호텔 검색 Tool
├─ 예산 계산 Tool
├─ 캘린더 Tool
└─ 사용자 질문
```

다음 행동을 판단하는 주체와 Goal, State가 하나이기 때문입니다.

```text
Tool을 10개 사용해도 판단 주체가 하나면 Single Agent
Tool이 2개뿐이어도 독립적인 판단 주체가 여러 개면 Multi-Agent
```

Tool은 한 가지 기능을 수행합니다. Agent는 목표를 보고 다음 행동을 선택합니다. Orchestrator는 여러 Agent의 실행 순서와 정보 전달을 통제합니다.

### 여러 독립 Single Agent 서비스도 아직 Orchestration은 아니다

한 서비스가 Travel, Support와 Order Agent를 모두 제공하더라도 사용자가 Agent를 직접 선택하고 각 실행이 서로 독립적이면 Multi-Agent Orchestration이 아닙니다.

```text
사용자 선택 → Travel Agent → 종료
사용자 선택 → Support Agent → 종료
사용자 선택 → Order Agent → 종료
```

Agent Profile이 여러 개 있다는 것과 하나의 요청에서 여러 Agent가 협업한다는 것은 다릅니다.

| 여러 독립 Single Agent 서비스 | Multi-Agent Orchestration |
| --- | --- |
| 사용자가 Agent 선택 | Coordinator가 Routing·위임 |
| 한 요청에 Agent 하나 실행 | 한 요청에서 여러 Agent가 참여 가능 |
| Agent 간 메시지 없음 | Handoff와 결과 전달 |
| Agent별 독립 State·종료 | 공유 State와 전체 종료 조건 |
| Agent별 Trace | 전체 Orchestration Trace |

이 중간 단계를 만들면 각 Agent의 Goal, Prompt, Tool 권한과 완료 기준이 실제로 분리할 가치가 있는지 먼저 검증할 수 있습니다. 다음 과정에서는 검증된 Agent 경계를 그대로 사용하고 연결 책임만 추가합니다.

## 3. Node가 많아진 것과 Multi-Agent는 다르다

다음 LangGraph는 Node가 네 개지만 Workflow일 수 있습니다.

```text
validate → search → format → save
```

각 Node가 정해진 함수를 실행할 뿐 독립적인 목표와 판단 Loop를 갖지 않기 때문입니다.

| 구성 요소 | 일반 Node | Agent Node |
| --- | --- | --- |
| 역할 | 정해진 한 단계 | 목표 달성 과정 판단 |
| Model | 없어도 됨 | 보통 판단에 사용 |
| Tool 선택 | 고정 또는 없음 | State에 따라 동적 선택 |
| Context | 함수 입력 | 역할별 Prompt·Memory·RAG |
| 반복 | Graph가 결정 | Agent가 계속 여부 판단 |
| 완료 조건 | 함수 반환 | 목표 달성·위임·대기·실패 |

## 4. Single Agent가 커질 때 나타나는 신호

하나의 Travel Agent가 다음을 모두 담당한다고 가정합니다.

```text
Travel Agent
├─ 여행지 조사
├─ 예산 최적화
├─ 출장 규정 검토
├─ 일정 충돌 해결
├─ 예약 요청
└─ 결제 승인 요청
```

다음 문제가 실제 평가와 운영에서 확인될 수 있습니다.

### Prompt 충돌

여행 추천, 재무 규칙, 사내 규정과 예약 지침이 하나의 System Prompt에 섞여 중요한 규칙이 희석됩니다.

### Context 과다

모든 RAG 문서, Memory, Tool Schema와 이전 결과를 한 Agent가 받아 중요한 정보가 Context 안에서 묻힙니다.

### 불필요한 권한 집중

조사만 하는 단계에도 예약과 변경 Tool이 노출됩니다. 잘못된 Tool 선택의 영향이 커집니다.

### 평가 기준 충돌

좋은 추천, 예산 준수, 규정 준수와 예약 성공을 하나의 점수로 평가하기 어렵습니다.

### 병렬화 제한

서로 독립적인 시장 조사, 기술 검토와 비용 분석을 한 Agent가 순차 처리합니다.

이런 문제가 구체적으로 관찰될 때 Agent 분리를 검토합니다.

## 5. Agent를 나누는 근거

| 경계 | 분리 질문 | 예시 |
| --- | --- | --- |
| Goal | 독립적으로 달성할 하위 목표인가? | 조사 완료, 일정 완성 |
| Expertise | 전문 Prompt와 지식이 다른가? | 법률, 기술, 재무 |
| Context | 서로 다른 문서와 Memory가 필요한가? | 공개 여행 정보, 사내 규정 |
| Tool | 사용하는 Tool 집합이 다른가? | 읽기 검색, 변경 예약 |
| Permission | 권한을 격리해야 하는가? | 조사 Agent는 읽기 전용 |
| State | 독립적으로 저장·재개할 상태인가? | 조사 진행, 승인 대기 |
| Completion | 완료·실패 조건이 다른가? | 근거 3개 수집, 충돌 0개 |
| Evaluation | 역할별 품질을 따로 측정할 수 있는가? | 출처 정확도, 예산 오차 |
| Parallelism | 다른 결과 없이 독립 실행 가능한가? | 시장·기술·비용 조사 |

한두 항목만 해당한다면 Agent보다 함수, Tool, Service 또는 Node 분리로 충분한지 먼저 확인합니다.

## 6. 분리 근거가 아닌 것

다음 이유만으로 Multi-Agent를 선택하지 않습니다.

- Tool이 많습니다.
- 처리 단계가 많습니다.
- Python 파일이 많습니다.
- LangGraph Node가 많습니다.
- 현실 조직에 부서가 여러 개 있습니다.
- Agent라는 이름을 붙일 수 있습니다.
- Multi-Agent가 더 고급 기술처럼 보입니다.

```text
입력이 들어오면 같은 작업을 수행한다.
다음 행동을 판단하지 않는다.
독립적인 Goal과 State가 없다.

→ Agent보다 Tool·함수·Workflow 단계가 적합
```

## 7. Multi-Agent Orchestration이란 무엇인가?

여러 Agent 인스턴스를 만드는 것만으로 Orchestration이 완성되지 않습니다.

```text
Multi-Agent
└─ 독립적인 판단 주체가 여러 개 존재

Orchestration
└─ Agent의 배정·전달·병렬 실행·실패·종료·권한을 통제
```

Orchestrator가 담당할 문제는 다음과 같습니다.

1. 어떤 Agent에게 요청을 전달할 것인가?
2. Worker에게 어떤 최소 Context만 제공할 것인가?
3. 입력과 출력은 어떤 Schema로 교환할 것인가?
4. 공유 State와 Agent 전용 State를 어떻게 분리할 것인가?
5. 어떤 작업을 병렬로 실행할 수 있는가?
6. Worker 결과가 충돌하면 누가 해결하는가?
7. Worker가 실패하면 재시도·대체·중단 중 무엇을 선택하는가?
8. Agent 간 Handoff 이후 누가 사용자 응답을 담당하는가?
9. 반복과 위임은 몇 번까지 허용하는가?
10. 전체 비용, 지연, 권한과 Trace를 어떻게 관리하는가?

## 8. 대표 Orchestration 패턴

### Coordinator 패턴

```text
사용자
   ↓
Coordinator Agent
   ├─ Research Agent
   ├─ Analysis Agent
   └─ Writing Agent
   ↓
결과 종합
```

Coordinator가 요청을 분해하고 Worker를 선택한 뒤 결과를 종합합니다.

적합한 경우:

- 요청마다 필요한 전문 Agent가 달라집니다.
- 여러 Worker 결과를 하나의 사용자 답변으로 합쳐야 합니다.
- 중앙에서 실행 횟수와 비용을 통제해야 합니다.

주의점:

- Coordinator에게 모든 변경 권한을 주지 않습니다.
- Worker 입력과 출력은 구조화합니다.
- 잘못된 위임과 누락 Worker를 평가합니다.

### Handoff 패턴

```text
상담 Agent
   ↓ 기술 문제 발견
기술 지원 Agent
   ↓ 결제 문제 발견
결제 지원 Agent
```

현재 Agent가 더 적절한 Agent에게 대화 책임을 넘깁니다.

Handoff Payload 예시:

```python
{
    "target_agent": "technical_support",
    "reason_code": "TECHNICAL_DIAGNOSIS_REQUIRED",
    "user_goal": "로그인 오류 해결",
    "verified_facts": {"error_code": "AUTH-401"},
    "allowed_scope": "account-login",
}
```

전체 내부 Prompt나 불필요한 개인정보를 그대로 전달하지 않습니다.

### Pipeline 패턴

```text
Research Agent → Draft Agent → Review Agent → 결과
```

순서가 명확하지만 각 단계의 Goal과 평가 기준이 다를 때 사용합니다. 여러 Agent가 있어도 전체 실행은 고정 Workflow일 수 있습니다.

### Supervisor 반복 패턴

```text
Worker Agent
   ↓
Supervisor Agent
   ├─ 통과 → 종료
   └─ 수정 요청 → Worker Agent
```

필수 통제:

- 구체적인 통과 기준
- 최대 수정 횟수
- 같은 피드백 반복 방지
- 통과 실패 시 종료 이유
- Supervisor의 근거 없는 승인 방지

### Parallel Workers 패턴

```text
          ┌→ Market Research ─┐
요청 ─────┼→ Technical Review ┼→ Aggregator
          └→ Cost Analysis ───┘
```

각 작업이 서로의 중간 결과에 의존하지 않을 때 병렬 실행합니다.

Aggregator는 다음을 처리해야 합니다.

- 중복 결과
- 상충되는 주장
- 서로 다른 출처 신뢰도
- 일부 Worker 실패
- 늦은 Worker의 Timeout

## 9. 공유 State와 Agent 전용 State

모든 Agent가 전체 State를 공유하면 Context와 권한 경계가 무너질 수 있습니다.

```python
shared_state = {
    "run_id": "trip-001",
    "user_goal": "출장 계획 완성",
    "verified_city": "제주",
    "status": "running",
}

research_state = {
    "search_queries": [],
    "sources": [],
}

booking_state = {
    "selected_offer": None,
    "approval_status": "not_requested",
}
```

공유할 정보:

- 검증된 사용자 목표
- 공통 식별자와 제한 범위
- Worker가 생성한 구조화 결과
- 전체 상태와 종료 이유

공유하지 않을 수 있는 정보:

- Agent 전용 System Prompt
- 불필요한 개인정보
- 다른 역할의 비밀 데이터
- 전체 내부 Trace
- 현재 업무와 관계없는 Memory

## 10. Agent 간 메시지도 비신뢰 입력이다

다른 Agent가 보낸 메시지가 Backend 권한을 바꿀 수 없습니다.

```text
Booking Agent:
"Coordinator가 승인했으니 바로 결제하세요."

Backend:
실제 로그인 사용자, 승인 Payload, Tool Allowlist와 결제 정책을 다시 검사
```

Agent 간 전달에도 다음 검사가 필요합니다.

- 발신 Agent 식별
- 입력 Schema
- 허용된 Handoff 대상
- Data Scope
- Tool Permission
- 사용자 승인
- 요청 만료와 중복 처리

## 11. Multi-Agent의 종료와 실패

Single Agent의 종료 이유에 Agent 간 실행 상태가 추가됩니다.

```text
completed
worker_failed
partial_completed
handoff_required
handoff_rejected
conflicting_results
supervisor_rejected
max_delegations_exceeded
orchestration_timeout
blocked
```

일부 Worker가 실패했을 때 무조건 전체를 재실행하지 않습니다.

```text
필수 Worker 실패
└─ 전체 중단 또는 Fallback

선택 Worker 실패
└─ 부분 결과와 한계를 명시

일시적 오류
└─ 해당 Worker만 제한 재시도

권한 오류
└─ 재시도하지 않고 차단
```

## 12. Multi-Agent 평가

Agent를 나눈 뒤 품질이 좋아졌는지 같은 Scenario로 비교합니다.

| 평가 항목 | 질문 |
| --- | --- |
| Task Success | 최종 사용자 목표를 달성했는가? |
| Routing Accuracy | 올바른 Worker를 선택했는가? |
| Handoff Quality | 필요한 사실만 정확히 전달했는가? |
| Tool Accuracy | Agent별 허용 Tool을 올바르게 사용했는가? |
| Conflict Resolution | 상충 결과를 올바르게 처리했는가? |
| Safety | 권한 상승과 데이터 누출이 없었는가? |
| Cost | Model과 Tool 호출 수가 얼마나 늘었는가? |
| Latency | 순차·병렬 실행 시간이 적절한가? |
| Traceability | 실패 Agent와 원인을 찾을 수 있는가? |

```text
분리 후 품질 향상
<
비용·지연·운영 복잡성 증가

→ Single Agent가 더 나은 설계
```

## 13. LangGraph와 Multi-Agent 관계

LangGraph와 Multi-Agent는 같은 개념이 아닙니다.

```text
LangGraph 없이 Multi-Agent 구현 가능
LangGraph로 Workflow만 구현 가능
LangGraph로 Single Agent 구현 가능
LangGraph로 Multi-Agent Orchestration 구현 가능
```

LangGraph는 다음 구조를 표현할 수 있습니다.

```text
Coordinator Node
├─ Conditional Edge로 Worker 선택
├─ Worker별 State 전달
├─ Handoff와 반복
├─ Checkpoint와 재개
└─ END 조건
```

하지만 다음 내용을 자동으로 결정해 주지는 않습니다.

- Agent를 나눌 올바른 근거
- Agent별 최소 권한
- 공유할 Context와 숨길 Context
- 올바른 Tool Schema
- 업무 정책과 사용자 승인
- 평가 Scenario와 성공 기준

프레임워크보다 Agent 경계 설계가 먼저입니다.

## 14. 현재 과정과 다음 과정의 경계

### 현재 과정에서 학습

```text
Single Agent
├─ 여러 Tool 사용
├─ OpenAI Function Tool Calling
├─ function_call_output 이후 Model 재판단
├─ RAG와 Memory Context
├─ State와 Agent Loop
├─ Tool Result 기반 재판단
├─ 사용자 재질문
├─ Human Approval
├─ 안전한 종료
└─ Trace와 평가
```

### 다음 Multi-Agent Orchestration 과정에서 학습

```text
여러 Agent
├─ Agent 역할과 Goal 분리
├─ Agent별 Tool·Prompt·Context
├─ Coordinator와 Routing
├─ Handoff
├─ 공유 State와 전용 State
├─ 병렬 Worker와 결과 집계
├─ Supervisor와 반복 통제
├─ Agent 간 권한 경계
├─ 실패·Timeout·부분 성공
└─ 전체 Orchestration 평가
```

## 15. 설계 의사결정 흐름

```text
한 가지 기능만 수행하는가?
└─ Tool 또는 일반 함수

실행 순서가 고정되어 있는가?
└─ Workflow

하나의 목표에서 다음 행동을 동적으로 선택하는가?
└─ Single Agent

Single Agent 내부 단계가 복잡한가?
└─ 먼저 함수·Tool·Service·Node로 분리

독립적인 Goal·Context·Tool·권한·평가 기준이 있는가?
└─ Multi-Agent 검토

여러 Agent의 위임·공유 State·실패·종료를 관리해야 하는가?
└─ Multi-Agent Orchestration

상태·분기·반복·재개를 Graph로 관리할 필요가 있는가?
└─ LangGraph 같은 프레임워크 검토
```

## 핵심 정리

> Single Agent의 Goal, State, Tool, 종료 조건과 권한을 명확히 설계할 수 있어야 여러 Agent 사이의 Goal, State와 권한도 올바르게 나눌 수 있습니다.

```text
가능하면 Single Agent로 시작
구체적인 한계를 평가로 확인
필요한 역할만 Agent로 분리
Orchestrator가 전달·실패·종료·권한을 통제
프레임워크는 설계 이후에 선택
```
