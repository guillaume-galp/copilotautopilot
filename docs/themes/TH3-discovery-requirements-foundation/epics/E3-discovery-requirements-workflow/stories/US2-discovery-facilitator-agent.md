---
id: TH3.E3.US2
title: "discovery-facilitator agent"
type: standard
priority: high
size: S
agents: [developer]
skills: [bdd-stories, the-copilot-build-method]
traceability:
  vision: [VO-001, VO-002]
  requirements: [PR-003, PR-005, PR-006, PR-016, QR-006, QR-008]
  adrs: [ADR-002]
  invariants: [INV-012]
acceptance-criteria:
  - AC1: "`.github/agents/discovery-facilitator.agent.md` declares responsibility for investigation sequencing, evidence taxonomy, dossier coherence, and the readiness recommendation."
  - AC2: "The agent references the `discovery-dossier` skill for all schema knowledge and restates none of it."
  - AC3: "A consequential assumption, preference, decision, deferral, override, or risk acceptance is written only after an attributable human acceptance carrying actor, timestamp, scope, verdict, rationale, and source revision."
  - AC4: "The agent updates the dossier `## Working state` block after every checkpoint so a paused Discovery resumes without replaying accepted decisions."
  - AC5: "The agent may not approve a consequential decision and may not author the PRD."
depends-on: [TH3.E3.US1]
---

As a discovery facilitator, I want a thin bounded agent definition so that dossier
coherence is maintained without the agent acquiring approval authority.

## Acceptance criteria

- [ ] AC1: Responsibility statement covering sequencing and recommendation.
- [ ] AC2: Schema knowledge referenced, never restated.
- [ ] AC3: Consequential records require attributable human acceptance.
- [ ] AC4: Working state maintained at every checkpoint.
- [ ] AC5: No approval authority, no PRD authorship.

## BDD scenarios

### Happy path: accepted decision is recorded

Given the human accepts a proposed decision at a checkpoint
When the facilitator records it
Then a DEC record is written with actor, timestamp, scope, verdict, rationale, and source revision
And the Working state lists the decision under accepted records.

### Edge case: resume a paused Discovery

Given a Discovery session ended with three accepted decisions and one open DQ
When a new session starts
Then the facilitator reads the Working state
And re-elicits only the open DQ.

### Error case: approval requested from the agent

Given the orchestrator asks the facilitator to approve a deferral
When the agent evaluates the request
Then it refuses
And it returns a grouped human checkpoint request instead.
