# Architecture Decision Records (ADRs)

Significant architecture decisions are documented here using the ADR format.

## Naming Convention

```
ADR-<NNN>-<slug>.md
```

Example: `ADR-001-database-choice.md`

## Template

```markdown
# ADR-<NNN>: <Title>

## Status
Proposed | Accepted | Deprecated | Superseded by ADR-<NNN>

## Context
<What is the issue that motivates this decision?>

## Decision
<What is the change that we're proposing and/or doing?>

## Consequences

### Positive
- <benefit>

### Negative
- <trade-off>

### Risks
- <risk and mitigation>

## Alternatives Considered

### <Alternative 1>
- Pros: <advantages>
- Cons: <disadvantages>
- Rejected because: <reason>
```

## Index

| ADR | Title | Status | Scope |
|---|---|---|---|
| [ADR-001](ADR-001-gitflow-operator.md) | Gitflow Operator Responsibility | Accepted | TH2 (locked) |
| [ADR-002](ADR-002-six-stage-gated-lifecycle.md) | Six-Stage Gated Lifecycle, Entrypoint Boundaries, and Artefact Ownership | Accepted | VP3 / TH3 |
| [ADR-003](ADR-003-markdown-records-and-local-validator.md) | Markdown Records, YAML State, and a Local Fail-Closed Validator | Accepted | VP3 / TH3 |
| [ADR-004](ADR-004-backlog-schema-v2-and-transitions.md) | Versioned Backlog Schema v2 and Optimistic Revisioned Transitions | Accepted | VP3 contract; enforced TH4/TH5 |
| [ADR-005](ADR-005-agent-packets-and-source-hashing.md) | Compact Agent Packets with Composite Source Hashing | Accepted | VP3 contract; enforced TH4 |
| [ADR-006](ADR-006-risk-verification-and-model-routing.md) | Risk Tiers, Verification Profiles, and Provider-Neutral Model Routing | Accepted | VP3 contract; enforced TH4 |
| [ADR-007](ADR-007-usage-adapter-and-budget-enforcement.md) | Usage Capability Adapter, Nested Soft-Cap Budgets, and Calibration | Accepted | VP3 contract; enforced TH5 |
| [ADR-008](ADR-008-multi-theme-lock-and-activation-ledger.md) | Multi-Theme VP Lock Semantics and Control Activation Ledger | Accepted | VP3 / TH3, TH5 |
