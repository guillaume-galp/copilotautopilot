---
id: TH2.E1.US1
title: "Develop-branch workflow for delivery items"
type: standard
priority: high
size: M
agents: [developer]
skills: [bdd-stories, the-copilot-build-method]
acceptance-criteria:
  - AC1: "The gitflow-operator can create one feature/fix branch per affected repo from develop for a delivery item."
  - AC2: "The gitflow-operator reports branch status, current commit, dirty files, and delivery item ID."
  - AC3: "Repos without develop receive an explicit bootstrap or blocked-state report instead of silent fallback."
depends-on: []
---

As an orchestrator, I want delivery items to start from `develop` so that all delivery
work follows the same integration branch policy.

## Acceptance criteria

- [ ] AC1: Branch-from-develop works per affected repo.
- [ ] AC2: Status reports include branch, commit, dirty state, and queue ID.
- [ ] AC3: Missing `develop` is explicit and non-silent.

## BDD scenarios

### Happy path: branch from develop

Given a repo has a `develop` branch
And a delivery item is ready for implementation
When the gitflow-operator creates a feature branch
Then the branch starts from `develop`
And the branch metadata references the delivery item ID.

### Edge case: multi-repo delivery item

Given a delivery item affects two repos
When the gitflow-operator starts the item
Then each repo receives one feature/fix branch
And all branches share the same delivery item ID.

### Error case: develop missing

Given a repo has no `develop` branch
When the gitflow-operator runs branch-from-develop
Then it reports a blocked state
And it does not silently branch from `main` or `master`.
