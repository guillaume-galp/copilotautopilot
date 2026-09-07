# TH3.E1 - Lifecycle Contracts and Structured Artefact Schemas

Canonical contracts that everything else in TH3 depends on: the six-stage
lifecycle and its gates, the Discovery dossier record schema, the product
requirements record schema, and the artefact templates that make gate records
and working state uniform.

This epic owns definitions only. Validation is TH3.E2 and the interactive
workflow is TH3.E3.

## Stories

| ID | Title | Priority | Risk | Depends on |
|---|---|---|---|---|
| TH3.E1.US1 | Six-stage lifecycle and gate contract | high | R2 | - |
| TH3.E1.US2 | Discovery dossier record schema | high | R2 | TH3.E1.US1 |
| TH3.E1.US3 | Product requirements record schema | high | R2 | TH3.E1.US1 |
| TH3.E1.US4 | Lifecycle artefact templates and gate records | medium | R1 | TH3.E1.US2, TH3.E1.US3 |

## Requirements

PR-001, PR-002, PR-003, PR-004, PR-005, PR-007, PR-008, PR-009, PR-011,
PR-012, QR-006, QR-008, QR-010.

## ADRs

ADR-002, ADR-003, ADR-008.

## Done when

- `the-copilot-build-method` is the single owner of the stage map and lock rules.
- `discovery-dossier` and `product-requirements` skills exist and are canonical.
- Templates for the dossier, PRD, EXP, DR, and PCR artefacts parse under the
  record grammar.
- No active skill or agent restates a lifecycle stage list.
