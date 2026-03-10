# Copilot Autopilot — Workspace Instructions

## Project Purpose

This is a **template repository** for AI-driven autonomous product development. It provides a squad of specialized Copilot agents that collaborate through a structured lifecycle to take a product from vision to working software.

## Development Lifecycle

### Phase 1 — Vision Design (Human + AI)

The user brainstorms product vision in `docs/vision_of_product/VP<n>-<name>/`. Each VP maps 1:1 to a theme `TH<n>`. This is a free-form canvas — notes, sketches, conversations, wireframes, requirements.

### Phase 2 — Architecture (Architect Agent)

The architect agent reads `docs/vision_of_product/` and produces:
- `docs/architecture/` — system design, tech stack, component diagrams
- `docs/ADRs/` — Architecture Decision Records (numbered ADR-NNN)

### Phase 3 — Planning (Product Owner Agent)

The product-owner agent reads vision + architecture and produces:
- `docs/themes/TH<n>-<name>/` — theme directories with epics and user stories
- `docs/plan/backlog.md` — the **core state file** with YAML dependency graph

### Phase 4 — Autopilot Execution (Orchestrator Agent)

The orchestrator reads `docs/plan/backlog.md` and loops:
1. Pick next eligible story (dependencies resolved)
2. Delegate to implementer → tester → reviewer
3. Update backlog state
4. At epic end: integration tests + refactor + review + changelog
5. At theme end: regression tests + release readiness + release notes + vision revalidation
6. Failed stories → troubleshooter loop until fixed
7. Repeat until all themes complete

## Directory Conventions

```
docs/
├── vision_of_product/          # Phase 1: free-form product vision
│   ├── VP1-mvp/                # Maps to TH1
│   ├── VP2-<feature>/          # Maps to TH2
│   └── ...
├── architecture/               # Phase 2: system design + tech stack
├── ADRs/                       # Phase 2: decision records (ADR-001, ADR-002...)
├── themes/                     # Phase 3: implementation plan
│   ├── TH1-<theme>/
│   │   ├── README.md           # Theme overview
│   │   └── epics/
│   │       ├── E1-<epic>/
│   │       │   ├── README.md   # Epic overview
│   │       │   └── stories/
│   │       │       ├── US1-<story>.md    # User story (hybrid BDD)
│   │       │       └── US2-<story>.md
│   │       └── E2-<epic>/
│   └── TH2-<theme>/
└── plan/
    └── backlog.md              # Core state file (YAML dependency graph + status)
```

## Naming Conventions

| Entity | Pattern | Example |
|--------|---------|---------|
| Vision Phase | `VP<n>-<slug>/` | `VP1-mvp/` |
| Theme | `TH<n>-<slug>/` | `TH1-core-platform/` |
| Epic | `E<m>-<slug>/` | `E1-user-auth/` |
| User Story | `US<l>-<slug>.md` | `US1-login-form.md` |
| ADR | `ADR-<NNN>-<slug>.md` | `ADR-001-database-choice.md` |

VP<n> maps 1:1 to TH<n> by convention.

## Backlog State File (`docs/plan/backlog.md`)

This is the **single source of truth** for orchestration. It contains YAML frontmatter with the dependency graph and status of every theme, epic, and story.

### Status Values

| Symbol | Meaning |
|--------|---------|
| `todo` | Not started |
| `in-progress` | Currently being worked on |
| `done` | Completed and verified |
| `failed` | Failed, needs troubleshooting |
| `blocked` | Blocked by dependency |

## User Story Format (Hybrid BDD)

Each `US<l>-<slug>.md` file contains:

```markdown
---
id: US1
title: "<story title>"
status: todo
agents: [implementer, tester, reviewer]    # agents assigned to this story
skills: [bdd-stories]                      # skills agents should load
acceptance-criteria:
  - AC1: "<criterion>"
  - AC2: "<criterion>"
depends-on: []                             # story IDs this depends on
---

# US1 — <Story Title>

**As a** <role>, **I want** <goal>, **so that** <benefit>.

## Acceptance Criteria

- [ ] AC1: <criterion>
- [ ] AC2: <criterion>

## BDD Scenarios

### Scenario: <name>
- **Given** <context>
- **When** <action>
- **Then** <outcome>

### Scenario: <name>
- **Given** <context>
- **When** <action>
- **Then** <outcome>
```

## Definition of Done

A user story is `done` when ALL of:
1. Code compiles / lints clean
2. All BDD scenario tests pass
3. All acceptance criteria verified
4. Build artifacts produce successfully
5. Code review agent approves
6. Relevant documentation updated

An epic is `done` when ALL of:
1. All stories are `done`
2. Integration test suite passes across all stories in the epic
3. Refactor pass completed and reviewer approves
4. Documenter produces epic changelog entry

A theme is `done` when ALL of:
1. All epics are `done`
2. Regression test suite passes across all epics
3. Release readiness check passes (all artifacts build, docs complete, no `failed` stories)
4. Documenter produces theme release notes
5. Product-owner revalidates theme against original vision in `docs/vision_of_product/VP<n>/`

## Agent Squad

| Agent | Phase | Role | Skills |
|-------|-------|------|--------|
| **product-owner** | 3 | Vision → themes → epics → stories + backlog | `the-copilot-build-method`, `bdd-stories`, `backlog-management` |
| **architect** | 2 | Vision → architecture + ADRs | `the-copilot-build-method`, `architecture-decisions` |
| **orchestrator** | 4 | Autopilot loop: sequencing, parallelism, state management | `the-copilot-build-method`, `backlog-management` |
| **implementer** | 4 | Implements one user story | `the-copilot-build-method`, `bdd-stories` |
| **tester** | 4 | Writes + runs BDD/TDD tests | `the-copilot-build-method`, `bdd-stories` |
| **reviewer** | 4 | Code review against conventions + security | `the-copilot-build-method`, `code-quality` |
| **refactorer** | 4 | Refactors at epic boundaries | `the-copilot-build-method`, `code-quality` |
| **troubleshooter** | 4 | Diagnoses + fixes failed stories | `the-copilot-build-method`, `bdd-stories`, `code-quality` |
| **documenter** | 4 | Docs, changelogs, release notes | `the-copilot-build-method` |

Full squad details: [.github/agents/README.md](agents/README.md)

## Skills

| Skill | Purpose |
|-------|---------|
| `the-copilot-build-method` | Core methodology: lifecycle phases, VP↔TH mapping, conventions, Definition of Done |
| `bdd-stories` | Story format, acceptance criteria, Given/When/Then patterns, story sizing |
| `backlog-management` | YAML backlog format, status state machine, dependency resolution |
| `code-quality` | Review checklist, OWASP security audit, refactoring patterns |
| `architecture-decisions` | ADR format, tech stack analysis, component boundaries |

## Anti-Patterns

- **Never hardcode state in agent memory** — always read/write `docs/plan/backlog.md`
- **Never skip the troubleshooter** — failed stories must be fixed before epic completion
- **Never modify vision docs during Phase 4** — vision is frozen once planning begins
- **Never implement multiple stories in one agent session** — 1 story = 1 implementer call
- **Never skip the refactor at epic end** — technical debt compounds
