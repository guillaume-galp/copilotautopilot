---
name: gitflow-operator
description: Provider-neutral Gitflow operations and evidence for GitHub and GitLab repositories.
---

# Gitflow Operator

Within Copilot Autopilot, use `the-copilot-build-method` for lifecycle and
authority; this skill owns Gitflow operations only.

Use the standalone `gitflow-operator` command for branch, status, commit,
merge-request, CI, squash-merge, and release-note operations. This skill owns
Gitflow behavior only; consumers retain their own lifecycle, approval, and
work-dispatch authority.

## Resolve the command

Prefer the repository compatibility launcher if present; otherwise resolve the
standalone installation from `PATH`. If neither exists, stop and report the
missing command; do not silently substitute raw Git commands or another CLI.

```bash
if test -x "$REPO/bin/gitflow-operator"; then
  GITFLOW_OPERATOR="$REPO/bin/gitflow-operator"
else
  GITFLOW_OPERATOR="$(command -v gitflow-operator)" || {
    printf '%s\n' "gitflow-operator not found" >&2
    exit 127
  }
fi
```

## Use

```bash
"$GITFLOW_OPERATOR" --repo <repo> --item-id <id> status
"$GITFLOW_OPERATOR" --repo <repo> --item-id <id> branch-from-develop --branch feature/<slug>
"$GITFLOW_OPERATOR" --repo <repo> --item-id <id> commit --message "feat(<id>): <summary>" .
"$GITFLOW_OPERATOR" --repo <repo> --item-id <id> create-merge-request --title "<title>" --body "<release notes>"
"$GITFLOW_OPERATOR" --repo <repo> --item-id <id> watch-ci
"$GITFLOW_OPERATOR" --repo <repo> --item-id <id> prepare-release-notes --summary "<summary>" --tests "<tests>"
"$GITFLOW_OPERATOR" --repo <repo> --item-id <id> squash-merge-to-develop
```

Provider selection comes from the repository's HTTPS or SSH `origin` remote.
SCM1 uses `GITLAB_LGC_TOKEN`; configured self-managed GitLab uses `GITLAB_TOKEN`
and the `GITFLOW_GITLAB_HOSTS` allowlist. GitHub uses the authenticated `gh`
CLI. Never pass tokens in command arguments or repository URLs.

Every operation emits JSON evidence. A failed gate is nonzero and remains
failed; do not treat a JSON response alone as success. Before squash merge the
operator verifies the current source SHA, target, request state, CI,
discussions, approvals, and protected-branch settings. It never uses an
administrative or gate-bypassing merge option.

Consumers compose this skill with their own delivery process. A Gitflow result
does not grant product acceptance, deployment, release, or production
authorization.

## Credential preflight

Before requesting GitLab authentication, check `~/.secrets/ulysses.env` for the
relevant credential name without displaying its value. Load only the required
credential into the invoking process. Never print tokens, enable shell tracing
around them, place them in arguments or remotes, or store them in evidence.
Credentials do not authorize bypassing server-enforced branch rules.
