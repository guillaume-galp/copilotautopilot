# EXP-002: Circuit Breaker and Model Routing

| Field | Value |
|---|---|
| Outcome | `VALIDATED_WITH_CONSTRAINTS` |
| Question | Can the method stop new work at a threshold and route model capability by task? |
| Method | Inspect installed CLI help and prototype a pre-delegation usage gate. |
| Stop condition | Identify supported control points or a safe manual fallback. |

## Evidence

- Copilot CLI supports `--max-ai-credits` and interactive `/limits`.
- Session limits include subagents and hidden model work.
- After a limit is observed, the next model call is blocked.
- CLI model selection exists at session and subagent levels; delegated tasks in
  the current runtime accept an explicit model.
- A local pre-delegation comparison against cumulative `totalNanoAiu` correctly
  produced `PAUSE` and `CONTINUE` outcomes at different thresholds.

## Constraint

The native limit is a soft cap. One in-flight response can overshoot before the
CLI observes its cost.

## Disposition

Define the pause contract as:

> Once the pause threshold is observed, no new model call or delegated task may
> begin without human authorization.

Budgets require an overshoot allowance based on the permitted model class and
task size. Native session limits provide a final safety net; nested item budgets
use orchestrator baseline/delta accounting.

