# TH3.E3 - Interactive Discovery and Requirements Workflow

The human-facing workflow: the `discover` and `requirements` interactive
skills, the bounded internal `discovery-facilitator`, `investigator`, and
`requirements-facilitator` agents, and the revised two-stage `plan` with its
human architecture checkpoint.

Depends on TH3.E2 because the skills call `method validate gates` and
`method validate schema` before they open or close a stage.

## Stories

| ID | Title | Priority | Risk | Depends on |
|---|---|---|---|---|
| TH3.E3.US1 | discover interactive skill | high | R2 | - |
| TH3.E3.US2 | discovery-facilitator agent | high | R1 | TH3.E3.US1 |
| TH3.E3.US3 | investigator agent with untrusted-evidence handling | high | R3 | TH3.E3.US1 |
| TH3.E3.US4 | requirements interactive skill | high | R2 | - |
| TH3.E3.US5 | requirements-facilitator agent | medium | R1 | TH3.E3.US4 |
| TH3.E3.US6 | plan stage gating and human architecture checkpoint | high | R2 | TH3.E3.US1, TH3.E3.US4 |

## Requirements

PR-001, PR-002, PR-003, PR-004, PR-005, PR-006, PR-008, PR-009, PR-010, PR-011,
PR-015, PR-016, QR-001, QR-002, QR-003, QR-005, QR-006, QR-008, QR-009,
QR-015.

## ADRs

ADR-002, ADR-004, ADR-005.

## Done when

- Interactive skills own the human dialogue and never approve decisions.
- Bounded agents draft and investigate but hold no approval authority.
- A LIGHTWEIGHT Discovery meets the one-checkpoint, 30-minute target.
- Untrusted retrieved content is retained as evidence and never executed.
- `plan` refuses stage 1 without accepted Discovery and PRD gates and refuses
  stage 2 without recorded architecture acceptance.

## Note on risk

TH3.E3.US3 is R3 because the investigator is the boundary where untrusted
external and repository content enters the lifecycle. Its verification profile
is therefore `integration-plus-failure-injection` and its theme suite policy is
`full-plus-release-readiness`, per the ADR-006 R3 row. Risk tier enforcement
itself activates in TH4; the tier is declared here so the story carries an
honest verification and review profile.

## Execution order

By priority then story order: `US1 -> US2 -> US3 -> US4 -> US6 -> US5`.
TH3.E3.US6 is high priority and becomes ready once US1 and US4 are done, so it
precedes the medium-priority US5.
