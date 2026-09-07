---
name: bdd-stories
description: 'Hybrid BDD story format, acceptance criteria patterns, scenario requirements, sizing, and story types.'
---

# BDD Stories Skill

Use `the-copilot-build-method` as the canonical lifecycle, gate, authority, and
split-lock contract; this skill defines story form only and does not restate
that contract.

## Story Path

`docs/themes/TH<n>-<slug>/epics/E<m>-<slug>/stories/US<l>-<slug>.md`

## Required Frontmatter

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

## Traceability Frontmatter Contract

`traceability` is the authoritative story-level declaration. References in a
story body, epic summary, backlog description, or generated packet do not add
or replace story traceability.

Every `standard` and `spike` story must declare the block and all four keys.
Each value is a YAML list of one or more record IDs. A `trivial` story must
also declare all four keys, but may use an empty list for any or every key
when no such record applies. Extra keys, scalar values, aliases, and IDs with
prefixes not assigned to that key are invalid.

The following fenced block is the machine-readable contract consumed by
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

## Body Template

- As-a / I-want / So-that sentence
- Acceptance criteria checklist
- BDD scenarios (Given / When / Then)

## AC Rules

- independently testable
- measurable (avoid vague terms)
- include boundaries/error behavior
- include concrete NFR thresholds when needed (latency, reliability, security)

## Scenario Coverage

- happy path (required)
- edge cases (required for standard stories)
- error cases (required for standard stories)

## Sizing Guide

- story should fit one agent session
- typical standard story: 2–6 ACs, 3–8 scenarios
- split oversized stories

## Story Types

- `standard`: production feature + tests
- `trivial`: small/doc/config changes; reduced scenario burden
- `spike`: feasibility investigation; output is findings/ADR updates, not production feature completion

## Status Flow

`todo -> in-progress -> done` or `in-progress -> failed -> in-progress -> done`
