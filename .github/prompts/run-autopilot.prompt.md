---
description: "Run orchestrator to execute backlog in dependency order with recovery and progress reporting."
agent: "orchestrator"
tools: [read, edit, search, execute, agent, todo, github/github-mcp-server/default]
---

## Agents & Skills

- `@orchestrator`: `the-copilot-build-method`, `backlog-management`
- `@developer`: `the-copilot-build-method`, `bdd-stories`
- `@reviewer`: `the-copilot-build-method`, `code-quality`
- `@troubleshooter`: `the-copilot-build-method`, `bdd-stories`, `code-quality`
- `@product-owner`: `the-copilot-build-method`, `bdd-stories`, `backlog-management`

## Pre-flight

Verify:
1. `docs/plan/backlog.yaml` exists, parses, and contains themes
2. `docs/architecture/` exists
3. `docs/themes/` has epics/stories
4. recover any story left `in-progress` per crash-recovery rules

## Execution

Run dependency-ordered loop: implement → test → review per story.
Report progress after each completed story.
