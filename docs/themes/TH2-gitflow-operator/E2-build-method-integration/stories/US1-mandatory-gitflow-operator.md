---
id: TH2.E2.US1
title: "Mandatory gitflow-operator usage"
type: standard
priority: high
size: S
agents: [developer]
skills: [the-copilot-build-method, bdd-stories]
acceptance-criteria:
  - AC1: "The build method states that current autopilot skills MUST use gitflow-operator for branch, commit, MR, CI, and release-note operations."
  - AC2: "Autopilot docs do not claim ownership of cockpit runtime orchestration, worker dispatch, or cockpit-specific clearance gates."
  - AC3: "A delivery item cannot be marked GitOps-complete without gitflow-operator evidence or an explicit not-applicable rationale."
depends-on: []
---

As an orchestrator, I want current autopilot skills to use `gitflow-operator` so
that GitOps delivery is consistent and token-efficient.

## Acceptance criteria

- [ ] AC1: Current autopilot skills MUST use `gitflow-operator` for Gitflow operations.
- [ ] AC2: Autopilot docs do not own cockpit runtime behavior.
- [ ] AC3: GitOps completion requires `gitflow-operator` evidence or a not-applicable rationale.

## BDD scenarios

### Happy path: Gitflow operation needed

Given a delivery item requires a branch, commit, MR, CI watch, or release-note update
When an autopilot skill plans the work
Then it invokes or delegates to `gitflow-operator`
And records the returned evidence.

### Edge case: no Gitflow operation needed

Given a delivery item does not touch repository state
When completion is evaluated
Then the skill records an explicit Gitflow not-applicable rationale.

### Error case: ad hoc GitOps

Given a skill hand-writes branch or MR instructions without `gitflow-operator`
When the delivery is reviewed
Then the item fails the GitOps method check.
