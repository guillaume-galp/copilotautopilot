---
id: TH3.E4.US5
title: "TH3 self-hosted validation run"
type: standard
priority: high
size: M
agents: [developer]
skills: [bdd-stories, the-copilot-build-method, code-quality]
traceability:
  vision: [VO-007]
  requirements: [PR-015, QR-002, QR-003, QR-010, QR-011]
  adrs: [ADR-003]
  invariants: [INV-001, INV-003, INV-004]
acceptance-criteria:
  - AC1: "`bin/method validate all --json` exits 0 on this repository with TH3 artefacts, the TH1 and TH2 archives, and the VP3 dossier, PRD, and architecture records in place."
  - AC2: "The whole-repository `all` run completes in under five seconds and performs no network access."
  - AC3: "Each check, schema, gates, lock, trace, maturity, and docs, has at least one passing fixture and one failing fixture under `tests/`."
  - AC4: "For each of CTL-001, CTL-002, CTL-003, and CTL-014, a corrupt-then-restore recovery case runs before maturity promotion: the corrupted fixture drives its check to exit 2, the restored fixture drives the same check to exit 0, and both runs are recorded as the ENFORCED evidence consumed by TH3.E4.US1."
  - AC5: "`method validate maturity` refuses to accept an ENFORCED claim whose corrupt-then-restore recovery case has not been run in this repository."
  - AC6: "The full pytest suite passes and is recorded as the TH3 theme verification gate."
depends-on: [TH3.E4.US1, TH3.E4.US2, TH3.E4.US3, TH3.E4.US4, TH3.E4.US6]
---

As a method maintainer, I want the method validated against its own repository so that
TH3 proves the six-stage lifecycle end to end instead of only describing it.

## Acceptance criteria

- [ ] AC1: `validate all` exits 0 on this repository.
- [ ] AC2: Under five seconds, no network access.
- [ ] AC3: Passing and failing fixtures per check.
- [ ] AC4: Corrupt-then-restore recovery case per ENFORCED-target control.
- [ ] AC5: Unrun recovery case blocks the ENFORCED promotion.
- [ ] AC6: Full suite green and recorded as the theme gate.

## BDD scenarios

### Happy path: self-hosted validation is green

Given TH3 artefacts, archives, and VP3 records are in place
When `bin/method validate all --json` runs
Then the command exits 0
And stdout contains one JSON object summarizing every executed check.

### Edge case: timing budget under load

Given a repository fixture with several times the current record count
When `validate all` runs
Then the elapsed time stays under five seconds
And the timing assertion in the suite passes.

### Error case: deliberately corrupted fixture

Given a fixture repository with a broken gate record, a dangling trace, and an edited locked file
When `validate all` runs
Then the command exits 2
And it reports at least one finding for each of the gates, trace, and lock checks.

### Error case: recovery case not run before promotion

Given CTL-014 claims ENFORCED
And no corrupt-then-restore recovery case has been run for `method validate docs`
When `bin/method validate all --json` runs
Then the command exits 2
And the finding names CTL-014 and the missing recovery run.

### Edge case: corrupt-then-restore recovery per control

Given each of CTL-001, CTL-002, CTL-003, and CTL-014 has a corrupted fixture and a restored fixture
When the recovery cases run before maturity promotion
Then each corrupted run exits 2 with a finding naming its control
And each restored run exits 0
And both runs are recorded as that control's ENFORCED evidence.

## Retained evidence contract

`bin/run-th3-e4-us5-evidence` is the only generator for this story's retained
recovery and self-hosted outputs. Its operation vocabulary and validator
arguments are closed in source code. Evidence YAML contains no command to
execute.

Recovery evidence version 2 binds each control/check pair to:

- a canonical case from `tests/fixtures/method_recovery/cases.yaml`;
- SHA-256 digests of that fixture, the qualified test, the runner, and the
  closed validator input, including the deterministic transitive set of local
  Python implementation dependencies reached by the runner and `bin/method`;
- a bounded machine-generated JSON output and its SHA-256 digest;
- the observed exit and offset-aware completion timestamp.

`method validate maturity` reads those files as inert data, recomputes every
digest, checks the JSON result, and requires both pair timestamps to be
strictly earlier than the attributable human promotion.

The version 2 self-hosted report is generated only after lock verification. It
retains digested command, loaded-subprocess, network-namespace, and full-suite
outputs. Every retained aggregate command output must identify `validate all`
and contain exactly schema, gates, lock, trace, maturity, and docs with success
and zero findings. The loaded run must contain strictly more than three times
the baseline record count. The backlog copy is explicitly a point-in-time
observation rather than an immutable baseline. The orchestrator-owned session
log is omitted from baseline claims. TH3 and its shared VP remain unlocked,
and WVR-001 remains open.
