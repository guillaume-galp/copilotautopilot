---
name: "TH2.E1 Gitflow operator"
about: "Define and deliver the mandatory gitflow-operator command contract"
title: "TH2.E1: Gitflow operator"
labels: ["theme:TH2", "epic:E1", "copilotautopilot", "gitflow"]
assignees: ""
---

## Epic

TH2.E1 — Gitflow operator

## Goal

Provide the method-owned `gitflow-operator` command contract for consistent
branch-from-develop, MR, CI, squash-merge, and release-note evidence.

## Stories

- [ ] TH2.E1.US1 — Develop-branch workflow for delivery items
- [ ] TH2.E1.US2 — Merge request, CI, and release-note operator

## Acceptance criteria

- Delivery branches start from `develop`.
- Missing `develop` is explicit and non-silent.
- MR descriptions include release-note content.
- Squash merge to `develop` is gated by CI or explicit override.

## Verification

- Tests or fixtures cover branch creation, missing-develop blocking, CI failure
  blocking, and squash-merge evidence.
