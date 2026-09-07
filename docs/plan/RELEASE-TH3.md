# Release: Discovery and requirements foundation

## Summary

TH3 establishes the Discovery and requirements foundation for the six-stage
Copilot Build Method. It adds canonical Discovery and PRD records, interactive
workflows and bounded agents, local fail-closed validators, prospective
migration support, control-maturity reporting, and self-hosted verification.

Release readiness passed with 22 of 22 stories and 4 of 4 epics complete. The
full suite passed 735 tests, Ruff and compilation passed, `method validate all`
passed all six checks with zero findings, and all four VP3 lifecycle gate
checks passed. TH3 was then accepted at the explicit human checkpoint and
archived as the locked schema-v2 snapshot at backlog revision 68.

## Acceptance

| Field | Value |
|---|---|
| Actor | Human: designer |
| Timestamp | 2026-09-07T09:22:22.527+01:00 |
| Scope | TH3 |
| Verdict | Accepted |
| Rationale | Explicit human checkpoint acceptance of the completed TH3 release; WVR-001 is consumed at its contractual expiry, and TH3 usage remains unknown because no usage instrumentation was available. |
| Source revision | backlog revision 67; sha256:800f69de716dff98a938354128fbd766ee603a5f9b838a1819fef862ef34e6dc |

The acceptance baseline uses deterministic SHA-256 scope digests because this
human checkpoint has no release commit. It locks the TH3 theme directory and
archive snapshot plus ADR-002 through ADR-008 bodies. VP3 Vision, Discovery,
and PRD remain structurally unlocked and append-only through DR/PCR records
until TH4 and TH5 are accepted. WVR-001 is consumed at this boundary; absent
usage remains `unknown` and no instrumentation is claimed.

## Epics Delivered

- TH3.E1 — Lifecycle contracts and structured artefact schemas
- TH3.E2 — Local method CLI and TH3 contract validators
- TH3.E3 — Interactive Discovery and requirements workflow
- TH3.E4 — Activation, migration, and lifecycle integration

## Breaking Changes

- The active method now uses the canonical six-stage lifecycle: Vision sketch,
  Discovery, PRD finalization, Architecture, Planning, and Autopilot.
- `kickstart` hands off to `discover`; architecture and planning are separate
  gated stages of `plan`.
- New and unlocked backlog themes use schema version 2.
- Active lifecycle documentation is checked by `method validate docs`, and
  `method validate all` now executes schema, gates, lock, trace, maturity, and
  docs validation.

## Migration Notes

- Run `bin/method migrate assess` to produce a deterministic prospective
  migration assessment. Historical evidence that does not exist remains
  `unknown`; the command does not fabricate it.
- Existing locked TH1/TH2 artefacts and ADR-001 remain immutable.
- The accepted VP3 ownership contract is unchanged: the PRD owns `VO-###`
  records, Discovery owns `DEF-###` records, and PRD deferral rows are
  references.
- Current control maturity is four `ENFORCED` controls (CTL-001, CTL-002,
  CTL-003, CTL-014), one `MANUAL` control (CTL-004), and nine `SPECIFIED`
  controls (CTL-005 through CTL-013).
- WVR-001 was consumed by the explicit TH3 acceptance checkpoint. TH3 usage
  remains `unknown`, never zero; this does not claim instrumentation.
- No deployment document exists, so deployment readiness is not applicable.
- Gitflow operations remain not applicable because `develop` is missing. The
  operator prepared release-note evidence on `master`, but no branch, commit,
  merge request, CI watch, or merge was attempted.

## Publication

For the v0.9.0 publication, `develop` was initialized from the previous
v0.8.0 release and protected against deletion and force-pushes. The accepted
TH3 change set is delivered through a feature branch and pull request before
promotion to `master`.
