# VP3: Discovery-Led, Cost-Aware Copilot Build Method

| Field | Value |
|---|---|
| Product | `copilotautopilot` |
| Vision phase | VP3 |
| Status | Discovery accepted; PRD approved |
| Date | 2026-09-05 |
| Intended themes | TH3, TH4, TH5 |
| Working title | Discovery-led, cost-aware build methodology |

## 1. One-line vision

> Evolve the Copilot Build Method from a four-stage delivery pipeline into a
> discovery-led, six-stage engineering method where a curious human designer
> and LLM investigate mechanisms, assumptions, trade-offs, ontology, and
> governance before architecture is committed, then execute with explicit
> risk, model, test, review, and AIC budgets.

## 2. Problem statement

The current method moves directly from product vision into architecture and
ADRs:

```text
Vision -> Architecture/ADRs -> Planning -> Autopilot
```

That transition is often too abrupt. A vision describes the desired product and
its user value, but it does not necessarily provide enough technical knowledge
to make durable architecture decisions. The architect must then choose
mechanisms while still discovering how the underlying system works.

When that discovery is shallow or implicit:

- high-level architecture is plausible but underspecified;
- low-level concurrency, persistence, migration, security, integration, and
  failure semantics remain unresolved;
- ADRs choose a direction without specifying the invariants that make it safe;
- stories are sized around visible features instead of hidden technical
  boundaries;
- implementation mixes two different activities: learning what must be built
  and building it;
- reviews uncover architectural questions after substantial code and tests
  already exist;
- repeated rework becomes the mechanism through which architecture is finally
  discovered;
- expensive models repeatedly reload context and independently rediscover the
  same constraints;
- full suites, mutation tests, fuzzing, and deep reviews are applied without a
  risk-proportional policy;
- bounded rework counts do not bound the AIC consumed inside each attempt.

An observed real-world methodology run consumed approximately 21,000 AIC while
building a control-plane improvement:

- almost 90% of the measured AIC came from a premium reasoning model;
- early stories combined schema, integration, concurrency, repair, journal, and
  recovery concerns;
- implementation and review exposed missing lock and crash-consistency
  invariants;
- the work had to pause, enrich architecture and ADRs, and split stories before
  it could proceed safely;
- quality was high, but discovery happened inside the most expensive phase.

This is not merely a prompt-efficiency problem. It is a lifecycle-design
problem: **Discovery and Build are distinct engineering modes and need separate,
bounded phases.**

## 3. Product vision

The method should make the cheapest safe mistake an early discovery correction,
not a late implementation rewrite.

After the human and LLM establish an initial product vision sketch, they enter
an explicit **Discovery** phase. In Discovery, the human designer and LLM learn
together how the relevant system works under the hood, identify candidate
mechanisms, expose assumptions, choose simplifications, define the system
ontology and governance, and prove the riskiest technical claims before product
requirements, architecture, or delivery scope are frozen.

An interactive Requirements phase then turns the accepted Discovery handoff
into a human-approved PRD. Architecture and ADRs formalize decisions already
grounded in Discovery evidence. Planning decomposes those decisions into
stories aligned with real technical boundaries. Autopilot executes under
enforceable economic and verification constraints proportional to risk.

The intended lifecycle is:

```text
1. Vision sketch
        |
        v
2. Human-led Discovery
        |
        v
3. PRD finalization
        |
        v
4. Architecture and ADRs
        |
        v
5. Planning and BDD backlog
        |
        v
6. Cost-aware Autopilot
```

Discovery is collaborative and educational rather than an autonomous black box.
The human designer remains an active decider.

## 4. Target users and personas

### Human designer / curious engineer

Wants to understand the system deeply enough to make deliberate choices rather
than approve opaque AI recommendations. During Discovery, this person:

- asks how mechanisms work internally;
- challenges terminology, boundaries, and hidden assumptions;
- chooses where to simplify and where to preserve rigor;
- decides which risks are acceptable;
- selects the concepts and ontology the product will use;
- helps distinguish product requirements from accidental implementation
  complexity;
- explicitly approves the Discovery findings before architecture begins.

### Product owner

Needs product intent and PRDs to remain solution-aware enough to be feasible,
but not contaminated by premature architecture. Uses Discovery results to
understand what can safely be promised and what should be deferred.

### Discovery facilitator

A new agent or skill that guides the human and specialist LLMs through
questions, experiments, trade-off analysis, and decision capture. It does not
silently make product or architecture decisions.

### Architect

Consumes a completed Discovery dossier instead of rediscovering the domain
during architecture authoring. Converts validated mechanisms, invariants, and
human decisions into components, interfaces, data ownership, and ADRs.

### Orchestrator

Executes a plan whose stories already reflect the discovered technical
boundaries. Enforces risk tier, model route, verification profile, AIC budget,
and circuit-breaker rules.

### Developer, reviewer, and troubleshooter

Receive compact evidence packets with explicit scope and proportional
verification obligations. They do not reload the full methodology history or
invent architecture during implementation.

## 5. Core capability: the Discovery stage

### 5.1 Position in the lifecycle

Discovery begins after the Vision sketch describes:

- the user and problem;
- desired outcomes;
- constraints and explicit non-goals;
- unresolved product questions.

Discovery ends before PRD finalization and before architecture and ADRs are
authored or revised for the delivery scope.

### 5.2 Discovery goals

Discovery must answer:

1. What system or domain are we changing?
2. How does it work today, at both conceptual and mechanism levels?
3. Which external systems, protocols, standards, repositories, and operational
   boundaries constrain the change?
4. Which parts are known facts, hypotheses, assumptions, or human preferences?
5. Which technical risks could invalidate the product approach?
6. Which mechanisms could satisfy the requirements?
7. What are the trade-offs, failure modes, concurrency or consistency
   semantics, security boundaries, and migration implications?
8. Where can the design deliberately simplify?
9. Which invariants must architecture preserve?
10. Which questions require experiments, prototypes, benchmarks, source
    reading, or human decisions?
11. What ontology and shared vocabulary will product, architecture, planning,
    code, tests, and operations use?
12. What governance applies to changes, evidence, exceptions, and later
    architectural discoveries?

### 5.3 Discovery artefacts

Each vision phase may create:

```text
docs/discovery/VP<n>-<slug>/
  README.md                    # scope, status, participants, gate
  system-map.md                # context, components, actors, boundaries
  domain-ontology.md           # concepts, terms, relationships, invariants
  mechanisms.md                # under-the-hood behavior and candidate mechanisms
  assumptions.md               # fact/hypothesis/assumption/preference register
  decisions.md                 # human focusing and simplification decisions
  risks-and-failure-modes.md   # technical and operational risk register
  experiments/                 # bounded spikes, traces, benchmarks, prototypes
  evidence-index.md            # source and experiment references
  architecture-handoff.md      # accepted discovery contract
```

Small VPs may combine these into one `DISCOVERY.md`, but they must preserve the
same information model.

### 5.4 Evidence taxonomy

Every material discovery claim is labeled:

| Classification | Meaning |
|---|---|
| `observed` | Directly evidenced in source, runtime, documentation, or experiment. |
| `inferred` | Strongly derived from evidence but not directly observed. |
| `hypothesis` | Plausible claim requiring validation. |
| `assumption` | Condition accepted for the design to proceed. |
| `preference` | Human-selected focus, simplification, or trade-off. |
| `decision` | Explicitly accepted outcome that constrains architecture. |
| `unknown` | Open question with owner and disposition. |

Architecture must not silently promote a hypothesis into a decision.

### 5.5 Human contribution and checkpoints

Discovery is intentionally human-intensive. The facilitator must periodically
present:

- what has been learned;
- what remains uncertain;
- competing mechanisms and their trade-offs;
- proposed assumptions and simplifications;
- consequences of choosing rigor versus scope reduction;
- recommended experiments;
- decisions that only the human should make.

The human can:

- accept a decision;
- reject a mechanism;
- request deeper explanation;
- ask for an experiment;
- simplify product scope;
- defer an unknown with an explicit risk;
- stop Discovery and revise the Vision or PRD.

No Discovery dossier becomes architecture input without a human checkpoint.

### 5.6 Bounded Discovery

Discovery must not become endless research.

Each investigation has:

- a question;
- why it matters;
- a time or AIC budget;
- an evidence method;
- an expected decision;
- a stop condition;
- an outcome: validated, rejected, deferred, or unresolved.

Discovery stops when the architecture-readiness gate is met, not when all
possible knowledge is exhausted.

### 5.7 Discovery is not production implementation

Discovery may use:

- source and architecture analysis;
- documentation and standards research;
- runtime traces;
- small disposable experiments;
- benchmarks;
- fault simulations;
- interface sketches;
- data-model examples;
- threat and failure-mode analysis.

Discovery does not:

- merge production features;
- quietly create the final implementation;
- mark delivery stories done;
- freeze accidental prototype code into architecture;
- use implementation rework as a substitute for resolving known unknowns.

Reusable experiment code must be explicitly promoted through architecture and
planning before it becomes production code.

## 6. Architecture-readiness gate

Architecture may begin only when the Discovery dossier provides:

- agreed system context and boundaries;
- an accepted domain ontology and glossary;
- candidate mechanisms evaluated against requirements;
- chosen simplifications and rejected complexity;
- explicit safety, security, consistency, concurrency, durability, and
  operational invariants where relevant;
- authoritative versus derived state ownership;
- identified external dependencies and compatibility constraints;
- migration and rollback expectations;
- resolved or consciously deferred high-risk unknowns;
- experimental evidence for claims that materially affect feasibility;
- a risk classification for each major component or behavior;
- human decisions and assumptions with owners;
- an architecture handoff that lists what architecture may decide and what is
  already constrained.

If implementation later exposes a missing invariant or foundational technical
unknown, the story is paused and routed back through **Discovery Revision**.
The methodology records this as a lifecycle correction, not ordinary developer
rework.

## 7. Post-Discovery architecture and ADRs

Architecture becomes a formalization phase, not the first deep investigation.

The architect must:

- cite Discovery evidence for significant decisions;
- map discovered ontology into components, interfaces, and data ownership;
- specify high-level and low-level contracts required by the risk profile;
- distinguish architecture invariants from implementation choices;
- turn accepted decisions into ADRs;
- create a new ADR when later discovery changes a previously accepted decision;
- include executable fault or verification matrices for critical mechanisms;
- declare which decisions remain intentionally deferred to implementation;
- reject architecture completion when a critical discovery question is still
  disguised as an implementation detail.

ADRs include:

- evidence references;
- assumptions relied upon;
- chosen simplifications;
- risk tier;
- invariants;
- validation strategy;
- conditions that would invalidate or supersede the decision.

## 8. Planning after Discovery

Planning must decompose architecture according to real technical boundaries.

Before accepting a story, the product owner checks:

- one primary state transition or mechanism;
- one independently reviewable responsibility;
- explicit dependencies;
- no unresolved architecture decision hidden in the acceptance criteria;
- a verification profile proportional to risk;
- a model and AIC budget;
- expected evidence and stop conditions;
- story size that fits one developer session without combining discovery and
  production implementation.

If a story contains acquisition plus repair plus journaling plus replay, or a
similar set of separable mechanisms, it is not one story.

## 9. Cost-aware Autopilot

### 9.1 Risk tiers

Every story and review receives a risk tier:

| Tier | Typical change | Default verification |
|---|---|---|
| R0 | Documentation, labels, generated metadata | Lightweight review; syntax/link checks. |
| R1 | Local deterministic behavior with limited blast radius | Targeted tests and standard review. |
| R2 | Cross-component state, migration, external integration | Targeted plus integration tests and adversarial review. |
| R3 | Security, concurrency, durability, destructive operations, production control planes | Fault injection, mutation testing, fuzzing, or specialist review as justified. |

Deep verification is available to every tier but is not the default for every
story.

### 9.2 Test-gate cadence

Default cadence:

- story: smallest targeted tests that prove its acceptance criteria;
- rework: rerun failed or directly affected targeted tests;
- epic: relevant integration tests and proportional quality review;
- theme or delivery PR: full repository suite and release-readiness checks.

A full suite during every story/review cycle requires an explicit reason such as
unreliable test isolation, a cross-cutting change, or R3 risk.

### 9.3 Review profiles

| Profile | Intended use |
|---|---|
| Lightweight | Trivial and R0 changes. |
| Standard | Most R1 stories; acceptance criteria, correctness, regression risk. |
| Adversarial | R2 changes; negative paths, integration boundaries, misuse. |
| Critical | R3 only; concurrency, security, durability, migration, destructive behavior. |

Mutation testing, randomized fuzzing, repeated process interleavings, and
independent exploit reproduction require an adversarial or critical profile.

### 9.4 Model routing

The plan declares a model class rather than silently choosing the most expensive
available model:

- economy: routine searches, formatting, straightforward tests and changes;
- standard: normal development and review;
- reasoning: architecture, difficult debugging, R2 design;
- critical: narrowly scoped R3 analysis after cheaper evidence is insufficient.

The orchestrator may escalate model class only with a recorded reason. Premium
models are not the default for every developer and reviewer session.

### 9.5 AIC budgets and circuit breakers

Each phase and delivery item has:

- target AIC;
- warning threshold;
- hard pause threshold;
- actual consumption;
- model mix;
- escalation reason when the budget is exceeded.

Initial configurable defaults should be calibrated from real usage, with an
example policy:

| Work item | Target | Warning | Pause |
|---|---:|---:|---:|
| R0/R1 story | 150 AIC | 300 | 500 |
| R2 story | 300 AIC | 600 | 900 |
| R3 story | 600 AIC | 1,000 | 1,500 |
| Epic ceremony | 200 AIC | 400 | 700 |

These numbers are policy defaults, not permanent universal limits.

At the hard threshold, the agent must stop after preserving state and ask for
one of:

- continue with the same approach;
- simplify scope;
- split the story;
- return to Discovery;
- change model class;
- accept or waive a verification activity.

A rework-count limit remains, but it no longer substitutes for a cost limit.

### 9.6 Compact agent packets

Each agent receives only:

- item identity and acceptance criteria;
- relevant architecture/ADR sections;
- declared boundaries and dependencies;
- current evidence references;
- risk tier, model class, verification profile, and AIC budget;
- required report shape.

Agents should not reload entire session logs, full backlogs, or unrelated
architecture histories.

### 9.7 Bounded operational records

The backlog remains authoritative for state. Operational history is concise and
structured:

- transition;
- evidence reference;
- blocker or decision;
- next action;
- actual AIC and model.

Verbose forensic reports are stored as trace artefacts or Git/PR evidence rather
than repeatedly loaded into the session log.

## 10. Core product capabilities

VP3 delivers:

1. A six-stage lifecycle with Discovery between the Vision sketch and PRD
   finalization.
2. A `discover` skill and facilitator role.
3. Discovery artefact schemas and an architecture-readiness gate.
4. Human-decision and assumption registers.
5. Bounded experiments and Discovery Revision routing.
6. Discovery-aware architecture and ADR formats.
7. Discovery-aware story sizing and dependency checks.
8. Risk-tiered verification and review profiles.
9. Model routing policy.
10. Phase, story, review, and ceremony AIC budgets with circuit breakers.
11. Targeted-versus-full test cadence.
12. Compact agent context packets.
13. Bounded operational records and external evidence references.
14. Reporting that compares planned and actual AIC, model mix, rework, and
    discovery escapes.

## 11. Success criteria

### Discovery quality

1. Every new theme has a completed Discovery dossier or an explicit
   human-approved lightweight-discovery waiver.
2. Every R3 mechanism has named invariants, failure modes, and a validation
   matrix before production implementation begins.
3. Architecture and ADRs cite the Discovery evidence and assumptions they rely
   on.
4. A human designer explicitly accepts or defers all high-impact assumptions.
5. Stories contain no unresolved foundational decision disguised as an
   implementation task.

### Build efficiency

6. At least 80% of R0/R1 stories complete without a premium critical-model
   session.
7. Full repository suites run by default at epic/theme/PR gates rather than
   every normal story/review iteration.
8. Mutation testing, fuzzing, and deterministic concurrency campaigns occur
   only under declared R2/R3 profiles.
9. The orchestrator pauses automatically at the configured AIC threshold.
10. Every completed story reports actual AIC, model mix, verification profile,
    and rework count.
11. Median AIC per R0/R1 story targets a provisional 60% reduction against the
    measured pre-VP3 baseline, subject to quality and calibration evidence.
12. No single agent session consumes more than twice its warning threshold
    without explicit human authorization.
13. Overseer/orchestrator AIC remains below 30% of total delivery AIC during
    normal execution.

### Lifecycle effectiveness

14. When implementation discovers a missing foundational invariant, the method
    routes to Discovery Revision within one review cycle.
15. Replanned stories preserve accepted completed work and evidence.
16. The human can explain the selected mechanisms, assumptions, and
    simplifications from the Discovery dossier without reading implementation
    code.
17. Post-theme review distinguishes discovery escapes, implementation defects,
    test defects, and requirement changes.

## 12. Constraints

- `docs/plan/backlog.yaml` remains authoritative execution state.
- Existing locked themes and their VP/ADR artefacts remain immutable.
- Discovery must be proportional; small changes can use a concise dossier.
- Human participation is required for high-impact assumptions and focusing
  decisions.
- The methodology remains language- and platform-agnostic.
- Cost controls must work even when exact provider billing data is unavailable;
  local AIC estimates or token proxies are acceptable with confidence labels.
- Missing usage data must not be interpreted as zero consumption.
- Tooling must support different model families without hardcoding one vendor.
- Economy must not override safety: R3 work may exceed defaults with explicit
  authorization and evidence.
- Discovery experiments must be isolated from production delivery state.
- Git history and trace artefacts are the durable audit trail; session logs stay
  bounded.

## 13. Explicit non-goals

- Eliminating architecture changes after implementation begins.
- Predicting every implementation detail before coding.
- Replacing human engineering judgment with automated scoring.
- Making the human approve routine low-risk implementation choices.
- Minimizing AIC at the expense of correctness or safety.
- Applying formal verification to every change.
- Turning Discovery into an unlimited research phase.
- Promoting disposable prototypes directly into production.
- Standardizing one technology stack or one model provider.

## 14. Key assumptions

- The greatest avoidable delivery cost comes from late discovery, repeated
  context loading, premium-model overuse, and disproportionate verification.
- A human designer can make better focusing decisions when mechanisms and
  trade-offs are explained before architecture is frozen.
- Discovery evidence can be summarized compactly enough to reduce downstream
  context cost.
- Risk tiers can be made objective enough for consistent default behavior while
  allowing human override.
- Exact AIC accounting may vary by model/provider, but budget enforcement can
  operate on the best available measurement.
- Most stories do not require adversarial or critical review.

## 15. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Discovery becomes analysis paralysis | Budget every question and gate on decision readiness, not exhaustive knowledge. |
| Human participation becomes burdensome | Ask only high-impact questions in grouped checkpoints; allow lightweight waivers. |
| Agents game risk tiers to receive cheaper review | Define objective triggers and permit reviewer escalation with evidence. |
| Cost limits stop necessary critical work | Allow explicit human continuation with revised budget and reason. |
| Discovery artefacts duplicate architecture | Discovery records evidence and choices; architecture defines the resulting system. |
| Prototypes accidentally become production | Require explicit promotion through architecture, planning, tests, and review. |
| Usage telemetry is unavailable or inaccurate | Record confidence and use conservative token/turn proxies. |
| Compact context omits a critical constraint | Include dependency-selected ADR and boundary references; permit justified expansion. |

## 16. Discovery outcome

The Discovery dossier at
`docs/discovery/VP3-discovery-led-cost-aware-methodology/` resolves the original
open questions. The accepted direction includes:

- a new `discover` entrypoint and separate `requirements` phase;
- one interactive facilitator coordinating bounded specialist investigations;
- structured evidence, decision, risk, deferral, revision, and gate records;
- risk-tiered planning, provider-neutral model routing, and proportional
  verification;
- measured, estimated, or unknown usage with observed soft-cap pauses;
- append-only Discovery and PRD revisions;
- independent theme locking with VP-level locking after all mapped themes;
- staged delivery through TH3, TH4, and TH5.

## 17. Recommended next workflow

VP3 has completed self-hosted Discovery and PRD finalization. The approved
architecture and ADRs define the system contract. The next lifecycle action is
delivery planning for TH3, followed by TH4 and TH5 in dependency order.
