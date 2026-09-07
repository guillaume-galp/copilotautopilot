---
name: "TH2.E2 Build-method gitflow integration"
about: "Make current autopilot skills use gitflow-operator for GitOps work"
title: "TH2.E2: Build-method gitflow integration"
labels: ["theme:TH2", "epic:E2", "copilotautopilot", "skills"]
assignees: ""
---

## Epic

TH2.E2 — Build-method gitflow integration

## Goal

Update the build method and current skills so Gitflow operations use
`gitflow-operator` instead of ad hoc branch/MR/CI/release-note instructions.

## Stories

- [ ] TH2.E2.US1 — Mandatory gitflow-operator usage
- [ ] TH2.E2.US2 — Multi-repo gitflow contract

## Acceptance criteria

- Skills that need branch, commit, MR, CI, or release-note operations call
  `gitflow-operator`.
- Autopilot docs do not own cockpit runtime behavior.
- Multi-repo delivery items aggregate one Gitflow evidence report per repo.

## Verification

- Skill lint/docs checks confirm the mandatory usage language and no stale
  cockpit queue/E2E ownership claims.
