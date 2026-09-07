---
id: TH3.E4.US1
title: "Activation ledger and validate maturity check"
type: standard
priority: high
size: M
agents: [developer]
skills: [bdd-stories, the-copilot-build-method]
traceability:
  vision: [VO-006, VO-007]
  requirements: [PR-013, PR-015, QR-002, QR-003, QR-010]
  adrs: [ADR-008, ADR-003]
  invariants: [INV-010]
acceptance-criteria:
  - AC1: "`docs/plan/activation-ledger.yaml` records every control with id, name, requirement references, state, effective point, limitations, evidence, proposer, and promoter."
  - AC2: "States are SPECIFIED, MANUAL, INSTRUMENTED, ENFORCED, and VERIFIED, and every TH3 entry reports the state actually implemented in the repository."
  - AC3: "`method validate maturity` fails closed with exit 2 when a claimed state lacks its evidence or contradicts what the repository implements."
  - AC4: "Promotion to ENFORCED requires bypass-attempt evidence showing the control failing closed and recovery evidence showing that the same check passes again once the fixture is restored to a valid state; promotion to VERIFIED requires evidence from a completed theme."
  - AC5: "A control is promoted only by a human record carrying actor, timestamp, and a record reference."
  - AC6: "For each of CTL-001, CTL-002, CTL-003, and CTL-014, the ENFORCED evidence list names both a bypass-attempt artefact and a restore-and-pass artefact, and a missing restore-and-pass artefact fails closed with exit 2."
depends-on: []
---

As a human designer, I want an honest control activation ledger so that release claims
match implemented reality while the method self-hosts before enforcement exists.

## Acceptance criteria

- [ ] AC1: Ledger records the full control set with required fields.
- [ ] AC2: Five states, each reporting the implemented reality.
- [ ] AC3: Unsupported claims fail closed.
- [ ] AC4: Bypass-attempt plus restore-and-pass evidence for ENFORCED; completed-theme evidence for VERIFIED.
- [ ] AC5: Attributable human promotion only.
- [ ] AC6: CTL-001, CTL-002, CTL-003, CTL-014 each name both evidence artefacts.

## BDD scenarios

### Happy path: gate control promoted to ENFORCED

Given `method validate gates` exists
And a bypass-attempt test drives it to exit 2 on an invalid fixture
And the same check exits 0 once the fixture is restored to a valid state
When the human promotes the gate control to ENFORCED
Then the ledger records both the bypass-attempt and the restore-and-pass evidence paths with the promoting actor and timestamp
And `method validate maturity` exits 0.

### Edge case: manual control with a named operator

Given the activation-ledger control itself is operated by a human at theme boundaries
When it claims MANUAL
Then the check accepts the claim with its effective point and limitations
And no automation evidence is required.

### Error case: unsupported ENFORCED claim

Given a control claims ENFORCED with an empty evidence list
When `method validate maturity` runs
Then the command exits 2
And the finding names the control and the missing bypass and recovery evidence.

### Error case: bypass evidence without recovery evidence

Given CTL-003 claims ENFORCED with a bypass-attempt artefact and no restore-and-pass artefact
When `method validate maturity` runs
Then the command exits 2
And the finding names CTL-003 and the missing restore-and-pass evidence.
