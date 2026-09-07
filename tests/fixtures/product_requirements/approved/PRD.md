# VP99 Product Requirements Document

| Field | Value |
|---|---|
| Schema version | 1 |
| Product | Contract fixture |
| Vision | VP99: Contract fixture; docs/vision_of_product/VP99-fixture/VP99.md |
| Status | Approved |
| Version | 1.0 |
| Date | 2026-09-05 |
| Discovery verdict | READY |
| Discovery source revision | sha256:288ec55fdb1d02bf1c77ec084613f7250625841282b72e36e9045a4fa55106c4 |
| Delivery mapping | TH99 |

## Approval

| Field | Value |
|---|---|
| Actor | Human: product owner |
| Timestamp | 2026-09-05T18:00:00+01:00 |
| Scope | VP99 PRD version 1.0 |
| Verdict | Approved |
| Rationale | The complete fixture PRD is accepted for contract testing. |
| Source revision | sha256:04a85243ce479e2a3a9ec1e382dd39c6d74ee9db2bc7856ebe147e0da610b115 |

## Product promise

Give fixture users an observable, bounded result.

## Vision outcomes

| ID | Outcome |
|---|---|
| VO-001 | Users receive the bounded result. |

## Lifecycle

The result follows the accepted product lifecycle.

## Release scope

The first release includes the bounded result and its quality target.

## Functional requirements

| ID | Schema version | Requirement | Measure | Impact | Impact rationale | Traces |
|---|---|---|---|---|---|---|
| PR-001 | 1 | The product shall report completion to the user. | An acceptance scenario observes one completion report. | consequential | Changing the behavior alters observable scope and acceptance. | VO-001, DEC-001 |

## Quality requirements

| ID | Schema version | Requirement | Measure | Impact | Impact rationale | Traces |
|---|---|---|---|---|---|---|
| QR-001 | 1 | The completion report shall be available within one second. | Measure elapsed time in the acceptance scenario; maximum one second. | consequential | Changing the threshold alters an accepted quality target. | VO-001, INV-001 |

## Acceptance scenarios

Given a user starts the bounded operation, when it completes, then the user
observes a completion report within one second.

## Success measures

All fixture acceptance runs observe the bounded result.

## Constraints and deferrals

There are no accepted deferrals for this fixture.

## Non-goals

Selecting implementation components or technologies is not a goal.

## Change control

Consequential approved changes append
`changes/PCR-###-<slug>.md` under this PRD directory.
