# EXP-001: Usage Telemetry

| Field | Value |
|---|---|
| Outcome | `VALIDATED_WITH_LIMITATIONS` |
| Question | Can active workflows obtain timely AIC/model usage at control boundaries? |
| Method | Inspect local session event fields and compare them with `aic-tracker` output. |
| Stop condition | Identify a viable measured source plus fallback confidence semantics. |

## Evidence

- `session.usage_checkpoint.data.totalNanoAiu` emitted exact cumulative values.
- Observed consecutive checkpoints from `193.89406` through `240.70862` AIC.
- Checkpoints included cumulative premium-request counts.
- Assistant records identified `gpt-5.5` and `gpt-5.6-sol`.
- Detailed internal model-call records exposed input, output, cache, and reasoning
  token fields.

## Limitations

- Enforcement occurs after a response/checkpoint, not during an in-flight call.
- The existing personal `aic-tracker` returned zero for this session because
  current `assistant.message.outputTokens` values were zero and its pricing
  table did not include `gpt-5.6-sol`.
- Exact cumulative AIC is available, but task-level attribution needs
  baseline/delta accounting.
- The observed source is local CLI state, not a provider-neutral API.

## Disposition

Use a capability adapter that prefers measured cumulative AIC, falls back to a
conservative proxy, and otherwise reports `unknown`. Do not depend on the
current tracker implementation without updating its parser.

