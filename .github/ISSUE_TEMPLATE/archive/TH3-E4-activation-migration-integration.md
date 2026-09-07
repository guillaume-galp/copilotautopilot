---
name: "TH3.E4 Activation, migration, and lifecycle integration"
about: "Deliver the activation ledger, migration assessment, documentation alignment, standing waiver, and self-hosted validation"
title: "TH3.E4: Activation, migration, and lifecycle integration"
labels: ["theme:TH3", "epic:E4", "copilotautopilot", "governance"]
assignees: ""
---

## Epic

TH3.E4 - Activation, migration, and lifecycle integration

## Goal

Make TH3 honest and self-hosting: report real control maturity, provide a
prospective migration path, migrate every active document to the six-stage
lifecycle and enforce it with `validate docs`, record the scoped
usage-evidence waiver, and validate the method against its own repository.

## Stories

Execution order by priority then story order: US1, US3, US6, US2, US4, US5.

- [ ] TH3.E4.US1 - Activation ledger and validate maturity check: five states with evidence thresholds and attributable promotion.
- [ ] TH3.E4.US2 - Migration assessment command and artefact: coverage, gaps, maturity, prospective adoption point.
- [ ] TH3.E4.US3 - Lifecycle documentation migration to the six-stage lifecycle: active README, instructions, skills, agents, and the `kickstart` handoff, with a migration inventory.
- [ ] TH3.E4.US4 - TH3 usage-evidence waiver and honest acceptance reporting: scoped, expiring, attributable waiver.
- [ ] TH3.E4.US5 - TH3 self-hosted validation run: `validate all` green under five seconds with the full suite passing.
- [ ] TH3.E4.US6 - validate docs check and lifecycle documentation tests: fail-closed enforcement of the migrated lifecycle, depends on TH3.E4.US3.

Full stories: `docs/themes/TH3-discovery-requirements-foundation/epics/E4-activation-migration-integration/stories/`

## Acceptance criteria

- No control claims a maturity it does not implement.
- Every control promoted to ENFORCED carries bypass-attempt evidence and restore-and-pass recovery evidence.
- The migration assessment fabricates no historical evidence.
- No active document, skill, agent, or test describes a four-stage lifecycle.
- The usage-evidence waiver covers usage only, expires at TH3 acceptance or earlier CTL-010 `INSTRUMENTED`, and is rejected if TH4 cites it; TH4 must create its own waiver.
- `bin/method validate all --json` exits 0 on this repository in under five seconds.

## Verification

- Full pytest suite green as the theme verification gate.
- Corrupted-fixture run reports one finding per broken check.
- Corrupt-then-restore recovery case per ENFORCED-target control, run before maturity promotion.

## Traceability

PR-013, PR-014, PR-015, QR-002, QR-003, QR-004, QR-006, QR-010, QR-011,
QR-012, QR-013, QR-014; ADR-002, ADR-003, ADR-007, ADR-008.
