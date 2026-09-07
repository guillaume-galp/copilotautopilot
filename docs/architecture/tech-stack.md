# Tech Stack

Scope: VP3 (TH3, TH4, TH5). The product is a methodology repository consumed by
a local Copilot CLI session. The stack is chosen for the simplest viable
architecture that satisfies the PRD (ADR-003).

## Selected stack

| Layer | Choice | Rationale |
|---|---|---|
| Lifecycle artefacts | Markdown with ID-prefixed pipe tables | Already used by the VP3 dossier and PRD (EV-006); human-first and diff-friendly; machine-parsable without a second source of truth |
| Runtime state | YAML (`docs/plan/backlog.yaml`, schema v2) | Existing authoritative format (DEC-014); ordered, reviewable, mergeable |
| Append-only traces | NDJSON (`journal.ndjson`) | Append-safe, crash-tolerant line framing, trivially compactable |
| Packet manifests | YAML per task | Human-inspectable, hashable, consistent with backlog tooling |
| Tooling language | Python 3.11+ standard library plus PyYAML | Already present (`bin/gitflow-operator`, PyYAML 6, Python 3.13); zero install beyond PyYAML |
| CLI surface | Single `bin/method` dispatcher plus `methodlib/` package | Shared primitives (records, hashing, YAML IO, journal, exit codes) used by every command |
| Tests | pytest contract tests in `tests/` | Existing convention (`tests/test_gitflow_operator.py`) |
| Version control | Git | Provides durable history and blob revisions used by packet hashing |
| Delivery operations | `bin/gitflow-operator` (unchanged) | Locked TH2 contract, ADR-001 |

## Constraints honored

| Constraint | Effect on stack |
|---|---|
| QR-007 provider and language neutrality | Method contracts never name a model vendor or target language; model classes are provider-neutral and resolved through policy |
| QR-011 no network, under five seconds | Pure local filesystem reads, no HTTP client, no external service, lazily loaded validators |
| QR-006 thin agents, rich skills | Reusable knowledge lives in skills, schemas, and validators; agent files stay declarative |
| QR-009 untrusted content | Repository and researched content are parsed as data; no `eval`, no dynamic import of repository content, no execution of retrieved instructions |
| QR-015 provenance without secrets | Records store paths, hashes, and versions; usage samples store aggregates, never tokens or credentials |
| QR-016 deterministic conflicts | `os.replace`, `O_EXCL` lock creation, and `fsync` are capability-probed by `method doctor` |

## Evaluation rubric

Scores: 1 (poor) to 5 (excellent).

| Option | Fitness | Maturity | Simplicity | Ecosystem | NFR fit | Security | Cost | Verdict |
|---|---|---|---|---|---|---|---|---|
| Python 3 stdlib + PyYAML, single CLI | 5 | 5 | 4 | 4 | 5 | 4 | 5 | Selected |
| Python + pydantic/jsonschema + typer | 5 | 5 | 2 | 5 | 4 | 4 | 3 | Rejected: dependency install for a repo that currently needs none |
| Node/TypeScript CLI | 4 | 5 | 2 | 5 | 4 | 4 | 3 | Rejected: introduces a second toolchain alongside existing Python tooling |
| Shell scripts plus `yq`/`jq` | 2 | 4 | 3 | 3 | 2 | 3 | 4 | Rejected: hashing, journal recovery, and schema validation become fragile |
| SQLite runtime store | 3 | 5 | 2 | 4 | 4 | 4 | 3 | Rejected: binary state is unreviewable and conflicts with backlog authority |
| Prompt-only method, no tooling | 2 | 3 | 5 | 2 | 1 | 2 | 5 | Rejected: cannot satisfy fail-closed validation (QR-002, QR-003) |

## Dependency policy

- Runtime dependencies: PyYAML only. Any new dependency requires an ADR.
- Test dependencies: pytest only.
- No network access at method runtime. Commands that would require it are not
  implemented; usage sampling reads local session state only.
- Standard library modules used: `argparse`, `hashlib`, `json`, `os`,
  `pathlib`, `re`, `subprocess` (git and gitflow-operator only), `tempfile`,
  `datetime`, `dataclasses`.

## Interface style

- Every `bin/method` subcommand emits JSON on stdout and human-readable
  diagnostics on stderr, mirroring `gitflow-operator`.
- Exit codes are shared across subcommands (see `project-setup.md`): `0` ok,
  `1` usage error, `2` validation failure, `3` conflict, `4` pause or blocked,
  `5` recovery required.
- Commands are idempotent where possible; state-changing commands take an
  expected revision.

## Deliberate non-choices

- No programming language, framework, or model vendor is standardized for the
  products built with this method (QR-007, non-goals).
- No external audit database, service, or dashboard in VP3.
- No packaging or distribution step; the repository is used in place.
