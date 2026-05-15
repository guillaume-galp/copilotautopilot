---
description: "Run focused code review on recent changes with correctness, security, architecture, and tests."
agent: "reviewer"
tools: [read, search, execute, github/github-mcp-server/default]
---

## Agents & Skills

- `@reviewer`: `the-copilot-build-method`, `code-quality`

## Context Gathering

1. detect changed files (`git diff --name-only HEAD~1` or staged diff)
2. if story path provided, read its AC/BDD context
3. read architecture/ADR conventions as needed

## Review Scope

Apply `code-quality` checklist:
- correctness
- OWASP-oriented security
- architecture/ADR compliance
- code quality conventions
- test quality and determinism

## Output

Return: `APPROVE` or `REQUEST_CHANGES`, plus findings by severity (`critical`, `suggestion`, `nit`).
