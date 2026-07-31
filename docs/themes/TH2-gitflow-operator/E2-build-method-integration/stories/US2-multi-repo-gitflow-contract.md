---
id: TH2.E2.US2
title: "Multi-repo gitflow contract"
type: standard
priority: medium
size: M
agents: [developer]
skills: [the-copilot-build-method, bdd-stories]
acceptance-criteria:
  - AC1: "The method defines how one delivery item maps to multiple repo branches and reports."
  - AC2: "The method separates cockpit queue/E2E ownership from autopilot gitflow-operator ownership."
  - AC3: "The method defines the minimum metadata exchanged between autopilot skills and gitflow-operator."
depends-on: [TH2.E1.US1, TH2.E2.US1]
---

As an orchestrator, I want a multi-repo gitflow contract so that a single
delivery item can span repos without losing traceability.

## Acceptance criteria

- [ ] AC1: Multi-repo delivery mapping is defined.
- [ ] AC2: Ownership split is explicit.
- [ ] AC3: Exchanged metadata is specified.

## BDD scenarios

### Happy path: two repos, one delivery item

Given a delivery item affects `copilotcockpit` and `copilotautopilot`
When the item is planned
Then each repo gets its own branch/MR evidence
And the delivery item aggregates both reports.

### Edge case: one repo completes first

Given a multi-repo delivery item has two branches
And one repo is merged while the other is still failing CI
When the orchestrator evaluates GitOps completion
Then the delivery item remains incomplete.

### Error case: missing repo report

Given a delivery item declares an affected repo
But the gitflow-operator returns no evidence for that repo
When GitOps completion is evaluated
Then the item is blocked.
