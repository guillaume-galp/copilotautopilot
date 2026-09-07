---
id: TH3.E4.US4
title: "TH3 usage-evidence waiver and honest acceptance reporting"
type: standard
priority: medium
size: S
agents: [developer]
skills: [bdd-stories, the-copilot-build-method, code-quality]
traceability:
  vision: [VO-006, VO-007]
  requirements: [PR-013, QR-010, QR-013, QR-014]
  adrs: [ADR-008, ADR-007]
  invariants: [INV-005, INV-009]
acceptance-criteria:
  - AC1: "`docs/plan/waivers/TH3-usage-evidence.md` records the standing waiver with control, theme, actor, timestamp, scope, verdict, rationale, source revision, expiry, and invalidation conditions."
  - AC2: "The waiver expires at TH3 acceptance, or earlier if CTL-010 reaches `INSTRUMENTED`, and is referenced from the usage-measurement control in `docs/plan/activation-ledger.yaml`."
  - AC3: "The waiver covers missing usage evidence only and explicitly does not waive acceptance, quality, verification, review, or Gitflow evidence."
  - AC4: "TH3 acceptance reporting states the actual maturity of every control and lists every open waiver with its expiry."
  - AC5: "Validation rejects a waiver that is unreferenced, undated, or without an expiry condition."
  - AC6: "The waiver is not reusable beyond TH3: a citation of `WVR-001` by TH4 or any later theme is rejected, and the finding requires that theme to create and approve its own scope-specific waiver."
depends-on: [TH3.E4.US1]
---

As a human designer, I want an explicit scoped waiver for missing usage evidence so that
TH3 can complete honestly while QR-013 is satisfied by an attributable, expiring decision
rather than a silent exemption.

## Acceptance criteria

- [ ] AC1: Waiver record with full gate-record fields plus expiry and invalidation.
- [ ] AC2: Expiry at TH3 acceptance or earlier CTL-010 `INSTRUMENTED`, referenced from the ledger.
- [ ] AC3: Scope limited to usage evidence only.
- [ ] AC4: Acceptance reporting states real maturity and open waivers.
- [ ] AC5: Incomplete waivers rejected.
- [ ] AC6: Reuse by TH4 or any later theme rejected.

## BDD scenarios

### Happy path: TH3 accepted with the waiver cited

Given TH3 has no usage instrumentation
And the standing usage-evidence waiver is recorded and referenced
When TH3 acceptance is evaluated
Then usage confidence is reported as `unknown` rather than zero
And acceptance proceeds with the waiver named in the report.

### Edge case: TH4 attempts to reuse the standing waiver

Given TH4 also completes before usage instrumentation exists
And TH4 acceptance cites `WVR-001` for its missing usage evidence
When TH4 acceptance is evaluated
Then the citation is rejected because the waiver expired at TH3 acceptance
And the finding requires TH4 to create and approve its own scope-specific waiver.

### Edge case: instrumentation arrives before TH3 acceptance

Given CTL-010 is promoted to `INSTRUMENTED` while TH3 is still in progress
When TH3 acceptance is evaluated
Then the waiver is reported as invalidated early rather than open
And TH3 acceptance requires the now-available usage evidence.

### Error case: waiver stretched to verification evidence

Given a story has no verification evidence
When the usage-evidence waiver is cited to close it
Then the claim is rejected
And the finding states that the waiver covers usage evidence only.
