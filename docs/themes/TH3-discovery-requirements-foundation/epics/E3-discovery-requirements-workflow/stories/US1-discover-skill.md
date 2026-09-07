---
id: TH3.E3.US1
title: "discover interactive skill"
type: standard
priority: high
size: M
agents: [developer]
skills: [bdd-stories, the-copilot-build-method]
traceability:
  vision: [VO-001, VO-002]
  requirements: [PR-002, PR-006, PR-016, QR-001, QR-008]
  adrs: [ADR-002]
  invariants: [INV-001, INV-012]
acceptance-criteria:
  - AC1: "`.github/skills/discover/SKILL.md` defines the interactive flow: classify the Discovery disposition, frame DQ records, sequence bounded investigations, group human checkpoints, and recommend a readiness verdict."
  - AC2: "The skill calls `method validate gates --vp <vp> --stage discovery` before recommending readiness and refuses to recommend READY or READY_WITH_DEFERRALS while validation fails."
  - AC3: "A LIGHTWEIGHT run targets at most one grouped human checkpoint and 30 minutes of human interaction."
  - AC4: "Every DQ record carries a budget and a stop condition, and any unknown without an owner and a disposition blocks the readiness recommendation."
  - AC5: "The skill delegates all dossier writing to `discovery-facilitator` and never approves a consequential decision itself."
depends-on: []
---

As a human designer, I want an interactive `discover` entrypoint so that foundational
unknowns, assumptions, conflicts, and invariants become visible before requirements and
architecture are committed.

## Acceptance criteria

- [ ] AC1: Interactive flow from classification to verdict recommendation.
- [ ] AC2: Gate validation precedes any readiness recommendation.
- [ ] AC3: LIGHTWEIGHT usability budget of one checkpoint and 30 minutes.
- [ ] AC4: Every DQ bounded; ownerless unknowns block readiness.
- [ ] AC5: Dialogue in the skill, writing in the facilitator, approval with the human.

## BDD scenarios

### Happy path: LIGHTWEIGHT scope in one checkpoint

Given a low-risk scope is classified LIGHTWEIGHT
When `discover` runs
Then the human is asked for one grouped set of decisions
And the session recommends a readiness verdict within the 30-minute target.

### Edge case: waived scope expands materially

Given a scope carries a human-approved WAIVED disposition
And the scope later expands materially
When `discover` re-evaluates the disposition
Then the waiver is invalidated
And the scope is reclassified as LIGHTWEIGHT or FULL before work continues.

### Error case: validation fails before readiness

Given `method validate gates --stage discovery` reports an incomplete acceptance record
When the facilitator proposes READY
Then `discover` refuses to present the recommendation
And it reports the failing finding and its remediation to the human.
