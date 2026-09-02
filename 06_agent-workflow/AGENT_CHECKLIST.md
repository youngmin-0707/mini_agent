# AI Agent 설계 점검표

이 문서는 예제나 자신의 프로그램이 이 과정에서 말하는 **LLM 기반 Tool-using AI Agent**인지 확인하는 마지막 점검표입니다.

## 1. 판단 주체

- [ ] LLM이 사용자 Goal과 현재 State를 읽는가?
- [ ] LLM이 Tool 호출, 사용자 질문 또는 종료 중 다음 행동을 선택하는가?
- [ ] 단순히 LLM을 한 번 호출한 프로그램을 Agent라고 부르고 있지는 않은가?
- [ ] 고정된 `if/else` 정책이라면 Rule-based Agent 또는 Workflow로 정확히 구분했는가?

## 2. Tool 실행 경계

- [ ] Model에는 허용된 Tool Schema만 제공하는가?
- [ ] Model의 Tool Call을 실행 명령이 아닌 제안으로 취급하는가?
- [ ] Backend가 Tool Allowlist와 arguments를 검증하는가?
- [ ] 사용자 ID, 소유권과 권한을 Backend가 다시 검사하는가?
- [ ] 외부 상태를 변경하는 Tool에는 필요한 승인 절차가 있는가?

## 3. Agent Loop와 State

- [ ] Tool Result를 Model에 다시 전달하는가?
- [ ] Result가 다음 Tool, 재시도, 질문 또는 종료 판단에 사용되는가?
- [ ] Goal, 현재 단계, Tool Result와 실행 횟수를 구분해서 저장하는가?
- [ ] 대화 History, 업무 State, 장기 Memory와 Trace를 같은 개념으로 취급하지 않는가?

## 4. 종료와 실패

- [ ] 성공 종료 조건이 명확한가?
- [ ] Tool이 필요 없는 요청도 바로 종료할 수 있는가?
- [ ] 최대 반복 횟수가 있는가?
- [ ] `model_error`, `invalid_tool_call`, `tool_error`를 구분하는가?
- [ ] 권한 거부와 사용자 승인 대기를 무의미하게 재시도하지 않는가?
- [ ] 모든 실행에 구조화된 `termination_reason`이 남는가?

## 5. 관찰과 평가

- [ ] LLM 호출과 Tool 호출을 Trace에서 확인할 수 있는가?
- [ ] Tool 이름, 검증된 arguments와 Result를 추적할 수 있는가?
- [ ] Tool Result에 없는 사실을 최종 답변이 만들어내지 않는지 평가하는가?
- [ ] 정상, 빈 결과, 잘못된 입력, Tool 실패와 반복 초과를 시험하는가?
- [ ] 호출 횟수, 토큰 비용과 응답 지연을 측정하는가?

## 6. Workflow와 Multi-Agent 선택

- [ ] 순서가 명확한 부분은 Workflow로 유지했는가?
- [ ] 불확실한 판단이 필요한 부분에만 Agent를 사용했는가?
- [ ] Tool이나 Node가 많다는 이유만으로 Multi-Agent로 나누지 않았는가?
- [ ] 독립 Goal, 전문 Context, Tool 권한 또는 평가 기준이 있을 때만 Agent 분리를 검토했는가?
- [ ] 여러 Agent가 필요하다면 공유 State, Handoff, 실패와 전체 종료의 책임자를 정했는가?

## 최종 판단

```text
Model이 답변만 생성한다
→ LLM Application

Model이 고정 Workflow의 한 단계를 수행한다
→ LLM-enhanced Workflow

규칙이 관찰 결과를 보고 행동을 반복 선택한다
→ Rule-based Agent Loop

LLM이 Goal과 Tool Result를 보고 다음 행동과 종료를 반복 선택한다
→ LLM-based AI Agent

Workflow, Agent, Memory, 승인과 평가가 하나의 시스템으로 연결된다
→ Agentic System
```

체크되지 않은 항목이 있다고 무조건 잘못된 시스템은 아닙니다. 다만 빠진 항목이 의도적인 단순화인지, 운영 전에 보강해야 할 위험인지 설명할 수 있어야 합니다.
