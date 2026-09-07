---
name: kickstart
description: 'Interactive product vision kickoff that captures lock-aware VP artefacts.'
---

# Kickstart Skill

## Agents & Skills

- Interactive (`ask`) + `the-copilot-build-method`

## Pre-flight

Read `docs/plan/backlog.yaml` if present:
- identify theme-to-VP mappings and acceptance state
- identify highest existing VP number

Apply the shared-VP lock scope from `the-copilot-build-method`. Never edit a
locked VP artefact; create the next `VP<n+1>-<slug>/`.

## Vision Capture Checklist

For each VP directory, capture:
- problem statement
- target users/personas
- core features
- success criteria
- constraints
- open questions

## Conversation Starter

Ask:
1. What product are we building?
2. What problem does it solve?
3. Who is it for?

## Handoff

After the Vision sketch is recorded, hand off to `discover`; never hand off
directly to `plan`. The human must accept the Discovery readiness gate with a
`READY` or `READY_WITH_DEFERRALS` verdict before `plan` stage 1 can run.
`plan` stage 1 also independently requires the human-approved PRD, as defined
by the canonical lifecycle contract in `the-copilot-build-method`.
