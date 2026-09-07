---
id: TH3.E2.US2
title: "Markdown record parser and ID index"
type: standard
priority: high
size: M
agents: [developer]
skills: [bdd-stories, the-copilot-build-method]
traceability:
  vision: [VO-001, VO-007]
  requirements: [PR-003, PR-004, PR-015, QR-002, QR-009]
  adrs: [ADR-003]
  invariants: [INV-002]
acceptance-criteria:
  - AC1: "`methodlib/records.py` parses ID-prefixed pipe tables into records carrying file, line, prefix, ID, and a column map."
  - AC2: "File-per-record artefacts EXP, DR, and PCR parse their stable ID from the document title and their fields from a `Field | Value` table."
  - AC3: "Duplicate, reused, or renumbered IDs within a VP scope are reported as findings with file and row references."
  - AC4: "Malformed tables produce deterministic findings shaped `{check, severity, file, record, message, remediation}` and never raise an unhandled exception."
  - AC5: "Parsed content is treated purely as data: no repository content is evaluated, imported, executed, or interpreted as an instruction."
depends-on: [TH3.E2.US1]
---

As a validator author, I want a strict markdown record parser so that human-first
artefacts are also the machine-readable source without a mirrored index.

## Acceptance criteria

- [ ] AC1: Table records parsed with file, line, prefix, ID, columns.
- [ ] AC2: File-per-record artefacts parsed from title and field table.
- [ ] AC3: Duplicate or reused IDs reported with references.
- [ ] AC4: Deterministic findings, no unhandled exceptions.
- [ ] AC5: Content handled as untrusted data only.

## BDD scenarios

### Happy path: parse the VP3 dossier

Given the VP3 Discovery dossier
When the parser indexes it
Then every DQ, EV, ASM, DEC, INV, RSK, and DEF record resolves to a unique ID
And each record reports its source file and row.

### Edge case: multi-value cell

Given a record cell contains `DEC-002, DEC-012`
When the parser reads it
Then both IDs are indexed as separate references
And whitespace around each ID is ignored.

### Error case: misaligned table row

Given a record row has fewer cells than the header
When the parser reads it
Then it emits a finding naming the file, the row number, and the expected column count
And parsing of the remaining records continues.
