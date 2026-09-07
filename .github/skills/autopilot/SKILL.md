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

Verify:
1. the canonical lifecycle stage order and Autopilot admission gate in
   `the-copilot-build-method` permit execution
2. `method packet project` succeeds before any story is selected
3. `docs/architecture/` exists
4. recover any story left `in-progress` per crash-recovery rules
5. if `graphify-out/graph.json` exists and `graphify` is available, pass the
   repository graph path to delegated agents and instruct them to use
   `graphify query "<question>" --graph "$REPO/graphify-out/graph.json"` before
   broad text search for codebase, architecture, and file-relationship questions

## Mandatory Packet Contract

Run `method packet build` for the projected story with explicit `--task`,
`--story`, `--mode`, `--implementation-root`,
`--allowed-implementation-root`, and exactly one `--planning-root` naming the
authoritative repository. Retain the `authorization_hash` returned by build
outside the packet.

Before every backlog transition or worker delegation, call `method packet
preflight` with the caller-retained authorization hash and allowed
implementation root. After every backlog status or evidence transition, call
`method packet reconcile` with the prior hash and retain the new returned
hash. Append verification evidence while the story remains `in-progress`,
reconcile that evidence-only revision, and call `method packet verify` with
the new hash before review. Complete the story in its own revision. Advance an
epic in a later parent-only revision, then advance its theme in another later
parent-only revision. Reconcile each resulting `done → done` story event and
verify before claiming that parent completion. Never combine story, epic, or
theme completion transitions in one revision.

Workers consume only the packet scope, acceptance criteria, sources, workspace
grants, and gates. No agent or adapter may maintain a second queue. Cockpit
owns durable worker delivery/lifecycle only and returns evidence; Autopilot
alone projects backlog eligibility and proposes authoritative transitions.

## Execution

Run dependency-ordered loop: implement → test → review per story.
Use `gitflow-operator` for branch, commit, merge-request, CI, squash-merge, and
release-note operations; do not hand-write ad hoc Gitflow steps.
Report progress after each completed story.
