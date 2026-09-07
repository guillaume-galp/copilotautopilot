# Candidate Mechanisms and Accepted Directions

| Area | Considered mechanisms | Accepted direction |
|---|---|---|
| Lifecycle placement | Discovery after PRDs; Discovery inside `plan`; Discovery before final PRDs | Vision sketch -> Discovery -> PRD finalization |
| Entrypoint | Expand `kickstart`; expand `plan`; new entrypoint | New `discover` skill |
| Human workflow | Interview; evidence workbench; decision tree | Collaborative evidence workbench |
| Facilitation | Specialist committee; human-directed specialists; single facilitator | One facilitator coordinates bounded specialists |
| PRD handoff | Discovery writes final PRD; draft PRD; recommendations only | Recommendations only; separate `requirements` skill |
| Dossier shape | Single file; adaptive; structured | Always structured, concise when appropriate |
| Readiness | Score; human-only; semantic verdict | Facilitator recommends `READY`, `READY_WITH_DEFERRALS`, or `BLOCKED`; human accepts |
| Revisions | Edit in place; snapshots; addenda | Append-only `DR-###` addenda with linked current status |
| Proportionality | Universal full Discovery; scoring; three dispositions | `FULL`, `LIGHTWEIGHT`, or human-approved single-scope `WAIVED` |
| State updates | Single writer; long-held lock; optimistic writers | Expected revision plus short atomic transaction lock and conflict detection |
| Packets | Full-context reload; ephemeral packet; retained generated manifest | Generated task packet with retained manifest and source hashes |
| Verification | Full suite per story; fixed profiles; risk-proportional matrix | Targeted story evidence, conditional epic suite, mandatory theme/release suite |
| Model routing | Fixed by role; fixed by story; task-level | Provider-neutral task-level routing within story controls |
| Scope | One large TH3; separate VPs; one VP with multiple themes | VP3 delivered through TH3, TH4, and TH5 |

## Investigation loop

```text
Frame DQ
  -> define consequence, owner, budget, method, and stop condition
  -> collect EV
  -> classify finding
  -> validate, reject, defer, or escalate for human decision
  -> update readiness
```

Investigations use both time/turn limits and AI-credit targets. Consequential
evidence requires reproducibility information; low-impact evidence requires a
clear citation.

## Delivery control bridge

```text
Discovery risk
  -> architecture invariant and contract
  -> planned story tier
  -> model route
  -> verification and review profile
  -> AIC target, warning, and pause thresholds
  -> actual evidence and calibration
```

