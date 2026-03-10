---
name: architecture-decisions
description: 'ADR format, tech stack analysis methodology, component boundary definition, system design patterns. Use when: creating ADRs, choosing tech stack, defining architecture, designing components, making system design decisions.'
---

# Architecture Decisions Skill

## ADR Format

Architecture Decision Records live in `docs/ADRs/ADR-<NNN>-<slug>.md`.

### Template

```markdown
# ADR-<NNN>: <Title>

## Status
Proposed | Accepted | Deprecated | Superseded by ADR-<NNN>

## Context
<What is the issue that motivates this decision? What forces are at play?>

## Decision
<What is the change that we're proposing and/or doing?>

## Consequences

### Positive
- <benefit 1>
- <benefit 2>

### Negative
- <trade-off 1>
- <trade-off 2>

### Risks
- <risk and mitigation>

## Alternatives Considered

### <Alternative 1>
- Pros: <advantages>
- Cons: <disadvantages>
- Rejected because: <reason>

### <Alternative 2>
- Pros: <advantages>
- Cons: <disadvantages>
- Rejected because: <reason>
```

### ADR Lifecycle

1. **Proposed** → Under discussion, not yet committed
2. **Accepted** → Decision made, implementation proceeds
3. **Deprecated** → No longer relevant (explain why)
4. **Superseded** → Replaced by a newer ADR (link to it)

## Tech Stack Analysis

When choosing technologies, evaluate along these dimensions:

| Dimension | Questions |
|:---|:---|
| Fitness | Does it solve the actual problem from the vision? |
| Maturity | Is it production-ready? Community size? |
| Simplicity | Is this the simplest tool that works? |
| Team fit | (Language-agnostic template — defer to project context) |
| Ecosystem | Libraries, tooling, CI/CD support? |
| Scalability | Does it meet the NFRs from the vision? |
| Security | CVE history? Active maintenance? |
| Cost | Licensing? Infrastructure requirements? |

### Simplest Viable Architecture

Always start with the simplest architecture that satisfies the vision's requirements. Complexity is added only when justified by concrete, documented NFRs — not hypothetical future needs.

## Component Boundaries

### Defining Components

Each component in `docs/architecture/components.md` should specify:
- **Responsibility**: What it does (single sentence)
- **Interface**: How other components interact with it
- **Data ownership**: What data it owns and persists
- **Dependencies**: What it depends on (other components, external services)

### Boundary Rules
- Components communicate through defined interfaces, not internal details
- Data ownership is exclusive — one component owns each data entity
- Cross-cutting concerns (logging, auth, config) are separate shared components
- New dependencies require architectural review (check against ADRs)

## Architecture Document Structure

```
docs/architecture/
├── README.md           # System context + high-level design
├── tech-stack.md        # Chosen technologies with rationale
├── components.md        # Component breakdown and boundaries
├── data-model.md        # Data entities, storage, relationships
└── project-setup.md     # Repo structure, build system, dev environment
```

Each significant decision is cross-referenced with its ADR in `docs/ADRs/`.
