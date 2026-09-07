# Data Model

All lifecycle data is files in the repository. There is no database. Each
entity below names its owner, encoding, and retention.

## 1. Record encoding

Consequential records are rows of ID-prefixed markdown pipe tables inside their
owning artefact (ADR-003). The parser accepts:

```text
| ID | <column> | ... |
|---|---|---|
| <PREFIX>-<NNN> | <value> | ... |
```

Rules:

- The first column of a record table is the stable ID.
- IDs are unique per prefix within a VP scope and are never reused or renumbered.
- Cell values are plain text; multi-value cells use comma-separated IDs.
- Records are never physically deleted. An accepted record is logically
  superseded only by retaining the original unchanged and appending a
  `DR-###` or `PCR-###`.
- File-per-record artefacts (`EXP-###`, `DR-###`, and `PCR-###`) may place the
  stable ID in the document title and use a `| Field | Value |` metadata table.

Record prefixes: `VO`, `DQ`, `EXP`, `EV`, `ASM`, `DEC`, `INV`, `RSK`, `DEF`,
`DR`, `PR`, `QR`, `PCR`, `ADR`, and story IDs `TH<n>.E<m>.US<l>`. The
canonical PRD owns `VO`, `PR`, and `QR`; the Vision sketch is source context
and is not required to carry an `ID | Outcome` table.

## 2. Gate records

Every gate is a section named `## Approval` or `## Acceptance` in its owning
artefact, containing a `| Field | Value |` table:

| Field | Required | Meaning |
|---|---|---|
| Actor | yes | Human or role that granted the verdict |
| Timestamp | yes | ISO-8601 with offset |
| Scope | yes | What the verdict covers |
| Verdict | yes | `READY`, `READY_WITH_DEFERRALS`, `BLOCKED`, `Approved`, `Rejected`, `Accepted` |
| Rationale | yes | Why |
| Source revision | yes | Git revision or dated artefact revision the verdict applies to |

Waivers add `Expiry` and `Invalidation`. This satisfies QR-010 and INV-012 and
is the only machine-readable source of gate state (INV-002). Consequential
assumptions, preferences, decisions, deferrals, overrides, and risk acceptance
carry the same field set on their own record, so acceptance is always
attributable (PR-005) and only a human verdict opens a gate (PR-006).

## 2b. Working state (resumability)

An in-progress dossier or PRD carries a `## Working state` section:

| Field | Meaning |
|---|---|
| Status | `not-started`, `in-progress`, `awaiting-human`, `accepted`, `blocked` |
| Open items | Unresolved `DQ-###` or draft requirement IDs with owners |
| Accepted so far | Record IDs already accepted, which are never re-elicited |
| Next action | The single next step for the facilitator or the human |

The section is removed or set to `accepted` at the gate. It satisfies QR-008
and is the only place where in-flight lifecycle progress is persisted.

## 3. Discovery dossier

Path: `docs/discovery/VP<n>-<slug>/`

| Required path | Sole ownership |
|---|---|
| `README.md` | Dossier identity, source Vision, scope, dossier disposition, `DEF-###` records, readiness verdict, `## Working state`, and `## Acceptance` |
| `discovery-questions.md` | `DQ-###` Discovery questions |
| `system-map.md` | System context, actors, external dependencies, and trust and authority boundaries |
| `domain-ontology.md` | Dossier-specific domain terms, meanings, relationships, and instances only; it references but must not redefine canonical record prefixes or schemas |
| `mechanisms.md` | Candidate mechanisms and comparisons; accepted directions are references to `DEC-###`, not duplicate decisions |
| `evidence-index.md` | `EV-###` evidence records |
| `assumptions.md` | `ASM-###` assumptions and accepted preferences |
| `decisions.md` | `DEC-###` accepted decisions |
| `risks-and-failure-modes.md` | `INV-###` invariants and `RSK-###` risks, failure modes, and treatments |
| `prd-recommendations.md` | Recommendations for requirements and explicit non-requirements; it does not own `PR-###` records |
| `architecture-handoff.md` | Evidence-backed constraints, unresolved architecture decisions, and dossier record references |
| `experiments/EXP-###-<slug>.md` | One `EXP-###` experiment per file |
| `revisions/DR-###-<slug>.md` | One append-only `DR-###` Discovery Revision per file |

`DR-###` fields, in exact order after schema version and classification:
reason, requestor, affected records, downstream impact set (PR/QR/ADR/story
IDs), invalidated gates, actor, timestamp, scope, verdict, rationale, source
revision, provenance, confidence or limitations, owner, and disposition.
Requestor remains separate from the human acceptance actor. Actor, timestamp,
scope, verdict, rationale, and source revision form the complete attributable
acceptance; the source revision is immutable and uses the canonical
`git:<40 lowercase hexadecimal characters>` or
`sha256:<64 lowercase hexadecimal characters>` grammar. Creating a `DR` pauses
only the affected dependency subgraph (PR-215).

The `discovery-dossier` skill is the canonical owner of Discovery record
prefixes, ID grammar, schema versions, columns, metadata fields, and
applicability-marker grammar. `domain-ontology.md` owns the dossier's domain
concepts and terminology only; it may reference those canonical definitions
but cannot add, remove, rename, or redefine them.

Evidence classifications: `observed`, `inferred`, `hypothesis`, `assumption`,
`preference`, `decision`, `unknown`. A `hypothesis` cannot constrain a PRD until
validated or accepted as an assumption.

## 4. PRD

Path: `docs/requirements/VP<n>-<slug>/PRD.md`

Required sections: header table, `## Approval`, product promise, vision
outcomes, lifecycle, release scope, requirement tables (`PR-###` with `Traces`),
quality requirements (`QR-###`), acceptance scenarios, success measures,
constraints and deferrals, non-goals, change control.

The PRD's `## Vision outcomes` section is the sole canonical owner of
same-VP `VO-###` records. It contains an `ID | Outcome` table; Discovery
`Vision outcomes` cells and downstream traceability declarations resolve
against those PRD rows. A Vision sketch may describe intent in free form and
does not have to duplicate the rows.

The constraints and deferrals table may cite canonical dossier-owned
`DEF-###` records. Those cells are reference edges to the Discovery records,
not duplicate `DEF` definitions; Discovery remains the sole `DEF` owner.

Changes after approval: `docs/requirements/VP<n>-<slug>/changes/PCR-###-<slug>.md`
with reason, requestor, affected `PR`/`QR`/decisions/assumptions/risks/themes,
Discovery and architecture impact, migration and replanning impact, human
verdict, source revision.

## 5. Traceability graph

```text
PRD-owned VO-### -> DQ-### -> EV/ASM/DEC/INV/RSK/DEF -> PR-###/QR-### -> ADR-### ->
TH<n>.E<m>.US<l> -> verification, review, gitflow, and usage evidence
```

- Consequential records must resolve at least one upstream link and, once
  downstream work exists, at least one downstream link.
- Low-impact details may use document-level references.
- `method validate trace` resolves every declared ID and fails closed on
  dangling references (INV-004, PR-011).

## 6. `docs/plan/backlog.yaml` schema v2

Version 1 (TH1, TH2, archives) stays valid; absent `schema-version` on locked or
archived themes means version 1 (PR-115, QR-004).

```yaml
backlog:
  schema-version: 2
  revision: 7                     # monotonic; expected by every writer
  project: "<name>"
  last-updated: "<ISO-8601>"
  policy:
    model-policy: docs/plan/policy/model-policy.yaml@v1
    budget-policy: docs/plan/policy/budget-policy.yaml@v1
  active-themes:
    - id: TH3
      name: "Discovery and requirements foundation"
      schema-version: 2
      status: todo                # todo|in-progress|done
      locked: false
      vision-ref: docs/vision_of_product/VP3-discovery-led-cost-aware-methodology/
      discovery-ref: docs/discovery/VP3-discovery-led-cost-aware-methodology/
      requirements-ref: docs/requirements/VP3-discovery-led-cost-aware-methodology/PRD.md
      depends-on: []
      budgets: {target: null, warning: null, pause: null, unit: AIC}
      usage: {value: null, confidence: unknown, source: none, sampled-at: null}
      epics:
        - id: TH3.E1
          name: "<epic>"
          status: todo
          depends-on: []
          budgets: {target: null, warning: null, pause: null, unit: AIC}
          usage: {value: null, confidence: unknown, source: none, sampled-at: null}
          stories:
            - id: TH3.E1.US1
              title: "<title>"
              status: todo        # todo|in-progress|blocked|failed|done
              priority: medium
              file: docs/themes/TH3-<slug>/epics/E1-<slug>/stories/US1-<slug>.md
              depends-on: []
              risk:
                tier: R1          # R0|R1|R2|R3
                triggers: [concurrency]
                assigned-by: product-owner
                validated-by: architect
                overrides: []     # {from,to,authority,reviewer,rationale,record}
              model-route:
                default-class: balanced
                allowed-classes: [light, balanced, reasoning]
                escalations: []   # {task,class,question,scope,stop,estimated-aic,record}
              verification:
                profile: targeted-plus-integration
                matrix: [lint, unit, integration]
                suite-policy: {story: targeted, epic: conditional, theme: full}
                waivers: []       # {check,authority,reviewer,rationale,record}
              review-profile: standard
              budgets: {target: null, warning: null, pause: null, unit: AIC}
              usage: {value: null, confidence: unknown, source: none, sampled-at: null}
              evidence:
                packets: [docs/plan/runtime/packets/TH3.E1.US1/]
                verification: []
                review: []
                gitflow: []
                usage: []
              confidence: unknown  # measured|estimated|unknown
  archived-themes:
    - id: TH1
      archive-ref: docs/plan/backlog-archive/TH1.yaml
```

Ownership: the backlog owns runtime status, dependencies, risk tier, model
route, verification and review profile, budgets, aggregate usage, confidence,
and evidence references (PR-113). It does not own packet detail, attempt
traces, story text, or requirement text (PR-114).

Status machine: `todo -> in-progress -> done`, `in-progress -> failed ->
in-progress`, `in-progress -> blocked -> in-progress`. `blocked` is used for
pause dispositions and Discovery-escape subgraph pauses.

## 7. Transition journal

Path: `docs/plan/runtime/journal.ndjson` (append-only, one JSON object per line).

```json
{"seq": 42, "ts": "2026-09-05T16:00:00+01:00", "actor": "orchestrator",
 "ops-digest": "sha256:...", "base-revision": 6, "new-revision": 7,
 "base-hash": "sha256:...", "new-hash": "sha256:...",
 "outcome": "committed", "scope": "TH3.E1.US1"}
```

`outcome` is `committed`, `aborted`, `conflict`, or `recovered-commit`.

Transient siblings: `.tx.lock` (exclusive create, holder pid and timestamp,
stale after 60s) and `.tx.prepare` (single prepared record). Both are excluded
from version control.

Compaction at theme lock: journal lines for the theme are summarized into
`docs/plan/backlog-archive/TH<n>-runtime.yaml` retaining decision, threshold,
review, CI, release, and usage summaries; raw lines are removed (PR-214).

## 8. Packet manifest

Path: `docs/plan/runtime/packets/<TH.E.US>/<task-id>.yaml`

```yaml
packet-version: 1
packet-id: TH3.E1.US1/impl-1
generated-at: "<ISO-8601>"
generator: method/0.1.0
story: TH3.E1.US1
scope: "<one bounded responsibility>"
acceptance-criteria: [AC-1, AC-2]
traceability: {vision: [VO-004], requirements: [PR-109], adrs: [ADR-005], invariants: [INV-007]}
dependencies: [TH3.E1.US0]
controls:
  risk-tier: R1
  model-class: balanced
  verification: [lint, unit]
  budgets: {target: null, warning: null, pause: null, unit: AIC}
sources:
  - path: docs/themes/TH3-.../US1-....md
    trust: untrusted
    sha256: "..."
    git-revision: "<blob sha>"
  - path: .github/skills/bdd-stories/SKILL.md
    trust: trusted
    sha256: "..."
    git-revision: "<blob sha>"
composite-hash: "sha256:<sha256 over sorted '<path>:<sha256>' lines>"
required-report: {fields: [outcome, changes, verification-evidence, usage, open-questions]}
expansions: []   # {question, reason, risk, source, estimated-aic, authority, record}
```

`method packet verify` recomputes `composite-hash`; any difference is `STALE`
and forces regeneration (PR-110, INV-007). Expansion appends a source, bumps
`packet-version`, and journals the approval.

## 9. Usage sample

Path: `docs/plan/runtime/usage/<scope-id>.ndjson`

```json
{"ts": "2026-09-05T16:00:00+01:00", "scope": "TH3.E1.US1", "kind": "baseline",
 "value": 193.89406, "unit": "AIC", "confidence": "measured",
 "source": "copilot-cli-session-checkpoint", "model-mix": {"gpt-5.6-sol": 0.82},
 "limitations": ["post-response granularity"]}
```

`kind` is `baseline`, `sample`, or `close`. Nested scope usage is
`close.value - baseline.value`. `confidence` is `measured`, `estimated`, or
`unknown`; `value` is `null` when `unknown` and is never `0` (INV-005, PR-202).

## 10. Policies

`docs/plan/policy/model-policy.yaml`:

```yaml
policy-version: 1
approved-by: {actor: "<human>", timestamp: "<ISO-8601>", record: "TH<n> report"}
capability-classes:
  light:     {intent: "mechanical, low-ambiguity tasks", overshoot-aic: 1}
  balanced:  {intent: "normal implementation and review", overshoot-aic: 5}
  reasoning: {intent: "design, diagnosis, cross-cutting analysis", overshoot-aic: 15}
  critical:  {intent: "R3 and safety-critical work", overshoot-aic: 25}
availability:
  resolution-order: [preferred, equivalent]
  on-unavailable: pause          # never silent downgrade (PR-213)
mappings:
  light:     {preferred: "<model-id>", equivalent: ["<model-id>"]}
  balanced:  {preferred: "<model-id>", equivalent: ["<model-id>"]}
  reasoning: {preferred: "<model-id>", equivalent: ["<model-id>"]}
  critical:  {preferred: "<model-id>", equivalent: ["<model-id>"]}
task-defaults:
  packet-assembly: light
  implementation: balanced
  review: balanced
  architecture: reasoning
  troubleshooting: reasoning
  r3-review: critical
```

Model IDs are placeholders resolved per environment; the method stays
provider-neutral (QR-007).

`docs/plan/policy/budget-policy.yaml`:

```yaml
policy-version: 1
approved-by: {actor: "<human>", timestamp: "<ISO-8601>", record: "TH<n> report"}
unit: AIC
scopes:                            # provisional defaults, calibrated by report
  discovery-phase:       {target: null, warning: null, pause: null}
  investigation:         {target: null, warning: null, pause: null}
  story:                 {target: null, warning: null, pause: null}
  review-rework:         {target: null, warning: null, pause: null}
  ceremony:              {target: null, warning: null, pause: null}
  orchestrator-overhead: {target: null, warning: null, pause: null}
session-safety-net: {mechanism: "--max-ai-credits", value: null}
dispositions: [continue-revised-budget, simplify, split, change-route,
               reduce-verification, waive-verification, return-to-discovery, abort]
```

Thresholds start at `null` meaning "unset, report only" until TH5 calibration
supplies human-approved values. Numeric zero remains a measured value and is
never used as an unknown or unset sentinel.

`docs/plan/policy/usage-policy.yaml` names the active adapter chain and the
`token-proxy` pricing table version.

## 11. Control activation ledger

`docs/plan/activation-ledger.yaml`:

```yaml
ledger-version: 1
controls:
  - id: CTL-001
    name: "Six-stage gate enforcement"
    requirements: [PR-001, PR-010]
    state: ENFORCED               # SPECIFIED|MANUAL|INSTRUMENTED|ENFORCED|VERIFIED
    effective-point: "method validate gates, plan stage entry"
    limitations: []
    evidence: [tests/test_method_gates.py]
    proposed-by: reviewer
    promoted-by: {actor: "<human>", timestamp: "<ISO-8601>", record: "TH3 acceptance"}
```

Promotion to `ENFORCED` requires bypass-attempt and recovery evidence;
promotion to `VERIFIED` requires evidence from a completed theme (PR-013,
acceptance scenario 12).

## 12. Retention summary

| Data | Live retention | At theme lock |
|---|---|---|
| Dossier and PRD | permanent | permanent, immutable when all mapped themes accept |
| Backlog theme detail | live | moved to `backlog-archive/TH<n>.yaml` |
| Journal lines | whole theme | compacted to `backlog-archive/TH<n>-runtime.yaml` |
| Packet manifests | through delivery and review | compacted to counts, staleness events, expansions |
| Usage samples | whole theme | compacted to per-scope totals and confidence mix |
| Reports and policies | permanent | permanent |

Permanent size limits are not set. `method report --growth` measures dossier,
packet, journal, and usage growth per theme; limits are chosen after TH5 data
(DEF-005).
