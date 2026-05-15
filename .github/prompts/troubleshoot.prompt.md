---
description: "Diagnose and fix failing build/test/story with minimal validated changes."
agent: "troubleshooter"
tools: [read, edit, search, execute, github/github-mcp-server/default]
---

## Agents & Skills

- `@troubleshooter`: `the-copilot-build-method`, `bdd-stories`, `code-quality`

## Context Gathering

1. if story path provided, read expected behavior
2. check backlog for `status: failed` stories
3. reproduce failure via existing project command(s)

## Diagnosis Flow

1. reproduce
2. categorize (logic/test/build/integration/requirement)
3. identify root cause
4. apply minimal fix
5. re-run relevant tests/build

## Output

Return root cause, category, fix summary, and verification evidence.
