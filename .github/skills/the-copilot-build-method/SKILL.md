---
name: the-copilot-build-method
description: 'Canonical six-stage lifecycle, gates, authority, DoD, naming, ceremonies, and split lock rules.'
---

# The Copilot Build Method

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
| Planning | `plan` stage 2 | `docs/themes/TH<n>-<slug>/`, its story files, issue templates, `docs/themes/TH<n>-<slug>/planning-admission.md`, and the theme state in `docs/plan/backlog.yaml` | Human-accepted architecture | `Accepted` planning-admission record issued by the product owner at `docs/themes/TH<n>-<slug>/planning-admission.md`, with its exact source revision passing the validator | product owner plus validator |
| Autopilot | `autopilot` | Product changes and their verification, review, Gitflow, and runtime evidence; runtime status in `docs/plan/backlog.yaml` | The planning-admission record is `Accepted` and its exact source revision passes the validator | Applicable story, epic, and theme Definition of Done | orchestrator and reviewer for delivery evidence; human for theme acceptance |

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

- Follow the canonical lifecycle and validate its gates before stage work.
- `docs/plan/backlog.yaml` is authoritative orchestration state.
- 1 story per developer session.
- Failed story must go through troubleshooter.
- Ceremonies happen at epic/theme boundaries.
- Current autopilot skills MUST use `gitflow-operator` for branch, commit,
  merge-request, CI, squash-merge, and release-note operations.

## VP ↔ TH Mapping

- VP can map to one or more themes (1:N).
- Theme numbering is sequential and independent of VP numbering.

## Definition of Done

### Story
- compile/lint/tests pass as applicable
- acceptance criteria verified
- relevant docs updated
- review completed (lightweight for trivial stories)

### Epic
- all stories done
- small epic (≤3): full epic tests + brief changelog
- large epic (4+): integration checks + reviewer quality pass + detailed changelog

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
bin/gitflow-operator --repo <repo> --item-id <story-or-delivery-id> status
bin/gitflow-operator --repo <repo> --item-id <story-or-delivery-id> branch-from-develop --branch feature/<slug>
bin/gitflow-operator --repo <repo> --item-id <story-or-delivery-id> prepare-release-notes --summary "<summary>"
```

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
