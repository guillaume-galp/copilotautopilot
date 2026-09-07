# TH3 - Discovery and Requirements Foundation

## Goal

Deliver the human-facing Discovery and requirements lifecycle for VP3: the
six-stage lifecycle contract and its gates, structured Discovery and PRD
schemas and templates, the interactive `discover` and `requirements`
entrypoints with bounded internal agents, the local `bin/method` foundation and
its TH3 validators, revised `plan` stage gating with a human architecture
checkpoint, multi-theme VP lock semantics, an honest control activation ledger,
a migration assessment, and one consistent lifecycle across all active
documentation and tests.

TH3 controls may operate at `MANUAL` maturity where instrumentation arrives
later. Nothing in TH3 claims a maturity it does not implement.

## References

| Input | Path |
|---|---|
| Vision | `docs/vision_of_product/VP3-discovery-led-cost-aware-methodology/` |
| Discovery dossier | `docs/discovery/VP3-discovery-led-cost-aware-methodology/` |
| PRD | `docs/requirements/VP3-discovery-led-cost-aware-methodology/PRD.md` |
| Architecture | `docs/architecture/README.md`, `components.md`, `data-model.md`, `project-setup.md`, `tech-stack.md` |
| ADRs | ADR-002 through ADR-008 |
| Backlog | `docs/plan/backlog.yaml` (schema v2) |

## Epics

| Epic | Name | Stories | Depends on |
|---|---|---|---|
| TH3.E1 | Lifecycle contracts and structured artefact schemas | 4 | - |
| TH3.E2 | Local method CLI and TH3 contract validators | 6 | TH3.E1 |
| TH3.E3 | Interactive Discovery and requirements workflow | 6 | TH3.E2 |
| TH3.E4 | Activation, migration, and lifecycle integration | 6 | TH3.E3 |

Total: 4 epics, 22 stories. The epic chain enforces foundation before workflow
before integration; story dependencies stay inside their epic.

## Scope boundaries

In scope for TH3:

- Six-stage lifecycle contracts, gates, dispositions, and verdicts.
- Discovery dossier and PRD record schemas, templates, gate records, and
  working-state resumability.
- `discover` and `requirements` interactive skills.
- `discovery-facilitator`, `investigator`, and `requirements-facilitator`
  bounded internal agents.
- `bin/method` and `methodlib` foundation plus the `schema`, `gates`, `lock`,
  `trace`, `maturity`, and `docs` validators.
- `plan` stage gating and the human architecture checkpoint.
- Multi-theme VP lock semantics.
- Control activation ledger at honest maturity.
- `method migrate assess` and its artefact.
- Lifecycle documentation and test alignment (QR-012).

Out of scope, deferred to TH4:

- Risk tier assignment enforcement, verification and review profile
  enforcement, task-level model routing, agent packets and source hashing,
  and backlog schema v2 runtime controls (PR-101 through PR-115).

Out of scope, deferred to TH5:

- Usage adapters, nested budgets, pause thresholds, revisioned transactions,
  recovery, theme reporting, and policy calibration (PR-201 through PR-215).

TH3 declares the schema v2 control fields in `backlog.yaml` because the theme
authors that file by hand. It does not implement TH4 or TH5 enforcement over
those fields. `docs/plan/policy/model-policy.yaml` and `budget-policy.yaml` do
not exist yet, so the backlog `policy` block is `null` until TH4 and TH5 create
them.

## Requirement coverage

| Requirement | Stories |
|---|---|
| PR-001 | TH3.E1.US1, TH3.E2.US4, TH3.E3.US6 |
| PR-002 | TH3.E1.US2, TH3.E2.US4, TH3.E3.US1 |
| PR-003 | TH3.E1.US2, TH3.E1.US4, TH3.E2.US2, TH3.E3.US2 |
| PR-004 | TH3.E1.US2, TH3.E2.US2, TH3.E3.US3 |
| PR-005 | TH3.E1.US4, TH3.E2.US4, TH3.E3.US2 |
| PR-006 | TH3.E2.US4, TH3.E3.US1, TH3.E3.US2 |
| PR-007 | TH3.E1.US2 |
| PR-008 | TH3.E1.US3, TH3.E3.US4, TH3.E3.US5 |
| PR-009 | TH3.E1.US3, TH3.E1.US4, TH3.E3.US4, TH3.E3.US5 |
| PR-010 | TH3.E2.US4, TH3.E3.US6 |
| PR-011 | TH3.E1.US3, TH3.E2.US6, TH3.E3.US5 |
| PR-012 | TH3.E1.US1, TH3.E2.US5 |
| PR-013 | TH3.E4.US1, TH3.E4.US4 |
| PR-014 | TH3.E4.US2 |
| PR-015 | TH3.E2.US1, TH3.E2.US2, TH3.E2.US3, TH3.E2.US4, TH3.E2.US5, TH3.E2.US6, TH3.E3.US6, TH3.E4.US1, TH3.E4.US2, TH3.E4.US3, TH3.E4.US5, TH3.E4.US6 |
| PR-016 | TH3.E3.US1, TH3.E3.US2, TH3.E3.US3, TH3.E3.US4, TH3.E3.US5 |
| QR-001 | TH3.E3.US1 |
| QR-002 | TH3.E2.US1, TH3.E2.US2, TH3.E2.US3, TH3.E2.US6, TH3.E3.US4, TH3.E4.US1, TH3.E4.US5, TH3.E4.US6 |
| QR-003 | TH3.E2.US3, TH3.E2.US4, TH3.E2.US5, TH3.E2.US6, TH3.E3.US6, TH3.E4.US1, TH3.E4.US5, TH3.E4.US6 |
| QR-004 | TH3.E2.US3, TH3.E2.US5, TH3.E4.US2 |
| QR-005 | TH3.E2.US3, TH3.E3.US6 |
| QR-006 | TH3.E1.US1, TH3.E1.US2, TH3.E1.US3, TH3.E2.US3, TH3.E2.US6, TH3.E3.US2, TH3.E3.US5, TH3.E3.US6, TH3.E4.US3 |
| QR-007 | TH3.E2.US1 |
| QR-008 | TH3.E1.US4, TH3.E2.US4, TH3.E3.US1, TH3.E3.US2, TH3.E3.US4 |
| QR-009 | TH3.E2.US2, TH3.E3.US3 |
| QR-010 | TH3.E1.US3, TH3.E1.US4, TH3.E2.US4, TH3.E4.US1, TH3.E4.US4, TH3.E4.US5 |
| QR-011 | TH3.E2.US1, TH3.E4.US5 |
| QR-012 | TH3.E4.US3, TH3.E4.US6 |
| QR-013 | TH3.E4.US4 |
| QR-014 | TH3.E4.US4 |
| QR-015 | TH3.E3.US3 |

PR-101 through PR-115 map to TH4. PR-201 through PR-215 map to TH5. QR-016
maps to TH5.

## Control activation targets

The ledger at `docs/plan/activation-ledger.yaml` starts every control at
`SPECIFIED` because nothing is implemented at planning time. TH3 acceptance
promotes only the controls it actually delivers. Every promotion to `ENFORCED`
requires both bypass-attempt evidence and restore-and-pass recovery evidence
from a corrupt-then-restore run, produced by TH3.E4.US5 and consumed by
TH3.E4.US1.

| Control | State at TH3 start | Target at TH3 acceptance |
|---|---|---|
| CTL-001 six-stage gates and dispositions | SPECIFIED | ENFORCED |
| CTL-002 dossier and PRD record schema | SPECIFIED | ENFORCED |
| CTL-003 lock and traceability rules | SPECIFIED | ENFORCED |
| CTL-004 control activation ledger | SPECIFIED | MANUAL |
| CTL-005 risk tiers and verification profiles | SPECIFIED | SPECIFIED |
| CTL-006 model capability routing | SPECIFIED | SPECIFIED |
| CTL-007 agent packets and staleness | SPECIFIED | SPECIFIED |
| CTL-008 backlog schema v2 controls | SPECIFIED | SPECIFIED |
| CTL-009 revisioned transitions and recovery | SPECIFIED | SPECIFIED |
| CTL-010 usage measurement | SPECIFIED | SPECIFIED (waived) |
| CTL-011 budget thresholds and pause | SPECIFIED | SPECIFIED |
| CTL-012 theme report and calibration | SPECIFIED | SPECIFIED |
| CTL-013 migration assessment | SPECIFIED | MANUAL |
| CTL-014 lifecycle documentation consistency | SPECIFIED | ENFORCED |

## Standing waiver

TH3 has no usage instrumentation, so QR-013 is satisfied by the scoped standing
waiver at `docs/plan/waivers/TH3-usage-evidence.md`. It covers missing usage
evidence only, expires at TH3 acceptance or earlier instrumentation, cannot be
reused by later themes, and waives no acceptance, quality, verification,
review, or Gitflow obligation.

## Execution order

`TH3.E1.US1 -> US2 -> US3 -> US4`, then
`TH3.E2.US1 -> US2 -> US3 -> US4 -> US5 -> US6`, then
`TH3.E3.US1 -> US2 -> US3 -> US4 -> US6 -> US5`, then
`TH3.E4.US1 -> US3 -> US6 -> US2 -> US4 -> US5`.

Within an epic, ready stories are selected by priority then story order. The
orders above are the result of applying that rule, not the raw ID order:
TH3.E3.US6 and TH3.E4.US6 are high priority and become ready before the
medium-priority stories that follow them.

## Definition of Done

TH3 builds its own validators, so the Definition of Done is staged. A
`method` requirement applies only from the story that delivers the command
onwards; before that point the equivalent obligation is met by the targeted
and manual checks named below.

### Story

- Acceptance criteria verified against the declared verification matrix.
- Targeted checks pass; lint clean.
- Traceability is complete:
  - in TH3.E1, by manual review of the story `traceability` frontmatter
    against the PRD and ADR record IDs, recorded in the review;
  - from TH3.E2.US6 onwards, by `method validate trace` resolving the same
    frontmatter.
- Review completed at the declared review profile.
- Gitflow evidence produced through `bin/gitflow-operator`.
- Usage evidence recorded, or explicitly covered by the TH3 standing waiver.

### Epic

- All stories done.
- Epic-level suites run as declared by each story `suite-policy`.
- Because every TH3 epic has four or more stories, the reviewer completes an
  epic quality pass before the epic is marked done.
- Contract conformance is demonstrated:
  - for TH3.E1, by the epic pytest fixtures over the record grammar, gate
    record completeness, and template parsing, since no validator exists yet;
  - from TH3.E2 onwards, by the validators implemented so far, run through
    `bin/method validate <check> --json` for each delivered check;
  - from TH3.E4.US6 onwards, by `bin/method validate all --json` exiting 0.
- Changelog entry written.

### Theme

- All epics done.
- Full pytest suite green; `bin/method validate all --json` exits 0 in under
  five seconds, which is enforceable at the theme gate because every TH3
  validator is delivered by then.
- TH3.E3.US3 additionally satisfies its `full-plus-release-readiness` theme
  suite policy at the theme gate.
- Activation ledger updated to the maturity actually implemented, with
  bypass-attempt and restore-and-pass recovery evidence recorded for every
  control promoted to ENFORCED.
- Open waivers listed with their expiry.
- Vision revalidation against VP3 for the TH3 slice only.
- TH3 release notes created with delivered scope, breaking changes, migration
  guidance, control maturity, and open waivers.
- TH2 issue templates already archived; TH3 templates archived at the next
  theme boundary.
- User checkpoint, then `locked: true` on TH3 in `backlog.yaml`.
- VP3, its dossier, and its PRD remain unlocked until TH5 is accepted.
