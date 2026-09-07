---
id: TH3.E1.US3
title: "Product requirements record schema"
type: standard
priority: high
size: M
agents: [developer]
skills: [bdd-stories, the-copilot-build-method]
traceability:
  vision: [VO-002, VO-003, VO-007]
  requirements: [PR-008, PR-009, PR-011, QR-006, QR-010]
  adrs: [ADR-002, ADR-003]
  invariants: [INV-004, INV-012]
acceptance-criteria:
  - AC1: "`.github/skills/product-requirements/SKILL.md` defines the PRD path `docs/requirements/VP<n>-<slug>/PRD.md` and its required sections."
  - AC2: "PR and QR tables require a `Traces` column whose values resolve to at least one upstream VO, DQ, DEC, INV, or RSK record."
  - AC3: "The `## Approval` gate record format is defined and complete human approval is required before the architecture stage may begin."
  - AC4: "PCR change records are append-only under `changes/PCR-###-<slug>.md` and carry reason, requestor, affected PR, QR, decisions, assumptions, risks and themes, Discovery and architecture impact, migration and replanning impact, human verdict, and source revision."
  - AC5: "The skill forbids the PRD from selecting components, technologies, or detailed interfaces, and points those decisions at the architecture stage."
depends-on: [TH3.E1.US1]
---

As a requirements facilitator, I want one canonical PRD schema so that approved
requirements stay measurable, attributable, and traceable without absorbing
architecture decisions.

## Acceptance criteria

- [ ] AC1: PRD path and required sections defined.
- [ ] AC2: Mandatory `Traces` column resolving upstream.
- [ ] AC3: Approval gate record required before architecture.
- [ ] AC4: Append-only PCR record fields defined.
- [ ] AC5: Component, technology, and interface selection excluded.

## BDD scenarios

### Happy path: an approved PRD passes the schema

Given a PRD with a complete `## Approval` table and traced requirements
When the schema is applied
Then every PR and QR resolves at least one upstream record
And the architecture stage may begin.

### Edge case: low-impact detail

Given a low-impact requirement detail has no single upstream record
When the schema is applied
Then a document-level reference is accepted
And the record is not treated as a consequential traceability failure.

### Error case: untraced consequential requirement

Given a consequential requirement has an empty `Traces` cell
When the schema is applied
Then the requirement is rejected with a remediation naming the missing upstream link
And the PRD cannot be approved.
