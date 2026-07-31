# ADR-001: Gitflow Operator Responsibility

## Status

Accepted

## Context

`copilotautopilot` owns the autonomous product delivery method and its current
skills. It should not own cockpit runtime orchestration, worker pane
coordination, or cockpit-specific clearance gates. Those responsibilities belong
outside this methodology repo.

The methodology still needs repeatable branch, commit, merge-request, CI, and
release-note operations. To avoid repeated overseer boilerplate, the current
skills must use a new `gitflow-operator` tool for GitOps work.

## Decision

`copilotautopilot` introduces a mandatory `gitflow-operator` tool contract for
its current skills.

The `gitflow-operator` contract includes:

- `branch-from-develop`
- `status`
- `commit`
- `create-merge-request`
- `squash-merge-to-develop`
- `watch-ci`
- `prepare-release-notes`

For each delivery item:

1. Create one feature/fix branch per affected repo from `develop`.
2. Keep commits scoped to the delivery item.
3. Create a merge request with release-note content in the description.
4. Watch CI.
5. Squash merge back to `develop` as one commit when gates pass.
6. Return Git evidence to the orchestrator.

All autopilot skills that need Git branch, commit, MR, CI, or release-note
operations must use `gitflow-operator` instead of hand-writing ad hoc GitOps
instructions.

## Consequences

### Positive

- Clear ownership boundary: `copilotautopilot` owns Gitflow method support and
  does not absorb cockpit runtime behavior.
- Lower orchestrator token spend through a reusable tool contract.
- Multi-repo delivery items can keep consistent branch/MR evidence.

### Negative

- Introducing `develop` requires migration guidance for repos that currently use
  only `main` or `master`.
- Provider-specific behavior must be abstracted or explicitly scoped.

### Risks

- Squash-only policy must be enforced consistently to avoid noisy history.
- If skills bypass `gitflow-operator`, the method can regress into ad hoc GitOps
  prompts.

## Alternatives Considered

### Put gitflow operations in copilotcockpit

Rejected. Gitflow belongs to the product delivery method, not the tmux cockpit
harness.

### Keep ad hoc Git instructions in each skill

Rejected. Repeated GitOps prompt boilerplate is token-expensive and inconsistent.

### Make cockpit runtime semantics part of copilotautopilot

Rejected. Runtime orchestration, worker dispatch, and cockpit-specific clearance
gates are not part of the autopilot methodology repo.
