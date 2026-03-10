# The Autopilot Squad

The Copilot Build Method is powered by a squad of 9 specialized agents, each with a focused role in the product development lifecycle.

## Squad Overview

```
                    ┌─────────────────┐
                    │   ORCHESTRATOR   │  Phase 4: Autopilot Loop
                    │  (squad leader)  │
                    └────────┬────────┘
                             │ delegates to
        ┌────────────────────┼────────────────────┐
        │                    │                    │
   ┌────▼─────┐       ┌─────▼─────┐       ┌─────▼──────┐
   │IMPLEMENTER│──────►│  TESTER   │──────►│  REVIEWER   │  Per-story cycle
   └───────────┘       └───────────┘       └─────────────┘
        │                                        │
        │ on failure                             │ at epic end
   ┌────▼──────────┐                      ┌─────▼──────┐
   │ TROUBLESHOOTER │                      │ REFACTORER  │  Epic ceremony
   └───────────────┘                      └─────────────┘
                                                │
                                          ┌─────▼──────┐
                                          │ DOCUMENTER  │  Changelogs & notes
                                          └────────────┘

   ┌──────────┐     ┌───────────────┐
   │ ARCHITECT │────►│ PRODUCT OWNER │  Phases 2-3: Design & Plan
   └──────────┘     └───────────────┘
```

## Agent Details

### Orchestrator
- **Phase**: 4 (Autopilot Execution)
- **Role**: Squad leader. Reads the backlog, sequences work, delegates to subagents, manages the full lifecycle loop.
- **Skills**: `the-copilot-build-method`, `backlog-management`
- **Delegates to**: All other agents
- **Invocable**: By user (via `/run-autopilot`)

### Product Owner
- **Phase**: 3 (Planning)
- **Role**: Transforms product vision into themes, epics, and BDD user stories. Builds the backlog. Revalidates vision at theme completion.
- **Skills**: `the-copilot-build-method`, `bdd-stories`, `backlog-management`
- **Invocable**: By user or orchestrator

### Architect
- **Phase**: 2 (Architecture)
- **Role**: Analyzes product vision and produces system architecture, tech stack decisions, and ADRs.
- **Skills**: `the-copilot-build-method`, `architecture-decisions`
- **Invocable**: By user (via `/plan-product`)

### Implementer
- **Phase**: 4 (Autopilot Execution)
- **Role**: Implements exactly one user story per session. Writes production code, runs builds.
- **Skills**: `the-copilot-build-method`, `bdd-stories`
- **Invocable**: Subagent only (orchestrator delegates)

### Tester
- **Phase**: 4 (Autopilot Execution)
- **Role**: Writes and runs BDD/TDD tests. Operates in three modes: story testing, epic integration testing, theme regression testing.
- **Skills**: `the-copilot-build-method`, `bdd-stories`
- **Invocable**: Subagent only (orchestrator delegates)

### Reviewer
- **Phase**: 4 (Autopilot Execution)
- **Role**: Code review for correctness, security (OWASP Top 10), architecture compliance, and conventions.
- **Skills**: `the-copilot-build-method`, `code-quality`
- **Invocable**: Subagent only (orchestrator delegates), or manually via `/review`

### Refactorer
- **Phase**: 4 (Epic Completion)
- **Role**: Refactors code at epic boundaries to reduce technical debt. Behavior-preserving changes only.
- **Skills**: `the-copilot-build-method`, `code-quality`
- **Invocable**: Subagent only (orchestrator delegates), or manually via `/refactor`

### Troubleshooter
- **Phase**: 4 (Failure Recovery)
- **Role**: Diagnoses and fixes failed stories. Root-cause analysis, minimal fix, verification.
- **Skills**: `the-copilot-build-method`, `bdd-stories`, `code-quality`
- **Invocable**: Subagent only (orchestrator delegates), or manually via `/troubleshoot`

### Documenter
- **Phase**: 4 (Epic/Theme Completion)
- **Role**: Produces changelogs at epic boundaries and release notes at theme boundaries. Updates project documentation.
- **Skills**: `the-copilot-build-method`
- **Invocable**: Subagent only (orchestrator delegates)

## Agent ↔ Skill Matrix

| Agent | `the-copilot-build-method` | `bdd-stories` | `backlog-management` | `code-quality` | `architecture-decisions` |
|:---|:---:|:---:|:---:|:---:|:---:|
| orchestrator | ✓ | | ✓ | | |
| product-owner | ✓ | ✓ | ✓ | | |
| architect | ✓ | | | | ✓ |
| implementer | ✓ | ✓ | | | |
| tester | ✓ | ✓ | | | |
| reviewer | ✓ | | | ✓ | |
| refactorer | ✓ | | | ✓ | |
| troubleshooter | ✓ | ✓ | | ✓ | |
| documenter | ✓ | | | | |

## Lifecycle Prompts

| Prompt | Agent(s) | Phase |
|:---|:---|:---|
| `/kickstart-vision` | ask (interactive) | 1 |
| `/plan-product` | architect → product-owner | 2-3 |
| `/run-autopilot` | orchestrator → all | 4 |
| `/refactor` | refactorer → reviewer | 4 (manual) |
| `/review` | reviewer | 4 (manual) |
| `/review-docs` | reviewer | 4 (manual) |
| `/troubleshoot` | troubleshooter | 4 (manual) |
