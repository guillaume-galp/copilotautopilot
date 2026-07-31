# TH2 Changelog — Gitflow Operator

## Epic TH2.E1 — Gitflow operator

### Stories Completed

- TH2.E1.US1 — Develop-branch workflow for delivery items
- TH2.E1.US2 — Merge request, CI, and release-note operator

### Key Changes

- Added `bin/gitflow-operator`.
- Added JSON evidence for status, branch-from-develop, commit, MR creation, CI
  watch, release-note preparation, and squash merge.
- Added tests for missing `develop`, branch creation, and release-note evidence.

## Epic TH2.E2 — Build-method gitflow integration

### Stories Completed

- TH2.E2.US1 — Mandatory gitflow-operator usage
- TH2.E2.US2 — Multi-repo gitflow contract

### Key Changes

- Added `.github/skills/gitflow-operator/SKILL.md`.
- Updated build-method, autopilot, orchestrator, and developer guidance to use
  `gitflow-operator`.
- Added tests that enforce the skill contract and prevent stale cockpit queue
  ownership claims in autopilot docs.
