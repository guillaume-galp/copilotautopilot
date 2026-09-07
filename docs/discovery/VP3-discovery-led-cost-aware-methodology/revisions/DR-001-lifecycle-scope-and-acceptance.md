# DR-001: Lifecycle, Scope, and Acceptance Alignment

| Field | Value |
|---|---|
| Reason | Normalize the accepted Discovery gate and align the mutable VP3 vision with the decisions reached during Discovery. |
| Requestor | Human product owner |
| Timestamp | 2026-09-05T16:34:40+01:00 |
| Affected records | DEC-001, DEC-005, DEC-007, DEC-020, DEC-021 |
| Downstream impact | VP3 vision, PRD, ADR-002, ADR-008 |
| Invalidated gates | None |
| Verdict | Accepted |
| Source revision | Discovery conversation and dossier dated 2026-09-05 |

## Changes

- Clarify that Discovery follows the Vision sketch and precedes PRD
  finalization.
- Name `discover` and `requirements` as separate interactive entrypoints.
- Replace the obsolete five-stage description with the accepted six-stage
  lifecycle.
- Record VP3 delivery through TH3, TH4, and TH5.
- Add the canonical machine-readable `## Acceptance` record to the dossier
  index.

## Rationale

The original VP3 draft treated PRDs as inputs to Discovery. The accepted
Discovery found that mechanisms and feasibility can materially change what the
product should promise, so PRD finalization must follow Discovery. This
revision changes no locked artefact and preserves the complete decision trail.

