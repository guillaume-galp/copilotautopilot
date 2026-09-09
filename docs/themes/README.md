# Themes

This directory contains themes and executable epics. Stories are optional
acceptance subdivisions, not independent LLM work assignments.

## Structure

```
themes/
├── TH1-<theme-name>/
│   ├── README.md                       # Theme overview
│   └── epics/
│       ├── E1-<epic-name>/
│       │   ├── README.md               # Executable epic specification
│       │   └── stories/                # Optional acceptance subdivisions
│       │       ├── US1-<story>.md       # Optional child acceptance criteria
│       │       └── US2-<story>.md
│       └── E2-<epic-name>/
│           └── README.md               # No stories required
├── TH2-<theme-name>/
│   └── ...
```

## Conventions

| Entity | Pattern | Maps to |
|--------|---------|---------|
| Theme | `TH<n>-<slug>/` | One VP may map to multiple themes |
| Epic | `E<m>-<slug>/README.md` | One bounded implementation, verification, and integration assignment |
| Story | `stories/US<l>-<slug>.md` | Optional acceptance subdivision owned by its epic |

## Epic Specification Format

Each epic specification contains authoritative acceptance criteria and
traceability in frontmatter, with its outcome, non-goals, and relevant
behavioral examples in the body. See `bdd-stories` for the canonical format,
including optional child stories. Status lives only in
`docs/plan/backlog.yaml`; new themes use the epic-first schema from
`backlog-management`. Existing locked themes retain their historical formats.

## Lifecycle

1. **product-owner** agent creates these directories and files during planning
2. **orchestrator** agent sequences epics and tracks status in `docs/plan/backlog.yaml`; the epic owner sequences internal tasks and optional children
3. **orchestrator** produces changelogs and release notes at epic/theme completion
