---
id: TH3.E1.US1
title: "Six-stage lifecycle and gate contract"
type: standard
priority: high
size: M
agents: [developer]
skills: [bdd-stories, the-copilot-build-method, architecture-decisions]
traceability:
  vision: [VO-001, VO-003, VO-007]
  requirements: [PR-001, PR-012, QR-006]
  adrs: [ADR-002, ADR-008]
  invariants: [INV-001, INV-002, INV-003]
acceptance-criteria:
  - AC1: "`the-copilot-build-method` names the six stages (vision sketch, Discovery, PRD finalization, architecture, planning, autopilot) with entrypoint, owning artefact, gate, and authority for each."
  - AC2: "The skill defines the gate record fields (actor, timestamp, scope, verdict, rationale, source revision) and the verdict vocabulary READY, READY_WITH_DEFERRALS, BLOCKED, Approved, Rejected, Accepted."
  - AC3: "The skill states that a stage refuses to start when its upstream gate record is missing, incomplete, unaccepted, or BLOCKED, and that refusal is fail-closed with exit code 2."
  - AC4: "The skill defines split lock scope: theme artefacts lock at theme acceptance, an ADR body locks at first dependent theme acceptance, and VP, dossier, and PRD artefacts lock only after all mapped themes are accepted."
  - AC5: "The skill is the single owner of the stage list; every other active skill, agent, or instruction file references it instead of restating it."
depends-on: []
---

As a method author, I want one canonical six-stage lifecycle and gate contract so that
every entrypoint, agent, and validator enforces the same stage order and the same
acceptance authority.

## Acceptance criteria

- [ ] AC1: Six stages with entrypoint, artefact, gate, and authority.
- [ ] AC2: Gate record fields and verdict vocabulary defined.
- [ ] AC3: Fail-closed refusal rule with exit code 2 documented.
- [ ] AC4: Split lock scope for multi-theme VPs documented.
- [ ] AC5: Single-owner rule enforced; no duplicated stage lists.

## BDD scenarios

### Happy path: stage map resolves an entrypoint

Given an agent needs to know which gate precedes the architecture stage
When it reads `the-copilot-build-method`
Then it finds `plan` stage 1 preceded by an accepted readiness verdict and an approved PRD
And it finds the human as the acceptance authority for both.

### Edge case: multi-theme VP lock scope

Given VP3 maps to TH3, TH4, and TH5
And TH3 is accepted
When the lock rules are applied
Then the TH3 theme directory, story files, and theme backlog snapshot are immutable
And the VP3 document, Discovery dossier, and PRD remain revisable through DR and PCR records.

### Error case: duplicated lifecycle statement

Given an active skill restates the lifecycle stage list
When the single-owner rule is applied
Then the duplicated list is replaced by a reference to `the-copilot-build-method`
And the stage list has exactly one authoritative owner.
