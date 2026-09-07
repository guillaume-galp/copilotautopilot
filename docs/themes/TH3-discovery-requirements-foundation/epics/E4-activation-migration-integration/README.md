# TH3.E4 - Activation, Migration, and Lifecycle Integration

The integration slice that makes TH3 honest and self-hosting: the control
activation ledger and `validate maturity`, the migration assessment, the
lifecycle documentation migration and its `validate docs` check, the scoped
standing usage-evidence waiver, and the end-to-end validation run over this
repository.

Depends on TH3.E3 so that the full six-stage flow exists before it is
validated end to end.

## Stories

| ID | Title | Priority | Risk | Depends on |
|---|---|---|---|---|
| TH3.E4.US1 | Activation ledger and validate maturity check | high | R2 | - |
| TH3.E4.US2 | Migration assessment command and artefact | medium | R1 | - |
| TH3.E4.US3 | Lifecycle documentation migration to the six-stage lifecycle | high | R1 | - |
| TH3.E4.US4 | TH3 usage-evidence waiver and honest acceptance reporting | medium | R1 | TH3.E4.US1 |
| TH3.E4.US5 | TH3 self-hosted validation run | high | R2 | TH3.E4.US1, TH3.E4.US2, TH3.E4.US3, TH3.E4.US4, TH3.E4.US6 |
| TH3.E4.US6 | validate docs check and lifecycle documentation tests | high | R2 | TH3.E4.US3 |

Execution order by priority then story order:
`US1 -> US3 -> US6 -> US2 -> US4 -> US5`.

TH3.E4.US3 migrates documentation content only; TH3.E4.US6 implements the
`method validate docs` check and its tests over the migrated content.

## Requirements

PR-013, PR-014, PR-015, QR-002, QR-003, QR-004, QR-006, QR-010, QR-011,
QR-012, QR-013, QR-014.

## ADRs

ADR-002, ADR-003, ADR-007, ADR-008.

## Done when

- Every control reports the maturity it actually implements.
- Each control targeted at ENFORCED carries bypass-attempt evidence and
  restore-and-pass recovery evidence from a corrupt-then-restore run.
- `method migrate assess` produces an assessment with no fabricated history.
- No active method document, skill, agent, or test describes a four-stage
  lifecycle (QR-012, AR-001).
- The standing usage-evidence waiver is recorded, scoped, and expires at TH3
  acceptance or earlier CTL-010 `INSTRUMENTED`, and is not reusable by TH4.
- `bin/method validate all --json` exits 0 on this repository in under five
  seconds and the full pytest suite is green.
