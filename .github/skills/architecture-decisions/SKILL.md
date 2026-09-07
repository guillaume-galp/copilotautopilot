---
name: architecture-decisions
description: 'ADR conventions, lightweight tech-stack evaluation, component boundary rules, and architecture documentation structure.'
---

# Architecture Decisions Skill

## ADR Format

Path: `docs/ADRs/ADR-<NNN>-<slug>.md`

Required sections:
- `# ADR-<NNN>: <Title>`
- `## Status` (`Proposed|Accepted|Deprecated|Superseded by ADR-<NNN>`)
- `## Replacement` when this ADR replaces an accepted ADR, containing exactly
  `| Replaces | ADR-<NNN> |` in a `Field | Value` metadata table
- `## Context`
- `## Decision`
- `## Consequences` (positive / negative / risks)
- `## Alternatives Considered`

## ADR Lifecycle & Lock Rules

- Proposed → Accepted → Deprecated/Superseded
- Determine ADR body lock timing and the sole status-line supersession
  exception from `the-copilot-build-method`; never infer it from a generic
  association alone.
- A locked ADR may move to `Superseded by ADR-<NNN>` only when the exact
  accepted replacement ADR carries the structured `Replacement` metadata
  naming it. Free-text, negated, conditional, or hypothetical prose is not a
  replacement relation.

## Tech-Stack Evaluation (minimal rubric)

Score options for: fitness, maturity, simplicity, ecosystem, scalability/NFR fit, security, cost.
Prefer simplest viable architecture that satisfies current requirements.

## Component Boundary Rules

Each component should define:
- responsibility
- interface
- data ownership
- dependencies

Rules:
- communicate through interfaces
- single owner per data entity
- isolate cross-cutting concerns
- require review for new dependencies

## Architecture Doc Set

- `docs/architecture/README.md`
- `docs/architecture/tech-stack.md`
- `docs/architecture/components.md`
- `docs/architecture/data-model.md`
- `docs/architecture/project-setup.md`
- `docs/architecture/deployment.md` (optional when deployment target exists)

## Commit Convention

Use qualified IDs:
- `feat(TH1.E1.US1): ...`
- `fix(TH1.E2.US3): ...`
- `docs(TH1.E3.US1): ...`
