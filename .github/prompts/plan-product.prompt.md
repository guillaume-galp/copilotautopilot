---
description: "Transform product vision into architecture and implementation plan. Runs architect then product-owner agents sequentially. Use when: planning implementation, generating backlog, creating architecture from vision."
agent: "agent"
tools: [read, edit, search, agent, todo, execute, web]
---

## Agents & Skills

| Agent | Skills |
|-------|--------|
| @architect | `the-copilot-build-method`, `architecture-decisions` |
| @product-owner | `the-copilot-build-method`, `bdd-stories`, `backlog-management` |

Execute the planning pipeline to transform vision into an actionable backlog.

## Pipeline

### Step 1 — Architecture
Invoke the @architect agent to analyze `docs/vision_of_product/` and produce:
- `docs/architecture/` — system design, tech stack, components
- `docs/ADRs/` — architecture decision records

### Step 2 — User Stories & Issue Templates
Invoke the @product-owner agent to break the vision + architecture into:
- `docs/themes/TH<n>-<name>/` — theme/epic/story hierarchy
- `docs/plan/backlog.yaml` — YAML dependency graph with all stories
- `.github/ISSUE_TEMPLATE/TH<n>-E<m>-<slug>.md` — one GitHub issue template per epic (required for Phase 4B Loom weaving)

> **Archiving rule**: When re-running `/plan-product` for a new theme, the @product-owner agent must move the previous theme's templates into `.github/ISSUE_TEMPLATE/archive/` before generating new ones, so only the current theme's epics are active.

After both steps complete, display a summary of:
- Number of themes, epics, and stories created
- Number of issue templates generated (one per epic)
- Dependency graph overview
- Estimated implementation order
