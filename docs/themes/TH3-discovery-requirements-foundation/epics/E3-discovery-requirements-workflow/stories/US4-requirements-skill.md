---
id: TH3.E3.US4
title: "requirements interactive skill"
type: standard
priority: high
size: M
agents: [developer]
skills: [bdd-stories, the-copilot-build-method]
traceability:
  vision: [VO-002, VO-003]
  requirements: [PR-008, PR-009, PR-016, QR-002, QR-008]
  adrs: [ADR-002]
  invariants: [INV-001, INV-004]
acceptance-criteria:
  - AC1: "`.github/skills/requirements/SKILL.md` defines the interactive translation of accepted Discovery recommendations into measurable PR and QR requirements."
  - AC2: "The skill refuses to start until `method validate gates --vp <vp> --stage requirements` confirms an accepted readiness verdict."
  - AC3: "The skill refuses to close the approval gate while any requirement lacks measurability or upstream traceability."
  - AC4: "The skill never selects components, technologies, or detailed interfaces and defers those to the architecture stage."
  - AC5: "An in-progress PRD keeps a `## Working state` block, and approved content is never re-elicited."
depends-on: []
---

As a human designer, I want an interactive `requirements` entrypoint so that accepted
Discovery becomes measurable, approved product requirements without absorbing
architecture decisions.

## Acceptance criteria

- [ ] AC1: Interactive translation flow defined.
- [ ] AC2: Entry blocked without an accepted readiness verdict.
- [ ] AC3: Approval blocked on unmeasurable or untraced requirements.
- [ ] AC4: No component, technology, or interface selection.
- [ ] AC5: Resumable through a Working state block.

## BDD scenarios

### Happy path: accepted Discovery becomes an approved PRD

Given a dossier accepted as READY_WITH_DEFERRALS
When `requirements` runs and the human approves the drafted requirements
Then the PRD is written to `docs/requirements/VP<n>-<slug>/PRD.md`
And its `## Approval` table records actor, timestamp, scope, verdict, rationale, and source revision.

### Edge case: deferrals carried forward

Given the dossier holds accepted DEF records
When the PRD is drafted
Then each deferral appears in the constraints section with its required downstream disposition
And no deferral is silently dropped.

### Error case: unmeasurable requirement

Given a drafted requirement states that the system shall be "fast"
When the skill validates measurability
Then approval is refused
And the remediation asks for a concrete threshold or an observable condition.
