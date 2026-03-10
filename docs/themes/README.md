# Themes

This directory contains the implementation plan organized as themes, epics, and user stories.

## Structure

```
themes/
├── TH1-<theme-name>/
│   ├── README.md                       # Theme overview
│   ├── RELEASE_NOTES.md                # Generated at theme completion
│   └── epics/
│       ├── E1-<epic-name>/
│       │   ├── README.md               # Epic overview
│       │   └── stories/
│       │       ├── US1-<story>.md       # User story (hybrid BDD)
│       │       └── US2-<story>.md
│       └── E2-<epic-name>/
│           ├── README.md
│           └── stories/
│               └── US1-<story>.md
├── TH2-<theme-name>/
│   └── ...
```

## Conventions

| Entity | Pattern | Maps to |
|--------|---------|---------|
| Theme | `TH<n>-<slug>/` | `VP<n>` in vision_of_product |
| Epic | `E<m>-<slug>/` | A coherent unit of deliverable functionality |
| Story | `US<l>-<slug>.md` | One implementable unit of work |

## Story File Format

Each user story file contains YAML frontmatter with metadata and status, followed by the story body with acceptance criteria and BDD scenarios. See `.github/copilot-instructions.md` for the full template.

## Lifecycle

1. **product-owner** agent creates these directories and files during planning
2. **orchestrator** agent reads and updates story status during execution
3. **documenter** agent produces changelogs and release notes at epic/theme completion
