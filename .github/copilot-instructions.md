# Copilot Autopilot — Workspace Instructions

## Project Purpose

This is a **template repository** for AI-driven autonomous product development. A squad of specialized Copilot agents collaborates through a 4-phase lifecycle (Vision → Architecture → Planning → Autopilot) to take a product from idea to working software.

## Key Entry Points

| Phase | Prompt | Output |
|-------|--------|--------|
| 1. Vision | `/kickstart-vision` | `docs/vision_of_product/VP<n>/` |
| 2. Architecture | `/plan-product` | `docs/architecture/` + `docs/ADRs/` |
| 3. Planning | `/plan-product` | `docs/themes/TH<n>/` + `docs/plan/backlog.yaml` + `.github/ISSUE_TEMPLATE/` |
| 4. Autopilot | `/run-autopilot` | Autonomous implement → test → review loop (local) |

## Core State

- `docs/plan/backlog.yaml` — **single source of truth** for all orchestration state (pure YAML)
- `docs/plan/session-log.md` — session history for resumability

## Agent Squad

| Agent | Phase | Role |
|-------|-------|------|
| **product-owner** | 3 | Vision → themes/epics/stories + backlog |
| **architect** | 2 | Vision → architecture + ADRs |
| **orchestrator** | 4 | Local autopilot loop: sequencing, state management |
| **developer** | 4 | Implements + tests one user story |
| **reviewer** | 4 | Code review: correctness, security, conventions |
| **troubleshooter** | 4 | Diagnoses + fixes failed stories |

## Skills Reference

Each topic below is owned by exactly one skill. See the skill for canonical details.

| Topic | Skill | Covers |
|-------|-------|--------|
| Lifecycle & conventions | `the-copilot-build-method` | 4-phase lifecycle, VP↔TH mapping, directory conventions, naming conventions, Definition of Done, agent roles |
| Story format | `bdd-stories` | Frontmatter schema, As-a/I-want/So-that, acceptance criteria, BDD scenarios |
| Backlog format | `backlog-management` | YAML schema, status state machine, dependency resolution, sequencing rules |
| Code review | `code-quality` | Review checklist, OWASP security audit |
| Architecture | `architecture-decisions` | ADR format, tech stack analysis, component boundaries |

## Anti-Patterns

- **Never hardcode state in agent memory** — always read/write `docs/plan/backlog.yaml`
- **Never skip the troubleshooter** — failed stories must be fixed before epic completion
- **Never modify vision docs during Phase 4** — vision is frozen for the theme currently in execution (future VPs can be amended at user checkpoints)
- **Never implement multiple stories in one agent session** — 1 story = 1 developer call
- **Never skip the code quality review at epic end** — technical debt compounds
- **Never leave completed theme templates active** — move old theme's `.github/ISSUE_TEMPLATE/TH<n>-*.md` to `ISSUE_TEMPLATE/archive/` at each theme boundary
- **Never edit locked artefacts** — once a theme has `locked: true` in `backlog.yaml`, its VP directory, theme directory, story files, and associated ADR bodies are immutable; the only allowed ADR change is updating the `Status` line to `Superseded by ADR-<NNN>` when creating a new ADR that replaces it — otherwise extend history by creating new VP<n+1>, TH<n+1>, or ADR-<NNN+1> documents instead
