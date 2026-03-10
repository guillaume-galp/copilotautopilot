---
name: the-copilot-build-method
description: 'The overarching autonomous product development methodology. Covers the 4-phase lifecycle (Vision → Architecture → Planning → Autopilot), VP↔TH mapping, Directory conventions, Definition of Done, agent squad roles, and lifecycle ceremonies. Use when: understanding the methodology, onboarding to the process, checking conventions, verifying Definition of Done.'
---

# The Copilot Build Method

An autonomous product development methodology powered by a squad of specialized AI agents operating through a structured lifecycle.

## Philosophy

- **Vision-first**: Products start as free-form ideas, not code
- **Architecture before implementation**: Design decisions are documented before a single line of code
- **BDD-driven**: Every feature is specified as testable scenarios before implementation
- **Incremental delivery**: Products are built in vision phases (VP<n>) that map to implementation themes (TH<n>)
- **Autonomous execution**: The orchestrator agent loops the squad through implement → test → review cycles
- **Persistent state**: All progress is tracked in `docs/plan/backlog.md` for resumability
- **Ceremony at boundaries**: Epic and theme completions trigger quality gates (integration tests, refactor, release notes)

## The 4 Phases

### Phase 1 — Vision Design (Human + AI)
- Prompt: `/kickstart-vision`
- Output: `docs/vision_of_product/VP<n>-<name>/`
- Free-form brainstorming canvas — no rigid structure
- Each VP<n> maps 1:1 to a theme TH<n>

### Phase 2 — Architecture (Architect Agent)
- Prompt: `/plan-product` (step 1)
- Output: `docs/architecture/` + `docs/ADRs/`
- System design, tech stack selection, component boundaries
- Every significant decision recorded as an ADR

### Phase 3 — Planning (Product Owner Agent)
- Prompt: `/plan-product` (step 2)
- Output: `docs/themes/TH<n>/` + `docs/plan/backlog.md`
- Vision decomposed into themes → epics → user stories
- Stories are hybrid BDD (acceptance criteria + Given/When/Then)
- Backlog YAML is the dependency graph + status state machine

### Phase 4 — Autopilot Execution (Orchestrator Agent)
- Prompt: `/run-autopilot`
- Loop: implement → test → review per story
- Epic end ceremony: integration tests + refactor + review + changelog
- Theme end ceremony: regression tests + release readiness + release notes + vision revalidation
- Failed stories: troubleshooter loop (max 3 attempts, then escalate)

## VP ↔ TH Mapping Convention

| Vision Phase | Theme | Relationship |
|:---|:---|:---|
| `docs/vision_of_product/VP1-mvp/` | `docs/themes/TH1-<name>/` | 1:1 by convention |
| `docs/vision_of_product/VP2-<feat>/` | `docs/themes/TH2-<name>/` | 1:1 by convention |

## Definition of Done

### Story Done
1. Code compiles / lints clean
2. All BDD scenario tests pass
3. All acceptance criteria verified
4. Build artifacts produce successfully
5. Code review agent approves
6. Relevant documentation updated

### Epic Done (Story DoD + ceremony)
1. All stories `done`
2. Integration test suite passes across all epic stories
3. Refactor pass completed + reviewer approves
4. Documenter produces epic changelog entry

### Theme Done (Epic DoD + ceremony)
1. All epics `done`
2. Regression test suite passes across all theme epics
3. Release readiness: artifacts build, docs complete, no `failed` stories
4. Documenter produces theme release notes
5. Product-owner revalidates theme against `docs/vision_of_product/VP<n>/`

## Naming Conventions

| Entity | Pattern | Example |
|:---|:---|:---|
| Vision Phase | `VP<n>-<slug>/` | `VP1-mvp/` |
| Theme | `TH<n>-<slug>/` | `TH1-core-platform/` |
| Epic | `E<m>-<slug>/` | `E1-user-auth/` |
| User Story | `US<l>-<slug>.md` | `US1-login-form.md` |
| ADR | `ADR-<NNN>-<slug>.md` | `ADR-001-database-choice.md` |

## Agent Squad Roles

| Agent | Phase | Responsibility |
|:---|:---|:---|
| orchestrator | 4 | Autopilot loop, sequencing, state management |
| product-owner | 3 | Vision → themes/epics/stories + backlog |
| architect | 2 | Vision → architecture + ADRs |
| implementer | 4 | Codes one user story per session |
| tester | 4 | BDD tests, integration tests, regression tests |
| reviewer | 4 | Code review: correctness, security, conventions |
| refactorer | 4 | Epic-boundary technical debt cleanup |
| troubleshooter | 4 | Diagnoses + fixes failed stories |
| documenter | 4 | Changelogs, release notes, docs updates |

## Anti-Patterns

- Never hardcode state in agent memory — read/write `docs/plan/backlog.md`
- Never skip the troubleshooter — failed stories must be fixed before epic completion
- Never modify vision docs during Phase 4
- Never implement multiple stories in one agent session
- Never skip the refactor at epic end
