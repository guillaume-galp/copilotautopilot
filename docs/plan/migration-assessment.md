# Migration Assessment

| Field | Value |
|---|---|
| Status | GENERATED |
| Generator | `bin/method migrate assess` |
| Target repository | `copilot-autopilot-methodology-improvements` |
| Assessed at | deterministic backlog revision 68 (no wall-clock timestamp) |
| Method version at assessment | `method/0.1.0` |

This assessment is prospective. It reports only repository evidence
available now; absent historical Discovery, verification, and usage remain
`unknown` and are never reconstructed.

## 1. Stage coverage

| Scope | Vision sketch | Discovery | PRD | Architecture | Planning | Autopilot |
|---|---|---|---|---|---|---|
| VP1 / TH1 | present | unknown | unknown | present | present | present |
| VP2 / TH2 | present | unknown | unknown | present | present | present |
| VP3 / TH3 | present | present | present | present | present | present |

Coverage values are `present`, `absent`, `not-applicable`, or `unknown`.
`present` means a current repository record supports the claim. Missing
historical material is `unknown`, not evidence that a stage failed.

## 2. Missing gate records

| Scope | Stage | Expected gate | Present | Note |
|---|---|---|---|---|
| VP1 / TH1 | Requirements | Discovery readiness acceptance | no | Not recorded; expected for a locked legacy scope and not remediated retroactively. |
| VP1 / TH1 | Architecture | PRD approval | no | Not recorded; expected for a locked legacy scope and not remediated retroactively. |
| VP1 / TH1 | Planning | Architecture acceptance | no | Not recorded; expected for a locked legacy scope and not remediated retroactively. |
| VP1 / TH1 | Autopilot | Planning-admission acceptance | no | Not recorded; expected for a locked legacy scope and not remediated retroactively. |
| VP2 / TH2 | Requirements | Discovery readiness acceptance | no | Not recorded; expected for a locked legacy scope and not remediated retroactively. |
| VP2 / TH2 | Architecture | PRD approval | no | Not recorded; expected for a locked legacy scope and not remediated retroactively. |
| VP2 / TH2 | Planning | Architecture acceptance | no | Not recorded; expected for a locked legacy scope and not remediated retroactively. |
| VP2 / TH2 | Autopilot | Planning-admission acceptance | no | Not recorded; expected for a locked legacy scope and not remediated retroactively. |
| VP3 / TH3 | Requirements | Discovery readiness acceptance | yes | Recorded current gate. |
| VP3 / TH3 | Architecture | PRD approval | yes | Recorded current gate. |
| VP3 / TH3 | Planning | Architecture acceptance | yes | Recorded current gate. |
| VP3 / TH3 | Autopilot | Planning-admission acceptance | no | Not recorded; expected for a locked legacy scope and not remediated retroactively. |

A missing gate for a locked legacy scope is expected and is not a
defect. The command records the gap and does not remediate it retroactively.

## 3. Control maturity snapshot

Derived verbatim from `docs/plan/activation-ledger.yaml`; the assessment
does not promote controls.

| Control | State | Effective point | Limitations |
|---|---|---|---|
| CTL-001 — Six-stage gate enforcement and Discovery dispositions | ENFORCED | method validate gates at Discovery, Requirements, Architecture, and Planning entry | The local validator enforces recorded entry gates; interactive orchestration of all six stages remains human-operated in TH3. |
| CTL-002 — Discovery dossier and PRD record schema | ENFORCED | method validate schema plus the gate and trace record parsers | Schema validation is local and repository-scoped; it does not validate future TH4 packet or policy formats. |
| CTL-003 — Lock scope and consequential traceability | ENFORCED | method validate lock and method validate trace | Open VP3 shared artefacts remain revisable under ADR-008 until every mapped theme is accepted. |
| CTL-004 — Control activation ledger | MANUAL | human promotion in this ledger at theme boundaries, checked by method validate maturity | A human still decides and records promotions; the validator checks evidence and repository support but does not make promotion decisions. |
| CTL-005 — Risk tiers, verification profiles, and review profiles | SPECIFIED | docs/plan/backlog.yaml story risk and verification declarations | TH3 declares tiers and profiles by hand. Architect validation, reviewer escalation, and enforcement are TH4 scope. |
| CTL-006 — Provider-neutral model capability routing | SPECIFIED | docs/plan/backlog.yaml story model-route declarations | docs/plan/policy/model-policy.yaml does not exist yet; the backlog policy reference is null until TH4. |
| CTL-007 — Agent packets and source staleness | SPECIFIED | docs/architecture/data-model.md packet manifest | No packets are generated in TH3. Story evidence.packets paths are reserved placeholders. TH4 scope. |
| CTL-008 — Backlog schema v2 controls | SPECIFIED | docs/plan/backlog.yaml schema-version 2 | TH3 authors schema v2 by hand and validates its shape only. Runtime control enforcement over these fields is TH4 scope. |
| CTL-009 — Revisioned transitions and recovery | SPECIFIED | ADR-004 transition protocol | method tx is not implemented. Backlog writes in TH3 follow the manual read-modify-write protocol and bump revision by hand. |
| CTL-010 — Usage measurement | SPECIFIED | ADR-007 adapter chain | No usage instrumentation exists in TH3 or TH4. All story usage values are null with confidence unknown and are never reported as zero.; QR-013 is satisfied for TH3 by docs/plan/waivers/TH3-usage-evidence.md, which expires at TH3 acceptance or earlier instrumentation and cannot be reused by TH4. |
| CTL-011 — Budget thresholds, pause, and dispositions | SPECIFIED | ADR-007 nested soft-cap budgets | docs/plan/policy/budget-policy.yaml does not exist yet; all budgets are null meaning unset and report-only. TH5 scope. |
| CTL-012 — Theme report and policy calibration | SPECIFIED | ADR-007 theme scorecard | method report is not implemented. TH3 acceptance reporting is prose plus this ledger. TH5 scope. |
| CTL-013 — Migration assessment | SPECIFIED | method migrate assess writes docs/plan/migration-assessment.md | Assessment is evidence-based and prospective; absent historical Discovery, verification, and usage remain unknown. |
| CTL-014 — Lifecycle documentation consistency | ENFORCED | method validate docs over active workspace, skill, agent, and test documentation | The validator intentionally excludes locked TH1/TH2 history, architecture history, archived agents and issue templates, and generated skill templates. |

## 4. Historical evidence confidence

| Scope | Discovery evidence | Verification evidence | Usage evidence |
|---|---|---|---|
| VP1 / TH1 | unknown | unknown | unknown |
| VP2 / TH2 | unknown | unknown | unknown |
| VP3 / TH3 | present | present | unknown |

Only structured evidence currently recorded for a scope is `present`.
Missing evidence is `unknown`; usage is never represented by a synthetic zero
and delivery status is never substituted for verification evidence.

## 5. Locked artefacts

| Artefact class | Locked | Migration required |
|---|---|---|
| TH1 theme and stories, and `docs/plan/backlog-archive/TH1.yaml` | yes | no |
| TH2 theme and stories, and `docs/plan/backlog-archive/TH2.yaml` | yes | no |
| TH3 theme and stories, and `docs/plan/backlog-archive/TH3.yaml` | yes | no |
| ADR-001 | yes | no |

Locked artefacts stay valid under their historical schema (QR-004, PR-115).
Absent `schema-version` on a locked or archived theme means version 1.

## 6. Prospective adoption point

| Field | Value |
|---|---|
| Adoption point | VP4 / TH4 (next new scope) |
| First scope required to run VP3 Discovery | VP4 / TH4 (next new scope) |
| Scopes adopting prospectively only | VP4 / TH4 and later new scopes |
| Legacy scopes retained without migration | VP1 / TH1, VP2 / TH2, VP3 / TH3 |
| Retroactive evidence generated | none, by contract |

## 7. Findings and remediation

| ID | Finding | Severity | Remediation |
|---|---|---|---|
| MIG-001 | 9 six-stage gate records are not recorded for locked legacy scopes. | information | Keep them missing; do not create retroactive gate history. |
| MIG-003 | Historical evidence remains unknown (Discovery: VP1 / TH1, VP2 / TH2; verification: VP1 / TH1, VP2 / TH2; usage: VP1 / TH1, VP2 / TH2, VP3 / TH3). | information | Retain `unknown`; never infer, reconstruct, or substitute zero/success. |

## Regeneration

```bash
bin/method migrate assess
```

For unchanged inputs, regeneration is byte-identical and does not rewrite
an already identical output. The command writes no other repository file.
