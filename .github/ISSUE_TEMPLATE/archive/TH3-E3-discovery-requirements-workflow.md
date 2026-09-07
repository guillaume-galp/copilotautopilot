---
name: "TH3.E3 Interactive Discovery and requirements workflow"
about: "Deliver the discover and requirements skills, bounded facilitator agents, and gated two-stage plan"
title: "TH3.E3: Interactive Discovery and requirements workflow"
labels: ["theme:TH3", "epic:E3", "copilotautopilot", "discovery"]
assignees: ""
---

## Epic

TH3.E3 - Interactive Discovery and requirements workflow

## Goal

Give the human designer an interactive Discovery and requirements flow where
skills own the dialogue, bounded internal agents investigate and draft, and
`plan` cannot start architecture or planning without an accepted gate.

## Stories

Execution order by priority then story order: US1, US2, US3, US4, US6, US5.

- [ ] TH3.E3.US1 - discover interactive skill: dispositions, bounded DQ records, grouped checkpoints, readiness recommendation.
- [ ] TH3.E3.US2 - discovery-facilitator agent: dossier coherence, attributable acceptance, working-state maintenance.
- [ ] TH3.E3.US3 - investigator agent: one bounded question, evidence packet with provenance, untrusted-content handling.
- [ ] TH3.E3.US4 - requirements interactive skill: measurable requirements, traceability, resumable approval flow.
- [ ] TH3.E3.US5 - requirements-facilitator agent: drafting and traceability without technology choices or approval authority.
- [ ] TH3.E3.US6 - plan stage gating and human architecture checkpoint: gated stage 1 and stage 2, with `architect` taking the accepted dossier and approved PRD as inputs.

Full stories: `docs/themes/TH3-discovery-requirements-foundation/epics/E3-discovery-requirements-workflow/stories/`

## Acceptance criteria

- Every scope receives a FULL, LIGHTWEIGHT, or human-approved WAIVED disposition.
- A LIGHTWEIGHT run targets one grouped checkpoint and 30 minutes of human time.
- Only human acceptance opens the requirements gate.
- Retrieved content is untrusted evidence and is never executed.
- `plan` stage 2 refuses to run before recorded architecture acceptance.

## Verification

- Fixtures for gate refusal, waiver invalidation, resumed sessions, and
  instruction-injection handling.
- TH3.E3.US3 runs `integration-plus-failure-injection` at story level and
  `full-plus-release-readiness` at the theme gate.

## Traceability

PR-002, PR-003, PR-004, PR-005, PR-006, PR-008, PR-009, PR-010, PR-011,
PR-015, PR-016, QR-001, QR-002, QR-003, QR-005, QR-006, QR-008, QR-009,
QR-015; ADR-002, ADR-004, ADR-005.
