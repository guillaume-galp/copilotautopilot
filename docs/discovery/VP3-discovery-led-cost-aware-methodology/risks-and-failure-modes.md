# Risks, Failure Modes, and Invariants

## Foundational invariants

| ID | Invariant |
|---|---|
| INV-001 | No phase advances without its accepted gate or a valid explicit waiver. |
| INV-002 | Each fact has one authoritative owner. |
| INV-003 | Locked VP, Discovery, PRD, theme/story, and ADR bodies remain immutable under their supersession rules. |
| INV-004 | Consequential requirements and decisions remain traceable upstream and downstream. |
| INV-005 | Missing usage or verification evidence is `unknown`, never zero or success. |
| INV-006 | A pause threshold preserves recoverable state before new work stops. |
| INV-007 | Agents act only from packets matching authoritative source revisions. |
| INV-008 | Runtime transitions are atomic, ordered, recoverable, and conflict-aware. |
| INV-009 | Completion requires applicable acceptance, verification, review, Gitflow, and usage evidence or valid waivers. |
| INV-010 | Risk, verification, model, and budget controls cannot be weakened without authority and rationale. |
| INV-011 | Invalidated upstream decisions pause affected downstream work before it continues. |
| INV-012 | Human approvals, overrides, deferrals, and risk acceptance remain attributable. |

## Risk register

| ID | Risk | Impact | Treatment |
|---|---|---|---|
| RSK-001 | Discovery becomes analysis paralysis. | Delayed delivery and excessive AIC. | Budget every question and stop at decision readiness. |
| RSK-002 | Structured records overload the human. | Checkpoint fatigue and process abandonment. | Decision-triggered checkpoints, concise files, and grouped choices. |
| RSK-003 | Waivers become a bypass path. | Unexamined uncertainty reaches delivery. | Narrow scope, human approval, invalidation conditions, release reporting. |
| RSK-004 | Agents downgrade risk or verification to meet budgets. | Hidden safety and quality loss. | Architect/reviewer authority, balanced metrics, attributable overrides. |
| RSK-005 | Telemetry is missing, delayed, or incompatible. | Budgets appear satisfied incorrectly. | Capability adapter, confidence labels, conservative proxies, block unless waived. |
| RSK-006 | Native soft limits overshoot. | Actual usage exceeds the nominal pause number. | Model/task overshoot allowance and pre-delegation gates. |
| RSK-007 | Concurrent state writers overwrite transitions. | Corrupt or incorrect backlog state. | Expected revisions, short transaction lock, atomic replace, journal and recovery. |
| RSK-008 | Compact packets omit a critical constraint. | Incorrect implementation under incomplete context. | Source manifests, expansion requests, stale rejection, repeated-gap escape detection. |
| RSK-009 | Retrieved content injects instructions. | Policy bypass or unsafe tool behavior. | Treat sources as untrusted data and preserve trusted instruction hierarchy. |
| RSK-010 | Multi-theme VP locking freezes evidence too early. | Later mapped themes cannot correct the shared basis. | Lock theme artefacts independently; lock VP-level artefacts after all mapped themes. |
| RSK-011 | The first theme claims controls not yet implemented. | False compliance and misleading release claims. | Five-state activation ledger with effective points and reviewer/human promotion. |
| RSK-012 | Cost targets encourage under-scoping or weak tests. | Lower AIC but worse product outcomes. | Balanced cost, flow, discovery, quality, scope, and evidence scorecard. |

## Failure routing

| Failure | Required behavior |
|---|---|
| Stale packet | Reject and regenerate. |
| State revision conflict | Reject the transition and reconcile before retrying. |
| Failure before atomic replace | Preserve the last valid state and journal the abort. |
| Crash after replace before commit marker | Reconcile the prepared record and current hash before continuing. |
| Missing completion evidence | Block unless explicitly waived. |
| Discovery escape | Pause the affected dependency subgraph and open `DR-###`. |
| Locked-theme escape | Create a new VP and Discovery dossier. |
| R3 waiver or downgrade | Require human authorization and independent reviewer acknowledgement. |

