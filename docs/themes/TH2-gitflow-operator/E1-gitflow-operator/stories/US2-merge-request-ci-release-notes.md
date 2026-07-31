---
id: TH2.E1.US2
title: "Merge request, CI, and release-note operator"
type: standard
priority: high
size: M
agents: [developer]
skills: [bdd-stories, the-copilot-build-method]
acceptance-criteria:
  - AC1: "The gitflow-operator can create a merge request for the delivery item with release-note content in the description."
  - AC2: "The gitflow-operator watches CI and reports pass/fail/blocker state."
  - AC3: "The gitflow-operator squash-merges to develop only after gates pass or an explicit human override is recorded."
depends-on: [TH2.E1.US1]
---

As an orchestrator, I want MR, CI, and release-note operations bundled into a
gitflow-operator so that every delivery item has traceable evidence.

## Acceptance criteria

- [ ] AC1: MR creation includes release-note content.
- [ ] AC2: CI watch reports pass/fail/blocker state.
- [ ] AC3: Squash merge to `develop` is gated.

## BDD scenarios

### Happy path: merge after CI green

Given a delivery item branch has committed changes
And CI passes
When the gitflow-operator squash-merges the MR
Then `develop` receives one squash commit
And the report includes MR, CI, and commit evidence.

### Edge case: explicit override

Given CI has a documented non-critical issue
And the human records an override
When the gitflow-operator proceeds
Then the override appears in the delivery evidence.

### Error case: CI fails

Given CI fails
When the gitflow-operator evaluates merge readiness
Then it refuses to squash-merge
And reports the failure as a blocker.
