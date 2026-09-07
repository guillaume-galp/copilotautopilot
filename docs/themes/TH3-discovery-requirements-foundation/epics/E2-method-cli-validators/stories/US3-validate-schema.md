---
id: TH3.E2.US3
title: "validate schema check"
type: standard
priority: high
size: M
agents: [developer]
skills: [bdd-stories, backlog-management]
traceability:
  vision: [VO-007]
  requirements: [PR-015, QR-002, QR-003, QR-004, QR-005, QR-006]
  adrs: [ADR-003, ADR-004]
  invariants: [INV-002, INV-003]
acceptance-criteria:
  - AC1: "`method validate schema` validates `docs/plan/backlog.yaml` against schema v2 including IDs, status vocabulary, dependencies, risk, model-route, verification, review-profile, budgets, usage, evidence, and confidence."
  - AC2: "An absent `schema-version` on a locked or archived theme is treated as version 1 and passes without migration, covering TH1, TH2, and their archive snapshots."
  - AC3: "A new or unlocked theme that is not `schema-version: 2` fails closed with exit 2."
  - AC4: "Every story `file:` path is resolved against the repository and a dangling path fails closed with exit 2."
  - AC5: "Findings are deterministic and name the offending YAML path plus a remediation string."
  - AC6: "`.github/skills/backlog-management/SKILL.md` is updated to own and document schema v2: the `schema-version` key, the `risk`, `model-route`, `verification`, `review-profile`, `budgets`, `usage`, `evidence`, and `confidence` blocks, and the version 1 compatibility rule that absent `schema-version` on a locked or archived theme means version 1."
  - AC7: "The same skill documents the `blocked` status and the transitions `in-progress -> blocked -> in-progress`, states that `blocked` is used for pause dispositions and Discovery-escape subgraph pauses, and keeps the version 1 status vocabulary valid for locked and archived themes."
  - AC8: "The validator reads its status vocabulary and its required v2 key set from the schema documented in `backlog-management`, and a test asserts that every key and status the skill documents is accepted and that a status outside the documented vocabulary fails closed with exit 2."
depends-on: [TH3.E2.US1]
---

As an orchestrator, I want backlog schema validation so that runtime state stays
well-formed while locked and archived version 1 themes remain valid without migration.

## Acceptance criteria

- [ ] AC1: Full schema v2 field validation.
- [ ] AC2: Version 1 coexistence for locked and archived themes.
- [ ] AC3: Unlocked theme without version 2 fails closed.
- [ ] AC4: Dangling story paths fail closed.
- [ ] AC5: Deterministic findings with YAML path and remediation.
- [ ] AC6: `backlog-management` owns and documents schema v2 with v1 compatibility.
- [ ] AC7: `blocked` status and its transitions documented in the same skill.
- [ ] AC8: Validator vocabulary pinned to the skill and asserted by tests.

## BDD scenarios

### Happy path: mixed-version backlog validates

Given `backlog.yaml` holds TH3 at schema-version 2 and archived TH1 and TH2 without a version
When `method validate schema` runs
Then the command exits 0
And no migration is requested for the archived themes.

### Edge case: archived snapshot lacks v2 fields

Given `docs/plan/backlog-archive/TH1.yaml` has no risk, model-route, or budgets keys
When the check runs
Then the snapshot is validated under version 1 rules
And the missing v2 fields are not reported as violations.

### Edge case: story paused with the blocked status

Given a TH3 story declares `status: blocked` as documented by `backlog-management`
When the check runs
Then the status is accepted as part of the schema v2 vocabulary
And no finding is raised.

### Error case: unlocked theme on the old schema

Given an unlocked theme declares no `schema-version`
When the check runs
Then the command exits 2
And the finding names the theme and the required `schema-version: 2`.

### Error case: status outside the documented vocabulary

Given a story declares `status: paused`
When the check runs
Then the command exits 2
And the finding names the YAML path and lists the vocabulary documented in `.github/skills/backlog-management/SKILL.md`.
