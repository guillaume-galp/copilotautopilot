---
id: TH3.E4.US2
title: "Migration assessment command and artefact"
type: standard
priority: medium
size: S
agents: [developer]
skills: [bdd-stories, the-copilot-build-method]
traceability:
  vision: [VO-007]
  requirements: [PR-014, PR-015, QR-004]
  adrs: [ADR-008]
  invariants: [INV-003, INV-005]
acceptance-criteria:
  - AC1: "`method migrate assess` writes `docs/plan/migration-assessment.md` for a repository already using the four-stage method."
  - AC2: "The assessment reports current stage coverage, missing gate records, control maturity, and the prospective adoption point."
  - AC3: "The command never fabricates historical Discovery, verification, or usage evidence; absent history is reported as `unknown`."
  - AC4: "Re-running the command on unchanged input reproduces the same artefact content and touches no other file."
depends-on: []
---

As a maintainer of an existing repository, I want a migration assessment so that VP3 is
adopted prospectively without inventing history for work that predates it.

## Acceptance criteria

- [ ] AC1: Command generates the assessment artefact.
- [ ] AC2: Coverage, gaps, maturity, and adoption point reported.
- [ ] AC3: Absent history reported as unknown, never fabricated.
- [ ] AC4: Idempotent regeneration scoped to the artefact.

## BDD scenarios

### Happy path: assess this repository

Given a repository with VP1 and VP2 delivered under the four-stage method
When `method migrate assess` runs
Then the assessment lists the stages covered, the missing gate records, and the next VP as the adoption point
And no existing locked artefact is modified.

### Edge case: no Discovery history at all

Given the repository has no `docs/discovery/` directory
When the assessment runs
Then Discovery coverage is reported as `unknown` for all prior scopes
And the adoption point is the next new scope.

### Error case: write target inside a locked theme

Given the requested output path resolves inside a locked theme directory
When the command runs
Then it exits 2
And the finding states that locked artefacts cannot receive generated content.
