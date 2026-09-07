# ADR-007: Usage Capability Adapter, Nested Soft-Cap Budgets, and Calibration

## Status

Accepted

## Context

An observed methodology run consumed roughly 21,000 AIC with almost 90 percent
from a premium reasoning model, and bounded rework counts did not bound the cost
inside each attempt.

EXP-001 observed exact cumulative `session.usage_checkpoint.data.totalNanoAiu`
values in local sessions, but also observed that enforcement happens after a
response, that an existing personal tracker returned zero because of a stale
parser and pricing table, and that the source is local CLI state rather than a
provider-neutral API. EXP-002 confirmed that the CLI supports
`--max-ai-credits` and blocks the next model call after an observed limit, that
session limits include subagents, and that one in-flight response can overshoot.

The PRD requires a usage adapter reporting `measured`, `estimated`, or `unknown`
(PR-201); preference for exact cumulative usage with conservative proxies and
never converting missing telemetry to zero (PR-202, INV-005); target, warning,
and pause budgets across Discovery phases, investigations, stories, reviews and
rework, ceremonies, and orchestrator overhead (PR-203); nested baseline and
delta accounting with native session limits as a final safety net (PR-204);
report, checkpoint, and pause behavior with no new model call or delegation
after the pause threshold without human authorization (PR-205, INV-006); an
overshoot allowance (PR-206); named human dispositions (PR-207); balanced theme
reporting (PR-211, DEC-018); versioned defaults recalibrated only through a
human-approved theme report (PR-212); and bounded traces compacted after theme
lock (PR-214). DEF-001 and DEF-002 delegate adapter selection and overshoot
accounting to architecture.

## Decision

1. `bin/method usage` implements a capability adapter chain:
   1. `copilot-cli-session-checkpoint` reads the local cumulative nano-AIU
      checkpoint and reports `confidence: measured`;
   2. `token-proxy` derives a conservative estimate from local token records and
      a versioned pricing table and reports `confidence: estimated`;
   3. otherwise the sample is `confidence: unknown` with `value: null`.
   A missing or unparsable source is never reported as `0`. Every sample records
   source, timestamp, model mix when available, and limitations.
2. Budget scopes are nested: theme, epic, story, plus Discovery phase,
   investigation, review and rework, ceremony, and orchestrator overhead. Scope
   usage is `close - baseline` over the cumulative measured value, recorded by
   `method budget open/close`. Native `--max-ai-credits` remains configured at
   the session level as the final safety net.
3. Each scope has `target`, `warning`, and `pause` thresholds in
   `docs/plan/policy/budget-policy.yaml`. Behavior is:
   - target crossed: `REPORT`;
   - warning crossed: `CHECKPOINT`, persist state, expose remaining cost, and
     require human authorization for context expansion;
   - pause threshold observed: `PAUSE` with exit code 4. No new model call or
     delegated task begins until a human disposition is recorded.
4. Overshoot is handled by a per-capability-class `overshoot-aic` allowance in
   the model policy. The effective pre-call limit is
   `pause_threshold - overshoot_aic(class)`, so a single in-flight response
   cannot silently cross the pause threshold. Initial allowances (`light` 1,
   `balanced` 5, `reasoning` 15, `critical` 25) are provisional.
5. `method budget check` runs immediately after the last committed transition so
   a pause always leaves recoverable state (INV-006).
6. Human dispositions are a closed set: continue with a revised budget,
   simplify, split, change the model route, reduce verification, waive
   verification, return to Discovery, or abort. Each disposition is recorded
   with actor, timestamp, scope, verdict, rationale, and source revision.
   Verification reduction or waiver at R3 additionally follows ADR-006.
7. `method report theme` produces a balanced scorecard covering planned versus
   actual cost, model mix, flow, Discovery escapes, quality, scope,
   verification, waivers, evidence confidence, orchestrator overhead, and
   artefact growth. Cost figures never appear without their confidence label.
8. Budget and model policy defaults are versioned. Recalibration happens only
   through a human-approved theme report that bumps `policy-version` and records
   the approval. Thresholds start at `0`, meaning unset and report-only, until
   TH5 supplies calibrated values.
9. Usage samples and journal lines are compacted at theme lock into
   `docs/plan/backlog-archive/TH<n>-runtime.yaml`, retaining decision,
   threshold, review, CI, release, and usage summaries.

## Consequences

### Positive

- Cost becomes visible, attributable per scope, and bounded at safe control
  points instead of only at session end.
- Missing telemetry degrades honestly instead of appearing as free work.
- Overshoot is budgeted rather than discovered after the fact.
- Calibration is deliberate, versioned, and human-approved.

### Negative

- Nested accounting depends on disciplined scope open and close calls.
- Provider or CLI changes can break the measured adapter and drop confidence to
  `estimated` or `unknown`.
- Report-only thresholds mean TH5 delivers enforcement machinery before it has
  calibrated numbers.

### Risks

- Telemetry missing, delayed, or incompatible (RSK-005). Mitigation: adapter
  chain, confidence labels, version pinning in the activation ledger, and
  completion blocked unless waived.
- Native soft limits overshoot (RSK-006). Mitigation: class-based overshoot
  allowance and pre-delegation gates.
- Cost targets encourage under-scoping or weak tests (RSK-012, QR-014).
  Mitigation: balanced scorecard, quality gates that cost cannot override, and
  provisional rather than binding reduction targets.
- Provisional allowances are wrong (AR-004). Mitigation: versioned policy and
  calibration only through an approved theme report.

## Alternatives Considered

### Rely only on the native session soft cap

- Pros: zero implementation.
- Cons: no nested attribution, no checkpoint before the cap, and overshoot is
  invisible.
- Rejected because: PR-203 and PR-204 require nested budgets with reporting and
  checkpoint behavior.

### Treat missing telemetry as zero

- Pros: simpler arithmetic and always-green budgets.
- Cons: fabricates compliance.
- Rejected because: INV-005 and PR-202 prohibit it.

### Hard stop mid-response

- Pros: no overshoot at all.
- Cons: not supported by the runtime, and truncation would waste the spend
  already incurred.
- Rejected because: EXP-002 established the soft-cap constraint; an allowance is
  the feasible treatment.

### Automatic budget recalibration from observed usage

- Pros: self-tuning.
- Cons: budgets would drift toward whatever was consumed, removing the control.
- Rejected because: PR-212 requires human-approved recalibration.
