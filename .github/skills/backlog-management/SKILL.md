---
name: backlog-management
description: 'Backlog YAML schema, status transitions, dependency sequencing, lock behavior, and crash recovery rules.'
---

# Backlog Management Skill

## Authoritative State

`docs/plan/backlog.yaml` is the single source of truth (pure YAML, no markdown wrapper).

## Minimal Schema

```yaml
backlog:
  project: "<name>"
  last-updated: "<ISO-8601>"
  themes:
    - id: TH<n>
      name: "<theme>"
      status: todo            # todo|in-progress|done
      locked: false
      vision-ref: docs/vision_of_product/VP<n>-<slug>/
      depends-on: []
      epics:
        - id: E<m>
          name: "<epic>"
          status: todo        # todo|in-progress|done
          depends-on: []
          stories:
            - id: TH<n>.E<m>.US<l>
              title: "<title>"
              status: todo    # todo|in-progress|done|failed
              priority: medium  # high|medium|low (default: medium)
              file: docs/themes/TH<n>-<slug>/epics/E<m>-<slug>/stories/US<l>-<slug>.md
              depends-on: []
```

## Status Machine

- `todo -> in-progress -> done`
- `in-progress -> failed -> in-progress`

## Dependency Rules

Story eligible when:
1. epic dependencies are done
2. story dependencies are done
3. story status is `todo`

If multiple stories are eligible:
- priority: `high > medium > low` (default `medium`)
- tie-breaker: story order (US1 before US2)

## Lock Rules (`locked: true`)

Do not modify associated VP/theme/story artefacts.
Locked ADRs follow supersession-only status update rule.
Backlog edits for locked themes are restricted to clearly wrong technical references (e.g., broken file path).

## Update Protocol

For every transition:
1. read current backlog
2. update status field
3. update `last-updated`
4. write atomically
5. append session-log entry

## Session Log

Append concise entry to `docs/plan/session-log.md`; keep last 50 entries.

## Crash Recovery

If any story is `in-progress` on startup:
1. detect partial work
2. choose continue / reset / escalate
3. update backlog accordingly

## Qualified IDs

- Theme: `TH<n>`
- Epic: `TH<n>.E<m>`
- Story: `TH<n>.E<m>.US<l>`
