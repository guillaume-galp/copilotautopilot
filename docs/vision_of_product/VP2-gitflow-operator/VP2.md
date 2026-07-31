# VP2: Gitflow Operator for Autopilot Delivery

## Problem statement

Autopilot delivery needs disciplined GitOps execution without making the
orchestrator spend boilerplate tokens on branch, commit, merge-request, CI, and
release-note instructions. The methodology needs a mandatory `gitflow-operator`
tool that the current skills use whenever delivery work touches Gitflow.

## Target users and personas

- **Human operator / product owner**: sees delivery work progress through a
  predictable branch and merge lifecycle.
- **Orchestrator / overseer**: invokes a concise `gitflow-operator` instead of hand-writing branch,
  commit, MR, CI, and release-note instructions.
- **Developer / troubleshooter agents**: work inside one scoped feature/fix
  branch per delivery item.
- **Reviewer**: reviews one squashable delivery unit at a time.

## Core features

- `gitflow-operator` command surface:
  `branch-from-develop`, `status`, `commit`, `create-merge-request`,
  `squash-merge-to-develop`, `watch-ci`, and `prepare-release-notes`.
- Branch policy:
  each delivery item creates one feature/fix branch per affected repo from
  `develop`, then returns to `develop` as one squash commit.
- Multi-repo delivery items create one branch per affected repo while sharing
  the same delivery item ID and report.
- Build-method integration:
  existing autopilot skills MUST use `gitflow-operator` for Gitflow operations.
- Completion evidence:
  no delivery item is complete without acceptance criteria, review, CI/MR state,
  local delivery evidence, and release-note evidence where applicable.

## Success criteria

- Every build-method delivery item has traceable Git branch/MR/release-note state.
- Every feature/fix branch starts from `develop` and merges back via one squash
  commit.
- Multi-repo items remain correlated by delivery item ID.
- The orchestrator spends fewer tokens on repeated GitOps boilerplate.
- Autopilot skills consistently use `gitflow-operator` instead of ad hoc GitOps
  instructions.

## Constraints

- `copilotautopilot` owns `gitflow-operator` semantics and current-skill
  integration.
- Cockpit runtime orchestration, worker dispatch, and cockpit-specific clearance
  gates are out of scope for `copilotautopilot`.
- Existing `main`/`master` release flows must not break when `develop` is
  introduced.
- Initial Git provider scope should be explicit and may start with the provider
  already used by the target repo.

## Open questions

- Should the first `gitflow-operator` implementation support GitHub only,
  GitLab only, or both behind a provider adapter?
- How should `develop` be bootstrapped in repos that only have `main` or
  `master`?
- Which delivery metadata fields must the `gitflow-operator` receive from each
  calling skill?
