# ADR-002: Six-Stage Gated Lifecycle, Entrypoint Boundaries, and Artefact Ownership

## Status

Accepted

## Context

The current method moves from vision directly into architecture through the
`plan` skill (EV-002). VP3 Discovery established that Discovery and Build are
distinct engineering modes and that architecture must formalize evidence-backed
constraints rather than discover the domain (DEC-001, DEC-009, VO-003).

The approved PRD requires a six-stage lifecycle with human-owned gates
(PR-001), a `discover` entrypoint with dispositions (PR-002), a separate
interactive `requirements` entrypoint (PR-008, DEC-005), a two-stage `plan`
(PR-010, DEC-019), append-only Discovery Revisions and Product Change Records
(PR-007, PR-009), and one authoritative owner per lifecycle fact (INV-002).

It also requires the hybrid facilitator model: interactive skills own the human
dialogue while bounded internal agents perform delegated investigation or
drafting (PR-016, DEC-004).

## Decision

Adopt six stages with five entrypoints and explicit gate records.

| Stage | Entrypoint | Gate | Authority |
|---|---|---|---|
| Vision sketch | `kickstart` | none | human |
| Discovery | `discover` | readiness verdict accepted | human |
| PRD finalization | `requirements` | PRD approval | human |
| Architecture | `plan` stage 1 | architecture acceptance | human |
| Planning | `plan` stage 2 | `Accepted` planning-admission record at exact validated source revision | product owner plus validator |
| Autopilot | `autopilot` | story, epic, and theme DoD | orchestrator, reviewer, human |

1. Each stage command reads the upstream gate record before doing work and
   refuses to proceed when it is missing, unaccepted, or `BLOCKED`. Refusal is
   fail-closed with exit code 2.
2. A gate record is a `## Approval` or `## Acceptance` section in the artefact
   that the gate covers, containing actor, timestamp, scope, verdict,
   rationale, and source revision. The gate record is the only machine-readable
   source of gate state.
3. Every scope receives a `FULL`, `LIGHTWEIGHT`, or human-approved `WAIVED`
   Discovery disposition. A `WAIVED` disposition names its invalidation
   conditions and is invalidated by material scope expansion.
4. `discover` and `requirements` are interactive skills. `discovery-facilitator`
   owns dossier coherence and the readiness recommendation; `investigator`
   returns bounded evidence packets only; `requirements-facilitator` drafts
   requirements and traceability. None of them approves anything.
5. Ownership is single-owner per fact: canonical `VO-###` vision outcomes and
   requirements are in the PRD, Discovery records (including `DEF-###`) are
   in the dossier, technical contracts are in `docs/architecture/` and
   `docs/ADRs/`, story definitions are in `docs/themes/`, and runtime state is
   in `docs/plan/backlog.yaml`. The Vision sketch supplies source context but
   need not duplicate the PRD's canonical outcome rows. A PRD constraints and
   deferrals table cites dossier-owned `DEF-###` records rather than owning
   copies.
6. Accepted Discovery changes append `DR-###` records; approved PRD changes
   append `PCR-###` records. A `DR-###` names its downstream impact set, which
   pauses only the affected dependency subgraph and forces resumption from the
   earliest invalidated gate.

## Consequences

### Positive

- Architecture starts from accepted evidence instead of raw vision.
- Gate state is auditable, attributable, and checkable without a database.
- Discovery cost is proportional to scope through three dispositions.
- The human keeps every consequential decision without reviewing every detail.

### Negative

- One additional entrypoint and one additional artefact set per VP.
- Small scopes still pay classification and gate-record overhead.
- The existing `kickstart` to `plan` handoff and all lifecycle documentation
  must be rewritten in TH3 (QR-012).

### Risks

- Checkpoint fatigue (RSK-002). Mitigation: grouped decision-triggered
  checkpoints, concise files, and a `LIGHTWEIGHT` path targeting one checkpoint
  and 30 minutes.
- Waivers become a bypass path (RSK-003). Mitigation: single-scope waivers,
  named invalidation conditions, validator checks, and release reporting.
- Analysis paralysis (RSK-001). Mitigation: every `DQ-###` carries a budget and
  a stop condition; readiness is a decision-readiness judgement, not
  completeness.

## Alternatives Considered

### Discovery inside `plan`

- Pros: no new entrypoint; fewer artefacts.
- Cons: mixes investigation with commitment; architecture would still begin
  before evidence acceptance.
- Rejected because: DEC-002 and EV-002 require Discovery to precede the
  architecture stage.

### Discovery writes the final PRD

- Pros: one fewer interactive stage.
- Cons: conflates investigation authority with requirement approval; the
  facilitator would effectively approve product scope.
- Rejected because: DEC-005 keeps recommendations and requirements separate.

### Separate `architecture` and `planning` skills

- Pros: sharper stage boundary.
- Cons: duplicates pre-flight, lock, and numbering logic across two skills.
- Rejected because: DEC-019 keeps one `plan` skill with an internal human
  checkpoint.

### Numeric readiness score

- Pros: simple threshold automation.
- Cons: false precision; hides which unknowns matter.
- Rejected because: DEC-007 selects semantic verdicts accepted by a human.
