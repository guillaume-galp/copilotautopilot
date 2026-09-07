# ADR-003: Markdown Records, YAML State, and a Local Fail-Closed Validator

## Status

Accepted

## Context

VP3 requires structured Discovery dossiers and PRDs with stable IDs, provenance,
and consequential traceability (PR-003, PR-004, PR-011), plus local validators
that deterministically detect lifecycle bypasses, invalid verdicts or waivers,
broken traceability, illegal locked edits, inconsistent control maturity, and
obsolete lifecycle documentation (PR-015).

Quality requirements constrain the implementation: deterministic pass or fail
with references and remediation (QR-002), fail-closed on gate, lock, approval,
schema, and traceability violations (QR-003), no network and under five seconds
(QR-011), thin agents with knowledge in skills and validators (QR-006), and
untrusted repository content (QR-009).

The repository already contains a Python 3 tool (`bin/gitflow-operator`), pytest
contract tests, PyYAML, and a documentation-first architecture (EV-006). The
VP3 dossier and PRD already encode records as ID-prefixed markdown tables.

The tension is between human readability and machine checkability. Adding a
separate machine-readable mirror of each record would create two owners for the
same fact and violate INV-002.

## Decision

1. Consequential records are rows of ID-prefixed markdown pipe tables inside
   their owning artefact. File-per-record `EXP-###`, `DR-###`, and `PCR-###`
   artefacts place the stable ID in the title and use a `Field | Value`
   metadata table. The markdown is both the human artefact and the
   machine-readable source. No mirrored index file is generated or committed as
   authoritative.
2. Runtime state stays YAML (`docs/plan/backlog.yaml`). Append-only traces use
   NDJSON. Packet manifests and policies use YAML.
3. Validation and tooling ship as one CLI, `bin/method`, backed by a
   `methodlib` Python package using only the standard library plus PyYAML.
   `bin/gitflow-operator` is unchanged and is not absorbed.
4. `method validate` provides `gates`, `schema`, `lock`, `trace`, `maturity`,
   `docs`, and `dod` checks plus `all`. It performs no network access, reads
   only repository files, and targets under five seconds for `all`.
5. All violations in scope of QR-003 fail closed with exit code 2 and emit
   `{check, severity, file, record, message, remediation}`.
6. Shared exit codes across subcommands: `0` ok, `1` usage error, `2`
   validation failure, `3` conflict, `4` pause or blocked, `5` recovery
   required. Every subcommand prints one JSON object to stdout and diagnostics
   to stderr.
7. Repository and retrieved content are parsed as data. The tooling never
   evaluates, imports, or executes repository content, and packet sources are
   explicitly labeled `trusted` or `untrusted`.

## Consequences

### Positive

- Human artefacts remain the single source of truth; no dual maintenance.
- Zero new runtime dependencies beyond PyYAML, which is already installed.
- Validation is reproducible, offline, fast, and testable with pytest fixtures.
- One CLI concentrates shared primitives (records, hashing, YAML IO, journal).

### Negative

- Markdown table parsing is stricter than free-form prose; authors must follow
  the table grammar.
- A single CLI grows several subcommands and needs disciplined module
  boundaries.
- Validator rules become method-critical code that must itself be reviewed and
  tested.

### Risks

- Format drift breaks parsing (AR-002). Mitigation: strict grammar, precise
  file and row references in findings, contract tests over fixture artefacts,
  and `method validate docs` catching stale lifecycle documentation.
- Validator false negatives create false confidence (RSK-011). Mitigation: the
  activation ledger requires bypass-attempt evidence before a control is
  promoted to `ENFORCED`.
- Performance regression as repositories grow (QR-011). Mitigation: per-check
  lazy loading, a single file-read pass, and a timing assertion in the suite.

## Alternatives Considered

### YAML frontmatter or sidecar files as the machine-readable record

- Pros: trivial parsing; schema validation with existing libraries.
- Cons: duplicates each record in two places or hides consequential content
  from the human reader; violates single ownership.
- Rejected because: INV-002 requires one authoritative owner per fact and the
  accepted artefacts are human-first.

### JSON Schema plus pydantic validation

- Pros: mature declarative schema tooling.
- Cons: installs dependencies into a repository that currently needs none and
  does not solve markdown record parsing.
- Rejected because: the simplest viable stack already satisfies the
  requirements (tech-stack rubric).

### Separate single-purpose executables per capability

- Pros: mirrors `gitflow-operator`; small files.
- Cons: duplicates record parsing, hashing, YAML IO, journal, and exit-code
  logic across six tools.
- Rejected because: shared primitives dominate; one dispatcher with a shared
  library is simpler to keep consistent.

### Prompt-only validation by agents

- Pros: no tooling to build.
- Cons: non-deterministic, unverifiable, and cannot fail closed.
- Rejected because: QR-002 and QR-003 require deterministic fail-closed
  results.
