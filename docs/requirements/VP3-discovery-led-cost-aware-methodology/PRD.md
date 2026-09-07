# VP3 Product Requirements Document

| Field | Value |
|---|---|
| Product | Copilot Build Method |
| Vision | VP3: Discovery-Led, Cost-Aware Methodology |
| Status | Approved |
| Version | 1.0 |
| Date | 2026-09-05 |
| Discovery verdict | `READY_WITH_DEFERRALS` |
| Delivery mapping | TH3, TH4, TH5 |

## Approval

| Field | Value |
|---|---|
| Actor | Human product owner |
| Timestamp | 2026-09-05T16:34:40+01:00 |
| Scope | Remaining VP3 product decisions and execution of the accepted direction |
| Verdict | Approved |
| Rationale | The human explicitly delegated the remaining routine product decisions and instructed the facilitator to proceed without further option-by-option elicitation. |
| Source revision | Discovery dossier accepted on 2026-09-05 |

## 1. Product promise

The Copilot Build Method shall help a human designer reach evidence-backed
product and technical commitments before architecture begins, then deliver
those commitments with risk-proportional context, verification, model use, and
AI-credit controls.

Decision quality, safety, and human comprehension take precedence over cost
reduction. Economic efficiency is successful only when product scope, quality,
and safety remain acceptable.

## 2. Vision outcomes

| ID | Outcome |
|---|---|
| VO-001 | Foundational unknowns, assumptions, conflicts, and invariants are visible before requirements and architecture are committed. |
| VO-002 | The human designer understands and controls consequential scope, risk, and simplification decisions. |
| VO-003 | Architecture formalizes evidence-backed constraints instead of discovering the domain from raw vision. |
| VO-004 | Stories contain bounded implementation responsibilities rather than hidden product or architecture discovery. |
| VO-005 | Verification, review, model capability, and context depth are proportional to risk. |
| VO-006 | AI-credit use is visible, bounded at safe control points, and calibrated without weakening quality. |
| VO-007 | Lifecycle history remains traceable, recoverable, and immutable at the appropriate acceptance boundaries. |

## 3. Users

| User | Job |
|---|---|
| Human designer / curious engineer | Understand mechanisms and make focusing decisions before commitments are frozen |
| Discovery facilitator | Coordinate bounded investigations, evidence, decisions, and readiness |
| Requirements facilitator | Translate accepted Discovery into measurable product requirements |
| Architect | Formalize validated constraints as components, contracts, and ADRs |
| Product owner | Decompose approved requirements and architecture into bounded delivery work |
| Orchestrator | Enforce sequencing, context, risk, verification, budget, and recovery controls |
| Developer, reviewer, troubleshooter | Execute one bounded responsibility with explicit evidence obligations |

## 4. Lifecycle

```text
Vision sketch
  -> Discovery
  -> PRD finalization
  -> Architecture and ADRs
  -> Planning and BDD backlog
  -> Cost-aware Autopilot
```

Every new scope shall receive a `FULL`, `LIGHTWEIGHT`, or explicitly approved
`WAIVED` Discovery disposition. Existing projects shall adopt VP3
prospectively through a migration assessment.

## 5. Release scope

### TH3 - Discovery and requirements foundation

Provide the human-facing Discovery and requirements lifecycle, structured
artefacts, gates, traceability, revisions, validators, and migration contract.
Controls may initially operate at `MANUAL` maturity.

### TH4 - Risk-aware planning and agent context

Provide risk tiers, verification/review profiles, task-level model routes,
compact source-bound agent packets, and versioned backlog execution controls.

### TH5 - Economic enforcement and learning

Provide usage capability adapters, nested budgets, observed threshold pauses,
revisioned runtime state, recovery, activation evidence, reporting, and policy
calibration.

## 6. TH3 functional requirements

| ID | Requirement | Traces |
|---|---|---|
| PR-001 | The method shall define the six-stage lifecycle and prevent architecture from beginning before accepted Discovery and PRD gates. | VO-001, VO-003, DEC-001 |
| PR-002 | The `discover` entrypoint shall classify each scope as `FULL`, `LIGHTWEIGHT`, or proposed `WAIVED`; waivers require human approval and invalidate on material scope expansion. | VO-001, DEC-002, DEC-012 |
| PR-003 | `discover` shall create the standard structured dossier with stable IDs for consequential questions, evidence, assumptions, decisions, invariants, risks, deferrals, and experiments. | VO-001, VO-007, DEC-006 |
| PR-004 | Material findings shall include classification, provenance, confidence or limitations, owner, and disposition. | VO-001, DEC-008 |
| PR-005 | Consequential assumptions, preferences, decisions, deferrals, overrides, and risk acceptance shall require attributable human acceptance. | VO-002, INV-012 |
| PR-006 | The facilitator shall recommend `READY`, `READY_WITH_DEFERRALS`, or `BLOCKED`; only human acceptance shall open the requirements gate. | VO-002, DEC-007 |
| PR-007 | Accepted Discovery changes shall use append-only `DR-###` records and invalidate affected downstream work before it continues. | VO-007, DEC-011, INV-011 |
| PR-008 | The interactive `requirements` entrypoint shall translate accepted Discovery recommendations into measurable `PR-###` requirements without selecting components, technologies, or detailed interfaces. | VO-003, DEC-005 |
| PR-009 | Final PRDs shall live under `docs/requirements/VP<n>-<slug>/PRD.md`, require complete human approval, and use append-only `PCR-###` records for consequential changes. | VO-002, VO-007, DEC-010 |
| PR-010 | `plan` shall reject missing or unaccepted Discovery/PRD inputs, separate architecture from delivery planning, and require human architecture acceptance before backlog creation. | VO-003, DEC-019 |
| PR-011 | Consequential requirements shall trace to vision outcomes and relevant Discovery records; architecture, stories, and evidence shall preserve downstream links. | VO-007, INV-004 |
| PR-012 | Themes shall lock independently. Shared VP, Discovery, and PRD artefacts shall lock only after all currently mapped themes are accepted. | VO-007, DEC-021 |
| PR-013 | Controls shall report `SPECIFIED`, `MANUAL`, `INSTRUMENTED`, `ENFORCED`, or `VERIFIED`, including effective point, limitations, and evidence. | VO-007, DEC-025 |
| PR-014 | Existing projects shall receive a migration assessment and apply VP3 prospectively without fabricated historical evidence. | VO-007, DEC-020 |
| PR-015 | Local contract validators shall detect lifecycle bypasses, invalid verdicts or waivers, broken consequential traceability, illegal locked edits, inconsistent control maturity, and obsolete lifecycle documentation. | VO-007, INV-001, INV-003 |
| PR-016 | Interactive `discover` and `requirements` skills shall own the human dialogue while bounded internal facilitator agents perform delegated investigation or drafting. | VO-002, DEC-004, DEC-005 |

## 7. TH4 functional requirements

| ID | Requirement | Traces |
|---|---|---|
| PR-101 | Planning shall assign every story an R0-R3 risk tier using objective triggers. | VO-005, DEC-013 |
| PR-102 | The architect shall validate technical risk triggers before implementation; the reviewer may escalate a tier. | VO-005, INV-010 |
| PR-103 | Tier reduction shall require architect approval with evidence and rationale before implementation. | VO-005, RSK-004 |
| PR-104 | Every story shall declare a provider-neutral default model route and allowed capability classes. | VO-005, DEC-017 |
| PR-105 | Model routing shall occur at task granularity; reasoning and critical escalation shall record the unresolved question, prior evidence, scope, stop condition, and estimated cost. | VO-005, VO-006 |
| PR-106 | Every story shall declare a verification matrix and review profile derived from its mechanism and risk. | VO-005, DEC-016 |
| PR-107 | Story verification shall use the smallest complete targeted checks; full suites shall be mandatory at theme/release and conditional at epic/story gates. | VO-005, DEC-016 |
| PR-108 | R3 or safety-critical verification waivers and risk downgrades shall require human authorization plus independent reviewer acknowledgement. | VO-002, VO-005, DEC-024 |
| PR-109 | The orchestrator shall generate a compact packet for each bounded task containing scope, acceptance criteria, traceability, dependencies, controls, source revision, and required report. | VO-004, DEC-015 |
| PR-110 | Agent packets shall retain source hashes or revisions and shall be rejected and regenerated when any authoritative referenced source changes. | VO-004, INV-007, EXP-004 |
| PR-111 | Agents shall request context expansion with the missing question, reason, risk, requested source, and estimated AIC. | VO-004, RSK-008 |
| PR-112 | Context expansion within budget may be approved by the orchestrator; expansion crossing the warning threshold requires human authorization. | VO-002, VO-006 |
| PR-113 | `backlog.yaml` shall be versioned and authoritative for runtime status, dependencies, risk tier, model route, verification profile, budgets, aggregate usage, confidence, and evidence references. | VO-007, DEC-014 |
| PR-114 | Detailed packet and attempt traces shall remain outside the backlog and be retained through delivery/review, then compacted after theme lock. | VO-006, VO-007 |
| PR-115 | New or unlocked themes shall use the current backlog schema; locked and archived themes shall remain valid under their historical schema. | VO-007, QR-004, QR-005 |

## 8. TH5 functional requirements

| ID | Requirement | Traces |
|---|---|---|
| PR-201 | A usage capability adapter shall report AI-credit usage as `measured`, `estimated`, or `unknown`. | VO-006, EXP-001 |
| PR-202 | The adapter shall prefer exact cumulative provider/CLI usage, use conservative proxies when necessary, and never convert missing telemetry to zero. | VO-006, INV-005 |
| PR-203 | Discovery phases, investigations, stories, reviews/rework, ceremonies, and orchestrator overhead shall support target, warning, and pause budgets. | VO-006 |
| PR-204 | Nested item usage shall be calculated from baseline/delta accounting while native session limits provide a final safety net. | VO-006, EXP-002 |
| PR-205 | Crossing a target shall be reported; crossing a warning shall checkpoint and expose remaining cost; after an observed pause threshold no new model call or delegation shall begin without human authorization. | VO-002, VO-006, INV-006 |
| PR-206 | Budget policy shall include an overshoot allowance because one in-flight model response may exceed the observed soft cap. | VO-006, EXP-002 |
| PR-207 | Human pause dispositions shall include continue with revised budget, simplify, split, change model route, reduce or waive verification, return to Discovery, or abort. | VO-002, VO-006 |
| PR-208 | Runtime state updates shall carry an expected revision and reject stale writers instead of silently overwriting state. | VO-007, INV-008, EXP-003 |
| PR-209 | State transitions shall use an atomic, recoverable mechanism with prepared/committed evidence and reconciliation after partial failure. | VO-007, EXP-003 |
| PR-210 | Agents shall remain proposers until their evidence or transition is validated by the relevant authority. | VO-007, DEC-023 |
| PR-211 | Theme reporting shall compare planned and actual cost, model mix, flow, Discovery escapes, quality, scope, verification, waivers, and evidence confidence. | VO-006, DEC-018 |
| PR-212 | Budget defaults shall be versioned and recalibrated only through a human-approved theme report. | VO-002, VO-006 |
| PR-213 | If an approved model capability class is unavailable, the method shall use a policy-declared equivalent or pause; it shall not silently downgrade. | VO-005, VO-006 |
| PR-214 | Detailed traces shall be bounded and compacted after theme lock while retaining durable decision, threshold, review, CI, release, and usage summaries. | VO-006, VO-007 |
| PR-215 | A Discovery escape shall pause only the affected dependency subgraph, open an append-only revision, and resume from the earliest invalidated gate. | VO-001, VO-007, INV-011 |

## 9. Quality requirements

| ID | Requirement |
|---|---|
| QR-001 | A normal `LIGHTWEIGHT` Discovery shall require at most one grouped human checkpoint and 30 minutes of human interaction. |
| QR-002 | Validators shall produce deterministic pass/fail results with record/file references and actionable remediation. |
| QR-003 | Gate, lock, approval, schema, and consequential traceability violations shall fail closed. |
| QR-004 | Existing locked TH1/TH2 artefacts and archived backlog snapshots shall remain valid without migration. |
| QR-005 | New schemas shall be versioned and apply prospectively to new or unlocked work. |
| QR-006 | Agents shall remain thin; reusable lifecycle knowledge shall live in canonical skills, schemas, and validators. |
| QR-007 | The method shall remain language-, platform-, provider-, and model-neutral. |
| QR-008 | Incomplete Discovery or requirements work shall resume from persisted status, open questions, accepted decisions, and next action. |
| QR-009 | Repository and external content shall be treated as untrusted evidence data, not instruction authority. |
| QR-010 | Consequential approvals and overrides shall record actor, timestamp, scope, verdict, rationale, and source revision. |
| QR-011 | Local lifecycle validation shall require no network access and complete within five seconds for a normal repository. |
| QR-012 | Documentation, examples, skills, agents, and tests shall describe one consistent six-stage lifecycle. |
| QR-013 | Missing usage or verification evidence shall block completion unless explicitly waived by the applicable authority. |
| QR-014 | Lower AIC shall never compensate for failed safety, quality, scope, or acceptance gates. |
| QR-015 | Security-relevant content, tool output, and evidence shall preserve provenance without exposing credentials or secrets. |
| QR-016 | Optimistic state conflict and recovery behavior shall be deterministic and testable on supported filesystems. |

## 10. Acceptance scenarios

1. An open VP completes Discovery, receives human readiness acceptance, produces
   an approved PRD, and enters architecture.
2. A `BLOCKED` Discovery prevents requirements and plan progression.
3. A low-risk scope completes `LIGHTWEIGHT` Discovery through the standard
   information model within the usability target.
4. A waiver records evidence and approval; material scope expansion invalidates
   it.
5. `plan` receives no accepted dossier or approved PRD and refuses architecture.
6. Paused Discovery resumes without replaying accepted decisions.
7. An attempted edit to a locked artefact fails validation.
8. TH3 acceptance locks TH3 while VP3-level artefacts remain revisable through
   DR/PCR records until TH5 acceptance.
9. A legacy project records a migration assessment and adopts VP3
   prospectively.
10. Instructions embedded in researched content are retained as untrusted
    evidence and are not executed.
11. A consequential requirement lacking upstream traceability fails validation.
12. A `MANUAL` control cannot claim `ENFORCED` without bypass and recovery
    evidence.
13. A stale task packet is rejected after an authoritative source changes.
14. An R3 verification downgrade without human and reviewer acknowledgement is
    rejected.
15. An observed pause threshold blocks the next task until the human records a
    disposition.
16. Two state writers using the same expected revision produce one commit and
    one explicit conflict.
17. A crash after atomic state replacement is reconciled before further work.
18. Missing usage telemetry is labeled estimated or unknown and cannot appear
    as zero.

## 11. Success measures

- 100% of new scopes receive a Discovery disposition.
- 100% of consequential requirements retain upstream traceability.
- No architecture phase begins without accepted Discovery and approved PRD.
- TH3 demonstrates the full human flow through the architecture checkpoint.
- All controls report their actual activation maturity.
- Discovery escapes are classified through TH3-TH5 to establish a baseline
  before a reduction target is set.
- Median R0/R1 AIC reduction of 60% remains a provisional, quality-gated goal
  until sufficient classified work establishes a reliable baseline.
- No session continues beyond twice its warning threshold without explicit
  human authorization.
- Orchestrator overhead is measured and targeted below 30% of normal delivery
  AIC after TH5 instrumentation is available.

## 12. Constraints and accepted deferrals

The Discovery dossier owns the `DEF-###` definitions. This table references
those records and states the required downstream disposition.

| ID | Constraint or deferral |
|---|---|
| DEF-001 | Architecture selects the production telemetry adapter. |
| DEF-002 | Architecture defines overshoot allowances and nested accounting. |
| DEF-003 | Architecture selects the state transition command, schema validator, journal compaction, and conflict UX. |
| DEF-004 | Architecture maps capability classes to available models through versioned policy. |
| DEF-005 | TH3-TH5 shall measure dossier and trace growth before setting permanent retention limits. |

The PRD permits these deferrals because feasibility is established and their
impact is bounded. They must remain explicit in architecture and delivery
planning.

## 13. Non-goals

- Predict every implementation detail before coding.
- Eliminate every later architecture change or Discovery escape.
- Let agents approve consequential product decisions.
- Minimize AIC at the expense of quality, safety, or scope.
- Require full suites, formal methods, mutation testing, or fuzzing for every
  change.
- Guarantee identical telemetry fidelity across all providers in TH3.
- Retroactively convert locked TH1/TH2 artefacts.
- Deliver TH4/TH5 enforcement inside the TH3 foundation release.
- Standardize one technology stack, model vendor, or programming language.

## 14. Architecture freedom

Architecture may choose schemas, commands, libraries, storage layout,
validation implementation, journal format, adapters, and model-policy format.
It may not silently change the lifecycle order, human authorities, theme scope,
lock semantics, authoritative state ownership, or fail-closed requirements.

If a required behavior is infeasible, architecture shall open a Discovery
Revision or Product Change Record rather than weakening it.

## 15. Change control

Consequential changes after approval require an append-only `PCR-###` record
containing:

- reason and requestor;
- affected `PR`, `QR`, decisions, assumptions, risks, and themes;
- Discovery and architecture impact;
- migration and replanning impact;
- human verdict and source revision.

This PRD locks only after TH3, TH4, and TH5 are accepted.
