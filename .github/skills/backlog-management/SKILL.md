---
name: backlog-management
description: 'Backlog YAML format, status state machine, dependency resolution, sequencing rules, state persistence. Use when: reading backlog, updating story status, resolving dependencies, managing sequencing, parsing backlog YAML.'
---

# Backlog Management Skill

## Core State File

`docs/plan/backlog.md` is the **single source of truth** for the orchestrator. It contains YAML frontmatter with the full dependency graph and status of every theme, epic, and story.

## YAML Schema

```yaml
---
backlog:
  project: "<project-name>"
  last-updated: "<ISO 8601 timestamp>"
  themes:
    - id: TH<n>
      name: "<theme name>"
      status: todo               # todo | in-progress | done
      vision-ref: docs/vision_of_product/VP<n>-<slug>/
      depends-on: []             # theme-level dependencies (cross-theme)
      epics:
        - id: E<m>
          name: "<epic name>"
          status: todo           # todo | in-progress | done
          depends-on: []         # epic-level dependencies [E1, TH1.E2]
          stories:
            - id: US<l>
              title: "<title>"
              status: todo       # todo | in-progress | done | failed | blocked
              file: docs/themes/TH<n>-<slug>/epics/E<m>-<slug>/stories/US<l>-<slug>.md
              depends-on: []     # story-level dependencies [US1, US2]
---
```

## Status Values

| Status | Meaning | Transitions to |
|:---|:---|:---|
| `todo` | Not started, eligible if dependencies met | `in-progress` |
| `in-progress` | Currently being worked on | `done`, `failed` |
| `done` | Completed and verified | (terminal) |
| `failed` | Failed, needs troubleshooting | `in-progress` |
| `blocked` | Dependency not yet `done` | `todo` (auto-resolves) |

## Dependency Resolution Rules

### Story Eligibility
A story is **eligible** when:
1. Its epic's dependencies are all `done`
2. Its own `depends-on` stories are all `done`
3. Its status is `todo`

### Epic Eligibility
An epic is **eligible** when:
1. Its theme's dependencies are all `done` (if cross-theme deps exist)
2. Its own `depends-on` epics are all `done`
3. It has at least one `todo` story

### Parallel Execution
- Epics with no mutual dependencies MAY be processed in parallel (interleaved story-by-story)
- Stories within the same epic are processed in order (US1 before US2) unless dependencies explicitly allow otherwise

## State Update Protocol

1. **Read** backlog.md before every decision
2. **Modify** the relevant status field
3. **Update** `last-updated` timestamp
4. **Write** backlog.md atomically
5. **Mirror** the status in the individual story file's frontmatter

## Session Log

After each state change, append a line to `docs/plan/session-log.md`:

```markdown
### <ISO timestamp>
- <action>: <entity id> → <new status>
- Context: <brief description>
```

## Quick Status Table

The backlog file should maintain a human-readable summary table below the YAML:

```markdown
| Theme | Epics | Stories | Done | Failed | Remaining |
|-------|-------|---------|------|--------|-----------|
| TH1   | 3     | 12      | 8    | 1      | 3         |
```

Update this table after every story completion.
