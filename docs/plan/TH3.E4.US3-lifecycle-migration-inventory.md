# TH3.E4.US3 Lifecycle Documentation Migration Inventory

## Provenance

| Field | Value |
|---|---|
| Story | `TH3.E4.US3` |
| Backlog revision at execution | `56` (`in-progress`) |
| Prepared at | `2026-09-07T00:12:03.355+01:00` |
| Canonical contract | `.github/skills/the-copilot-build-method/SKILL.md` |
| Inventory scope | Root README, workspace instructions, all 13 active skill entry files, and all 10 active top-level agent Markdown files |
| Active files inspected | `25` |
| Migrated | `3` |
| Already consistent | `22` |
| Pull-request provenance | Gitflow was blocked under the session constraint and no pull request could exist. This repository artefact retains the inventory for inclusion in a later pull request; it is not represented as PR-generated evidence. |

`Migrated` means this story changed the active file. `Already consistent`
means inspection found a reference to `the-copilot-build-method` where the
file names lifecycle stages and found no competing ordered stage list. The
canonical skill is the sole permitted owner of the complete stage map.

## Active file inventory

| Active file | Verdict | Inspection result |
|---|---|---|
| `README.md` | migrated | Replaced the legacy flow with the six-stage, five-entrypoint reader summary and canonical-owner reference. |
| `.github/copilot-instructions.md` | migrated | States six stages and five entrypoints while deferring the map to the canonical skill. |
| `.github/skills/architecture-decisions/SKILL.md` | already-consistent | References the canonical skill for lifecycle lock timing; no stage list. |
| `.github/skills/autopilot/SKILL.md` | already-consistent | References the canonical skill through its participating roles; describes only its own delivery work. |
| `.github/skills/backlog-management/SKILL.md` | already-consistent | References the canonical skill for split locks; no stage list. |
| `.github/skills/bdd-stories/SKILL.md` | already-consistent | Explicitly defers lifecycle, gates, authority, and locks to the canonical skill. |
| `.github/skills/code-quality/SKILL.md` | already-consistent | Explicitly defers lifecycle, gates, authority, and locks to the canonical skill. |
| `.github/skills/discover/SKILL.md` | already-consistent | Defers lifecycle order and authority to the canonical skill and defines only Discovery behavior. |
| `.github/skills/discovery-dossier/SKILL.md` | already-consistent | References the canonical lifecycle owner; defines only the dossier contract. |
| `.github/skills/gitflow-operator/SKILL.md` | already-consistent | Explicitly defers lifecycle, gates, authority, and locks to the canonical skill. |
| `.github/skills/kickstart/SKILL.md` | migrated | Added the `discover` handoff and the accepted Discovery readiness prerequisite for `plan` stage 1. |
| `.github/skills/plan/SKILL.md` | already-consistent | Defers lifecycle ownership and describes only the two stages belonging to its entrypoint. |
| `.github/skills/product-requirements/SKILL.md` | already-consistent | References the canonical lifecycle owner; defines only PRD schema and ownership. |
| `.github/skills/requirements/SKILL.md` | already-consistent | Defers lifecycle and gate authority and describes only requirements orchestration. |
| `.github/skills/the-copilot-build-method/SKILL.md` | already-consistent | Sole canonical owner of the complete six-stage map and five entrypoints. |
| `.github/agents/README.md` | already-consistent | Explicitly defers stage order and entrypoint mapping to the canonical skill. |
| `.github/agents/architect.agent.md` | already-consistent | References the canonical skill and limits itself to Architecture responsibilities. |
| `.github/agents/developer.agent.md` | already-consistent | Declares the canonical skill dependency; no stage list. |
| `.github/agents/discovery-facilitator.agent.md` | already-consistent | References canonical human authority and working-state rules; no stage list. |
| `.github/agents/investigator.agent.md` | already-consistent | Defers lifecycle and human authority to the canonical skill; no stage list. |
| `.github/agents/orchestrator.agent.md` | already-consistent | Reads the canonical lifecycle and admission contract; no competing stage list. |
| `.github/agents/product-owner.agent.md` | already-consistent | References the canonical skill and describes only `plan` stage 2 responsibilities. |
| `.github/agents/requirements-facilitator.agent.md` | already-consistent | Defers lifecycle authority and locks to the canonical skill; no stage list. |
| `.github/agents/reviewer.agent.md` | already-consistent | Declares the canonical skill dependency; no stage list. |
| `.github/agents/troubleshooter.agent.md` | already-consistent | Declares the canonical skill dependency; no stage list. |

## Explicit exclusions

Excluded content was not migrated. Historical lifecycle wording in these
scopes remains evidence, not an active instruction.

| Excluded scope | Reason |
|---|---|
| `docs/themes/TH1-methodology-improvements/**` and `docs/plan/backlog-archive/TH1.yaml` | Locked TH1 artefacts; retain byte-identical history. |
| `docs/themes/TH2-gitflow-operator/**` and `docs/plan/backlog-archive/TH2.yaml` | Locked TH2 artefacts; retain byte-identical history. |
| `docs/architecture/history/**` | Archived architecture history. |
| `.github/agents/archive/**` | Retired agent history, not active instructions. |
| `.github/ISSUE_TEMPLATE/archive/**` | Archived issue-template history. |
| `docs/vision_of_product/VP3-discovery-led-cost-aware-methodology/**` | Frozen VP3 Vision source. |
| `docs/discovery/VP3-discovery-led-cost-aware-methodology/**` | Frozen accepted VP3 Discovery dossier and revisions. |
| `docs/requirements/VP3-discovery-led-cost-aware-methodology/**` | Frozen approved VP3 PRD. |
| `docs/ADRs/ADR-001-gitflow-operator.md` | Locked ADR-001 contract. |
| `docs/plan/backlog.yaml` | Authoritative runtime state; revision 56 was observed, not edited. |
| `docs/plan/session-log.md` | Protected session history; not edited. |

The active architecture set and ADRs other than ADR-001 were consulted for
context only. Their accepted technical and ownership contracts were not
rewritten by this documentation migration.
