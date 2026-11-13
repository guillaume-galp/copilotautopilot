---
name: gitflow-operator
description: "Mandatory Gitflow tool contract for autopilot skills: branch from develop, status, commit, create merge request, watch CI, squash-merge to develop, and prepare release notes."
---

# Gitflow Operator Skill

Use `the-copilot-build-method` as the canonical lifecycle, gate, authority, and
split-lock contract; this skill defines delivery Gitflow only and does not
restate that contract.

## Scope

Use this skill whenever an autopilot delivery needs Git operations: branch,
status, commit, merge request, CI watching, squash merge, or release-note
preparation.

This skill does not own cockpit runtime orchestration, worker dispatch, queue
state, or cockpit-specific clearance gates.

## Command Surface

Resolve the executable for the repository being changed before using this
surface. Prefer `<repo>/bin/gitflow-operator` when it is executable; otherwise
resolve `gitflow-operator` with `command -v` from `PATH`. Use the resolved
path for every operation. If neither exists, stop and report the missing
command; do not silently substitute raw Git commands or another CLI.

```bash
if test -x "$REPO/bin/gitflow-operator"; then
  GITFLOW_OPERATOR="$REPO/bin/gitflow-operator"
else
  GITFLOW_OPERATOR="$(command -v gitflow-operator)" || {
    printf '%s\n' "gitflow-operator not found in repository bin/ or PATH" >&2
    exit 127
  }
fi

"$GITFLOW_OPERATOR" --repo <repo> --item-id <id> branch-from-develop --branch feature/<slug>
"$GITFLOW_OPERATOR" --repo <repo> --item-id <id> status
"$GITFLOW_OPERATOR" --repo <repo> --item-id <id> commit --message "feat(<id>): <summary>" .
"$GITFLOW_OPERATOR" --repo <repo> --item-id <id> create-merge-request --title "<title>" --body "<release notes>"
"$GITFLOW_OPERATOR" --repo <repo> --item-id <id> watch-ci
"$GITFLOW_OPERATOR" --repo <repo> --item-id <id> prepare-release-notes --summary "<summary>" --tests "<tests>"
"$GITFLOW_OPERATOR" --repo <repo> --item-id <id> squash-merge-to-develop
```

## Rules

- Branches start from `develop`; missing `develop` is a blocked state, not a
  silent fallback to `main` or `master`.
- Every command emits JSON evidence.
- Completion requires Gitflow evidence or an explicit not-applicable rationale.
- Multi-repo delivery items collect one evidence report per affected repo.
