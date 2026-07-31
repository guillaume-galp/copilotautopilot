# Release: TH2 Gitflow Operator

## Summary

TH2 adds a mandatory `gitflow-operator` contract for autopilot Gitflow work.
Current autopilot skills now use the operator for branch, commit, merge-request,
CI, squash-merge, and release-note operations instead of repeating ad hoc GitOps
instructions.

## Epics Delivered

- TH2.E1 — Gitflow operator
- TH2.E2 — Build-method gitflow integration

## Breaking Changes

- None.

## Migration Notes

- Delivery workflows that need Gitflow evidence should call
  `bin/gitflow-operator`.
- Repos without `develop` are reported as blocked instead of silently falling
  back to `main` or `master`.
