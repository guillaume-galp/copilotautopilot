---
name: autopilot
description: 'Run orchestrator to execute backlog in dependency order with recovery and progress reporting.'
---

# Autopilot Skill

## Agents & Skills

- `@orchestrator`: `the-copilot-build-method`, `backlog-management`, `gitflow-operator`
- `@developer`: `the-copilot-build-method`, `bdd-stories`, `gitflow-operator`
- `@reviewer`: `the-copilot-build-method`, `code-quality`
- `@troubleshooter`: `the-copilot-build-method`, `bdd-stories`, `code-quality`, `gitflow-operator`
- `@product-owner`: `the-copilot-build-method`, `bdd-stories`, `backlog-management`

## Pre-flight

First select the delivery lane from `the-copilot-build-method`. For new
unadmitted Direct/Managed work, use `method lane assess` and `start`, retain
the returned revision, then `preflight` before implementation/resumption.
Use one owner with the compact scope/acceptance/check brief; do not invoke
Vision, Discovery, PRD or planning merely to satisfy a packet requirement.
The checks below and the Mandatory Packet Contract apply to **admitted work
and Governed packet execution**, not to the lighter local route.

Verify:
1. the canonical lifecycle stage order and Autopilot admission gate in
   `the-copilot-build-method` permit execution
2. `method packet project` succeeds before any epic is selected
3. `docs/architecture/` exists
4. recover any epic left `in-progress` per crash-recovery rules
5. if `graphify-out/graph.json` exists and `graphify` is available, pass the
   repository graph path to delegated agents and instruct them to use
   `graphify query "<question>" --graph "$REPO/graphify-out/graph.json"` before
   broad text search for codebase, architecture, and file-relationship questions

## Mandatory Packet Contract

Run `method packet build` for the projected epic with explicit `--task`,
`--epic`, `--mode`, `--implementation-root`,
`--allowed-implementation-root`, and exactly one `--planning-root` naming the
authoritative repository. Retain the `authorization_hash` returned by build
outside the packet.

Before every backlog transition or worker delegation, call `method packet
preflight` with the caller-retained authorization hash and allowed
implementation root. After every backlog status or evidence transition, call
`method packet reconcile` with the prior hash and retain the new returned
hash. Append verification evidence while the epic remains `in-progress`,
reconcile that evidence-only revision, and call `method packet verify` with
the new hash before review. Complete the epic and its optional children in one
authorized revision after all criteria are covered. Advance its theme in a
later parent-only revision while the epic remains `done`, reconcile, and
verify before claiming that parent completion. Never combine epic and theme
completion.

Workers consume only the packet scope, acceptance criteria, sources, workspace
grants, and gates. No agent or adapter may maintain a second queue. Cockpit
owns durable worker delivery/lifecycle only and returns evidence; Autopilot
alone projects backlog eligibility and proposes authoritative transitions.

The default is one bounded epic per agent assignment under the epic-first
schema. Version 1/2 state and story packets retain their legacy protocol;
`--story` is a compatibility selector, never authority to implement siblings.

## Execution

Direct/Managed: the retained owner implements within scope, runs `method lane
check` for every declared targeted/integration check and acceptance criterion,
records real risk-scaled review via `method lane review`, then uses `complete`
for implementation completion only. Failures stay with the owner for bounded
repair; use `pause` for unresolved failures or authority refusal. Use `amend`
to change scope/risk and invalidate old evidence; explicitly `resume` only
when clear and eligible. Governed escalation refuses local execution and
requires human authority plus applicable lifecycle gates and packets.
Never create a second product queue, relabel an admitted item, or claim
release readiness, product acceptance or activation from lane completion.

Run dependency-ordered loop: implement → test → quality assessment per epic.
Retain one owner through local repairs and optional child sequencing. Apply
the canonical risk/profile policy for self-review or native independent
review; no mandatory per-story handoffs or duplicate epic review passes.
Escalate only after bounded repair or when missing expertise/authority blocks
the owner.
Use `gitflow-operator` for branch, commit, merge-request, CI, squash-merge, and
release-note operations at epic scope; do not hand-write ad hoc Gitflow steps.
Report progress after each completed epic and persist resumable blockers.
