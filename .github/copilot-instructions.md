# Copilot Autopilot — Workspace Instructions

## Purpose

Template repo for autonomous product development. The authoritative stage
order, entrypoints, artefacts, gates, authorities, and split lock scope are
defined only by the `the-copilot-build-method` skill. The method has six
stages exposed through five entrypoints; use that skill's canonical map rather
than restating the stage sequence here. Legacy prompt names are deprecated;
use the entrypoints named by the canonical skill.

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

- Lifecycle, entrypoints, gates, authority, and locks:
  `the-copilot-build-method`
- Story format: `bdd-stories`
- Backlog rules: `backlog-management`
- Review/security: `code-quality`
- ADR/architecture: `architecture-decisions`

## Code Intelligence

If `graphify-out/graph.json` exists and the `graphify` CLI is available, use
`graphify query "<question>" --graph "$REPO/graphify-out/graph.json"` before
broad text search for codebase, architecture, file-relationship, and
project-content questions. If project-specific instructions define a
higher-priority code intelligence system, follow that first; otherwise prefer
Graphify over grep-style search.

## Hard Rules

- Always read/write state from `docs/plan/backlog.yaml` (never memory-only state).
- One developer session = one story.
- Never skip troubleshooter for failed stories.
- Never skip code-quality review at epic boundary.
- At theme boundary, move old templates from `.github/ISSUE_TEMPLATE/TH<n>-*.md` to `.github/ISSUE_TEMPLATE/archive/`.
- Apply the split lock and ADR supersession rules from
  `the-copilot-build-method`; do not infer VP-level lock from one theme alone.

## Token-Efficient Execution Defaults (GPT-5.4+ / Sonnet 4.6+)

- Prefer shortest valid output format that still preserves correctness.
- Reuse existing structure/templates; avoid re-explaining methodology unless asked.
- Summaries over verbose narration; include details only for decisions, risks, or blockers.
- Read only required files/sections before writing.
- Batch independent tool calls in parallel.
