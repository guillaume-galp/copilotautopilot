# Project Setup

Local, network-free setup for the VP3 method tooling. No build step, no
packaging, no deployment target.

## Prerequisites

| Requirement | Version | Check |
|---|---|---|
| Python | 3.11+ (3.13 in use) | `python3 --version` |
| PyYAML | 6.x | `python3 -c "import yaml; print(yaml.__version__)"` |
| pytest | 8+ (9.0.3 in use) | `pytest --version` |
| git | any recent | `git --version` |
| Copilot CLI | session usage checkpoints, model selection, `--max-ai-credits` | `method doctor` |

Install PyYAML and pytest only if missing: `python3 -m pip install pyyaml pytest`.

## Repository layout (VP3 additions)

```text
bin/
  method                       new multi-command CLI (executable, shebang python3)
  gitflow-operator             unchanged (ADR-001)
methodlib/
  __init__.py
  cli.py                       argparse dispatch, shared options, JSON output
  exits.py                     shared exit codes
  records.py                   markdown table record parser and ID index
  gates.py                     gate record parsing and stage gating
  trace.py                     traceability graph resolution
  backlog.py                   schema v2 load, validate, closed op vocabulary
  txn.py                       lock, prepare, atomic replace, journal, recover
  packets.py                   manifest build, composite hashing, verify, expand
  usage.py                     adapter chain and confidence labeling
  budget.py                    nested scopes, thresholds, overshoot, dispositions
  activation.py                control maturity ledger checks
  report.py                    theme scorecard and growth metrics
  migrate.py                   migration assessment
docs/plan/
  policy/{model-policy.yaml,budget-policy.yaml,usage-policy.yaml}
  activation-ledger.yaml
  runtime/{journal.ndjson,packets/,usage/}
  reports/
  migration-assessment.md
tests/
  test_method_records.py       table parsing and ID indexing
  test_method_gates.py         gate refusal and waiver validity
  test_method_lock.py          locked artefact edit detection
  test_method_trace.py         dangling and missing traceability
  test_method_backlog.py       schema v1/v2 coexistence and op vocabulary
  test_method_txn.py           conflict, abort, recovery, ordering
  test_method_packets.py       composite hash, staleness, expansion authority
  test_method_usage.py         measured/estimated/unknown, never zero
  test_method_budget.py        target/warning/pause, overshoot, route fallback
  test_method_activation.py    maturity promotion evidence
  test_gitflow_operator.py     unchanged
  test_skill_gitflow_contract.py unchanged
```

`bin/method` inserts the repository root on `sys.path` and imports `methodlib`,
matching the zero-install style of `bin/gitflow-operator`. Tests invoke
`bin/method` as a subprocess for contract behavior and import `methodlib` for
unit behavior.

## Commands

```bash
bin/method doctor
bin/method validate all --json
bin/method validate gates --vp VP3 --stage architecture
bin/method migrate assess

bin/method packet build --story TH4.E1.US1 --task impl-1
bin/method packet verify --packet docs/plan/runtime/packets/TH4.E1.US1/impl-1.yaml
bin/method packet expand --packet <path> --request expansion.yaml

bin/method usage sample --scope TH5.E1.US1 --baseline
bin/method budget check --scope TH5.E1.US1 --class reasoning
bin/method budget disposition --scope TH5.E1.US1 --verdict simplify

bin/method tx apply --expected-revision 7 --ops ops.yaml --actor orchestrator
bin/method tx recover
bin/method report theme --id TH5 --growth
```

## Exit codes

| Code | Meaning | Caller behavior |
|---|---|---|
| 0 | Success | continue |
| 1 | Usage or input error | fix invocation |
| 2 | Validation failure (fail-closed) | stop, remediate, re-run |
| 3 | Revision conflict | reload state, reconcile, retry |
| 4 | Pause or blocked | stop model calls and delegation, request human disposition |
| 5 | Recovery required | run `method tx recover`, escalate on failure |

## Output contract

- stdout: one JSON object per invocation.
- stderr: human-readable diagnostics.
- Validation findings: `{check, severity, file, record, message, remediation}`.
- No command writes to stdout in non-JSON form, so tools can chain safely.

## Verification

```bash
pytest -q                                   # full suite (theme/release gate)
pytest -q tests/test_method_txn.py          # targeted (story gate)
time bin/method validate all --json         # must stay under 5 seconds (QR-011)
```

Story-level verification uses the smallest complete targeted selection for the
declared matrix. Epic-level suites are conditional. Theme and release gates run
the full suite (PR-107, DEC-016).

## Conventions

- Commit messages use qualified IDs: `feat(TH3.E1.US1): ...`.
- Delivery Gitflow operations go through `bin/gitflow-operator` (ADR-001).
- Markdown is ASCII, wrapped near 80 columns, using pipe tables for records.
- YAML keys are lowercase kebab-case; IDs keep their canonical uppercase form.
- Never hand-edit `docs/plan/backlog.yaml` once `method tx` reaches
  `ENFORCED`; before then, follow the read-modify-write protocol in the
  `backlog-management` skill and bump `revision`.
- Add to `.gitignore`: `docs/plan/runtime/.tx.lock`,
  `docs/plan/runtime/.tx.prepare`.

## Bootstrap order (TH3)

1. `methodlib` core: exits, records, YAML IO, hashing.
2. `method validate` checks: schema, gates, lock, trace, maturity, docs.
3. `discovery-dossier` and `product-requirements` skills.
4. `discover`, `requirements`, and `plan` v2 skill contracts plus facilitator
   and investigator agents.
5. Activation ledger, migration assessment, and lifecycle documentation
   updates (QR-012).
