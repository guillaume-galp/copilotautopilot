# Components

Each component declares responsibility, interface, data ownership,
dependencies, failure behavior, delivering theme, and activation state at the
end of that theme.

Legend for activation: `SPECIFIED`, `MANUAL`, `INSTRUMENTED`, `ENFORCED`,
`VERIFIED` (ADR-008).

## 1. Lifecycle entrypoints (skills)

### 1.1 `discover` skill (TH3)

| Aspect | Definition |
|---|---|
| Responsibility | Interactive evidence workbench: classify Discovery disposition, frame `DQ-###`, sequence bounded investigations, group human decision checkpoints, recommend a readiness verdict (PR-006) |
| Interface | Human dialogue; invokes `discovery-facilitator`; calls `method validate gates --vp <vp> --stage discovery` before recommending readiness |
| Owns | Nothing directly; drives the dossier through the facilitator |
| Depends on | `discovery-dossier` skill, `the-copilot-build-method`, VP sketch |
| Fails | Refuses to recommend `READY`/`READY_WITH_DEFERRALS` while validation fails or `unknown` items lack an owner and disposition |
| Activation | `ENFORCED` at TH3 |

Dispositions: `FULL`, `LIGHTWEIGHT`, `WAIVED` (human-approved, single scope,
invalidated by material scope expansion). A `LIGHTWEIGHT` run targets one
grouped checkpoint and 30 minutes of human time (QR-001).

Consequential assumptions, preferences, decisions, deferrals, overrides, and
risk acceptance are written only after attributable human acceptance; the
facilitator records actor, timestamp, scope, verdict, rationale, and source
revision on the accepting record (PR-005, INV-012). Only human acceptance of
the recommended verdict opens the requirements gate (PR-006).

Resumability (QR-008): the dossier `README.md` carries a `## Working state`
section with current status, open `DQ-###` items and their owners, accepted
decision IDs, and a single `Next action`. `method validate gates --stage
discovery` reports that block, so a paused Discovery resumes without replaying
accepted decisions.

### 1.2 `requirements` skill (TH3)

| Aspect | Definition |
|---|---|
| Responsibility | Translate accepted Discovery recommendations into measurable `PR-###`/`QR-###` requirements; obtain complete human approval; maintain `PCR-###` records |
| Interface | Human dialogue; invokes `requirements-facilitator`; calls `method validate gates --vp <vp> --stage requirements` |
| Owns | Nothing directly; drives the PRD through the facilitator |
| Depends on | Accepted dossier, `product-requirements` skill |
| Fails | Refuses to start without an accepted readiness verdict; refuses approval while any requirement lacks measurability or upstream traceability; never selects components, technologies, or interfaces |
| Activation | `ENFORCED` at TH3 |

Resumability (QR-008): an in-progress PRD keeps a `## Working state` section
with status, unresolved requirement drafts, open human questions, and the next
action. Approved content is never re-elicited.

### 1.3 `plan` skill v2 (TH3)

| Aspect | Definition |
|---|---|
| Responsibility | Stage 1 architecture (architect), human architecture checkpoint, stage 2 delivery planning (product owner) |
| Interface | `method validate gates --stage architecture` before stage 1; `--stage planning` before stage 2 |
| Owns | Nothing; delegates artefacts to architect and product owner |
| Depends on | Accepted dossier, approved PRD, `architecture-decisions`, `bdd-stories`, `backlog-management` |
| Fails | Exit 2 when Discovery or PRD gates are missing, unaccepted, or `BLOCKED`; stage 2 refuses to run before recorded architecture acceptance |
| Activation | `ENFORCED` at TH3 |

### 1.4 `autopilot` skill v2 (TH4, TH5)

| Aspect | Definition |
|---|---|
| Responsibility | Cost-aware execution loop: project eligible work, build and preflight packets, reconcile backlog transitions, verify completion authority, route models, enforce budgets, commit transitions, run ceremonies |
| Interface | Implemented packet lifecycle: `method packet project`, `build`, `preflight`, `reconcile`, and `verify`; planned TH4/TH5 controls: `method budget check`, `method tx apply`, `method validate dod`; delivery: `gitflow-operator` |
| Owns | Nothing; orchestrator writes state through `method tx` |
| Depends on | Backlog schema v2, policies, activation ledger |
| Fails | Blocks on stale packets, revision conflicts, pause thresholds, missing evidence |
| Activation | `ENFORCED` at TH4 for context and verification, `ENFORCED` at TH5 for economics |

`kickstart` is unchanged except for its handoff, which now points to `discover`
instead of `plan`.

## 2. Canonical skills (contracts)

| Skill | Owns | Theme |
|---|---|---|
| `discovery-dossier` | Dossier file set, record prefixes, evidence classifications, dispositions, verdict semantics, `DR-###` rules | TH3 |
| `product-requirements` | PRD structure, gate record format, `PCR-###` rules, traceability obligations | TH3 |
| `risk-and-verification` | R0-R3 triggers, verification matrix, review profiles, waiver authority | TH4 |
| `model-routing` | Capability classes, task-level routing, escalation record, unavailability behavior | TH4 |
| `agent-packets` | Packet manifest schema, source selection, hashing, expansion protocol, untrusted-source handling | TH4 |
| `cost-governance` | Budget scopes, thresholds, overshoot, dispositions, adapter contract, theme report | TH5 |
| `the-copilot-build-method` (update) | Six-stage lifecycle, DoD, naming, lock rules | TH3 |
| `backlog-management` (update) | Schema v2, status machine, transition protocol, compaction | TH4 |

Rule: one topic has exactly one owning skill; agents reference skills and never
restate their content (QR-006).

## 3. Agents (thin roles)

| Agent | Responsibility | May not |
|---|---|---|
| `discovery-facilitator` (TH3) | Investigation sequence, evidence taxonomy, dossier coherence, readiness recommendation | Approve consequential decisions or author the PRD |
| `investigator` (TH3) | Execute one bounded investigation and return an evidence packet with provenance and limitations | Modify the dossier, decide dispositions, or exceed its budget or stop condition |
| `requirements-facilitator` (TH3) | Draft requirements and traceability from accepted Discovery | Choose components, technologies, or interfaces; approve the PRD |
| `architect` (update TH3) | Components, interfaces, ownership, contracts, ADRs; validate story risk triggers | Weaken PRD requirements; edit locked ADR bodies |
| `product-owner` (update TH4) | Themes, epics, stories, dependencies, initial risk tiers, verification and model declarations | Assign a tier below the objective trigger without architect approval |
| `orchestrator` (update TH4/TH5) | Sequencing, packet assembly, budget gates, transitions, escape routing | Authorize a pause continuation or an R3 downgrade |
| `developer` (update TH4) | Implement one story with its declared verification matrix | Change tier, route, budget, or verification profile |
| `reviewer` (update TH4) | Review correctness, security, conventions; escalate risk tier; acknowledge R3 waivers | Lower a tier; grant the human half of an R3 waiver |
| `troubleshooter` (update TH4) | Diagnose and fix failed stories, classify Discovery escapes | Close an escape without a `DR-###` |

All agents are proposers. Their evidence becomes authoritative only after the
relevant authority or validator accepts it (DEC-023, PR-210).

## 4. `bin/method` commands

Shared library: `methodlib` (record parsing, YAML IO, hashing, journal, policy
loading, exit codes, capability probes).

### 4.1 `method validate` (TH3)

| Aspect | Definition |
|---|---|
| Responsibility | Deterministic, network-free, fail-closed contract validation |
| Interface | `method validate [all\|gates\|schema\|lock\|trace\|maturity\|docs] [--vp VP3] [--json]` |
| Owns | No lifecycle facts; emits findings only |
| Depends on | Repository files, `docs/plan/backlog.yaml`, locked-theme manifests |
| Fails | Exit 2 with `{check, severity, file, record, message, remediation}` per finding |
| Activation | `ENFORCED` at TH3 |

Checks map to PR-015: lifecycle bypass (`gates`), invalid verdict or waiver
(`gates`), broken consequential traceability (`trace`), illegal locked edits
(`lock`), inconsistent control maturity (`maturity`), obsolete lifecycle
documentation (`docs`). Budget: whole-repository `all` run under five seconds
(QR-011).

`method validate dod` is a TH4 execution control delivered with the risk,
verification, evidence, and backlog enforcement surface. It is not part of the
TH3 validator set.

### 4.2 `method tx` (contract TH4, enforced TH5)

| Aspect | Definition |
|---|---|
| Responsibility | Optimistic, atomic, recoverable state transitions on `backlog.yaml` |
| Interface | `method tx apply --expected-revision N --ops ops.yaml --actor <id>`, `method tx status`, `method tx recover` |
| Owns | `docs/plan/runtime/journal.ndjson`, `.tx.lock`, `.tx.prepare` |
| Depends on | `method validate schema`, filesystem atomic replace |
| Fails | Exit 3 on revision conflict, exit 5 when recovery cannot classify the state, exit 2 on schema violation |
| Activation | `MANUAL` at TH4, `ENFORCED` at TH5 |

Protocol: acquire `O_EXCL` lock -> compare expected revision -> apply ops
in-memory -> validate schema -> write prepare record (base hash, target hash,
new revision, ops digest) -> write temp file, `fsync`, `os.replace` -> append
journal commit -> remove prepare -> release lock. Recovery compares the current
file hash against the prepared base and target hashes and journals `aborted`,
`recovered-commit`, or exits 5.

Op vocabulary is closed: `set`, `append`, `increment`, restricted to allowed
backlog paths. Arbitrary path writes are rejected.

### 4.3 `method packet` (TH4)

| Aspect | Definition |
|---|---|
| Responsibility | Project one FIFO-eligible story; build its v1 mission packet; preflight workspace and freshness; reconcile append-only evidence and status changes; verify current authority |
| Interface | `method packet project [--expected-revision N]`; `method packet build --task <id> [--story <TH.E.US>] [--mode <developer\|planning>] --implementation-root <path> --allowed-implementation-root <path> --planning-root <repository-root> [--output <canonical-path>] [--trace-id <id>] [--expected-revision N]`; `method packet verify\|preflight\|reconcile --packet <canonical-path> --allowed-implementation-root <path> --expected-authorization-hash sha256:<digest>` |
| Owns | `docs/plan/runtime/packets/<TH.E.US>/<task>.yaml` |
| Depends on | Authoritative backlog, canonical story frontmatter/trace contract, architecture and ADR references, caller-retained authorization hash, canonical workspace paths |
| Fails | Exit 2 on ambiguous/ineligible projection, malformed story authority, stale or tampered packet, inaccessible or broad workspace, invalid transition, non-append evidence change, missing completion evidence, or incomplete parent Definition of Done |
| Activation | `ENFORCED` for the implemented BUG-001 lifecycle surface |

Every source is labeled `trusted` (method contracts) or `untrusted` (product
code, docs, retrieved content). Untrusted content is data, never instruction
(QR-009, RSK-009).

`build` requires exactly one planning root, and it must resolve to the
authoritative repository. The implementation root must be a writable directory
inside the explicit caller-authorized implementation boundary; both must be
disjoint from the planning root, and a filesystem root or ancestor containing
the repository is too broad. `verify`, `preflight`, and `reconcile` require the
authorization hash retained by the caller from `build` or the preceding
successful reconciliation. The hash stored inside the packet is not an
independent trust anchor.

`reconcile` accepts only a strictly newer backlog revision, one documented
status transition, and evidence lists that preserve every prior entry and only
append. Completion requires evidence for every verification matrix item,
review evidence, and Gitflow evidence or `not-applicable: <rationale>`. An epic
can become done only when all its stories are done; a theme can become done
only when all its epics are done. Reconciliation refreshes current evidence,
backlog and source hashes, the composite hash, status snapshots, history, and
the authorization hash atomically.

There is no implemented `method packet expand` command. Packet `expansions`
is a closed v1 manifest field reserved as an empty list.

### 4.4 `method usage` (TH5)

| Aspect | Definition |
|---|---|
| Responsibility | Capability adapter reporting cumulative AI-credit usage with confidence |
| Interface | `method usage sample [--scope <id>] [--baseline]`, `method usage adapters` |
| Owns | `docs/plan/runtime/usage/*.ndjson` samples |
| Depends on | Local Copilot CLI session state, `docs/plan/policy/usage-policy.yaml` |
| Fails | Never emits `0` for missing data; emits `confidence: unknown` with limitations |
| Activation | `INSTRUMENTED` at TH5 |

Adapter order: `copilot-cli-session-checkpoint` (`measured`, exact cumulative
nano-AIU) -> `token-proxy` (`estimated`, versioned pricing table) -> `none`
(`unknown`).

### 4.5 `method budget` (TH5)

| Aspect | Definition |
|---|---|
| Responsibility | Pre-call and pre-delegation gate over nested budget scopes |
| Interface | `method budget check --scope <id> --class <capability-class>`, `method budget open/close --scope <id>`, `method budget disposition --scope <id> --verdict <...>` |
| Owns | Budget aggregates written into `backlog.yaml` through `method tx` |
| Depends on | `method usage`, `docs/plan/policy/budget-policy.yaml`, `model-policy.yaml` |
| Fails | Exit 4 `PAUSE`; `CHECKPOINT` on warning; `REPORT` on target; refuses silent model downgrade |
| Activation | `ENFORCED` at TH5 |

Nested accounting uses baseline and delta over the cumulative measured value.
The effective pre-call limit subtracts the capability class overshoot allowance
so one in-flight response cannot cross the pause threshold unnoticed. Native
session limits (`--max-ai-credits`) stay configured as the final safety net.

### 4.6 `method report` (TH5)

| Aspect | Definition |
|---|---|
| Responsibility | Balanced theme scorecard: planned vs actual cost, model mix, flow, Discovery escapes, quality, scope, verification, waivers, evidence confidence, orchestrator overhead, artefact growth |
| Interface | `method report theme --id TH<n> [--growth]` |
| Owns | `docs/plan/reports/TH<n>-report.md` (generated) |
| Depends on | Backlog, journal, usage samples, packets, validator findings |
| Fails | Marks missing inputs as `unknown`; never substitutes zero |
| Activation | `ENFORCED` at TH5 |

Policy recalibration is applied only by a human-approved theme report, which
bumps `policy-version` in the affected policy file (PR-212).

### 4.7 `method doctor` and `method migrate` (TH3)

- `method doctor` probes filesystem capabilities (atomic replace, exclusive
  create, `fsync`), Python and PyYAML versions, git availability, and the usage
  adapter. Missing capabilities block promotion of transition controls beyond
  `MANUAL`.
- `method migrate assess` writes `docs/plan/migration-assessment.md` for
  repositories already using the four-stage method, recording current coverage,
  gaps, and the prospective adoption point without fabricating history.

### 4.8 `bin/gitflow-operator` (TH2, unchanged)

Delivery Gitflow evidence remains the ADR-001 contract. `method` does not
duplicate or wrap it; the orchestrator calls both.

## 5. Stores

| Store | Owner | Retention |
|---|---|---|
| `docs/plan/backlog.yaml` | orchestrator via `method tx` | Live; theme detail archived at lock |
| `docs/plan/runtime/journal.ndjson` | `method tx` | Append-only; compacted to a theme summary at lock |
| `docs/plan/runtime/packets/` | `method packet` | Through delivery and review; compacted at theme lock |
| `docs/plan/runtime/usage/` | `method usage` | Through the theme; summarized at lock |
| `docs/plan/policy/` | human-approved theme report | Versioned, append-only history |
| `docs/plan/activation-ledger.yaml` | reviewer proposes, human promotes | Live |
| `docs/plan/backlog-archive/` | theme lock ceremony | Permanent |

## 6. Dependency flow

```text
discovery-dossier ---> product-requirements ---> architecture + ADRs
        |                      |                        |
        v                      v                        v
   method validate  <----------+------------------ backlog schema v2
        |                                                |
        |                                                v
        +---------------------------------------> method packet ---> agents
                                                         |
                                             method usage -> method budget
                                                         |
                                                    method tx -> journal
                                                         |
                                                   method report -> policy
```

TH3 delivers the left column (contracts and validation). TH4 delivers packets,
risk, verification, routing, and schema v2. TH5 delivers usage, budgets,
transitions, recovery, reporting, and calibration.
