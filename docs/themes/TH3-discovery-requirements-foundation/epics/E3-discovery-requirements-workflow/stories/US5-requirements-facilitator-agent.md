---
id: TH3.E3.US5
title: "requirements-facilitator agent"
type: standard
priority: medium
size: S
agents: [developer]
skills: [bdd-stories, the-copilot-build-method]
traceability:
  vision: [VO-002, VO-003, VO-007]
  requirements: [PR-008, PR-009, PR-011, PR-016, QR-006]
  adrs: [ADR-002]
  invariants: [INV-004]
acceptance-criteria:
  - AC1: "`.github/agents/requirements-facilitator.agent.md` declares responsibility for drafting requirements and traceability from accepted Discovery only."
  - AC2: "Every drafted requirement carries a `Traces` cell resolving to at least one accepted Discovery or vision record."
  - AC3: "The agent references the `product-requirements` skill for schema knowledge and restates none of it."
  - AC4: "The agent proposes PCR records for consequential post-approval changes and never approves them."
  - AC5: "The agent may not choose components, technologies, or interfaces, and may not approve the PRD."
depends-on: [TH3.E3.US4]
---

As a requirements facilitator, I want a thin bounded agent definition so that PRD
drafting stays traceable and stays out of architecture and approval authority.

## Acceptance criteria

- [ ] AC1: Drafting scope limited to accepted Discovery.
- [ ] AC2: Mandatory resolving `Traces` cell per requirement.
- [ ] AC3: Schema referenced, never restated.
- [ ] AC4: PCR records proposed, never approved.
- [ ] AC5: No technology choices, no PRD approval.

## BDD scenarios

### Happy path: traced requirement drafted

Given an accepted DEC record recommends a bounded control
When the facilitator drafts the matching requirement
Then the requirement is measurable
And its `Traces` cell names the vision outcome and the DEC record.

### Edge case: recommendation without evidence

Given a Discovery recommendation has no accepted supporting record
When the facilitator processes it
Then it returns an open question to the `requirements` skill
And it does not draft a requirement from it.

### Error case: technology selection requested

Given the human asks the facilitator to pick a storage engine
When the agent evaluates the request
Then it refuses
And it defers the decision to the architecture stage with a note for the architect.
