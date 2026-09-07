---
id: TH3.E2.US1
title: "method CLI foundation and methodlib core"
type: standard
priority: high
size: M
agents: [developer]
skills: [bdd-stories, the-copilot-build-method]
traceability:
  vision: [VO-007]
  requirements: [PR-015, QR-002, QR-007, QR-011]
  adrs: [ADR-003]
  invariants: [INV-002]
acceptance-criteria:
  - AC1: "`bin/method` is an executable python3 entrypoint that inserts the repository root on `sys.path`, imports `methodlib`, and dispatches `validate` and `doctor` while reserving `tx`, `packet`, `usage`, `budget`, `report`, and `migrate`."
  - AC2: "`methodlib/exits.py` defines the shared codes 0 success, 1 usage error, 2 validation failure, 3 conflict, 4 pause or blocked, 5 recovery required, and every subcommand uses them."
  - AC3: "Every invocation prints exactly one JSON object on stdout and all human diagnostics on stderr."
  - AC4: "The CLI performs no network access and imports nothing beyond the standard library and PyYAML."
  - AC5: "`method doctor` reports Python version, PyYAML version, git availability, atomic-replace and exclusive-create filesystem capability, and returns findings instead of raising when a capability is missing."
depends-on: []
---

As an orchestrator, I want one local method CLI with shared exit codes and a JSON output
contract so that every lifecycle check is scriptable, offline, and deterministic.

## Acceptance criteria

- [ ] AC1: `bin/method` dispatch with reserved subcommands.
- [ ] AC2: Shared exit-code module used everywhere.
- [ ] AC3: One JSON object on stdout, diagnostics on stderr.
- [ ] AC4: No network, no dependency beyond PyYAML.
- [ ] AC5: `method doctor` capability probe degrades gracefully.

## BDD scenarios

### Happy path: doctor reports capabilities

Given a repository with Python 3.11+, PyYAML, and git available
When `bin/method doctor` runs
Then stdout contains one JSON object listing each probed capability
And the exit code is 0.

### Edge case: unknown subcommand

Given a caller runs `bin/method frobnicate`
When the CLI dispatches
Then it emits a usage-error JSON object naming the valid subcommands
And exits 1.

### Error case: filesystem lacks atomic replace

Given the working filesystem cannot perform atomic replace
When `bin/method doctor` runs
Then the finding marks transition controls as blocked above MANUAL
And the command still exits 0 with the limitation recorded rather than crashing.
