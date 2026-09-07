# VP3 Discovery Dossier

| Field | Value |
|---|---|
| Vision | `docs/vision_of_product/VP3-discovery-led-cost-aware-methodology/VP3.md` |
| Status | Accepted |
| Verdict | `READY_WITH_DEFERRALS` |
| Human acceptance | 2026-09-05 |
| Discovery depth | Full |
| Facilitator model | Interactive evidence workbench with bounded specialist investigations |

## Scope

This dossier discovers how to evolve the Copilot Build Method into a
discovery-led, cost-aware lifecycle without prematurely choosing its
implementation architecture.

The accepted lifecycle is:

```text
Vision sketch
  -> Discovery
  -> PRD finalization
  -> Architecture and ADRs
  -> Planning and BDD backlog
  -> Cost-aware Autopilot
```

## Accepted delivery scope

VP3 maps to three themes:

| Theme | Outcome |
|---|---|
| TH3 | Discovery and requirements foundation |
| TH4 | Risk-aware planning and compact agent context |
| TH5 | Economic enforcement, recovery, and calibration |

TH3 is the minimum first release. It provides the `discover` and
`requirements` workflows, the dossier and PRD gates, and the revised two-stage
`plan` contract. Controls may initially be governed manually and must report
their actual activation maturity.

## Readiness conclusion

The vision is ready for PRD finalization with bounded deferrals. Discovery
validated that:

- exact cumulative local AI-credit telemetry is available at session
  checkpoints;
- the CLI can block the next model call at a configured soft limit;
- task-level model selection and provider-neutral routing are feasible;
- packet staleness can be detected deterministically with source hashes;
- optimistic revisioned YAML updates can reject conflicts and recover around
  atomic replacement failures.

The remaining work concerns architecture and implementation choices rather than
product feasibility.

## Accepted deferrals

| ID | Deferral | Required disposition |
|---|---|---|
| DEF-001 | Select the production telemetry capability adapter. | Architecture and TH5 |
| DEF-002 | Define overshoot allowances and nested budget accounting over the native session soft cap. | Architecture and TH5 |
| DEF-003 | Select the production state-transition command, schema validation, journal compaction, and conflict UX. | Architecture and TH5 |
| DEF-004 | Map provider-neutral model classes to available models and version the policy. | Architecture and TH4 |
| DEF-005 | Validate dossier and trace boundedness during staged self-hosting. | TH3-TH5 measurement |

## Gate rules

- The facilitator recommends `READY`, `READY_WITH_DEFERRALS`, or `BLOCKED`.
- The human accepts or rejects the recommendation.
- A deferral is not an unowned unknown. Its owner, impact, trigger, and
  treatment are risk-dependent and remain visible downstream.
- Architecture may not begin from VP3 alone. It requires the approved PRD and
  this dossier's architecture handoff.

## Acceptance

| Field | Value |
|---|---|
| Actor | Human product owner |
| Timestamp | 2026-09-05T16:08:02+01:00 |
| Scope | VP3 Discovery dossier and bounded architecture deferrals |
| Verdict | READY_WITH_DEFERRALS |
| Rationale | The product direction, lifecycle, governance, feasibility, and staged scope are sufficiently resolved for PRD finalization and architecture. |
| Source revision | Discovery dossier state at 2026-09-05T16:08:02+01:00 |

The normalized acceptance record and the resulting lifecycle/scope alignment
are documented in
`revisions/DR-001-lifecycle-scope-and-acceptance.md`.

## Gitflow applicability

Gitflow operations are not applicable to this Discovery activity because it
creates pre-delivery evidence and does not branch, commit, merge, or release a
delivery item.
