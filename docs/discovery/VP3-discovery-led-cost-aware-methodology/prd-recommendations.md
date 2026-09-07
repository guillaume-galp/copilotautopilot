# PRD Recommendations

These recommendations are inputs to the interactive `requirements` phase. They
are not approved product requirements.

## Product outcome

Enable a human designer and Copilot agents to discover consequential unknowns
before requirements and architecture are frozen, then execute delivery with
risk-proportional context, verification, model use, and AI-credit controls.

## Recommended functional requirement groups

### TH3: Discovery and requirements foundation

- Provide a `discover` entrypoint operating as a collaborative evidence
  workbench.
- Create structured Discovery dossiers with stable record IDs and provenance.
- Support `FULL`, `LIGHTWEIGHT`, and human-approved single-scope `WAIVED`
  dispositions.
- Produce facilitator-recommended, human-accepted readiness verdicts.
- Support append-only Discovery Revisions and downstream invalidation.
- Provide a separate interactive `requirements` entrypoint.
- Store approved PRDs at
  `docs/requirements/VP<n>-<slug>/PRD.md`.
- Require append-only `PCR-###` records for consequential approved-PRD changes.
- Require `plan` to gate architecture on accepted Discovery and approved PRD,
  then gate delivery planning on human-approved architecture.

### TH4: Risk-aware planning and context

- Add objective R0-R3 story classification with validation and escalation.
- Add verification and review profiles selected by mechanism and risk.
- Add provider-neutral model capability classes routed at task granularity.
- Generate compact agent packet manifests with source hashes and controlled
  expansion.
- Extend the versioned backlog schema with execution controls.

### TH5: Economic enforcement and learning

- Measure cumulative AI-credit usage through a capability adapter with
  confidence labels.
- Enforce target, warning, and observed pause thresholds.
- Require human disposition after the pause threshold.
- Support optimistic revisioned runtime state, atomic transitions, conflict
  detection, and recovery.
- Track control activation through
  `SPECIFIED -> MANUAL -> INSTRUMENTED -> ENFORCED -> VERIFIED`.
- Report cost, flow, Discovery, quality, scope, and evidence metrics.
- Recalibrate policy defaults only through a human-approved theme report.

## Recommended quality requirements

- Missing usage or verification evidence must block completion unless waived.
- No new model call may begin after an observed pause threshold without human
  authorization.
- Stale packets must be regenerated.
- Locked artefacts must retain their immutability guarantees.
- R3 waivers or downgrades require human authorization and reviewer
  acknowledgement.
- The full test suite is mandatory at theme/release readiness and conditional at
  epic level; story verification is targeted and complete for its declared
  matrix.

## Recommended exclusions

- Do not require an external audit database for the initial release.
- Do not mandate one provider, model, programming language, or architecture.
- Do not make Discovery an autonomous black box.
- Do not require all economic enforcement capabilities in TH3.
- Do not use the provisional 60 percent AIC reduction as a hard first-release
  acceptance criterion.

## Recommended success measures

- Human-approved Discovery and PRD gates exist before architecture begins.
- Consequential requirements retain traceability to outcomes and Discovery
  records.
- TH3 self-hosts with honest control maturity labels.
- Later themes reduce premium-model share and rework without worsening quality,
  safety, or delivered scope.
- Discovery escapes are classified and routed within one review cycle.

