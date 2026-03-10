---
description: "Manually trigger a code review on recent changes or specific files. Use when: reviewing code, checking implementation quality, security audit."
agent: "reviewer"
tools: [read, search]
---

Perform a code review on the specified files or recent changes.

## Skills

Load: `the-copilot-build-method`, `code-quality`

## Process

1. Identify the scope: specific files, a story's implementation, or an epic's changes
2. Apply the full review checklist from the `code-quality` skill:
   - Correctness against acceptance criteria
   - Security (OWASP Top 10)
   - Architecture compliance
   - Code quality and conventions
   - Test coverage adequacy
3. Return a structured review report with verdict: APPROVE or REQUEST_CHANGES
