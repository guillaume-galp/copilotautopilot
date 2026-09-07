---
id: TH3.E4.US6
title: "validate docs check and lifecycle documentation tests"
type: standard
priority: high
size: M
agents: [developer]
skills: [bdd-stories, the-copilot-build-method]
traceability:
  vision: [VO-007]
  requirements: [PR-015, QR-002, QR-003, QR-012]
  adrs: [ADR-003, ADR-002]
  invariants: [INV-002]
acceptance-criteria:
  - AC1: "`method validate docs` scans active method content, namely `README.md`, `.github/copilot-instructions.md`, `.github/skills/`, `.github/agents/`, and `tests/`, and emits one JSON object on stdout listing every file checked."
  - AC2: "The check fails closed with exit 2 on a four-stage lifecycle statement or a stale entrypoint handoff in active content, and each finding names the file, the line number, and the required six-stage stage map."
  - AC3: "Archived and locked content, namely TH1 and TH2 artefacts, `docs/architecture/history/`, `.github/agents/archive/`, and `.github/ISSUE_TEMPLATE/archive/`, is excluded and never produces a finding."
  - AC4: "Tests pin the documented lifecycle to the stage map owned by `the-copilot-build-method`, with at least one passing fixture and one failing fixture for each of stale stage list, stale handoff, and excluded archived path."
  - AC5: "`method validate docs` is registered in `method validate all` and the repository run over the TH3.E4.US3 migration inventory exits 0."
depends-on: [TH3.E4.US3]
---

As a method maintainer, I want the documented lifecycle enforced by a check so that the
TH3.E4.US3 migration cannot silently regress once new documentation is written.

## Acceptance criteria

- [ ] AC1: Active content scanned with one JSON object listing files checked.
- [ ] AC2: Stale lifecycle text and stale handoffs fail closed with file and line.
- [ ] AC3: Archived and locked content excluded.
- [ ] AC4: Passing and failing fixtures for each finding class.
- [ ] AC5: Registered in `validate all` and green on this repository.

## BDD scenarios

### Happy path: migrated documentation passes

Given the TH3.E4.US3 migration inventory reports every active file consistent
When `method validate docs` runs
Then the command exits 0
And the JSON output lists the files checked.

### Edge case: locked theme keeps its historical text

Given a locked TH2 document still describes the four-stage lifecycle
When the check runs
Then the file is excluded as locked history
And no finding is raised for it.

### Edge case: newly added active skill

Given a new active skill file is added after the migration
When the check runs
Then the file is included in the scanned set
And it is evaluated against the owned stage map.

### Error case: an active skill still lists four phases

Given an active skill enumerates vision, architecture, planning, and autopilot as the lifecycle
When the check runs
Then the command exits 2
And the finding names the file, the line, and the required six-stage stage map.

### Error case: stale entrypoint handoff

Given an active skill hands off from `kickstart` to `plan`
When the check runs
Then the command exits 2
And the finding names the file, the line, and the required `discover` handoff.
