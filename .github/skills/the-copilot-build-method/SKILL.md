---
name: the-copilot-build-method
description: 'Lifecycle conventions for autonomous product development: 4 phases, VP↔TH mapping, DoD, roles, ceremonies, and lock rules.'
---

# The Copilot Build Method

## Lifecycle

1. Vision (`kickstart` skill) → `docs/vision_of_product/VP<n>-<slug>/`
2. Architecture (`plan` skill step 1) → `docs/architecture/`, `docs/ADRs/`
3. Planning (`plan` skill step 2) → `docs/themes/TH<n>-<slug>/`, `docs/plan/backlog.yaml`, issue templates
4. Autopilot (`autopilot` skill) → implement → test → review loop

## Core Principles

- Vision-first, then architecture, then implementation.
- `docs/plan/backlog.yaml` is authoritative orchestration state.
- 1 story per developer session.
- Failed story must go through troubleshooter.
- Ceremonies happen at epic/theme boundaries.

## VP ↔ TH Mapping

- VP can map to one or more themes (1:N).
- Theme numbering is sequential and independent of VP numbering.

## Definition of Done

### Story
- compile/lint/tests pass as applicable
- acceptance criteria verified
- relevant docs updated
- review completed (lightweight for trivial stories)

### Epic
- all stories done
- small epic (≤3): full epic tests + brief changelog
- large epic (4+): integration checks + reviewer quality pass + detailed changelog

### Theme
- all epics done
- full suite + release readiness checks
- deployment readiness validation if deployment doc exists
- release notes + vision revalidation
- archive old issue templates
- user checkpoint (accept/reject/amend next VP)
- set `locked: true` on accepted theme

## Naming

- VP: `VP<n>-<slug>/`
- Theme: `TH<n>-<slug>/`
- Epic: `E<m>-<slug>/`
- Story: `US<l>-<slug>.md`
- ADR: `ADR-<NNN>-<slug>.md`

## Lock / Immutability Rules

When a theme is `locked: true`:
- VP/theme/story artefacts for that theme are immutable
- ADR body is immutable
- only allowed edit on old ADR: update `Status:` to `Superseded by ADR-<NNN>` when creating a replacement ADR
- new work extends history with new VP/TH/ADR IDs

## Token-Efficient Defaults (GPT-5.4+ / Sonnet 4.6+)

- Load only needed files/sections.
- Prefer concise structured outputs.
- Avoid repeating lifecycle explanations unless requested.
- Batch independent tool calls.

## Code Intelligence Defaults

When a repository has `graphify-out/graph.json` and the `graphify` CLI is
available, agents should treat Graphify as the first-choice local index for
codebase, architecture, file-relationship, and project-content questions:

```bash
graphify query "<question>" --graph "$REPO/graphify-out/graph.json"
```

Use Graphify before broad text search when the task asks where behavior lives,
how files relate, what components exist, or what implementation patterns are
already present. If a project provides higher-priority code intelligence
instructions (for example CodeGraph/transversal skills for cross-service impact
analysis), follow those first; otherwise prefer Graphify over grep-style search.

If no Graphify graph exists, or the query result is too low-confidence to act on,
fall back to normal repository search and source-file reads. Keep generated
graphs out of commits unless the target repository explicitly versions
`graphify-out/`; use `graphify update "$REPO"` or Graphify hooks to refresh the
index after meaningful code changes.
