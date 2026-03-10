# Copilot Autopilot

A template repository for **AI-driven autonomous product development** using VS Code Copilot agents.

## What is this?

A squad of specialized Copilot agents that collaborate through a structured lifecycle to take a product from **vision** to **working software** — autonomously.

## Development Lifecycle

```
┌─────────────────────────────────────────────────────────────────┐
│  Phase 1: VISION          Human + AI brainstorm                 │
│  /kickstart-vision        → docs/vision_of_product/VP<n>/       │
├─────────────────────────────────────────────────────────────────┤
│  Phase 2: ARCHITECTURE    Architect agent                       │
│  /plan-product            → docs/architecture/ + docs/ADRs/     │
├─────────────────────────────────────────────────────────────────┤
│  Phase 3: PLANNING        Product Owner agent                   │
│  /plan-product            → docs/themes/TH<n>/ + backlog.md     │
├─────────────────────────────────────────────────────────────────┤
│  Phase 4: AUTOPILOT       Orchestrator loops the squad          │
│  /run-autopilot           implement → test → review → repeat    │
│                           epic end: integration + refactor       │
│                           theme end: regression + release notes  │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

1. **Design your product vision**
   - Run `/kickstart-vision` in Copilot Chat
   - Brainstorm freely — capture ideas in `docs/vision_of_product/VP1-mvp/`
   - Add more phases: `VP2-<feature>/`, `VP3-<feature>/`, etc.

2. **Generate architecture and plan**
   - Run `/plan-product` in Copilot Chat
   - Architect agent produces `docs/architecture/` and `docs/ADRs/`
   - Product Owner agent breaks vision into themes/epics/stories and builds `docs/plan/backlog.md`

3. **Launch autopilot**
   - Run `/run-autopilot` in Copilot Chat
   - Orchestrator executes stories autonomously: implement → test → review
   - Session state persists in `docs/plan/backlog.md` — resume anytime

## Agent Squad

| Agent | Role | Phase |
|-------|------|-------|
| **orchestrator** | Autopilot loop: sequencing, parallelism, state management | 4 |
| **product-owner** | Vision → themes → epics → BDD stories | 3 |
| **architect** | Vision → architecture, tech stack, ADRs | 2 |
| **implementer** | Implements one user story per session | 4 |
| **tester** | Writes + runs BDD/TDD tests (story, integration, regression) | 4 |
| **reviewer** | Code review: correctness, security, conventions | 4 |
| **refactorer** | Cleans up tech debt at epic boundaries | 4 |
| **troubleshooter** | Diagnoses and fixes failed stories | 4 |
| **documenter** | Changelogs, release notes, docs updates | 4 |

## Directory Structure

```
docs/
├── vision_of_product/    # Free-form product vision (VP<n> → TH<n>)
├── architecture/         # System design + tech stack
├── ADRs/                 # Architecture Decision Records
├── themes/               # TH<n>/epics/E<m>/stories/US<l>.md
└── plan/
    ├── backlog.md        # Core state file (YAML dependency graph)
    └── session-log.md    # Autopilot session history

.github/
├── agents/               # 9 specialized agents
├── prompts/              # 3 lifecycle prompts
├── hooks/                # Session lifecycle automation
└── copilot-instructions.md
```

## Key Conventions

- **VP<n> ↔ TH<n>**: Vision phases map 1:1 to implementation themes
- **1 story = 1 implementer session**: Stories are sized for single-agent execution
- **Backlog is truth**: `docs/plan/backlog.md` is the only state file the orchestrator trusts
- **Hybrid BDD**: Stories contain acceptance criteria + Given/When/Then scenarios
- **Language-agnostic**: Architect agent chooses tech stack based on your vision

## Using as a Template

1. Create a new repo from this template
2. Start with `/kickstart-vision` to design your product
3. The conventions, agents, and prompts are ready to use immediately

## License

MIT
