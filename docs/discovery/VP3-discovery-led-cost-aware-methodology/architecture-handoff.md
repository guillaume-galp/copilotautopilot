# Architecture Handoff

## Readiness

`READY_WITH_DEFERRALS`, accepted by the human designer on 2026-09-05.

Architecture must consume the approved VP3 PRD together with this handoff.

## Constraints architecture must preserve

1. Keep interactive human ownership of consequential Discovery and requirements
   decisions.
2. Preserve one authoritative owner for each lifecycle fact.
3. Keep the backlog authoritative for runtime state and execution controls.
4. Use stable consequential traceability across Discovery, PRD, ADR, story, and
   evidence records.
5. Preserve existing locked theme and ADR immutability.
6. For VP 1:N mapping, lock each theme independently and lock shared VP,
   Discovery, and PRD artefacts only after all mapped themes are accepted.
7. Treat usage as measured, estimated, or unknown; never silently zero.
8. Define pause enforcement at model/delegation boundaries with an overshoot
   allowance for the in-flight response.
9. Support stale-packet rejection and governed context expansion.
10. Support optimistic state writers through expected revisions, atomic
    transitions, explicit conflicts, and recovery.
11. Keep agents as proposers until evidence or gate validation.
12. Keep the implementation provider-neutral through capability adapters and
    policy mappings.

## Architecture decisions required

- Discovery and requirements skill/agent boundaries for the hybrid facilitator
  model.
- Dossier schemas and validation strategy.
- Versioned backlog schema and transition command.
- Usage capability adapter and nested baseline/delta accounting.
- Model capability policy and availability fallback.
- Packet generation, source selection, hashing, persistence, and expansion.
- Transition journal, recovery, compaction, and multi-process behavior.
- Control activation ledger and evidence requirements.
- Trace storage and theme-lock compaction.
- Migration assessment for repositories already using the four-stage method.

## Decisions architecture may not revisit silently

- Discovery occurs before PRD finalization.
- Discovery and requirements are separate interactive entrypoints.
- The human accepts readiness, PRDs, architecture, and critical overrides.
- TH3, TH4, and TH5 form the accepted VP3 scope.
- Runtime controls are authoritative in `backlog.yaml`.
- R3 waivers/downgrades require human plus reviewer acknowledgement.

If architecture finds any of these infeasible, it must open a Discovery Revision
or PRD change record rather than weakening the contract.

