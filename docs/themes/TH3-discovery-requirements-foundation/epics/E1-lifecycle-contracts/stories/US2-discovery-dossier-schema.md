---
id: TH3.E1.US2
title: "Discovery dossier record schema"
type: standard
priority: high
size: M
agents: [developer]
skills: [bdd-stories, the-copilot-build-method]
traceability:
  vision: [VO-001, VO-007]
  requirements: [PR-002, PR-003, PR-004, PR-007, QR-006]
  adrs: [ADR-002, ADR-003]
  invariants: [INV-002, INV-011]
acceptance-criteria:
  - AC1: "`.github/skills/discovery-dossier/SKILL.md` defines the dossier path `docs/discovery/VP<n>-<slug>/` and every required file with the records it owns."
  - AC2: "Record prefixes DQ, EV, ASM, DEC, INV, RSK, DEF, EXP, and DR are defined with required columns and the ID-prefixed markdown table grammar, including the file-per-record title form."
  - AC3: "Evidence classifications observed, inferred, hypothesis, assumption, preference, decision, and unknown are defined, and a hypothesis may not constrain a PRD until it is validated or accepted as an assumption."
  - AC4: "Dispositions FULL, LIGHTWEIGHT, and WAIVED and verdicts READY, READY_WITH_DEFERRALS, and BLOCKED are defined, and a WAIVED disposition names its invalidation conditions and is invalidated by material scope expansion."
  - AC5: "DR records are append-only and carry reason, requestor, affected records, downstream impact set, invalidated gates, and complete attributable human acceptance: actor, timestamp, scope, verdict, rationale, and immutable source revision."
  - AC6: "Every consequential record carries classification, provenance, confidence or limitations, owner, and disposition."
depends-on: [TH3.E1.US1]
---

As a discovery facilitator, I want one canonical dossier schema so that Discovery
evidence is structured, attributable, and machine-checkable without a second copy of
the same facts.

## Acceptance criteria

- [ ] AC1: Dossier path and file set with record ownership.
- [ ] AC2: Record prefixes, columns, and table grammar.
- [ ] AC3: Evidence classifications with the hypothesis restriction.
- [ ] AC4: Dispositions, verdicts, and waiver invalidation.
- [ ] AC5: Append-only DR fields with complete attributable human acceptance.
- [ ] AC6: Provenance fields required on consequential records.

## BDD scenarios

### Happy path: a new dossier follows the schema

Given a new VP scope requires Discovery
When the facilitator creates the dossier from the schema
Then every required file exists with its owning record prefix
And each record carries a stable ID, classification, provenance, and owner.

### Edge case: LIGHTWEIGHT dossier subset

Given a scope is classified LIGHTWEIGHT
When the dossier is created
Then the schema names the reduced but still-required record set
And omitted files are recorded as not-applicable rather than silently absent.

### Error case: attempted record deletion

Given DEC-004 was accepted and is now considered wrong
When an author tries to delete the DEC-004 row
Then the schema refuses deletion
And the only permitted change is a superseding DR record that names DEC-004 in its impact set.
