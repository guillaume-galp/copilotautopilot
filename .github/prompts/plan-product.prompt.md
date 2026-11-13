---
description: "Run the current gated architecture or delivery-planning stage."
agent: "agent"
tools: [read, edit, search, agent, todo, execute, web, github/github-mcp-server/default]
---

Invoke the `plan` skill for the requested stage and follow its current
instructions, including all upstream gates and human approvals. Do not start
planning automatically after architecture or bypass a missing approval. This
prompt is a compatibility alias, not a separate lifecycle.
