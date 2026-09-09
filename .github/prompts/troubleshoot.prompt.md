---
description: "Diagnose and fix an epic's unresolved build/test failures after bounded owner repair."
agent: "troubleshooter"
tools: [read, edit, search, execute, github/github-mcp-server/default]
---

## Agents & Skills

- `@troubleshooter`: `the-copilot-build-method`, `bdd-stories`, `code-quality`

## Context Gathering

1. read the epic packet, expected behavior, and prior repair attempts
2. check backlog for failed or blocked epics (legacy story requests retain their original scope)
3. reproduce failure via existing project command(s)

## Diagnosis Flow

1. reproduce
2. categorize (logic/test/build/integration/requirement)
3. identify root cause
4. apply minimal fix
5. re-run relevant tests/build

## Output

Return root cause, category, fix summary, and verification evidence.
