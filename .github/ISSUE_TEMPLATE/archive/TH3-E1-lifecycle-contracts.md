---
name: "TH3.E1 Lifecycle contracts and structured artefact schemas"
about: "Define the six-stage lifecycle, gate contract, Discovery and PRD record schemas, and artefact templates"
title: "TH3.E1: Lifecycle contracts and structured artefact schemas"
labels: ["theme:TH3", "epic:E1", "copilotautopilot", "lifecycle"]
assignees: ""
---

## Epic

TH3.E1 - Lifecycle contracts and structured artefact schemas

## Goal

Establish the canonical six-stage lifecycle, gate record format, multi-theme
lock scope, Discovery dossier schema, product requirements schema, and the
templates that make gate records and working state uniform.

## Stories

- [ ] TH3.E1.US1 - Six-stage lifecycle and gate contract: stage map, gate record fields, fail-closed refusal, split lock scope.
- [ ] TH3.E1.US2 - Discovery dossier record schema: file set, record prefixes, evidence classifications, dispositions, verdicts, DR rules.
- [ ] TH3.E1.US3 - Product requirements record schema: PRD sections, Traces column, approval gate, PCR rules.
- [ ] TH3.E1.US4 - Lifecycle artefact templates and gate records: dossier, PRD, EXP, DR, PCR, approval and working-state templates.

Full stories: `docs/themes/TH3-discovery-requirements-foundation/epics/E1-lifecycle-contracts/stories/`

## Acceptance criteria

- The six stages, their entrypoints, gates, and authorities have exactly one owner.
- Gate records carry actor, timestamp, scope, verdict, rationale, source revision.
- Theme artefacts lock at theme acceptance; VP, dossier, and PRD lock only after all mapped themes are accepted.
- Discovery and PRD records have stable IDs, provenance, and mandatory upstream traceability.
- Templates parse under the record grammar and cannot be mistaken for accepted records.

## Verification

- Fixtures covering the record grammar, gate record completeness, and template parsing.
- No active skill or agent restates the lifecycle stage list.

## Traceability

PR-001, PR-002, PR-003, PR-004, PR-005, PR-007, PR-008, PR-009, PR-011,
PR-012, QR-006, QR-008, QR-010; ADR-002, ADR-003, ADR-008.
