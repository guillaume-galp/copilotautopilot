# Architecture Overview

| Field | Value |
|---|---|
| Product | Copilot Build Method (`copilotautopilot`) |
| Current target | VP3: Discovery-Led, Cost-Aware Methodology |
| Delivery mapping | TH3 (foundation), TH4 (risk/context), TH5 (economics) |
| Inputs | `docs/requirements/VP3-discovery-led-cost-aware-methodology/PRD.md`, `docs/discovery/VP3-discovery-led-cost-aware-methodology/` |
| Status | Accepted |
| Date | 2026-09-05 |

## Acceptance

| Field | Value |
|---|---|
| Actor | Human: product owner |
| Timestamp | 2026-09-06T21:41:37+01:00 |
| Scope | VP3 architecture/ADR ownership and structured trace reconciliation |
| Verdict | Accepted |
| Rationale | No product, lifecycle, or technical decision changed. |
| Source revision | sha256:3a28033557297230549656619a28d46ecd9c5e1a2a245f39a8991c5fca7b2ece |

## Structured trace declaration

This declaration is the sole machine-readable source for accepted architecture
relationships. Prose references elsewhere are explanatory and are not parsed
as trace edges. An empty `stories` list means the mapped delivery theme is not
yet active; it does not reserve placeholder work or evidence.

<!-- architecture-trace:start -->
```yaml
schema-version: 1
vp: VP3
mappings:
  - records: [ASM-001]
    theme: TH3
    requirements: [PR-005, PR-006, QR-010]
    adrs: [ADR-002]
    components: [docs/architecture/components.md#1-lifecycle-entrypoints-skills]
    stories: [TH3.E1.US4, TH3.E2.US4, TH3.E3.US1, TH3.E3.US2]
  - records: [ASM-009]
    theme: TH3
    requirements: [PR-002, QR-001]
    adrs: [ADR-002]
    components: [docs/architecture/components.md#1-lifecycle-entrypoints-skills]
    stories: [TH3.E1.US2, TH3.E2.US4, TH3.E3.US1]
  - records: [DEC-003]
    theme: TH3
    requirements: [PR-003, PR-016, QR-008]
    adrs: [ADR-002]
    components: [docs/architecture/components.md#1-lifecycle-entrypoints-skills]
    stories: [TH3.E1.US2, TH3.E1.US4, TH3.E3.US2]
  - records: [ASM-002]
    theme: TH3
    requirements: [PR-003, PR-011, QR-008]
    adrs: [ADR-002, ADR-003]
    components: [docs/architecture/components.md#2-canonical-skills-contracts]
    stories: [TH3.E1.US2, TH3.E2.US6]
  - records: [ASM-010]
    theme: TH3
    requirements: [PR-012, PR-014]
    adrs: [ADR-008]
    components: [docs/architecture/components.md#5-stores]
    stories: [TH3.E1.US1, TH3.E2.US5, TH3.E4.US2]
  - records: [DEC-009]
    theme: TH3
    requirements: [PR-008, PR-011]
    adrs: [ADR-002]
    components: [docs/architecture/components.md#13-plan-skill-v2-th3]
    stories: [TH3.E1.US3, TH3.E2.US6, TH3.E3.US4, TH3.E3.US5]
  - records: [RSK-001]
    theme: TH3
    requirements: [PR-002, PR-006, QR-001]
    adrs: [ADR-002]
    components: [docs/architecture/components.md#11-discover-skill-th3]
    stories: [TH3.E3.US1]
  - records: [RSK-002, RSK-003]
    theme: TH3
    requirements: [PR-002, PR-005, PR-006, QR-008, QR-010]
    adrs: [ADR-002]
    components: [docs/architecture/components.md#1-lifecycle-entrypoints-skills]
    stories: [TH3.E1.US4, TH3.E2.US4, TH3.E3.US1, TH3.E3.US2]
  - records: [RSK-009]
    theme: TH3
    requirements: [QR-009, QR-015]
    adrs: [ADR-003, ADR-005]
    components: [docs/architecture/components.md#41-method-validate-th3]
    stories: [TH3.E2.US2, TH3.E3.US3]
  - records: [RSK-010]
    theme: TH3
    requirements: [PR-012, QR-004]
    adrs: [ADR-008]
    components: [docs/architecture/components.md#5-stores]
    stories: [TH3.E1.US1, TH3.E2.US5]
  - records: [RSK-011]
    theme: TH3
    requirements: [PR-013, PR-015, QR-003]
    adrs: [ADR-003, ADR-008]
    components: [docs/architecture/components.md#41-method-validate-th3]
    stories: [TH3.E4.US1, TH3.E4.US5]
  - records: [INV-002]
    theme: TH3
    requirements: [QR-006]
    adrs: [ADR-002, ADR-003]
    components: [docs/architecture/components.md#2-canonical-skills-contracts]
    stories: [TH3.E1.US1, TH3.E1.US2, TH3.E1.US3, TH3.E2.US6]
  - records: [INV-009]
    theme: TH3
    requirements: [QR-013]
    adrs: [ADR-007, ADR-008]
    components: [docs/architecture/components.md#5-stores]
    stories: [TH3.E4.US4]
  - records: [PR-001, PR-012, QR-006]
    theme: TH3
    requirements: []
    adrs: [ADR-002, ADR-008]
    components: [docs/architecture/components.md#1-lifecycle-entrypoints-skills]
    stories: [TH3.E1.US1]
  - records: [PR-002, PR-003, PR-004, PR-007, QR-006]
    theme: TH3
    requirements: []
    adrs: [ADR-002, ADR-003]
    components: [docs/architecture/components.md#2-canonical-skills-contracts]
    stories: [TH3.E1.US2]
  - records: [PR-008, PR-009, PR-011, QR-006, QR-010]
    theme: TH3
    requirements: []
    adrs: [ADR-002, ADR-003]
    components: [docs/architecture/components.md#2-canonical-skills-contracts]
    stories: [TH3.E1.US3]
  - records: [PR-003, PR-005, PR-009, QR-008, QR-010]
    theme: TH3
    requirements: []
    adrs: [ADR-002, ADR-003]
    components: [docs/architecture/components.md#2-canonical-skills-contracts]
    stories: [TH3.E1.US4]
  - records: [PR-015, QR-002, QR-007, QR-011]
    theme: TH3
    requirements: []
    adrs: [ADR-003]
    components: [docs/architecture/components.md#41-method-validate-th3]
    stories: [TH3.E2.US1]
  - records: [PR-003, PR-004, PR-015, QR-002, QR-009]
    theme: TH3
    requirements: []
    adrs: [ADR-003]
    components: [docs/architecture/components.md#41-method-validate-th3]
    stories: [TH3.E2.US2]
  - records: [PR-015, QR-002, QR-003, QR-004, QR-005, QR-006]
    theme: TH3
    requirements: []
    adrs: [ADR-003, ADR-004]
    components: [docs/architecture/components.md#41-method-validate-th3]
    stories: [TH3.E2.US3]
  - records: [PR-001, PR-002, PR-005, PR-006, PR-010, PR-015, QR-003, QR-008, QR-010]
    theme: TH3
    requirements: []
    adrs: [ADR-002, ADR-003]
    components: [docs/architecture/components.md#41-method-validate-th3]
    stories: [TH3.E2.US4]
  - records: [PR-012, PR-015, QR-003, QR-004]
    theme: TH3
    requirements: []
    adrs: [ADR-003, ADR-008]
    components: [docs/architecture/components.md#41-method-validate-th3]
    stories: [TH3.E2.US5]
  - records: [PR-011, PR-015, QR-002, QR-003, QR-006]
    theme: TH3
    requirements: []
    adrs: [ADR-002, ADR-003]
    components: [docs/architecture/components.md#41-method-validate-th3]
    stories: [TH3.E2.US6]
  - records: [PR-002, PR-006, PR-016, QR-001, QR-008]
    theme: TH3
    requirements: []
    adrs: [ADR-002]
    components: [docs/architecture/components.md#11-discover-skill-th3]
    stories: [TH3.E3.US1]
  - records: [PR-003, PR-005, PR-006, PR-016, QR-006, QR-008]
    theme: TH3
    requirements: []
    adrs: [ADR-002]
    components: [docs/architecture/components.md#3-agents-thin-roles]
    stories: [TH3.E3.US2]
  - records: [PR-004, PR-016, QR-009, QR-015]
    theme: TH3
    requirements: []
    adrs: [ADR-002, ADR-005]
    components: [docs/architecture/components.md#3-agents-thin-roles]
    stories: [TH3.E3.US3]
  - records: [PR-008, PR-009, PR-016, QR-002, QR-008]
    theme: TH3
    requirements: []
    adrs: [ADR-002]
    components: [docs/architecture/components.md#12-requirements-skill-th3]
    stories: [TH3.E3.US4]
  - records: [PR-008, PR-009, PR-011, PR-016, QR-006]
    theme: TH3
    requirements: []
    adrs: [ADR-002]
    components: [docs/architecture/components.md#3-agents-thin-roles]
    stories: [TH3.E3.US5]
  - records: [PR-001, PR-010, PR-015, QR-003, QR-005, QR-006]
    theme: TH3
    requirements: []
    adrs: [ADR-002, ADR-004]
    components: [docs/architecture/components.md#13-plan-skill-v2-th3]
    stories: [TH3.E3.US6]
  - records: [PR-013, PR-015, QR-002, QR-003, QR-010]
    theme: TH3
    requirements: []
    adrs: [ADR-003, ADR-008]
    components: [docs/architecture/components.md#41-method-validate-th3]
    stories: [TH3.E4.US1]
  - records: [PR-014, PR-015, QR-004]
    theme: TH3
    requirements: []
    adrs: [ADR-008]
    components: [docs/architecture/components.md#47-method-doctor-and-method-migrate-th3]
    stories: [TH3.E4.US2]
  - records: [PR-015, QR-006, QR-012]
    theme: TH3
    requirements: []
    adrs: [ADR-002, ADR-003]
    components: [docs/architecture/components.md#2-canonical-skills-contracts]
    stories: [TH3.E4.US3]
  - records: [PR-013, QR-010, QR-013, QR-014]
    theme: TH3
    requirements: []
    adrs: [ADR-007, ADR-008]
    components: [docs/architecture/components.md#5-stores]
    stories: [TH3.E4.US4]
  - records: [PR-015, QR-002, QR-003, QR-010, QR-011]
    theme: TH3
    requirements: []
    adrs: [ADR-003]
    components: [docs/architecture/components.md#41-method-validate-th3]
    stories: [TH3.E4.US5]
  - records: [PR-015, QR-002, QR-003, QR-012]
    theme: TH3
    requirements: []
    adrs: [ADR-002, ADR-003]
    components: [docs/architecture/components.md#41-method-validate-th3]
    stories: [TH3.E4.US6]
  - records: [ASM-005]
    theme: TH4
    requirements: [PR-109, PR-110]
    adrs: [ADR-005]
    components: [docs/architecture/components.md#43-method-packet-th4]
    stories: []
  - records: [ASM-007, ASM-008]
    theme: TH4
    requirements: [PR-101, PR-102, PR-103, PR-104, PR-105, PR-106, PR-107, PR-108]
    adrs: [ADR-006]
    components: [docs/architecture/components.md#14-autopilot-skill-v2-th4-th5]
    stories: []
  - records: [DEF-004]
    theme: TH4
    requirements: [PR-104, PR-105]
    adrs: [ADR-006]
    components: [docs/architecture/components.md#14-autopilot-skill-v2-th4-th5]
    stories: []
  - records: [PR-101, PR-102, PR-103, PR-104, PR-105, PR-106, PR-107, PR-108]
    theme: TH4
    requirements: []
    adrs: [ADR-006]
    components: [docs/architecture/components.md#14-autopilot-skill-v2-th4-th5]
    stories: []
  - records: [PR-109, PR-110, PR-111, PR-112]
    theme: TH4
    requirements: []
    adrs: [ADR-005]
    components: [docs/architecture/components.md#43-method-packet-th4]
    stories: []
  - records: [PR-113, PR-114, PR-115]
    theme: TH4
    requirements: []
    adrs: [ADR-004, ADR-005, ADR-008]
    components: [docs/architecture/components.md#5-stores]
    stories: []
  - records: [ASM-003]
    theme: TH5
    requirements: [PR-201, PR-202]
    adrs: [ADR-007]
    components: [docs/architecture/components.md#44-method-usage-th5]
    stories: []
  - records: [ASM-004]
    theme: TH5
    requirements: [PR-204, PR-206]
    adrs: [ADR-007]
    components: [docs/architecture/components.md#45-method-budget-th5]
    stories: []
  - records: [ASM-006, DEC-022, RSK-007]
    theme: TH5
    requirements: [PR-208, PR-209, QR-016]
    adrs: [ADR-004]
    components: [docs/architecture/components.md#42-method-tx-contract-th4-enforced-th5]
    stories: []
  - records: [RSK-005]
    theme: TH5
    requirements: [PR-201, PR-202, QR-013]
    adrs: [ADR-007]
    components: [docs/architecture/components.md#44-method-usage-th5]
    stories: []
  - records: [RSK-006]
    theme: TH5
    requirements: [PR-204, PR-206]
    adrs: [ADR-007]
    components: [docs/architecture/components.md#45-method-budget-th5]
    stories: []
  - records: [RSK-012]
    theme: TH5
    requirements: [PR-211, PR-212, QR-014]
    adrs: [ADR-007]
    components: [docs/architecture/components.md#46-method-report-th5]
    stories: []
  - records: [DEF-001]
    theme: TH5
    requirements: [PR-201, PR-202]
    adrs: [ADR-007]
    components: [docs/architecture/components.md#44-method-usage-th5]
    stories: []
  - records: [DEF-002]
    theme: TH5
    requirements: [PR-204, PR-206]
    adrs: [ADR-007]
    components: [docs/architecture/components.md#45-method-budget-th5]
    stories: []
  - records: [DEF-003]
    theme: TH5
    requirements: [PR-208, PR-209, QR-016]
    adrs: [ADR-004]
    components: [docs/architecture/components.md#42-method-tx-contract-th4-enforced-th5]
    stories: []
  - records: [DEF-005]
    theme: TH5
    requirements: [PR-214]
    adrs: [ADR-007]
    components: [docs/architecture/components.md#46-method-report-th5]
    stories: []
  - records: [PR-201, PR-202, PR-203, PR-204, PR-205, PR-206, PR-207]
    theme: TH5
    requirements: []
    adrs: [ADR-007]
    components: [docs/architecture/components.md#45-method-budget-th5]
    stories: []
  - records: [PR-208, PR-209, QR-016]
    theme: TH5
    requirements: []
    adrs: [ADR-004]
    components: [docs/architecture/components.md#42-method-tx-contract-th4-enforced-th5]
    stories: []
  - records: [PR-210, PR-215]
    theme: TH5
    requirements: []
    adrs: [ADR-002, ADR-004]
    components: [docs/architecture/components.md#42-method-tx-contract-th4-enforced-th5]
    stories: []
  - records: [PR-211, PR-212, PR-213, PR-214]
    theme: TH5
    requirements: []
    adrs: [ADR-006, ADR-007]
    components: [docs/architecture/components.md#46-method-report-th5]
    stories: []
```
<!-- architecture-trace:end -->

## Document index

| Document | Content |
|---|---|
| `README.md` (this file) | System context, stage/gate map, staged activation, invariants, failure routing, migration |
| `tech-stack.md` | Stack selection, rubric, rejected options, constraints |
| `components.md` | Component responsibilities, interfaces, data ownership, dependencies, failure behavior |
| `data-model.md` | Record, schema, and store definitions with ownership and retention |
| `project-setup.md` | Repository layout, commands, exit codes, tests, conventions |
| `history/VP1-VP2-methodology-and-gitflow.md` | Locked TH1/TH2 architecture context |
| `../ADRs/` | ADR-001 (locked, Gitflow) and ADR-002..ADR-008 (VP3) |

No `deployment.md` exists. VP3 has no deployment target: the method ships as
repository content plus local commands and is consumed in-place by a local
Copilot CLI session. Release readiness is covered by `gitflow-operator`
(ADR-001) and the theme report (ADR-007).

## System context

The product is the method itself. It is composed of:

- human-readable lifecycle artefacts (markdown records) under `docs/`;
- canonical method contracts (skills) and thin roles (agents) under `.github/`;
- local, network-free commands under `bin/` that validate contracts, transition
  runtime state, build agent packets, sample usage, and report outcomes.

There is no server, database, or deployed runtime. Authority lives with the
human designer; agents are proposers until an authority or a validator accepts
their evidence (ADR-002, DEC-023).

```text
Human designer
  |
  +-- kickstart ----> vision sketch            docs/vision_of_product/VP<n>-<slug>/
  |
  +-- discover -----> Discovery dossier        docs/discovery/VP<n>-<slug>/
  |                     facilitator + bounded investigators
  |                     [gate] human readiness acceptance
  |
  +-- requirements -> approved PRD             docs/requirements/VP<n>-<slug>/PRD.md
  |                     [gate] human PRD approval
  |
  +-- plan ---------> stage 1 architecture     docs/architecture/, docs/ADRs/
  |                     [gate] human architecture acceptance
  |                   stage 2 planning         docs/themes/, docs/plan/backlog.yaml
  |
  +-- autopilot ----> packets, controls, delivery evidence
                        docs/plan/runtime/, gitflow-operator evidence
```

## Stage and gate map

| Stage | Entrypoint | Owning artefact | Gate | Authority | Enforced by |
|---|---|---|---|---|---|
| 1 Vision sketch | `kickstart` | `docs/vision_of_product/VP<n>-<slug>/` | none (sketch) | human | - |
| 2 Discovery | `discover` | `docs/discovery/VP<n>-<slug>/` | readiness verdict accepted | human | `method validate gates` |
| 3 PRD finalization | `requirements` | `docs/requirements/VP<n>-<slug>/PRD.md` | PRD approval | human | `method validate gates` |
| 4 Architecture | `plan` stage 1 | `docs/architecture/`, `docs/ADRs/` | architecture acceptance | human | `method validate gates` |
| 5 Planning | `plan` stage 2 | `docs/themes/`, `docs/plan/backlog.yaml`, and `docs/themes/TH<n>-<slug>/planning-admission.md` | `Accepted` planning-admission record at exact validated source revision | product owner + validator | `method validate gates` |
| 6 Autopilot | `autopilot` | `docs/plan/runtime/`, delivery repos | story/epic/theme DoD | orchestrator, reviewer, human | `method tx`, `method budget`, `method packet` |

Rules (PR-001, PR-010, INV-001):

- A stage command refuses to start when its upstream gate record is missing,
  unaccepted, or `BLOCKED`. Refusal is fail-closed with exit code 2.
- Each scope carries a Discovery disposition of `FULL`, `LIGHTWEIGHT`, or
  human-approved `WAIVED`; a `WAIVED` disposition invalidates on material scope
  expansion (PR-002).
- Accepted Discovery changes append `DR-###`; approved PRD changes append
  `PCR-###` (PR-007, PR-009). Neither rewrites accepted history.

## Component map

```text
.github/skills/          canonical contracts (one topic = one owner)
  discovery-dossier/       dossier records, dispositions, verdicts, DR
  product-requirements/    PRD schema, PCR, traceability
  risk-and-verification/   R0-R3 triggers, verification/review profiles
  model-routing/           capability classes, policy, escalation
  agent-packets/           packet manifest, hashing, expansion
  cost-governance/         budgets, thresholds, dispositions, adapters
  the-copilot-build-method/ six-stage lifecycle, DoD, lock rules  (updated)
  backlog-management/      backlog schema v2, transitions          (updated)
  plan/ autopilot/ kickstart/ bdd-stories/ code-quality/ architecture-decisions/ gitflow-operator/

.github/agents/          thin roles
  discovery-facilitator    owns dossier coherence + readiness recommendation
  investigator             bounded evidence packets only
  requirements-facilitator PRD drafting and traceability
  architect / product-owner / orchestrator / developer / reviewer / troubleshooter

bin/
  method                   single method CLI (validate, tx, packet, usage,
                           budget, report, doctor, migrate)
  gitflow-operator         unchanged TH2 delivery contract (ADR-001)

methodlib/                 shared Python library for bin/method

docs/plan/
  backlog.yaml             authoritative runtime state and controls (schema v2)
  policy/                  versioned model and budget policy
  activation-ledger.yaml   control maturity ledger
  runtime/                 journal, packets, usage samples (bounded, compacted)
  backlog-archive/         locked theme snapshots and compacted runtime summaries
```

Detailed contracts are in `components.md`; schemas are in `data-model.md`.

## Authority and ownership

| Fact | Single owner |
|---|---|
| Vision outcome (`VO-`) | Canonical PRD `## Vision outcomes` table (`docs/requirements/VP<n>-<slug>/PRD.md`) |
| Discovery records (`DQ/EV/ASM/DEC/INV/RSK/DEF/EXP/DR`) | Discovery dossier |
| Product requirements (`PR/QR/PCR`) | PRD |
| Technical contracts and decisions | `docs/architecture/`, `docs/ADRs/` |
| Story definition and acceptance criteria | `docs/themes/.../US<l>-<slug>.md` |
| Runtime status, controls, budgets, aggregate usage | `docs/plan/backlog.yaml` |
| Transition history | `docs/plan/runtime/journal.ndjson` |
| Agent context selection | packet manifest under `docs/plan/runtime/packets/` |
| Control maturity | `docs/plan/activation-ledger.yaml` |
| Model and budget defaults | `docs/plan/policy/` |

No fact is duplicated across owners (INV-002). Derived views (reports,
summaries) are regenerated, never hand-edited.

## Architecture invariants

The invariant text below is a derived architecture mapping. The Discovery
dossier remains authoritative for `INV-###` definitions.

| ID | Invariant | Realization |
|---|---|---|
| INV-001 | No stage advances without an accepted gate or explicit waiver | `method validate gates`, fail-closed exit 2 |
| INV-002 | One authoritative owner per fact | ownership table above, validated by `method validate schema` |
| INV-003 | Locked artefacts immutable | `method validate lock` compares against locked-theme manifests |
| INV-004 | Consequential traceability preserved | `method validate trace` walks `VO -> DQ -> DEC/INV -> PR -> ADR -> story -> evidence` |
| INV-005 | Missing usage/verification evidence is `unknown`, never zero | usage adapter confidence labels (ADR-007) |
| INV-006 | Pause preserves recoverable state before stopping | `method budget check` runs after the last committed transition |
| INV-007 | Agents act only from packets matching source revisions | composite source hash verification (ADR-005) |
| INV-008 | Transitions atomic, ordered, recoverable, conflict-aware | `method tx` protocol (ADR-004) |
| INV-009 | Completion requires acceptance, verification, review, Gitflow, usage evidence or waivers | TH4 story DoD check in `method validate dod` |
| INV-010 | Controls cannot be weakened without authority | risk/verification override records (ADR-006) |
| INV-011 | Invalidated upstream decisions pause downstream work | `DR-###` impact set -> dependency subgraph pause (ADR-002) |
| INV-012 | Human approvals remain attributable | gate record fields: actor, timestamp, scope, verdict, rationale, source revision |

## Failure routing

| Failure | Detection | Behavior |
|---|---|---|
| Missing or unaccepted upstream gate | `method validate gates` | refuse stage, exit 2 |
| Illegal edit to locked artefact | `method validate lock` | fail, exit 2 |
| Broken consequential traceability | `method validate trace` | fail, exit 2 |
| Stale packet | `method packet verify` | reject, regenerate, exit 2 |
| Revision conflict | `method tx apply` | reject writer, exit 3, reconcile then retry |
| Crash before atomic replace | `method tx recover` | state byte-identical, journal `aborted` |
| Crash after replace, before commit marker | `method tx recover` | prepared hash matched, journal `recovered-commit` |
| Unresolvable state divergence | `method tx recover` | exit 5, human reconciliation required |
| Missing completion evidence | `method validate dod` | block unless explicit waiver recorded |
| Usage telemetry unavailable | `method usage sample` | confidence `unknown`, never `0` |
| Pause threshold observed | `method budget check` | exit 4, no new model call or delegation until human disposition |
| Model capability class unavailable | `method budget check --route` | policy-declared equivalent or pause; never silent downgrade |
| Discovery escape | facilitator or reviewer | open `DR-###`, pause affected dependency subgraph only, resume from earliest invalidated gate |
| Escape inside a locked theme | `method validate lock` | new VP and Discovery dossier; locked artefacts untouched |
| Filesystem lacks atomic replace or exclusive create | `method doctor` | refuse to enable `INSTRUMENTED`+ transitions |

## Staged activation

Controls declare maturity in `docs/plan/activation-ledger.yaml` using
`SPECIFIED -> MANUAL -> INSTRUMENTED -> ENFORCED -> VERIFIED` (PR-013,
ADR-008). TH3 delivers contracts and human-operated controls; TH4 and TH5
deliver instrumentation and enforcement.

| Control | TH3 | TH4 | TH5 |
|---|---|---|---|
| Six-stage gates and dispositions | `ENFORCED` (validator) | `VERIFIED` | `VERIFIED` |
| Dossier / PRD record schema | `ENFORCED` | `VERIFIED` | `VERIFIED` |
| Lock and traceability rules | `ENFORCED` | `VERIFIED` | `VERIFIED` |
| Control activation ledger | `MANUAL` | `INSTRUMENTED` | `ENFORCED` |
| Risk tiers and verification profiles | `SPECIFIED` | `ENFORCED` | `VERIFIED` |
| Model capability routing | `SPECIFIED` | `INSTRUMENTED` | `ENFORCED` |
| Agent packets and staleness | `SPECIFIED` | `ENFORCED` | `VERIFIED` |
| Backlog schema v2 controls | `SPECIFIED` | `ENFORCED` | `VERIFIED` |
| Revisioned transitions and recovery | `SPECIFIED` | `MANUAL` | `ENFORCED` |
| Usage measurement | `SPECIFIED` | `SPECIFIED` | `INSTRUMENTED` |
| Budget thresholds and pause | `SPECIFIED` | `SPECIFIED` | `ENFORCED` |
| Theme report and calibration | `SPECIFIED` | `MANUAL` | `ENFORCED` |

TH3 and TH4 have no usage instrumentation. QR-013 blocks completion on missing
usage evidence, so each theme requires its own human-recorded waiver naming the
control, exact theme scope, and expiry at that theme's acceptance or earlier
instrumentation. This is an explicit waiver by the applicable authority, not a
silent exemption or a reusable cross-theme waiver.

## Migration path

1. TH1 and TH2 artefacts, ADR-001, and `docs/plan/backlog-archive/TH1.yaml`
   remain valid and untouched (QR-004). They carry schema version 1 implicitly;
   `method validate` treats absent `schema-version` on locked or archived
   themes as version 1.
2. New or unlocked themes use `schema-version: 2` (PR-115, QR-005).
3. `method migrate assess` writes `docs/plan/migration-assessment.md` for an
   existing repository: current stage coverage, missing gate records, control
   maturity, and the prospective adoption point. It never fabricates historical
   Discovery or usage evidence (PR-014).
4. VP3 self-hosting: the PRD `## Approval` table and dossier `## Acceptance`
   table conform to the canonical gate-record format. `DR-001` records the
   normalization and lifecycle/scope alignment without rewriting accepted
   conclusions.
5. Locked-theme escapes create a new VP and dossier; they never reopen TH1/TH2.

## Deferral dispositions

The deferral definitions remain authoritative in the Discovery dossier. This
table records only their architecture dispositions.

| Deferral | Architecture disposition |
|---|---|
| DEF-001 telemetry adapter | `copilot-cli-session-checkpoint` adapter is production; `token-proxy` is the estimated fallback (ADR-007) |
| DEF-002 overshoot and nested accounting | Per-capability-class overshoot allowance plus baseline/delta nested accounting (ADR-007) |
| DEF-003 transition command, validation, compaction, conflict UX | `method tx` with prepare/replace/commit journal and theme-lock compaction (ADR-004) |
| DEF-004 model class mapping | `docs/plan/policy/model-policy.yaml`, versioned, equivalents or pause (ADR-006) |
| DEF-005 dossier and trace growth | `method report --growth` measures size per theme; permanent limits set only after TH5 data |

## Open architecture risks

| ID | Risk | Treatment |
|---|---|---|
| AR-001 | Current method instructions and README files still describe the implemented four-stage lifecycle until TH3 changes them; QR-012 requires one consistent lifecycle at TH3 completion | `method validate docs` blocks TH3 completion until all active method documentation uses the six-stage lifecycle |
| AR-002 | Markdown-table record parsing is sensitive to formatting drift | Strict table grammar, deterministic errors with file and row references, contract tests over fixtures |
| AR-003 | Usage adapter depends on local CLI internals that may change | Capability probe, version pinning in the ledger, degrade to `estimated`/`unknown`, never zero |
| AR-004 | Overshoot allowances are provisional and unvalidated | Versioned policy, calibrated only through a human-approved theme report |
| AR-005 | Runtime store growth could dominate the repository | Bounded retention per theme, compaction at theme lock, growth measured under DEF-005 |
| AR-006 | Orchestrator overhead of packets, validation, and journaling may exceed its own 30% target | Measure overhead as a first-class metric in the theme report before adding more automation |
