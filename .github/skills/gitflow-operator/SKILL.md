---
name: gitflow-operator
description: Provider-neutral Gitflow operations and evidence for GitHub and GitLab repositories.
---

# Gitflow Operator

Use the standalone `gitflow-operator` command for branch, status, commit,
merge-request, CI, squash-merge, and release-note operations. This skill owns
Gitflow behavior only; consumers retain their own lifecycle, approval, and
work-dispatch authority.

When composed with Copilot Autopilot, `the-copilot-build-method` owns its
applicable lifecycle contract; standalone Gitflow does not impose that method.

## Repository-native defaults

This tool does not require a backlog, standard `docs/`, admission, mission
packet, product approval record or item ID. Do not invent them for an existing
repository. Follow its real instructions and the user's authorized scope.
Local status, branches and requested commits do not imply deployment/release.
An explicit request can already authorize a push or merge; do not ask for the
same approval again merely in a different format. Never infer extra authority.

## Resolve the command

Prefer the repository compatibility launcher if present; otherwise resolve the
standalone installation from `PATH`. If neither exists, the launcher cannot
find its installation, or the provider/operation is unsupported, report that
limitation and use native Git/provider tooling for authorized work unless
repository instructions explicitly require this operator. Preserve equivalent
applicable checks and truthful results. Never use fallback to evade failed CI,
approvals, authentication, protection rules or an actual authority refusal.

```bash
if test -x "$REPO/bin/gitflow-operator"; then
  GITFLOW_OPERATOR="$REPO/bin/gitflow-operator"
else
  GITFLOW_OPERATOR="$(command -v gitflow-operator)" || {
    printf '%s\n' "gitflow-operator unavailable; use explicit native fallback" >&2
    GITFLOW_OPERATOR=""
  }
fi
```

If resolution fails, use the explicit fallback above; a missing optional tool
is not a reason to block unrelated implementation.

## Follow repository branches

The base/target is resolved offline, in this order:
1. Command `--base` (branch creation) or `--target` (MR/CI/merge).
2. Repository Git config `gitflow.operator.base`, then `gitflow.branch.develop`.
3. One existing local/origin `develop` or `development` branch.
4. `gitflow.branch.master`, then the cached `origin/HEAD` default.
5. One existing local/origin `main` or `master` branch.

Ambiguity requires one specific branch choice, not a lifecycle gate. A custom
branch such as `integration` can be supplied explicitly or configured once:
`git config gitflow.operator.base integration`. Never create/rename `develop`
or `main` to make a repository fit the tool.

Branch creation uses the local base if available, otherwise the cached origin
base, without fetching or claiming remote freshness. It refuses a dirty tree
instead of stashing/discarding user work. Any valid topic-branch name is
allowed; detached HEAD and source-equals-target are rejected. The legacy
`branch-from-develop` and `squash-merge-to-develop` command names remain aliases
for auto-resolved branches, not demands for a literal `develop`.

## Use

```bash
"$GITFLOW_OPERATOR" --repo <repo> status
"$GITFLOW_OPERATOR" --repo <repo> branch --branch feature/<slug>
"$GITFLOW_OPERATOR" --repo <repo> branch --base development --branch bugfix/<slug>
"$GITFLOW_OPERATOR" --repo <repo> commit --message "fix: <summary>" <changed-paths>
"$GITFLOW_OPERATOR" --repo <repo> create-merge-request --target development --title "<title>" --body "<release notes>"
"$GITFLOW_OPERATOR" --repo <repo> watch-ci --target development
"$GITFLOW_OPERATOR" --repo <repo> prepare-release-notes --summary "<summary>" --tests "<tests>"
"$GITFLOW_OPERATOR" --repo <repo> squash-merge --target development
```

`--item-id` is optional metadata; use an existing ID when relevant. Targets
may be omitted when conventions are unambiguous. Stage only intended paths.

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
