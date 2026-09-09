---
description: "Run focused code review on recent changes with correctness, security, architecture, and tests."
agent: "reviewer"
tools: [read, search, execute, github/github-mcp-server/default]
---

## Agents & Skills

- `@reviewer`: `the-copilot-build-method`, `code-quality`

## Context Gathering

1. detect changed files (`git diff --name-only HEAD~1` or staged diff)
2. read the epic specification, acceptance criteria, and optional child coverage (legacy story requests retain their original scope)
3. read architecture/ADR conventions as needed

## Review Scope

Apply `code-quality` checklist:
- correctness
- OWASP-oriented security
- architecture/ADR compliance
- code quality conventions
- test quality and determinism

Review the integrated epic once. Follow the risk-based policy in
`the-copilot-build-method`; a completed native independent review does not
need a duplicate custom-agent pass.

## Output

Return: `APPROVE` or `REQUEST_CHANGES`, plus findings by severity (`critical`, `suggestion`, `nit`).
