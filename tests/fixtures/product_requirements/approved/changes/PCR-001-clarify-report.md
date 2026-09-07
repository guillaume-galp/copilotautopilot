# PCR-001: Clarify report wording

| Field | Value |
|---|---|
| Schema version | 1 |
| Requirement operation | replace |
| Change | PR-001 is logically replaced by PR-002, which uses user-facing completion wording. |
| Reason | User research found the original wording ambiguous. |
| Requestor | Human product owner |
| Affected PR | PR-001, PR-002 |
| Affected QR | None |
| Affected decisions | DEC-001 |
| Affected assumptions | None |
| Affected risks | RSK-001 |
| Affected themes | TH99 |
| Discovery impact | DEC-001 remains valid; Discovery gate is not invalidated. |
| Architecture impact | Recheck user-visible reporting contracts; no component selection is made here. |
| Migration impact | Existing documentation adopts the new user-facing wording. |
| Replanning impact | Recheck stories traced to PR-001. |
| Supersedes | PR-001 |
| Human actor | Human: product owner |
| Human timestamp | 2026-09-05T18:30:00+01:00 |
| Human scope | VP99 PCR-001 proposed content against PRD baseline sha256:04a85243ce479e2a3a9ec1e382dd39c6d74ee9db2bc7856ebe147e0da610b115 |
| Human verdict | Approved |
| Human rationale | The clarified observable result preserves the accepted outcome. |
| Baseline revision | sha256:04a85243ce479e2a3a9ec1e382dd39c6d74ee9db2bc7856ebe147e0da610b115 |
| Source revision | sha256:55568c1f9abc4bc1d7fc151fb90853cd67226109c8a525009357765741db7b68 |

| ID | Schema version | Requirement | Measure | Impact | Impact rationale | Traces |
|---|---|---|---|---|---|---|
| PR-002 | 1 | The product shall display a user-facing completion report. | An acceptance scenario observes one user-facing completion report. | consequential | Changing the behavior alters observable scope and acceptance. | VO-001, DEC-001 |
