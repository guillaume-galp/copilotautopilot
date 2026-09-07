# ADR-008: Multi-Theme VP Lock Semantics and Control Activation Ledger

## Status

Accepted

## Context

VP3 maps to three themes (TH3, TH4, TH5) delivered in sequence (DEC-020). The
existing lock rule freezes a theme's VP, theme, story, and ADR artefacts when
the theme is accepted. Applied unchanged to a one-to-many VP, accepting TH3
would freeze the shared VP3, Discovery, and PRD artefacts that TH4 and TH5 still
depend on (RSK-010).

The PRD requires themes to lock independently while shared VP, Discovery, and
PRD artefacts lock only after all currently mapped themes are accepted (PR-012,
DEC-021), and requires that locked TH1 and TH2 artefacts remain valid without
migration (QR-004).

TH3 also self-hosts the method before enforcement exists. Controls must report
`SPECIFIED`, `MANUAL`, `INSTRUMENTED`, `ENFORCED`, or `VERIFIED` with their
effective point, limitations, and evidence (PR-013, DEC-025), so the first
theme cannot claim controls it has not implemented (RSK-011). Existing projects
must receive a migration assessment and adopt VP3 prospectively without
fabricated historical evidence (PR-014).

## Decision

1. Lock scope is split.

   | Artefact class | Locks when |
   |---|---|
   | Theme directory, story files, theme backlog snapshot | that theme is accepted |
   | ADR body | the first theme that depends on it is accepted |
   | VP document, Discovery dossier, PRD | all themes currently mapped to that VP are accepted |

2. While a VP has unaccepted mapped themes, its shared artefacts remain
   revisable only through append-only `DR-###` and `PCR-###` records. Direct
   rewriting of accepted content is never permitted.
3. A locked ADR body is immutable. The only permitted edit is changing `Status`
   to `Superseded by ADR-<NNN>` when a new ADR replaces it. ADR-001 is
   unaffected by VP3.
4. Adding a theme to an already fully accepted VP is not a lock reopening: it
   requires a new VP with its own Discovery and PRD, or a `PCR-###` recorded
   before the final mapped theme is accepted. ASM-010 (all mapped themes are
   known before VP artefacts lock) is the accepted precondition.
5. `docs/plan/activation-ledger.yaml` records every control with its
   requirement references, state, effective point, limitations, evidence,
   proposer, and human promoter. Promotion to `ENFORCED` requires bypass-attempt
   and recovery evidence; promotion to `VERIFIED` requires evidence from a
   completed theme. `method validate maturity` fails closed when a claimed
   state lacks its evidence or contradicts what the repository actually
   implements.
6. Theme acceptance reports actual control maturity. Where a required control is
   not yet instrumented, acceptance records an explicit, scoped, expiring waiver
   naming the control and exact theme. The waiver expires at that theme's
   acceptance or earlier instrumentation and cannot be reused by a later theme.
   TH3 and TH4 each require their own usage-evidence waiver (QR-013) because
   measurement arrives in TH5.
7. `method migrate assess` produces `docs/plan/migration-assessment.md` for a
   repository already using the four-stage method, recording current stage
   coverage, missing gate records, control maturity, and the prospective
   adoption point. It never generates historical Discovery, verification, or
   usage evidence.

## Consequences

### Positive

- A multi-theme VP can correct its shared basis until its scope is complete,
  without weakening theme-level immutability.
- Release claims match implemented reality, which keeps self-hosting honest.
- Existing repositories adopt VP3 without retroactive fabrication.
- TH1, TH2, ADR-001, and the TH1 archive stay valid and untouched.

### Negative

- Two lock scopes must be understood and validated instead of one.
- The activation ledger is an extra artefact to maintain per theme.
- Standing waivers for uninstrumented controls must be tracked to expiry.

### Risks

- Multi-theme locking freezes evidence too early (RSK-010). Mitigation:
  VP-level lock deferred until all mapped themes are accepted.
- A theme claims controls it has not implemented (RSK-011). Mitigation: evidence
  requirements per state and fail-closed maturity validation.
- Waivers become permanent. Mitigation: waivers name a control, a theme, and an
  activation point, and appear in the theme report.
- VP scope grows after partial acceptance. Mitigation: a `PCR-###` before final
  acceptance, otherwise a new VP.

## Alternatives Considered

### Lock all VP artefacts at first theme acceptance

- Pros: one simple rule, identical to the current method.
- Cons: TH4 and TH5 could not correct the shared Discovery or PRD basis.
- Rejected because: PR-012 and DEC-021 require independent theme locking.

### Never lock VP-level artefacts

- Pros: maximum flexibility.
- Cons: accepted evidence could be rewritten after delivery, destroying
  auditability.
- Rejected because: INV-003 requires immutability at acceptance boundaries.

### One VP per theme

- Pros: the existing one-to-one lock rule would suffice.
- Cons: fragments one coherent product direction into three visions and
  duplicates Discovery.
- Rejected because: DEC-020 accepted a single VP with three themes.

### Binary implemented or not-implemented control flag

- Pros: simplest possible reporting.
- Cons: hides the difference between a specified contract, a manually operated
  control, and a verified enforced one.
- Rejected because: DEC-025 requires five states with effective points and
  evidence.
