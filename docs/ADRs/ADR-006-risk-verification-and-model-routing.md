# ADR-006: Risk Tiers, Verification Profiles, and Provider-Neutral Model Routing

## Status

Accepted

## Context

The current developer contract requires a full suite for every story (EV-003)
and model choice is fixed per role. VP3 requires verification, review, model
capability, and context depth to be proportional to risk (VO-005).

The PRD requires objective R0-R3 tiers assigned in planning, validated by the
architect, and escalable by the reviewer (PR-101, PR-102, DEC-013); tier
reduction only with architect approval, evidence, and rationale (PR-103); a
declared provider-neutral default model route and allowed capability classes per
story (PR-104, DEC-017); task-level routing with recorded escalation context
(PR-105); a verification matrix and review profile derived from mechanism and
risk (PR-106, DEC-016); smallest complete targeted story checks with mandatory
theme and release suites and conditional epic suites (PR-107); human
authorization plus independent reviewer acknowledgement for R3 or
safety-critical waivers and downgrades (PR-108, DEC-024); and a policy-declared
equivalent or a pause when an approved capability class is unavailable
(PR-213). DEF-004 leaves the class-to-model mapping to architecture.

RSK-004 warns that agents may downgrade risk or verification to meet budgets,
and QR-014 forbids lower cost from compensating for failed gates.

## Decision

1. Risk tiers use objective triggers evaluated in planning. A story takes the
   highest tier whose trigger matches.

   | Tier | Triggers |
   |---|---|
   | R0 | Documentation or comment-only change, no behavior change, trivially reversible |
   | R1 | Local behavior change inside one component, no external contract, no persisted data change |
   | R2 | Cross-component contract, persistence or migration, external integration, or non-trivial rollback |
   | R3 | Concurrency, crash consistency, security or secrets, irreversible data or release effects, or safety-critical behavior |

2. The product owner assigns the initial tier, the architect validates it before
   implementation, and the reviewer may escalate at any time. Reduction requires
   architect approval with evidence and rationale recorded in the story
   `risk.overrides` list. R3 reduction additionally requires human authorization
   and independent reviewer acknowledgement.

3. Verification profiles derive from tier and mechanism.

   | Tier | Story verification | Epic | Theme and release |
   |---|---|---|---|
   | R0 | Lint plus documentation checks | conditional | full suite |
   | R1 | Lint plus targeted unit | conditional | full suite |
   | R2 | Lint, targeted unit, integration or contract tests | required | full suite |
   | R3 | R2 plus failure-injection, concurrency, or recovery evidence | required | full suite plus release readiness |

   Story verification is the smallest complete set for the declared matrix, not
   the smallest convenient set. Waivers record the check, authority, reviewer,
   rationale, and record ID.

4. Review profiles use the canonical names from VP3: R0 `Lightweight` review
   plus validator; R1 `Standard` reviewer; R2 `Adversarial` reviewer plus
   architect contract check; R3 `Critical` reviewer plus architect plus human
   acknowledgement for any control weakening.

5. Model capability classes are provider-neutral: `light`, `balanced`,
   `reasoning`, `critical`. `docs/plan/policy/model-policy.yaml` is versioned
   and maps each class to a preferred model and declared equivalents, with
   `on-unavailable: pause`. Silent downgrade is prohibited.

6. Routing occurs at task granularity within story-level limits. Task defaults
   are declared in policy (packet assembly `light`, implementation and review
   `balanced`, architecture and troubleshooting `reasoning`, R3 review
   `critical`). A story declares `default-class` and `allowed-classes`.

7. Escalation to `reasoning` or `critical` records the unresolved question,
   prior evidence, scope, stop condition, and estimated cost in the story
   `model-route.escalations` list before the call is made.

8. Controls are declared in `backlog.yaml` and carried into every packet, so an
   agent cannot alter its own tier, route, verification matrix, or budget.

## Consequences

### Positive

- Verification effort and model cost track real risk instead of habit.
- Expensive reasoning is narrowly scoped and justified in writing.
- The method stays provider-neutral; only the policy file names models.
- Two independent roles must agree before any critical control weakens.

### Negative

- Planning must justify a tier for every story.
- Class-to-model mappings need maintenance as providers change.
- Task-level routing adds orchestration decisions per task.

### Risks

- Agents downgrade risk or verification to meet budgets (RSK-004). Mitigation:
  architect validation, reviewer escalation, attributable overrides, and
  balanced theme metrics.
- Tier assignment drifts between people or sessions (ASM-007). Mitigation:
  objective triggers, reviewer escalation, and tier distribution reporting.
- Capability class unavailability stalls work (PR-213). Mitigation: declared
  equivalents first, then an explicit pause with a human disposition.

## Alternatives Considered

### Full suite for every story

- Pros: simple, uniformly safe.
- Cons: dominant cost driver; discourages small stories.
- Rejected because: DEC-016 selects layered proportional verification with
  mandatory theme and release suites.

### Fixed model per agent role

- Pros: trivial configuration.
- Cons: a single expensive class handles both mechanical and analytical work.
- Rejected because: DEC-017 routes per task.

### Numeric risk score

- Pros: fine-grained ordering.
- Cons: false precision and score gaming under budget pressure.
- Rejected because: objective triggers are auditable and harder to game.

### Reviewer-only risk assignment

- Pros: one owner.
- Cons: risk becomes visible only after implementation.
- Rejected because: DEC-013 requires planning-time assignment with architect
  validation.
