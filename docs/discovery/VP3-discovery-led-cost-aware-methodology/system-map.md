# System Map

## Current method

```text
kickstart
  -> vision artefact
  -> plan
       -> architect
       -> product owner
  -> autopilot
       -> developer
       -> reviewer
       -> troubleshooter
```

Current authoritative surfaces:

| Surface | Responsibility |
|---|---|
| `docs/vision_of_product/` | Product vision |
| `docs/architecture/` and `docs/ADRs/` | Technical structure and decisions |
| `docs/themes/` | Story definitions |
| `docs/plan/backlog.yaml` | Runtime status and dependencies |
| `.github/skills/` | Canonical method contracts |
| `.github/agents/` | Thin role definitions |
| `.github/hooks/` | Session lifecycle automation |
| `bin/gitflow-operator` | Delivery Gitflow operations |

The current `plan` skill moves directly from vision to architecture. The
developer contract also requires a full suite for every story. There is no
Discovery dossier, PRD convention, risk profile, model route, agent packet, or
AI-credit enforcement contract.

## Target method

```text
Human designer
  |
  +-> kickstart -> Vision sketch
  |
  +-> discover -> Discovery facilitator
  |                 +-> bounded specialists
  |                 +-> evidence and experiments
  |                 +-> human decision checkpoints
  |
  +-> requirements -> approved PRD
  |
  +-> plan
  |     +-> architecture and ADRs
  |     +-> human architecture checkpoint
  |     +-> delivery planning
  |
  +-> autopilot
        +-> generated agent packets
        +-> risk/model/verification/AIC controls
        +-> implementation, review, recovery
```

## Trust and authority boundaries

| Actor or artefact | Authority |
|---|---|
| Human designer | Scope, preferences, accepted assumptions, deferrals, risk acceptance, readiness and PRD approval |
| Discovery facilitator | Investigation sequence, evidence taxonomy, dossier consistency, readiness recommendation |
| Specialists | Bounded evidence packets only |
| Requirements facilitator | PRD drafting and traceability; no architecture decisions |
| Architect | Components, interfaces, ownership, technical contracts, ADRs |
| Product owner | Themes, stories, delivery dependencies, initial story risk tiers |
| Orchestrator | Runtime sequencing, packet assembly, budget and transition enforcement |
| Agents | Proposals and work evidence until validated |
| `backlog.yaml` | Runtime execution state and controls |

Repository and external content are untrusted data. They do not become
instruction authority merely because an agent reads them.

## External dependencies and constraints

- Git and the local filesystem provide durable history and atomic replacement
  primitives for the current local execution model.
- Copilot CLI provides session usage checkpoints, model selection, subagents,
  hooks, and soft AI-credit limits.
- Exact telemetry and routing capabilities may vary by CLI/provider version;
  capability adapters must report `measured`, `estimated`, or `unknown`.
- Existing locked themes and ADR bodies remain immutable.

