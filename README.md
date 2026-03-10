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
│  /plan-product            → docs/themes/TH<n>/ + backlog.yaml   │
├─────────────────────────────────────────────────────────────────┤
│  Phase 4: AUTOPILOT       Orchestrator loops the squad          │
│  /run-autopilot           implement → test → review → repeat    │
│                           epic end: integration + review          │
│                           theme end: full test suite + release    │
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
   - Product Owner agent breaks vision into themes/epics/stories and builds `docs/plan/backlog.yaml`

3. **Launch autopilot**
   - Run `/run-autopilot` in Copilot Chat in "Autopilot" mode
   - Orchestrator executes stories autonomously: implement → test → review
   - Session state persists in `docs/plan/backlog.yaml` — resume anytime

## Agent Squad

| Agent | Role | Phase |
|-------|------|-------|
| **orchestrator** | Autopilot loop: sequencing, parallelism, state management | 4 |
| **product-owner** | Vision → themes → epics → BDD stories | 3 |
| **architect** | Vision → architecture, tech stack, ADRs | 2 |
| **developer** | Implements + tests one user story per session | 4 |
| **reviewer** | Code review: correctness, security, conventions | 4 |
| **troubleshooter** | Diagnoses and fixes failed stories | 4 |

## Directory Structure

```
docs/
├── vision_of_product/    # Free-form product vision (VP<n> → TH<n>)
├── architecture/         # System design + tech stack
├── ADRs/                 # Architecture Decision Records
├── themes/               # TH<n>/epics/E<m>/stories/US<l>.md
└── plan/
    ├── backlog.yaml      # Core state file (pure YAML dependency graph)
    └── session-log.md    # Autopilot session history

.github/
├── agents/               # 6 specialized agents
├── prompts/              # 3 lifecycle prompts
├── hooks/                # Session lifecycle automation
└── copilot-instructions.md
```

## Key Conventions

- **VP<n> ↔ TH<n>**: Vision phases map 1:N to implementation themes
- **1 story = 1 developer session**: Stories are sized for single-agent execution
- **Backlog is truth**: `docs/plan/backlog.yaml` is the only state file the orchestrator trusts
- **Hybrid BDD**: Stories contain acceptance criteria + Given/When/Then scenarios
- **Language-agnostic**: Architect agent chooses tech stack based on your vision

## Using as a Template

1. Create a new repo from this template
2. Start with `/kickstart-vision` to design your product
3. The conventions, agents, and prompts are ready to use immediately

## License

MIT
