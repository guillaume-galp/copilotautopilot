---
name: the-copilot-build-method
description: 'Canonical Direct, Managed and Governed delivery lanes, lifecycle gates, authority, DoD and split locks.'
---

# The Copilot Build Method

## Risk-Scaled Delivery Lanes

Select a delivery lane **before** selecting lifecycle work. This section is
the canonical authority for lane selection, execution and completion. The
six-stage lifecycle below remains the product/design lifecycle, not a
mandatory prerequisite for every maintenance assignment. `autopilot` is also
the delivery entrypoint for Direct and Managed work; do not send such work
through `kickstart` or `plan` merely to make it executable.

| Lane | Eligibility | Required controls | Unnecessary new artefacts |
|---|---|---|---|
| Direct | Bounded, well-understood fixes, documentation or behavior-preserving refactors within existing intent; R0/R1, clear scope and no consequential trigger | One owner, outcome/scope/acceptance checks, targeted verification, self-assessment and concise report | Vision, Discovery, PRD, theme, epic, mission packet |
| Managed | Substantial features or multi-session bounded work within an established design, with no Governed trigger | Retained owner, concise outcome/non-goals/acceptance brief, durable progress/next action, targeted and relevant integration checks, risk-scaled review | Complete greenfield lifecycle and new planning hierarchy for unchanged decisions |
| Governed | Consequential authority, integrity, sensitive operations, migrations, production/delivery operations, complex cross-service contracts or changes to this method's enforcement | Explicit human authority/scope, formal acceptance/verification/review evidence, recovery/rollback assessment where applicable, mission packets and applicable lifecycle gates | Re-creating or re-accepting unchanged, valid upstream evidence |

### Selection and Confirmation

The implementation owner assesses explicit facts and proposes the lowest
eligible lane. Size is not file count, duration or a license to ignore risk.
An R2 assessment requires at least Managed; R3 requires Governed. A new or
changed product/design decision requires the applicable human product/design
gates; it is not ordinary maintenance. Unknown design or risk facts and
uncertain scope pause execution for clarification, not optimistic defaults.
Human confirmation is required before consequential decisions/operations,
including this method's approval or execution semantics. Existing accepted
specifications remain binding in every lane.

The following executable classification vocabulary is owned here. The local
CLI reads this block from its packaged canonical skill, never from a target
project's potentially stale copy.

<!-- delivery-lanes-contract:start -->
```json
{
  "lanes": ["Direct", "Managed", "Governed"],
  "maintenance": ["fix", "docs", "refactor"],
  "kinds": ["fix", "docs", "refactor", "feature"],
  "designs": ["existing", "new", "unknown"],
  "certainty": ["clear", "uncertain", "unknown"],
  "risks": ["R0", "R1", "R2", "R3"],
  "profiles": ["standard", "adversarial", "critical"],
  "governed-triggers": [
    "authorization", "data-integrity", "sensitive-operation", "migration",
    "production", "deployment", "release", "cross-service", "method-enforcement"
  ],
  "governed-paths": [
    "docs/vision_of_product", "docs/discovery", "docs/requirements",
    "docs/architecture", "docs/ADRs", "docs/themes", "docs/plan/backlog.yaml",
    "docs/plan/backlog-archive"
  ],
  "enforcement-paths": [
    "methodlib", "bin/method", ".github/copilot-instructions.md",
    ".github/skills", ".github/agents", ".github/hooks", ".github/prompts"
  ]
}
```
<!-- delivery-lanes-contract:end -->

Triggers refer to **semantics**, not keywords: access-control decisions and
grants; integrity-critical writes; sensitive operational handling; schema/data
migrations; production actions; deployment/release; complex cross-service
contract changes; lifecycle/approval/verification enforcement. A purely local
capability implementation may still be Governed; it never grants activation.
Declared scope touching formal product/planning/architecture artefacts routes
to their existing contracts conservatively. Fixing an ordinary README typo
does not require new product decisions.
Enforcement code/instruction paths also route conservatively, without relying
on a declared trigger. A repository with unfinished product backlog work cannot
prove a new lighter assignment unrelated from implementation paths alone;
the local route refuses and retains the existing packet contract. Finish or
obtain disposition of that admitted work rather than omit its identity.

### Execution and Resumption

Use `method lane assess` before new unadmitted work; `method lane start`
records the selected lane. Direct can supply the brief as CLI arguments; no
handwritten planning file is required. Managed uses the same compact brief
with non-goals, existing design evidence and integration checks. The generated
record in `docs/plan/runtime/lanes/` is **working evidence**, not another
backlog, dispatch queue, product acceptance or mission packet. Retain its
returned `revision` outside the record and pass `--expected-revision` to every
subsequent command. Record hashes detect staleness/tampering; they are not
authentication signatures.

`method lane preflight` checks the retained owner, scope and unchanged
out-of-scope files before implementation/resumption. `method lane check`
runs only an explicitly supplied verification command (never commands read
from a brief), retaining real exit status, covered criteria and content
revision. `method lane review` binds an attributable actual review report to
that revision. R0/R1 standard permits self-review; R2/R3 or
adversarial/critical requires independent approval. Governed new work always
requires independent review; legacy admitted review rules stay unchanged.
`method lane complete` checks fresh, passing targeted/integration evidence,
complete acceptance coverage, review and an explicit Gitflow evidence or
not-applicable rationale. It reports **implementation completion only**.
Read the record on resume; continue its next action with the same owner.

Change the brief only with `method lane amend`. Outcome, scope, criteria,
checks, design, uncertainty or risk changes pause work and invalidate affected
verification/review (the compact route conservatively invalidates all).
Lane floors never decrease; previously declared consequential triggers
cannot be removed. `resume` is an explicit owner disposition for clear,
eligible lighter work, not automatic recovery. Governed escalation refuses
lighter execution and routes to human authority plus the packet/admission
contracts; migrate evidence by reference, never by pretending the record is a
packet. Increased risk, ambiguity, undeclared file changes or required review
refusal blocks execution/completion. `pause` records unresolved failures,
missing authority or refusal; an authority refusal cannot be cleared by
`resume`, `amend`, lane downgrade or a new overlapping task. Obtain human
disposition through the governed route instead.

After two unsuccessful owner repair attempts, pause for specialist/human
disposition; missing expertise/authority blocks immediately. Appropriate
checks are selected by the owner, not inferred from command success alone.
No tool proves the adequacy of a check, the truth of classification facts or
the authenticity of human/independent attribution: retain the real source
evidence and confirm consequential decisions with the human. The verification
runner is not an OS sandbox; never supply mutation/deployment/release commands
as checks or place secrets in command arguments.
The bounded inventory includes ignored files outside scope. Declare optional
`verification_outputs` (CLI `--verification-output`) for generated test/build
outputs before starting; those explicit write grants are excluded from the
implementation digest. They cannot overlap implementation, accepted evidence
or control paths, and cannot be expanded during repair to hide a violation.

### Invariants and Compatibility

Control renewal for a bounded delivery task may use
`docs/plan/control-promotions/delivery-<task>.md`, with the existing exact
Actor/Timestamp/Record/Decision/Basis/Limit promotion table. Its title and
Record identify the filename. Human authority, matching ledger decisions and
fresh recovery evidence remain required. Legacy story-named promotion records
remain valid and immutable; no synthetic story is required for renewal.

- No fabricated tests, approvals or completion. Failures, missing evidence
  and uncertainty are explicit blockers, never success-shaped fallbacks.
- No unauthorized external mutation, access grant, deployment, merge or
  release. Gitflow describes delivery procedure, not authorization to perform
  it. No lane choice grants human authority or waives a gate.
- Preserve accepted specifications, split locks and frozen history. The
  lighter route never writes product backlog, gates or accepted artefacts.
- Separate implementation completion, release readiness, product acceptance
  and production activation; none implies any of the others.
- Existing admitted v1/v2/v3 work continues its current packet, gate, review,
  verification and completion contracts. `--admitted-item` routes to packets;
  omission is not permission to relabel admitted work. No automatic conversion,
  history migration, widening of legacy story scope or gate downgrade.
- `method packet` and explicit product lifecycle entrypoints retain their
  existing defaults. The lane route cannot complete a backlog item, grant a
  worker a packet or accept a product. Governed work must use the applicable
  validated lifecycle admission and packet machinery. Valid existing product
  and architecture evidence may be reused; new decisions use their gates.

See [the delivery lane guide](delivery-lanes.md) for executable examples.

## Canonical Lifecycle Contract

This skill is the single authoritative owner of the lifecycle stage list,
ordering, entrypoints, owning artefacts, gates, and authorities. Other active
skills, agents, and instruction files MUST reference this section and MUST NOT
restate the lifecycle sequence.

| Stage | Entrypoint | Owning artefact(s) | Upstream entry gate | Completion gate | Authority |
|---|---|---|---|---|---|
| Vision sketch | `kickstart` | `docs/vision_of_product/VP<n>-<slug>/` VP document | None; this is the lifecycle root | Vision sketch recorded; no formal gate record | human |
| Discovery | `discover` | `docs/discovery/VP<n>-<slug>/` Discovery dossier | Vision sketch exists | `READY` or `READY_WITH_DEFERRALS` readiness verdict accepted | human |
| PRD finalization | `requirements` | `docs/requirements/VP<n>-<slug>/PRD.md` | Human-accepted Discovery readiness verdict | PRD `Approved` | human |
| Architecture | `plan` stage 1 | `docs/architecture/` and `docs/ADRs/` | Human-accepted Discovery readiness verdict and human-approved PRD | Architecture `Accepted` | human |
| Planning | `plan` stage 2 | `docs/themes/TH<n>-<slug>/`, its epic specifications and optional story files, issue templates, `docs/themes/TH<n>-<slug>/planning-admission.md`, and the theme state in `docs/plan/backlog.yaml` | Human-accepted architecture | `Accepted` planning-admission record issued by the product owner at `docs/themes/TH<n>-<slug>/planning-admission.md`, with its exact source revision passing the validator | product owner plus validator |
| Autopilot | `autopilot` | Product changes and their verification, review, Gitflow, and runtime evidence; runtime status in `docs/plan/backlog.yaml` | The planning-admission record is `Accepted` and its exact source revision passes the validator | Applicable epic and theme Definition of Done, including optional child acceptance coverage | orchestrator and epic owner for delivery evidence, independent reviewer when required; human for theme acceptance |

`plan` stage 1 therefore has two upstream product gates: an accepted Discovery
readiness verdict and an approved PRD. A human is the acceptance authority for
both. The PRD gate does not replace or imply the Discovery gate; both records
must resolve.

### Gate Record Contract

A formal gate is a `## Approval` or `## Acceptance` section in the artefact it
covers. Its `| Field | Value |` table MUST contain all of these non-empty
fields:

The required gate record fields are actor, timestamp, scope, verdict,
rationale, and source revision.

| Field | Requirement |
|---|---|
| Actor | Human or role that issued the verdict; it must match the authority in the lifecycle table |
| Timestamp | ISO-8601 timestamp with an explicit UTC offset |
| Scope | Exact VP, dossier, PRD, architecture, backlog, story, epic, or theme covered |
| Verdict | One value from the closed verdict vocabulary below |
| Rationale | Reason for the verdict, including accepted limitations or deferrals |
| Source revision | Git revision or dated artefact revision to which the verdict applies |

The closed verdict vocabulary is:

- `READY`, `READY_WITH_DEFERRALS`, `BLOCKED`
- `Approved`, `Rejected`, `Accepted`

`READY` and `READY_WITH_DEFERRALS` open the Discovery readiness gate only when
issued or accepted by its human authority. `Approved` opens an approval gate,
and `Accepted` opens an acceptance gate, only when the actor has the authority
declared in the lifecycle table. `BLOCKED` and `Rejected` never open a gate.
An agent recommendation without the required authority is unaccepted even if
its proposed verdict is otherwise valid.

### Planning-to-Autopilot Admission Gate

Planning has one formal admission record at
`docs/themes/TH<n>-<slug>/planning-admission.md`. The file contains a
`## Acceptance` gate record using every field in the Gate Record Contract.
Its scope names exactly one theme, and its source revision identifies the
exact planned theme artefacts and backlog revision submitted for validation.

The planning-to-autopilot gate opens only when both authorities agree:

1. the product owner issues the record with verdict `Accepted`; and
2. the validator passes the exact source revision named by that record.

The validator does not invent or issue a second gate verdict. In particular,
`Backlog admitted` is not a verdict. Any value outside the closed verdict
vocabulary is invalid, and any closed-vocabulary value other than `Accepted`
does not open this acceptance gate. A missing record, a non-product-owner
actor, a failed validator result, or a result for a different source revision
keeps the gate closed.

### Fail-Closed Stage Entry

Before doing stage work, every entrypoint MUST validate every formal upstream
gate independently. A stage refuses to start when an upstream gate record is:

- missing;
- incomplete, including an empty or malformed required field;
- unaccepted because its verdict or actor does not satisfy that gate's
  authority; or
- `BLOCKED`.

In short, a missing, incomplete, unaccepted, or `BLOCKED` upstream gate record
always refuses stage entry.

Refusal is fail-closed: the entrypoint performs no stage work, reports the
invalid gate and remediation, and exits with code `2` (exit code 2). Unknown
verdicts also exit `2`; they are never treated as approval. Vision sketch is
the lifecycle root and has no upstream gate record. Discovery checks that its
upstream vision artefact exists, but does not fabricate a gate that the
lifecycle table defines as absent.

### Canonical Gate and Working-State Templates

The reusable lifecycle forms are owned here:

| Template | Purpose |
|---|---|
| `templates/approval.md` | A `## Approval` gate with the six canonical gate fields |
| `templates/acceptance.md` | A `## Acceptance` gate with the six canonical gate fields |
| `templates/waiver.md` | A `## Acceptance` waiver with the six gate fields followed by `Expiry` and `Invalidation` |
| `templates/working-state.md` | The canonical resumability block |

Owning artefact skills may embed one of these forms and add only fields their
canonical schema requires. For example, `discovery-dossier` adds its
`Disposition` field in the position defined by that skill. It does not create
a competing gate grammar.

Every value enclosed in angle brackets is an unfilled placeholder. An
unfilled placeholder is incomplete data even though its table cell is
non-empty. It never identifies an actor, timestamp, scope, verdict, rationale,
source revision, expiry, invalidation condition, open item, accepted record,
or next action. In particular, `<actor>` is a missing `Actor`, and gate
evaluation must remain not accepted with remediation that names the `Actor`
field. Placeholder text must never equal a value from the closed verdict
vocabulary.

The canonical working-state field order is `Status`, `Open items`,
`Accepted so far`, and `Next action`. A new scope starts with
`Status: not-started`. On resume, the facilitator reads this block, continues
the single `Next action`, and does not re-elicit IDs in `Accepted so far`.
At the applicable gate, the block is removed or `Status` is changed to
`accepted`; no other status represents a completed gate.

## Core Principles

- Select the canonical delivery lane; validate applicable gates before stage work.
- `docs/plan/backlog.yaml` is authoritative product orchestration state;
  lighter working records never compete with it.
- For admitted packet work, one bounded epic per developer assignment; retain the same owner through
  implementation, testing, and local repair. Resume from durable evidence
  rather than treating one context window as a delivery boundary.
- Stories are optional acceptance subdivisions, not separate agent jobs.
- Escalate unresolved failures to the troubleshooter after bounded local
  repair, not on every failed test.
- Ceremonies happen at epic/theme boundaries.
- Current autopilot skills MUST use `gitflow-operator` for branch, commit,
  merge-request, CI, squash-merge, and release-note operations.

## VP ↔ TH Mapping

- VP can map to one or more themes (1:N).
- Theme numbering is sequential and independent of VP numbering.

## Definition of Done

### Atomic Work Unit

A bounded epic is the default unit of planning, delegation, verification,
review, and Gitflow delivery. It has one coherent outcome, explicit non-goals,
measurable acceptance criteria, and a reviewable change set. Split oversized
epics before admission when independent releases, authority boundaries,
migration stages, or review complexity require separate delivery units.

New themes use the epic-first schema from `backlog-management`. The epic
specification follows `bdd-stories`; no synthetic story is required to make
an epic executable. Optional stories preserve useful personas or acceptance
slices. The epic owner handles their internal sequencing in one assignment.
Stories do not require individual agent handoffs, reviews, or merge requests.

Existing version 1/2 backlogs and story-scoped packets remain legacy
compatibility inputs. Do not rewrite accepted history or silently widen a
legacy story packet into epic authority; new epic execution requires an
explicitly admitted epic-scoped contract.

### Epic
- All epic acceptance criteria and any optional child criteria are covered;
  all retained child stories are done before or with epic completion.
- Applicable build/lint, targeted tests, and integration checks pass against
  the delivered change; relevant documentation is updated.
- Quality assessment covers the integrated epic once, not once per child
  followed by another epic review. For R0/R1 with `standard` review profile,
  the owner may record self-review. R2/R3 or `adversarial`/`critical` profiles
  require explicit independent approval, using native review capabilities or
  a reviewer agent. A capability being available is not evidence it ran.
- Record verification, review, and Gitflow evidence at epic scope; produce
  one brief changelog entry. Rework only invalidates evidence affected by
  the changes; obtain fresh approval when the reviewed implementation changes.
- A failed check stays with the owner for bounded diagnosis and repair.
  After two unsuccessful repair attempts, or immediately when blocked by
  missing expertise or authority, escalate to the troubleshooter or human.

### Theme
- all epics done
- full suite + release readiness checks
- deployment readiness validation if deployment doc exists
- release notes + vision revalidation
- archive old issue templates
- user checkpoint (accept/reject/amend next VP)
- set `locked: true` on accepted theme

## Naming

- VP: `VP<n>-<slug>/`
- Theme: `TH<n>-<slug>/`
- Epic: `E<m>-<slug>/`
- Story: `US<l>-<slug>.md`
- ADR: `ADR-<NNN>-<slug>.md`

## Split Lock / Immutability Rules

Lock scope is intentionally split for a VP that maps to multiple themes:

Theme artefacts lock at theme acceptance; an ADR body locks at first dependent
theme acceptance; and shared VP, Discovery dossier, and PRD artefacts lock only
after all mapped themes are accepted.

| Artefact scope | Locks when |
|---|---|
| A theme directory, all of its story files, and its theme backlog snapshot | That theme is accepted |
| An ADR body | The first accepted theme that depends on that ADR |
| The shared VP document, Discovery dossier, and PRD | All themes currently mapped to that VP are accepted |

Until every mapped theme is accepted, shared VP, Discovery, and PRD artefacts
remain revisable only through the applicable append-only `DR-###` Discovery
Revision and `PCR-###` Product Change Record. Partial theme acceptance never
permits accepted content to be rewritten directly.

A locked ADR body is immutable. Its only permitted edit is changing its
`Status` to `Superseded by ADR-<NNN>` while creating the replacement ADR.
Adding a theme after all mapped themes were accepted does not reopen locked
artefacts; use a new VP, or record the mapping through an applicable `PCR-###`
before final VP-level lock.

For example, when VP3 maps to TH3, TH4, and TH5, accepting TH3 locks the TH3
theme directory, TH3 story files, and TH3 backlog snapshot. VP3, its Discovery
dossier, and its PRD remain revisable through `DR-###` and `PCR-###` records
until TH3, TH4, and TH5 are all accepted.

## Reference Rule

Active skills, agents, and workspace instruction files reference
`the-copilot-build-method` for the lifecycle and split lock contract. They may
describe the responsibilities or prerequisites of their own stage, but they
MUST NOT reproduce an ordered lifecycle stage list. Archived files are
historical evidence and are not active instructions.

## Token-Efficient Defaults (GPT-5.4+ / Sonnet 4.6+)

- Load only needed files/sections.
- Prefer concise structured outputs.
- Avoid repeating lifecycle explanations unless requested.
- Batch independent tool calls.

## Gitflow Operator

When delivery work needs Gitflow, use the `gitflow-operator` command surface
instead of hand-writing ad hoc Git instructions:

```bash
"$GITFLOW_OPERATOR" --repo <repo> --item-id <epic-id> status
"$GITFLOW_OPERATOR" --repo <repo> --item-id <epic-id> branch-from-develop --branch feature/<slug>
"$GITFLOW_OPERATOR" --repo <repo> --item-id <epic-id> prepare-release-notes --summary "<summary>"
```

Resolve `GITFLOW_OPERATOR` as defined in the `gitflow-operator` skill: prefer
the target repository's executable `bin/gitflow-operator`, then use
`command -v gitflow-operator` from `PATH`. Stop if neither path resolves.

If Gitflow is not applicable, record a not-applicable rationale.

## Code Intelligence Defaults

When a repository has `graphify-out/graph.json` and the `graphify` CLI is
available, agents should treat Graphify as the first-choice local index for
codebase, architecture, file-relationship, and project-content questions:

```bash
graphify query "<question>" --graph "$REPO/graphify-out/graph.json"
```

Use Graphify before broad text search when the task asks where behavior lives,
how files relate, what components exist, or what implementation patterns are
already present. If a project provides higher-priority code intelligence
instructions (for example CodeGraph/transversal skills for cross-service impact
analysis), follow those first; otherwise prefer Graphify over grep-style search.

If no Graphify graph exists, or the query result is too low-confidence to act on,
fall back to normal repository search and source-file reads. Keep generated
graphs out of commits unless the target repository explicitly versions
`graphify-out/`; use `graphify update "$REPO"` or Graphify hooks to refresh the
index after meaningful code changes.
