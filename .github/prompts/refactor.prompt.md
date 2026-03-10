---
description: "Manually trigger a refactoring pass on a specific epic or set of files. Use when: cleaning up code, reducing tech debt, refactoring after epic completion."
agent: "agent"
tools: [read, edit, search, execute, agent]
---

Perform a targeted refactoring pass.

## Agents & Skills

| Agent | Skills |
|-------|--------|
| @refactorer | `the-copilot-build-method`, `code-quality` |
| @reviewer | `the-copilot-build-method`, `code-quality` |

## Process

1. Invoke **@refactorer** on the specified scope (epic directory or file list)
2. Once refactoring is complete, invoke **@reviewer** to approve or request changes
3. If reviewer requests changes, loop @refactorer → @reviewer until approved
4. Run the full test suite to confirm no regressions
5. Report final status
