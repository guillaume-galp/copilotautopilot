# TH3 Standing Waiver: Missing Usage Evidence

| Field | Value |
|---|---|
| Waiver ID | WVR-001 |
| Control | CTL-010 Usage measurement |
| Theme | TH3 Discovery and requirements foundation |
| Requirement waived | QR-013, limited to the usage-evidence clause |
| Status | Consumed |

## Approval

| Field | Value |
|---|---|
| Actor | Facilitator under explicit human-delegated decision authority |
| Timestamp | 2026-09-05T17:02:11+01:00 |
| Scope | Missing AI-credit usage evidence for every TH3 story, epic, and theme gate, for the duration of TH3 |
| Verdict | Approved |
| Rationale | The human explicitly delegated the remaining routine product decisions and execution at 2026-09-05T16:34:40+01:00. The facilitator recorded this scoped waiver after architecture acceptance. VP3 architecture places usage instrumentation in TH5 (ADR-007), so TH3 has no adapter capable of producing usage evidence. QR-013 requires an explicit waiver rather than a silent exemption, and ADR-008 requires theme acceptance to report actual control maturity. |
| Source revision | VP3 PRD 1.0, VP3 architecture accepted 2026-09-05T16:55:16+01:00, ADR-007, ADR-008 |
| Expiry | TH3 acceptance, or earlier if CTL-010 reaches `INSTRUMENTED` |
| Invalidation | Any of: a usage adapter becomes available and produces `measured` or `estimated` samples for TH3; the waived scope is extended beyond usage evidence; TH3 is superseded or re-scoped by a PCR record |

## What this waiver covers

- Absent AI-credit usage samples for TH3 stories, epics, and the theme gate.
- Story, epic, and theme `usage` values remaining `null` with
  `confidence: unknown`.
- Story, epic, and theme `budgets` remaining `null`, meaning unset and
  report-only.

Under INV-005 and PR-202, missing usage is recorded as `unknown` and is never
recorded as `0`. This waiver permits the absence of the evidence; it does not
permit fabricating it.

## What this waiver does not cover

This waiver does not weaken any other gate. It explicitly does not waive:

- acceptance criteria verification or story, epic, and theme Definition of Done;
- the declared verification matrix, targeted checks, or theme and release full
  suites;
- code review at the declared review profile;
- Gitflow evidence produced through `bin/gitflow-operator`;
- gate, lock, schema, maturity, documentation, or traceability validation;
- any risk tier, and in particular no R3 verification downgrade;
- honest control maturity reporting in `docs/plan/activation-ledger.yaml`.

Consistent with QR-014, an absence of usage evidence never compensates for a
failed safety, quality, scope, or acceptance gate.

## Applicability beyond TH3

This waiver is not valid for TH4 or any later theme. A later theme that lacks
usage instrumentation must create and approve its own scope-specific waiver.

## Review obligations

- The waiver is referenced from CTL-010 in `docs/plan/activation-ledger.yaml`.
- TH3 acceptance reporting lists this waiver as open with its expiry.
- At TH3 acceptance, this record is closed as consumed unless it was invalidated
  earlier by available instrumentation.

## Closure

| Field | Value |
|---|---|
| Actor | Human: designer |
| Timestamp | 2026-09-07T09:22:22.527+01:00 |
| Scope | TH3 |
| Verdict | Accepted |
| Rationale | Explicit human checkpoint acceptance of the completed TH3 release; WVR-001 is consumed at its contractual expiry, and TH3 usage remains unknown because no usage instrumentation was available. |
| Source revision | backlog revision 67; sha256:800f69de716dff98a938354128fbd766ee603a5f9b838a1819fef862ef34e6dc |
