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

- `product-owner`: creates themes, executable epic specifications, optional stories, and backlog
- `architect`: defines architecture + ADRs
- `orchestrator`: runs implement → test → review loop
- `developer`: owns one bounded epic through implementation, testing, and repair
- `reviewer`: reviews correctness/security/conventions
- `troubleshooter`: diagnoses epic failures after bounded owner repair

## Skills Map

- Lifecycle, entrypoints, gates, authority, and locks:
  `the-copilot-build-method`
- Epic acceptance and optional story format: `bdd-stories`
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
- One developer assignment = one bounded epic; optional stories are not separate jobs.
- Apply the canonical bounded-repair and escalation rules, not automatic handoffs on failed tests.
- Assess quality once at the epic boundary, using the canonical risk-based review policy.
- At theme boundary, move old templates from `.github/ISSUE_TEMPLATE/TH<n>-*.md` to `.github/ISSUE_TEMPLATE/archive/`.
- Apply the split lock and ADR supersession rules from
  `the-copilot-build-method`; do not infer VP-level lock from one theme alone.

## Token-Efficient Execution Defaults (GPT-5.4+ / Sonnet 4.6+)

- Prefer shortest valid output format that still preserves correctness.
- Reuse existing structure/templates; avoid re-explaining methodology unless asked.
- Summaries over verbose narration; include details only for decisions, risks, or blockers.
- Read only required files/sections before writing.
- Batch independent tool calls in parallel.
