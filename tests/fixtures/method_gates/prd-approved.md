# VP9 Product Requirements Document

| Field | Value |
|---|---|
| Schema version | 1 |
| Product | Fixture |
| Vision | VP9: Fixture; docs/vision_of_product/VP9-fixture/VP9.md |
| Status | Approved |
| Version | 1.0 |
| Date | 2026-09-05 |
| Discovery verdict | READY |
| Discovery source revision | sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa |
| Delivery mapping | TH9 |

## Approval

| Field | Value |
|---|---|
| Actor | Human: product owner |
| Timestamp | 2026-09-05T13:00:00+01:00 |
| Scope | VP9 PRD version 1.0 |
| Verdict | Approved |
| Rationale | The complete fixture requirements are approved. |
| Source revision | sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb |

## Product promise

The fixture promises deterministic validation.

## Vision outcomes

| Vision outcome | Product contribution |
|---|---|
| VO-001 | Requirements: PR-001, QR-001 |

## Lifecycle

The fixture follows the accepted lifecycle.

## Release scope

The fixture includes deterministic gate validation.

## Functional requirements

| ID | Schema version | Requirement | Measure | Impact | Impact rationale | Traces |
|---|---|---|---|---|---|---|
| PR-001 | 1 | The product shall validate a stage gate. | A scenario observes the gate result. | consequential | A change alters lifecycle entry. | VO-001 |

## Quality requirements

| ID | Schema version | Requirement | Measure | Impact | Impact rationale | Traces |
|---|---|---|---|---|---|---|
| QR-001 | 1 | Validation shall fail closed. | A negative scenario exits two. | consequential | A change alters lifecycle safety. | VO-001 |

## Acceptance scenarios

Given an accepted gate, when validation runs, then the stage opens.

## Success measures

All gate scenarios produce deterministic results.

## Constraints and deferrals

There are no fixture deferrals.

## Non-goals

Implementing a deployment service is not a goal.

## Change control

Approved changes append a PCR.
