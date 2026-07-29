---
name: autopilot
description: 'Run orchestrator to execute backlog in dependency order with recovery and progress reporting.'
---

# Autopilot Skill

## Agents & Skills

- `@orchestrator`: `the-copilot-build-method`, `backlog-management`
- `@developer`: `the-copilot-build-method`, `bdd-stories`
- `@reviewer`: `the-copilot-build-method`, `code-quality`
- `@troubleshooter`: `the-copilot-build-method`, `bdd-stories`, `code-quality`
- `@product-owner`: `the-copilot-build-method`, `bdd-stories`, `backlog-management`

## Pre-flight

Verify:
1. `docs/plan/backlog.yaml` exists, parses, and contains `active-themes` or `archived-themes`
2. `docs/architecture/` exists
3. `docs/themes/` has epics/stories
4. recover any story left `in-progress` per crash-recovery rules
5. if `graphify-out/graph.json` exists and `graphify` is available, pass the
   repository graph path to delegated agents and instruct them to use
   `graphify query "<question>" --graph "$REPO/graphify-out/graph.json"` before
   broad text search for codebase, architecture, and file-relationship questions

## Execution

Run dependency-ordered loop: implement → test → review per story.
Report progress after each completed story.
