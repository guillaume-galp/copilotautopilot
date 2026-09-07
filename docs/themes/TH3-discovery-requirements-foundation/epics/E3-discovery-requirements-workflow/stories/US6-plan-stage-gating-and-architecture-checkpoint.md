---
id: TH3.E3.US6
title: "plan stage gating and human architecture checkpoint"
type: standard
priority: high
size: M
agents: [developer]
skills: [bdd-stories, the-copilot-build-method, architecture-decisions, backlog-management]
traceability:
  vision: [VO-003, VO-004]
  requirements: [PR-001, PR-010, PR-015, QR-003, QR-005, QR-006]
  adrs: [ADR-002, ADR-004]
  invariants: [INV-001]
acceptance-criteria:
  - AC1: "`plan` stage 1 calls `method validate gates --vp <vp> --stage architecture` and exits 2 when the dossier or PRD gate is missing, unaccepted, or BLOCKED."
  - AC2: "Stage 1 produces architecture documents and ADRs only, and creates no theme, epic, story, or backlog entry."
  - AC3: "A recorded human architecture acceptance is required before stage 2 starts; without it stage 2 refuses with exit 2."
  - AC4: "Stage 2 calls `method validate gates --stage planning` and `method validate schema` before the backlog is admitted."
  - AC5: "Stage 2 always appends a new theme number and creates new or unlocked themes with `schema-version: 2`."
  - AC6: "`.github/agents/architect.agent.md` declares its accepted inputs as the accepted Discovery dossier and the approved PRD, replacing the vision-directory-only input, and refuses to start when either gate record is missing, unaccepted, or BLOCKED."
  - AC7: "The same agent file states that architecture formalizes accepted PRD requirements into named `INV-` invariants recorded in `docs/architecture/`, and that it may not introduce a requirement absent from the PRD."
  - AC8: "The same agent file states the architecture gate behavior: it stops at the human architecture checkpoint, writes architecture and ADRs only, creates no theme, epic, story, or backlog entry, and records the acceptance under `## Approval` in `docs/architecture/README.md`."
  - AC9: "A test asserts that `plan` stage 1 dispatches to `architect` only when the dossier and PRD gates are accepted, and that a run without an accepted PRD exits 2 naming the missing gate."
depends-on: [TH3.E3.US1, TH3.E3.US4]
---

As an architect and product owner, I want `plan` split into a gated architecture stage
and a gated planning stage so that architecture formalizes accepted evidence and delivery
planning starts only after a human accepts the architecture.

## Acceptance criteria

- [ ] AC1: Stage 1 blocked without accepted Discovery and PRD gates.
- [ ] AC2: Stage 1 output limited to architecture and ADRs.
- [ ] AC3: Stage 2 blocked without recorded architecture acceptance.
- [ ] AC4: Stage 2 validates the planning gate and the backlog schema.
- [ ] AC5: New theme numbers appended with schema-version 2.
- [ ] AC6: `architect` accepts the dossier and PRD as inputs and refuses without accepted gates.
- [ ] AC7: `architect` formalizes PRD requirements into named `INV-` invariants only.
- [ ] AC8: `architect` stops at the human checkpoint and writes no planning artefacts.
- [ ] AC9: Test pins stage 1 dispatch to the accepted gates.

## BDD scenarios

### Happy path: gated two-stage plan

Given an accepted dossier and an approved PRD
When `plan` runs
Then stage 1 writes architecture and ADRs and stops at the human checkpoint
And stage 2 runs only after the acceptance record exists.

### Edge case: resumed planning in a later session

Given architecture acceptance was recorded in an earlier session
When `plan` is invoked again
Then stage 1 is skipped as already accepted
And stage 2 starts directly with the planning gate check.

### Error case: missing architecture acceptance

Given `docs/architecture/README.md` has no `## Approval` section
When stage 2 is requested
Then `plan` exits 2
And the finding names the missing architecture acceptance record.

### Error case: architect invoked without an approved PRD

Given the Discovery gate is accepted and the PRD gate is unaccepted
When `plan` stage 1 dispatches to `architect`
Then the agent refuses to start and stage 1 exits 2
And the finding names the unaccepted PRD gate record.

### Edge case: architecture invariant without a PRD requirement

Given the architect drafts an `INV-` invariant with no PR or QR requirement behind it
When the architecture checkpoint is prepared
Then the invariant is rejected as an introduced requirement
And the finding names the invariant and the missing PRD reference.
