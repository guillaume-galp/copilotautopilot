---
id: TH3.E1.US4
title: "Lifecycle artefact templates and gate records"
type: standard
priority: medium
size: S
agents: [developer]
skills: [bdd-stories, the-copilot-build-method]
traceability:
  vision: [VO-002, VO-007]
  requirements: [PR-003, PR-005, PR-009, QR-008, QR-010]
  adrs: [ADR-002, ADR-003]
  invariants: [INV-012]
acceptance-criteria:
  - AC1: "Templates exist for the full dossier file set, the PRD, and the EXP, DR, and PCR file-per-record artefacts, each stored under its owning skill."
  - AC2: "A canonical `## Approval` / `## Acceptance` gate-record template carries actor, timestamp, scope, verdict, rationale, and source revision, plus Expiry and Invalidation for waivers."
  - AC3: "A canonical `## Working state` template carries Status, Open items, Accepted so far, and a single Next action, and is set to `accepted` or removed at the gate."
  - AC4: "All templates are ASCII pipe tables that parse under the record grammar, and every placeholder is written so a validator cannot mistake it for a real accepted record."
depends-on: [TH3.E1.US2, TH3.E1.US3]
---

As a facilitator, I want ready-made lifecycle artefact templates so that new scopes
produce schema-valid, resumable, attributable records without hand-assembling structure.

## Acceptance criteria

- [ ] AC1: Dossier, PRD, EXP, DR, and PCR templates available.
- [ ] AC2: Gate-record template with waiver extensions.
- [ ] AC3: Working-state template for resumability.
- [ ] AC4: ASCII, parseable, and non-deceptive placeholders.

## BDD scenarios

### Happy path: scaffold a new dossier

Given a new VP scope enters Discovery
When the facilitator scaffolds from the templates
Then every dossier file exists with its record table headers
And the README carries a `## Working state` block with status `not-started`.

### Edge case: paused Discovery resumes

Given a dossier has status `awaiting-human` and two open DQ items
When the session resumes
Then the Next action is read from the Working state block
And accepted decisions are not re-elicited.

### Error case: unfilled gate placeholder

Given a `## Approval` table still contains the `<actor>` placeholder
When the gate is evaluated
Then the gate is treated as not accepted
And the remediation names the missing actor field.
