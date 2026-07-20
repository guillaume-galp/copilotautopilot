---
name: plan
description: 'Generate architecture and backlog from vision using architect then product-owner.'
---

# Plan Skill

## Agents & Skills

- `@architect`: `the-copilot-build-method`, `architecture-decisions`
- `@product-owner`: `the-copilot-build-method`, `bdd-stories`, `backlog-management`

## Pre-flight

Read `docs/plan/backlog.yaml` if present:
1. find `locked: true` themes
2. find next VP/TH/ADR numbers
3. report settled artefacts + next IDs

Rules:
- Never modify locked VP/theme artefacts.
- Locked ADRs: only `Status:` may change to `Superseded by ADR-<NNN>`.

## Pipeline

1. Run `@architect` to update/create:
   - `docs/architecture/`
   - `docs/ADRs/`
2. Run `@product-owner` to update/create:
   - `docs/themes/TH<n>-<slug>/`
   - `docs/plan/backlog.yaml`
   - `.github/ISSUE_TEMPLATE/TH<n>-E<m>-<slug>.md` (one per epic)

If creating a new theme, archive previous theme templates to `.github/ISSUE_TEMPLATE/archive/` first.

## Required Output Summary

- themes/epics/stories created
- templates created
- dependency overview
- recommended execution order
