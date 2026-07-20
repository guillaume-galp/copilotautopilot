---
name: kickstart
description: 'Interactive product vision kickoff that captures lock-aware VP artefacts.'
---

# Kickstart Skill

## Agents & Skills

- Interactive (`ask`) + `the-copilot-build-method`

## Pre-flight

Read `docs/plan/backlog.yaml` if present:
- identify `locked: true` themes and referenced VP paths
- identify highest existing VP number

Rule: never edit locked VP artefacts; create next `VP<n+1>-<slug>/`.

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
