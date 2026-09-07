# TH3.E2 - Local Method CLI and TH3 Contract Validators

The local, network-free `bin/method` entrypoint and `methodlib` core, plus the
six TH3 validators that make the E1 contracts fail closed: `schema`, `gates`,
`lock`, `trace`, and, delivered in TH3.E4, `maturity` and `docs`.

Depends on TH3.E1 because every validator checks an E1 contract.

## Stories

| ID | Title | Priority | Risk | Depends on |
|---|---|---|---|---|
| TH3.E2.US1 | method CLI foundation and methodlib core | high | R1 | - |
| TH3.E2.US2 | Markdown record parser and ID index | high | R1 | TH3.E2.US1 |
| TH3.E2.US3 | validate schema check | high | R2 | TH3.E2.US1 |
| TH3.E2.US4 | validate gates check | high | R2 | TH3.E2.US2 |
| TH3.E2.US5 | validate lock check | high | R2 | TH3.E2.US2 |
| TH3.E2.US6 | validate trace check | medium | R2 | TH3.E2.US2 |

## Requirements

PR-001, PR-002, PR-003, PR-004, PR-005, PR-006, PR-010, PR-011, PR-012,
PR-015, QR-002, QR-003, QR-004, QR-005, QR-006, QR-007, QR-008, QR-009,
QR-010, QR-011.

## ADRs

ADR-002, ADR-003, ADR-004, ADR-008.

## Done when

- `bin/method` dispatches with shared exit codes and a single JSON object per
  invocation.
- Records parse deterministically with file and row references.
- `schema`, `gates`, `lock`, and `trace` fail closed with exit 2.
- TH1, TH2, ADR-001, and the archive snapshots
  `docs/plan/backlog-archive/TH1.yaml` and `docs/plan/backlog-archive/TH2.yaml`
  validate as locked without migration.
- `backlog-management` owns schema v2 and the `blocked` status with version 1
  compatibility retained, and `bdd-stories` owns the story `traceability`
  frontmatter block.

## Out of scope

`method tx`, `method packet`, `method usage`, `method budget`, and
`method report` are TH4 and TH5. Their subcommand names are reserved only.
