---
name: backlog-management
description: 'Backlog YAML schema, status transitions, dependency sequencing, lock behavior, and crash recovery rules.'
---

# Backlog Management Skill

## Authoritative State

`docs/plan/backlog.yaml` is the runtime source of truth (pure YAML, with no
Markdown wrapper). Completed theme details are moved to
`docs/plan/backlog-archive/TH<n>.yaml` and indexed from `backlog.yaml`.

This skill owns both versions of the backlog schema. The machine-readable
contract below is normative: `method validate schema` reads it directly rather
than maintaining a second key or status vocabulary in Python. Changes to the
contract and validator tests therefore travel together.

## Machine-readable schema contract

<!-- backlog-schema-contract:start -->
```yaml
contract-version: 1
status-vocabulary:
  v1:
    theme: [todo, in-progress, done]
    epic: [todo, in-progress, done]
    story: [todo, in-progress, done, failed]
  v2:
    theme: [todo, in-progress, done]
    epic: [todo, in-progress, done]
    story: [todo, in-progress, blocked, failed, done]
schemas:
  backlog-v2:
    type: mapping
    required: [schema-version, revision, project, last-updated, policy, active-themes, archived-themes]
    additional-properties: false
    properties:
      schema-version: {type: integer, enum: [2]}
      revision: {type: integer, minimum: 0}
      project: {type: string, min-length: 1}
      last-updated: {type: string, format: iso-8601}
      policy: {$ref: policy}
      active-themes: {type: sequence, items: {type: mapping}}
      archived-themes: {type: sequence, items: {$ref: archived-theme}}
  policy:
    type: mapping
    required: [model-policy, budget-policy]
    additional-properties: false
    properties:
      model-policy: {type: [string, "null"], format: repository-path}
      budget-policy: {type: [string, "null"], format: repository-path}
  theme-v1:
    type: mapping
    required: [id, name, status, locked, vision-ref, depends-on, epics]
    optional: [schema-version]
    additional-properties: false
    properties:
      schema-version: {type: integer, enum: [1]}
      id: {type: string, format: theme-id}
      name: {type: string, min-length: 1}
      status: {type: string, status: v1.theme}
      locked: {type: boolean, enum: [true]}
      vision-ref: {type: string, format: repository-path}
      depends-on: {type: sequence, unique: true, items: {type: string, format: theme-id}}
      epics: {type: sequence, items: {$ref: epic-v1}}
  epic-v1:
    type: mapping
    required: [id, name, status, depends-on, stories]
    additional-properties: false
    properties:
      id: {type: string, format: v1-epic-id}
      name: {type: string, min-length: 1}
      status: {type: string, status: v1.epic}
      depends-on: {type: sequence, unique: true, items: {type: string, format: v1-epic-id}}
      stories: {type: sequence, items: {$ref: story-v1}}
  story-v1:
    type: mapping
    required: [id, title, status, file, depends-on]
    optional: [priority]
    additional-properties: false
    properties:
      id: {type: string, format: story-id}
      title: {type: string, min-length: 1}
      status: {type: string, status: v1.story}
      priority: {type: string, enum: [high, medium, low]}
      file: {type: string, format: repository-path}
      depends-on: {type: sequence, unique: true, items: {type: string, format: story-id}}
  theme-v2:
    type: mapping
    required: [id, name, schema-version, status, locked, vision-ref, discovery-ref, requirements-ref, depends-on, budgets, usage, epics]
    additional-properties: false
    properties:
      id: {type: string, format: theme-id}
      name: {type: string, min-length: 1}
      schema-version: {type: integer, enum: [2]}
      status: {type: string, status: v2.theme}
      locked: {type: boolean}
      vision-ref: {type: string, format: repository-path}
      discovery-ref: {type: string, format: repository-path}
      requirements-ref: {type: string, format: repository-path}
      depends-on: {type: sequence, unique: true, items: {type: string, format: theme-id}}
      budgets: {$ref: budgets}
      usage: {$ref: usage}
      epics: {type: sequence, items: {$ref: epic-v2}}
  epic-v2:
    type: mapping
    required: [id, name, status, depends-on, budgets, usage, stories]
    additional-properties: false
    properties:
      id: {type: string, format: epic-id}
      name: {type: string, min-length: 1}
      status: {type: string, status: v2.epic}
      depends-on: {type: sequence, unique: true, items: {type: string, format: epic-id}}
      budgets: {$ref: budgets}
      usage: {$ref: usage}
      stories: {type: sequence, items: {$ref: story-v2}}
  story-v2:
    type: mapping
    cross-field: story-confidence
    required: [id, title, status, priority, file, depends-on, risk, model-route, verification, review-profile, budgets, usage, evidence, confidence]
    additional-properties: false
    properties:
      id: {type: string, format: story-id}
      title: {type: string, min-length: 1}
      status: {type: string, status: v2.story}
      priority: {type: string, enum: [high, medium, low]}
      file: {type: string, format: repository-path}
      depends-on: {type: sequence, unique: true, items: {type: string, format: story-id}}
      risk: {$ref: risk}
      model-route: {$ref: model-route}
      verification: {$ref: verification}
      review-profile: {type: string, enum: [standard, adversarial, critical]}
      budgets: {$ref: budgets}
      usage: {$ref: usage}
      evidence: {$ref: evidence}
      confidence:
        type: string
        enum: [measured, estimated, unknown]
        legacy-enum: [high, medium, low]
        legacy-records:
          - TH3.E1.US1
          - TH3.E1.US2
          - TH3.E1.US3
          - TH3.E1.US4
          - TH3.E2.US1
          - TH3.E2.US2
  risk:
    type: mapping
    required: [tier, triggers, assigned-by, validated-by, overrides]
    additional-properties: false
    properties:
      tier: {type: string, enum: [R0, R1, R2, R3]}
      triggers: {type: sequence, unique: true, items: {type: string, min-length: 1}}
      assigned-by: {type: string, min-length: 1}
      validated-by: {type: [string, "null"], min-length: 1}
      overrides: {type: sequence, items: {$ref: risk-override}}
  risk-override:
    type: mapping
    required: [from, to, authority, reviewer, rationale, record]
    additional-properties: false
    properties:
      from: {type: string, enum: [R0, R1, R2, R3]}
      to: {type: string, enum: [R0, R1, R2, R3]}
      authority: {type: string, min-length: 1}
      reviewer: {type: string, min-length: 1}
      rationale: {type: string, min-length: 1}
      record: {type: string, min-length: 1}
  model-route:
    type: mapping
    required: [default-class, allowed-classes, escalations]
    additional-properties: false
    properties:
      default-class: {type: string, enum: [light, balanced, reasoning, critical]}
      allowed-classes: {type: sequence, min-items: 1, unique: true, items: {type: string, enum: [light, balanced, reasoning, critical]}}
      escalations: {type: sequence, items: {$ref: escalation}}
  escalation:
    type: mapping
    required: [task, class, question, scope, stop, estimated-aic, record]
    additional-properties: false
    properties:
      task: {type: string, min-length: 1}
      class: {type: string, enum: [light, balanced, reasoning, critical]}
      question: {type: string, min-length: 1}
      scope: {type: string, min-length: 1}
      stop: {type: string, min-length: 1}
      estimated-aic: {type: [number, "null"], minimum: 0}
      record: {type: string, min-length: 1}
  verification:
    type: mapping
    required: [profile, matrix, suite-policy, waivers]
    additional-properties: false
    properties:
      profile: {type: string, enum: [lint-and-targeted-unit, targeted-plus-integration, integration-plus-failure-injection]}
      matrix: {type: sequence, min-items: 1, unique: true, items: {type: string, enum: [lint, unit, integration, failure-injection]}}
      suite-policy: {$ref: suite-policy}
      waivers: {type: sequence, items: {$ref: verification-waiver}}
  suite-policy:
    type: mapping
    required: [story, epic, theme]
    additional-properties: false
    properties:
      story: {type: string, enum: [targeted]}
      epic: {type: string, enum: [conditional, required]}
      theme: {type: string, enum: [full, full-plus-release-readiness]}
  verification-waiver:
    type: mapping
    required: [check, authority, reviewer, rationale, record]
    additional-properties: false
    properties:
      check: {type: string, min-length: 1}
      authority: {type: string, min-length: 1}
      reviewer: {type: string, min-length: 1}
      rationale: {type: string, min-length: 1}
      record: {type: string, min-length: 1}
  budgets:
    type: mapping
    required: [target, warning, pause, unit]
    additional-properties: false
    properties:
      target: {type: [number, "null"], minimum: 0}
      warning: {type: [number, "null"], minimum: 0}
      pause: {type: [number, "null"], minimum: 0}
      unit: {type: string, enum: [AIC]}
  usage:
    type: mapping
    cross-field: usage-sample
    required: [value, confidence, source, sampled-at]
    additional-properties: false
    properties:
      value: {type: [number, "null"], minimum: 0}
      confidence: {type: string, enum: [measured, estimated, unknown]}
      source: {type: string, min-length: 1}
      sampled-at: {type: [string, "null"], format: iso-8601}
  evidence:
    type: mapping
    required: [packets, verification, review, gitflow, usage]
    additional-properties: false
    properties:
      packets: {type: sequence, items: {type: string, format: repository-path}}
      verification: {type: sequence, items: {type: string, min-length: 1}}
      review: {type: sequence, items: {type: string, min-length: 1}}
      gitflow: {type: sequence, items: {type: string, min-length: 1}}
      usage: {type: sequence, items: {type: string, min-length: 1}}
  archived-theme:
    type: mapping
    required: [id, name, status, locked, completed-at, archive-ref, stats]
    optional: [schema-version]
    additional-properties: false
    properties:
      schema-version: {type: integer, enum: [1, 2]}
      id: {type: string, format: theme-id}
      name: {type: string, min-length: 1}
      status: {type: string, status: v1.theme}
      locked: {type: boolean, enum: [true]}
      completed-at: {type: string, format: iso-8601}
      archive-ref: {type: string, format: repository-path}
      stats: {$ref: archive-stats}
  archive-stats:
    type: mapping
    required: [epics, stories]
    additional-properties: false
    properties:
      epics: {type: integer, minimum: 0}
      stories: {type: integer, minimum: 0}
```
<!-- backlog-schema-contract:end -->

All listed keys are accepted only in their documented object. Keys not listed
in `properties` are rejected. All required keys, value types, enumerations, ID
formats, and dependency references are validated. A v2 story `file` must be a
relative path resolving to an existing regular file inside the repository;
the same safety rule is retained for v1 story paths.

## Version 2 blocks

- The backlog root declares `schema-version: 2` and a non-negative,
  monotonically increasing `revision`.
- Every new or unlocked theme declares `schema-version: 2`.
- Themes and epics carry aggregate `budgets` and `usage`.
- Every v2 story carries `risk`, `model-route`, `verification`,
  `review-profile`, `budgets`, `usage`, `evidence`, and `confidence`.
- `risk` owns tier assignment, objective triggers, validation, and explicit
  overrides. `model-route` owns allowed capability classes and recorded
  escalations. `verification` owns the matrix, suite policy, and waivers.
- `budgets` use `null` for unset thresholds. `usage.value` is `null` when
  confidence is `unknown`; in that state `source` is `none` and `sampled-at`
  is `null`. A `measured` or `estimated` sample has a nonnegative numeric
  value, a named source other than `none`, and an ISO-8601 timestamp with an
  offset. Zero is valid only as an actual `measured` or `estimated` sample,
  never as an unknown sentinel.
- `evidence` contains references or concise evidence labels. Detailed packet,
  attempt, and usage records remain in `docs/plan/runtime/`.
- Story `confidence` uses the architecture's evidence vocabulary:
  `measured|estimated|unknown`. The earlier `high|medium|low` vocabulary
  conflicted with ADR-007, PR-201, and the architecture data model. Those
  legacy labels are accepted only on the completed pre-v2 story IDs explicitly
  listed in `legacy-records`; new and unfinished stories must use the canonical
  values. The finite allowlist makes this compatibility visible and prevents
  it from silently becoming the future vocabulary. It does not authorize
  migration edits to locked themes or archived snapshots.

## Version 1 compatibility

Version 1 remains valid without migration for TH1, TH2, and historical
snapshots. An absent `schema-version` means version 1 **only** when the theme is
locked or is loaded from `docs/plan/backlog-archive/`. An unlocked or new theme
without `schema-version: 2` fails closed. Version 1 keeps its historical status
vocabulary: themes and epics use `todo|in-progress|done`; stories use
`todo|in-progress|done|failed`. Version 2-only blocks are never required of a
version 1 theme.

## Status Machine

- `todo -> in-progress -> done`
- `in-progress -> failed -> in-progress`
- Version 2 adds `in-progress -> blocked -> in-progress`.

`blocked` is used for pause dispositions and Discovery-escape dependency
subgraph pauses. It is not a version 1 status and must not be backfilled into
locked or archived version 1 artefacts.

## Dependency Rules

IDs are qualified in version 2: themes are `TH<n>`, epics are
`TH<n>.E<m>`, and stories are `TH<n>.E<m>.US<l>`. Version 1 archive snapshots
also accept their historical `E<m>` epic IDs. Dependencies must name an existing entity of the same kind in the normalized
repository-wide index, which includes active themes and every indexed archive
snapshot. They cannot name the entity itself. Cycle checks apply to the
executable active graph; historical archive snapshots contribute existence
targets but are not reinterpreted as an executable graph.

A story is eligible when:

1. epic dependencies are done;
2. story dependencies are done; and
3. story status is `todo`.

If multiple stories are eligible, priority is `high > medium > low` (default
`medium` in version 1), then story number.

## Lock Rules (`locked: true`)

Use the split lock scope and ADR supersession exception defined by
`the-copilot-build-method`. One accepted theme does not by itself lock shared
VP-level artefacts. A locked theme and its backlog snapshot MUST NOT be
mutated, including to repair a technical reference or broken file path.
The sole mutation exception for any locked artefact is the canonical exception
for an ADR status changing to superseded while its replacement ADR is created;
that exception never permits a locked theme or backlog mutation. Validation
reports defects; it never repairs locked data.

## Update and Recovery Protocol

Until revisioned transitions are enforced, each transition reads the current
backlog, changes status, increments `revision`, updates `last-updated`, writes
atomically, and appends the session log. Once enforced, `method tx apply` is
the only writer and follows ADR-004's expected-revision, prepare, replace,
journal, and recovery protocol.

On theme completion, move the full theme payload to
`docs/plan/backlog-archive/TH<n>.yaml`, append its compact index entry to
`archived-themes`, and keep only active execution state in `backlog.yaml`.

If a story is `in-progress` on startup, detect partial work and explicitly
continue, reset, or escalate. A budget pause or Discovery escape uses
`blocked`, not an invented status.
