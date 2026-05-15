---
name: code-quality
description: 'Review checklist for correctness, security, architecture compliance, code quality, and test quality.'
---

# Code Quality Skill

## Review Checklist

### 1) Correctness
- implements acceptance criteria
- handles edge/error paths
- no obvious logic/race issues

### 2) Security (OWASP-oriented)
Check for injection, broken access control, crypto misuse, insecure defaults, vulnerable dependencies, auth/session flaws, integrity issues, sensitive logging, SSRF.

### 3) Architecture
- respects component boundaries
- aligns with ADR decisions
- avoids problematic dependencies/cycles

### 4) Code Quality
- follows conventions
- readable and non-duplicative
- complexity proportional to problem
- clear responsibilities

### 5) Tests
- meaningful assertions
- covers target scenarios
- deterministic and maintainable

## Severity Labels

- `must-fix` (blocking)
- `should-fix` (important)
- `optional` (nit)

## Refactor Guidance (epic boundary)

Prefer small, behavior-preserving refactors:
- extract duplicated logic
- remove dead code
- simplify high complexity
- externalize repeated constants/config

Run full relevant tests after refactor.

## Documentation Checks

Ensure README/API/architecture/ADR/changelog/story alignment with implemented behavior.

## UI Accessibility Checks (UI projects only)

Verify semantic structure, labels/ARIA correctness, keyboard operability, visible focus, and WCAG AA contrast.
