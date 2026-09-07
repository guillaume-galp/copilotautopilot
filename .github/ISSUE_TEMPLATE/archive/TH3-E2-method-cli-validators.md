---
name: "TH3.E2 Local method CLI and contract validators"
about: "Deliver bin/method, methodlib core, and the schema, gates, lock, and trace validators"
title: "TH3.E2: Local method CLI and contract validators"
labels: ["theme:TH3", "epic:E2", "copilotautopilot", "tooling"]
assignees: ""
---

## Epic

TH3.E2 - Local method CLI and TH3 contract validators

## Goal

Provide the local, network-free `bin/method` entrypoint and `methodlib` core,
then make the TH3.E1 contracts fail closed through deterministic validators.

## Stories

- [ ] TH3.E2.US1 - method CLI foundation and methodlib core: dispatch, shared exit codes, JSON output contract, doctor probe.
- [ ] TH3.E2.US2 - Markdown record parser and ID index: table grammar, file-per-record artefacts, duplicate IDs, deterministic findings.
- [ ] TH3.E2.US3 - validate schema check: backlog schema v2 with version 1 coexistence for locked and archived themes; `backlog-management` owns the v2 schema and the `blocked` status.
- [ ] TH3.E2.US4 - validate gates check: stage gating, verdict and waiver validity, working-state reporting.
- [ ] TH3.E2.US5 - validate lock check: locked theme, archive snapshot, and ADR immutability, deferred VP-level lock.
- [ ] TH3.E2.US6 - validate trace check: traceability graph resolution and dangling reference detection; `bdd-stories` defines the story `traceability` frontmatter block.

Full stories: `docs/themes/TH3-discovery-requirements-foundation/epics/E2-method-cli-validators/stories/`

## Acceptance criteria

- One JSON object per invocation on stdout; diagnostics on stderr.
- Shared exit codes 0, 1, 2, 3, 4, 5 across every subcommand.
- Gate, lock, schema, and traceability violations fail closed with exit 2.
- TH1, TH2, ADR-001, and both archive snapshots, `docs/plan/backlog-archive/TH1.yaml` and `docs/plan/backlog-archive/TH2.yaml`, validate as locked without migration.
- `backlog-management` documents schema v2 and `blocked` with version 1 compatibility retained.
- `bdd-stories` defines the story `traceability` frontmatter block.
- No network access; no dependency beyond the standard library and PyYAML.

## Verification

- Passing and failing fixtures per check under `tests/`.
- Locked-artefact fixtures covering `docs/plan/backlog-archive/TH1.yaml` and `docs/plan/backlog-archive/TH2.yaml`.
- `bin/method validate all --json` timing assertion under five seconds.

## Traceability

PR-001, PR-002, PR-003, PR-004, PR-005, PR-006, PR-010, PR-011, PR-012,
PR-015, QR-002, QR-003, QR-004, QR-005, QR-006, QR-007, QR-008, QR-009,
QR-010, QR-011; ADR-002, ADR-003, ADR-004, ADR-008.
