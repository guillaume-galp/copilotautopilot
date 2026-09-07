# Human Decision Register

| ID | Decision | Consequence |
|---|---|---|
| DEC-001 | Place Discovery after the vision sketch and before PRD finalization. | Discovery hardens both requirements and architecture readiness. |
| DEC-002 | Add a new `discover` entrypoint. | `plan` no longer begins directly from raw vision. |
| DEC-003 | Use a collaborative evidence workbench. | The human receives findings and consequential choices rather than a form or opaque recommendation. |
| DEC-004 | Use one facilitator with bounded specialists. | The facilitator owns dossier coherence; specialists cannot make final decisions. |
| DEC-005 | Add a separate interactive `requirements` skill. | Discovery provides recommendations but does not author or approve final PRDs. |
| DEC-006 | Always use a structured dossier. | Small work keeps the same information model with concise or not-applicable sections. |
| DEC-007 | Use semantic readiness verdicts accepted by the human. | Readiness is auditable without pretending to be a numeric truth. |
| DEC-008 | Use structured table records and consequential item-level traceability. | Important requirements retain evidence and decision lineage. |
| DEC-009 | Discovery identifies required invariants; architecture formalizes technical contracts. | Discovery does not prescribe components or technologies. |
| DEC-010 | Store finalized PRDs under `docs/requirements/VP<n>-<slug>/PRD.md`. | Requirements become an explicit lifecycle artefact. |
| DEC-011 | Store active Discovery changes as append-only `DR-###` records. | Accepted conclusions preserve history. |
| DEC-012 | Use `FULL`, `LIGHTWEIGHT`, and single-scope human-approved `WAIVED` dispositions. | Small changes avoid excessive process without bypassing classification. |
| DEC-013 | Product owner assigns story risk; architect validates; reviewer may escalate. | Risk is checked by multiple roles. |
| DEC-014 | Put runtime status, risk, model, verification, budgets, and aggregate usage in `backlog.yaml`. | The backlog remains authoritative for execution. |
| DEC-015 | Generate and retain compact packet manifests. | Agent context is auditable and stale sources are rejected. |
| DEC-016 | Use targeted story checks, conditional epic suites, and mandatory theme/release suites. | Verification is proportional and layered. |
| DEC-017 | Route models per task within story-level limits. | Expensive reasoning is narrowly scoped. |
| DEC-018 | Use a balanced scorecard and provisional cost targets. | Lower AIC cannot compensate for reduced quality, safety, or scope. |
| DEC-019 | Keep one `plan` skill with architecture and planning stages separated by human approval. | The first architecture proposal does not automatically become a backlog. |
| DEC-020 | Deliver VP3 through TH3, TH4, and TH5. | Bootstrap and enforcement risks are staged. |
| DEC-021 | Lock themes independently; lock VP/Discovery/PRD only after all mapped themes are accepted. | VP 1:N mapping remains revisable without changing locked theme contracts. |
| DEC-022 | Use optimistic multi-writer state with expected revisions and conflict detection. | Runtime updates require an atomic transition mechanism. |
| DEC-023 | Treat agents as proposers until evidence or gate validation. | Agents cannot self-certify compliance. |
| DEC-024 | Require human plus reviewer acknowledgement for R3 waivers or downgrades. | Critical controls cannot be weakened unilaterally. |
| DEC-025 | Use five control maturity states. | TH3 can self-host without claiming enforcement before it exists. |

