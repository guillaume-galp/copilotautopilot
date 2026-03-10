---
# Backlog — Core State File
# This YAML document is the single source of truth for the autopilot orchestrator.
# Structure: themes → epics → stories, with dependency graph and status tracking.
#
# Status values: todo | in-progress | done | failed | blocked
#
# The orchestrator reads this file before every decision and writes after every state change.
# Individual story files in docs/themes/ mirror the status in their own frontmatter.

backlog:
  project: "<project-name>"
  last-updated: "<timestamp>"
  themes: []
  # Example structure:
  #
  # themes:
  #   - id: TH1
  #     name: "MVP"
  #     status: todo
  #     vision-ref: docs/vision_of_product/VP1-mvp/
  #     depends-on: []
  #     epics:
  #       - id: E1
  #         name: "User Authentication"
  #         status: todo
  #         depends-on: []
  #         stories:
  #           - id: US1
  #             title: "User registration form"
  #             status: todo
  #             file: docs/themes/TH1-mvp/epics/E1-auth/stories/US1-registration.md
  #             depends-on: []
  #           - id: US2
  #             title: "Login with email/password"
  #             status: todo
  #             file: docs/themes/TH1-mvp/epics/E1-auth/stories/US2-login.md
  #             depends-on: [US1]
  #       - id: E2
  #         name: "Dashboard"
  #         status: todo
  #         depends-on: [E1]
  #         stories:
  #           - id: US1
  #             title: "Dashboard layout"
  #             status: todo
  #             file: docs/themes/TH1-mvp/epics/E2-dashboard/stories/US1-layout.md
  #             depends-on: []
---

# Product Backlog

The YAML frontmatter above is the machine-readable backlog consumed by the orchestrator agent.

## How to read this file

- **themes**: Top-level product increments (VP1 → TH1, VP2 → TH2, etc.)
- **epics**: Coherent feature groups within a theme
- **stories**: Individual implementable units within an epic
- **depends-on**: Items that must be `done` before this item can start
- **status**: Current state (`todo` → `in-progress` → `done` | `failed`)

## Quick Status

_This section is updated by the orchestrator agent after each state change._

| Theme | Epics | Stories | Done | Failed | Remaining |
|-------|-------|---------|------|--------|-----------|
| — | — | — | — | — | — |
