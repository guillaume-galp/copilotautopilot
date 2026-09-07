---
id: TH3.E2.US4
title: "validate gates check"
type: standard
priority: high
size: M
agents: [developer]
skills: [bdd-stories, the-copilot-build-method]
traceability:
  vision: [VO-001, VO-002, VO-003]
  requirements: [PR-001, PR-002, PR-005, PR-006, PR-010, PR-015, QR-003, QR-008, QR-010]
  adrs: [ADR-002, ADR-003]
  invariants: [INV-001, INV-012]
acceptance-criteria:
  - AC1: "`method validate gates --vp <vp> --stage <discovery|requirements|architecture|planning>` resolves the upstream gate record for the requested stage."
  - AC2: "A gate record that is missing, incomplete, unaccepted, or BLOCKED fails closed with exit 2 and an actionable remediation."
  - AC3: "A gate record missing any of actor, timestamp, scope, verdict, rationale, or source revision is reported invalid."
  - AC4: "A WAIVED Discovery disposition is valid only with a human approval record, an Expiry, and named Invalidation conditions; material scope expansion invalidates it."
  - AC5: "A `## Working state` block with status `in-progress` or `awaiting-human` is reported with its open items and next action, and does not open the gate."
  - AC6: "READY and READY_WITH_DEFERRALS both open the requirements gate once a human acceptance record exists."
depends-on: [TH3.E2.US2]
---

As a lifecycle entrypoint, I want deterministic gate validation so that no stage begins
before its upstream gate is accepted by a human.

## Acceptance criteria

- [ ] AC1: Stage-scoped gate resolution.
- [ ] AC2: Missing, unaccepted, or BLOCKED gates fail closed.
- [ ] AC3: Incomplete gate-record fields reported invalid.
- [ ] AC4: Waiver validity requires approval, expiry, invalidation.
- [ ] AC5: Working state reported without opening the gate.
- [ ] AC6: Both READY verdict forms accepted.

## BDD scenarios

### Happy path: requirements stage opens

Given the VP3 dossier carries an accepted READY_WITH_DEFERRALS acceptance record
When `method validate gates --vp VP3 --stage requirements` runs
Then the command exits 0
And the JSON output names the accepting actor, timestamp, and source revision.

### Edge case: paused Discovery

Given the dossier Working state status is `awaiting-human` with two open DQ items
When the discovery gate is checked
Then the output lists the open items and the next action
And the requirements gate remains closed without an error exit.

### Error case: BLOCKED verdict blocks architecture

Given the dossier verdict is BLOCKED
When `method validate gates --vp VP3 --stage architecture` runs
Then the command exits 2
And the finding states that architecture cannot begin before an accepted readiness verdict.
