---
name: bdd-stories
description: 'Hybrid BDD story format, acceptance criteria patterns, scenario requirements, sizing, and story types.'
---

# BDD Stories Skill

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
acceptance-criteria:
  - AC1: "<criterion>"
  - AC2: "<criterion>"
depends-on: []
---
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
