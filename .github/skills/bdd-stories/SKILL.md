---
name: bdd-stories
description: 'Executable epic BDD acceptance specs, optional acceptance children, and legacy story compatibility.'
---

# BDD Delivery and Acceptance Scope Skill

Use `the-copilot-build-method` as the canonical lifecycle, gate, authority, and
split-lock contract; this skill defines executable epic and acceptance-child
form only and does not restate
that contract.

## Default Delivery Path (schema-v3)

`docs/themes/TH<n>-<slug>/epics/E<m>-<slug>/README.md`

The epic is the executable BDD delivery unit: one bounded implementation
assignment, verification/review cycle, and Gitflow delivery. Zero stories is a
supported default. Optional acceptance children refine scope inside that
epic; they do not create independent sessions, reviews, packets, or Gitflow
cycles. Never invent a placeholder `US1` to make an epic executable.

## Epic Frontmatter

Required keys: `id`, `title`, `type`, `traceability`, `acceptance-criteria`.
Optional keys: `agents`, `skills`, `depends-on`, `priority`, `size`.

```yaml
---
id: TH<n>.E<m>
title: "<bounded epic outcome>"
type: standard            # standard | trivial | spike
traceability:
  vision: []
  requirements: [PR-001]
  adrs: []
  invariants: []
acceptance-criteria:
  - AC1: "<measurable outcome>"
  - AC2: "<boundary or failure outcome>"
---
```

When omitted, packet generation uses `agents: [developer]`,
`skills: [bdd-stories]`, and the epic's backlog `depends-on` list. Declared
dependencies must agree with the backlog and name epic IDs. Optional
`priority` is `high|medium|low`; optional `size` is `S|M|L`. Priority, when
declared, must agree with backlog priority.

Every epic declares all four traceability keys as lists. For `standard` and
`spike` epics, only `requirements` must be nonempty; the other three lists
may be empty when no applicable record exists. A `trivial` epic may use empty
lists for all four. Every declared reference remains strict: it must use the
key's canonical ID prefix and resolve in the canonical source. Unknown keys,
scalar values, aliases, and dangling references are invalid. Body mentions
do not substitute for frontmatter.

## Optional Acceptance Children (schema-v3)

`docs/themes/TH<n>-<slug>/epics/E<m>-<slug>/stories/US<l>-<slug>.md`

Use children only when naming a distinct acceptance slice improves clarity.
The lean backlog child has `id`, `title`, `status`, `file`, `depends-on`
(optional `priority`). Its document identifies that scope with `id` and
`title` and a nonempty `acceptance-criteria` frontmatter list using the epic's
AC mapping format, plus relevant behavioral examples in the body. Its optional `type` defaults
to `standard`; `agents` defaults to `[developer]`, `skills` to `[bdd-stories]`,
and `depends-on` to that child's backlog dependencies (child IDs, not epic IDs).
It does not duplicate epic risk, model routing, verification,
review profile, budgets, usage, or evidence.

Child `traceability` is optional. When declared, it must use all four keys,
canonical prefixes, and resolvable references; lists may be empty when no
record applies. Omission inherits the epic's delivery context rather than
fabricating references. Internal child dependencies order implementation
without blocking epic dispatch; external child dependencies must be done
before the epic packet can be built. A done epic requires all children done.

## Legacy Story Frontmatter (schema-v1/v2, unchanged)

Existing v1/v2 executable stories keep their historical path above and their
required frontmatter below; they are not silently migrated to epic execution.

```yaml
---
id: TH<n>.E<m>.US<l>
title: "<story title>"
type: standard            # standard | trivial | spike
priority: medium          # optional: high | medium | low
size: M                   # optional: S | M | L
agents: [developer]
skills: [bdd-stories]
traceability:
  vision: [VO-001]
  requirements: [PR-001, QR-001]
  adrs: [ADR-001]
  invariants: [INV-001]
acceptance-criteria:
  - AC1: "<criterion>"
  - AC2: "<criterion>"
depends-on: []
---
```

## Legacy Traceability Frontmatter Contract (pinned)

For v1/v2 executable stories, `traceability` is the authoritative story-level declaration. References in a
story body, epic summary, backlog description, or generated packet do not add
or replace story traceability.

Every `standard` and `spike` story must declare the block and all four keys.
Each value is a YAML list of one or more record IDs. A `trivial` story must
also declare all four keys, but may use an empty list for any or every key
when no such record applies. Extra keys, scalar values, aliases, and IDs with
prefixes not assigned to that key are invalid.

The following unchanged fenced block is the legacy machine-readable contract consumed by
`method validate trace`. The validator pins its version, fields, key set, and
prefix sets and fails closed if this definition drifts.

<!-- traceability-contract:start -->
```yaml
contract-version: 1
frontmatter-key: traceability
required-story-types: [standard, spike]
empty-allowed-story-types: [trivial]
keys:
  vision:
    prefixes: [VO]
  requirements:
    prefixes: [PR, QR]
  adrs:
    prefixes: [ADR]
  invariants:
    prefixes: [INV]
```
<!-- traceability-contract:end -->

Worked example:

```yaml
traceability:
  vision: [VO-004]
  requirements: [PR-109, QR-002]
  adrs: [ADR-005]
  invariants: [INV-007]
```

## Epic Body Template

- Outcome and explicit non-goals
- Behavioral examples tied to the authoritative frontmatter AC IDs
- Relevant boundaries, error behavior, and release/rollback constraints

Use Given / When / Then when it clarifies observable behavior, decision
tables for combinations, and invariants for stateful mechanisms. A persona
sentence is optional. Do not duplicate the acceptance criteria as a second
independently maintained checklist.

## AC Rules

- independently testable
- measurable (avoid vague terms)
- include boundaries/error behavior
- include concrete NFR thresholds when needed (latency, reliability, security)

## Scenario Coverage

- happy path (required)
- edge cases (required for standard epics and legacy standard stories)
- error cases (required for standard epics and legacy standard stories)

## Sizing Guide

- An executable epic must fit one bounded owner assignment and integrated
  review, with a coherent outcome, explicit boundaries, and a targeted
  verification plan. Context compaction or resume does not require a new
  delivery unit. Cover the behavior rather than filling an AC/scenario quota.
- Split oversized or independently releasable outcomes into separate epics,
  not mandatory story sessions. Optional children must not conceal unbounded
  work or expand the epic's agreed scope.
- Legacy executable stories retain the one-session sizing rule and typical
  2–6 ACs, 3–8 scenarios.

## Delivery Types

- `standard`: production feature + tests
- `trivial`: small/doc/config changes; reduced scenario burden
- `spike`: feasibility investigation; output is findings/ADR updates, not production feature completion

## Status Flow

V3 epic: `todo -> in-progress -> done`,
`in-progress -> failed -> in-progress -> done`, or
`in-progress -> blocked -> in-progress`. Children track acceptance completion.
Legacy v1/v2 status vocabularies remain governed by `backlog-management`.
