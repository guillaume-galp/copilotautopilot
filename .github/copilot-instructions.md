# Copilot Autopilot — Workspace Instructions

## Purpose

Template repo for autonomous product development with a 4-phase lifecycle:
1. Vision (`kickstart` skill)
2. Architecture (`plan` skill step 1)
3. Planning (`plan` skill step 2)
4. Autopilot execution (`autopilot` skill)

Core lifecycle entrypoints are skills (`kickstart`, `plan`, `autopilot`); legacy prompt names (`/kickstart-vision`, `/plan-product`, `/run-autopilot`) are deprecated and should not be used.

## Core State (authoritative)

- `docs/plan/backlog.yaml` — runtime source of truth for status/dependencies
- `docs/plan/backlog-archive/TH<n>.yaml` — completed theme snapshots (referenced by backlog.yaml)
- `docs/plan/session-log.md` — recent resumability log (supplementary)

## Agent Roles

- `product-owner`: creates themes/epics/stories + backlog
- `architect`: defines architecture + ADRs
- `orchestrator`: runs implement → test → review loop
- `developer`: implements one story per session
- `reviewer`: reviews correctness/security/conventions
- `troubleshooter`: fixes failed stories

## Skills Map

- Lifecycle/conventions: `the-copilot-build-method`
- Lifecycle entrypoints: `kickstart`, `plan`, `autopilot`
- Story format: `bdd-stories`
- Backlog rules: `backlog-management`
- Review/security: `code-quality`
- ADR/architecture: `architecture-decisions`

## Hard Rules

- Always read/write state from `docs/plan/backlog.yaml` (never memory-only state).
- One developer session = one story.
- Never skip troubleshooter for failed stories.
- Never skip code-quality review at epic boundary.
- At theme boundary, move old templates from `.github/ISSUE_TEMPLATE/TH<n>-*.md` to `.github/ISSUE_TEMPLATE/archive/`.
- If theme has `locked: true`, associated VP/theme/story artefacts and ADR bodies are immutable.
  - Only allowed locked-ADR edit: update `Status:` to `Superseded by ADR-<NNN>` when creating a new ADR.

## Token-Efficient Execution Defaults (GPT-5.4+ / Sonnet 4.6+)

- Prefer shortest valid output format that still preserves correctness.
- Reuse existing structure/templates; avoid re-explaining methodology unless asked.
- Summaries over verbose narration; include details only for decisions, risks, or blockers.
- Read only required files/sections before writing.
- Batch independent tool calls in parallel.
