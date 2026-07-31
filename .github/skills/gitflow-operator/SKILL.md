---
name: gitflow-operator
description: "Mandatory Gitflow tool contract for autopilot skills: branch from develop, status, commit, create merge request, watch CI, squash-merge to develop, and prepare release notes."
---

# Gitflow Operator Skill

## Scope

Use this skill whenever an autopilot delivery needs Git operations: branch,
status, commit, merge request, CI watching, squash merge, or release-note
preparation.

This skill does not own cockpit runtime orchestration, worker dispatch, queue
state, or cockpit-specific clearance gates.

## Command Surface

```bash
bin/gitflow-operator --repo <repo> --item-id <id> branch-from-develop --branch feature/<slug>
bin/gitflow-operator --repo <repo> --item-id <id> status
bin/gitflow-operator --repo <repo> --item-id <id> commit --message "feat(<id>): <summary>" .
bin/gitflow-operator --repo <repo> --item-id <id> create-merge-request --title "<title>" --body "<release notes>"
bin/gitflow-operator --repo <repo> --item-id <id> watch-ci
bin/gitflow-operator --repo <repo> --item-id <id> prepare-release-notes --summary "<summary>" --tests "<tests>"
bin/gitflow-operator --repo <repo> --item-id <id> squash-merge-to-develop
```

## Rules

- Branches start from `develop`; missing `develop` is a blocked state, not a
  silent fallback to `main` or `master`.
- Every command emits JSON evidence.
- Completion requires Gitflow evidence or an explicit not-applicable rationale.
- Multi-repo delivery items collect one evidence report per affected repo.
