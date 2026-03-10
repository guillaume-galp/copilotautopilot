---
description: "Launch the autopilot orchestrator to execute the product backlog autonomously. Use when: running autopilot, starting autonomous development, executing backlog."
agent: "orchestrator"
tools: [read, edit, search, execute, agent, todo]
---

Begin autonomous execution of the product backlog.

## Pre-flight Checks

Before starting the loop, verify:
1. `docs/plan/backlog.md` exists and contains valid YAML with at least one theme
2. `docs/architecture/` exists with tech stack and component definitions
3. `docs/themes/` contains at least one theme with epics and stories
4. Check `docs/plan/session-log.md` — if it exists, resume from the last completed story

## Execution

Start the autopilot loop as defined in your orchestrator instructions. Process stories in dependency order, running the full cycle (implement → test → review) for each.

Report progress after each story completion.
