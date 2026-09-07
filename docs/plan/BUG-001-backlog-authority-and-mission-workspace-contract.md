# BUG-001: Backlog Authority and Mission Workspace Contract Do Not Reach the Cockpit

**Status:** Resolved  
**Reported:** 2026-09-07  
**Owner:** CopilotAutopilot  
**Severity:** High  
**Affected components:** Build Method orchestration, backlog runtime contract,
agent mission packets, workspace boundary preflight  
**Related decisions:** ADR-004, ADR-005, ADR-008

## Summary

The Build Method correctly declares `docs/plan/backlog.yaml` to be the source
of truth, but it supplies no executable adapter that projects the next eligible
story into the cockpit FIFO controller. It also does not require a mission
packet to declare authoritative planning roots and writable implementation
roots before a worker starts.

In a UDM VP1/TH1 recovery, the cockpit therefore needed a second independent
queue, while the worker ran in an implementation checkout that could not read
the parent workspace containing the authoritative VP, architecture, theme, and
backlog artifacts. The worker attempted to compensate by copying planning files
into its checkout, which violates the separation between planning authority and
implementation work.

## Resolution

`bin/method packet` now exposes a versioned backlog dispatch and mission
packet surface:

- `method packet project` derives exactly one next dispatchable story from
  `docs/plan/backlog.yaml` and refuses stale, locked, blocked, failed, or
  dependency-ineligible work.
- `method packet build` emits one YAML mission packet under
  `docs/plan/runtime/packets/<TH.E.US>/<task>.yaml` with source backlog
  revision/hash, read-only planning roots, writable implementation root,
  permitted actions, denied paths, required gates, trace ID, and
  Autopilot/Cockpit boundary metadata.
- `method packet verify` rejects stale backlog or source hashes before a
  transition or review claim is accepted.
- `method packet preflight` verifies packet freshness plus planning-root read
  access and implementation-root write access before worker assignment.
- `method packet reconcile` accepts documented lifecycle changes at a strictly
  newer backlog revision, permits only append-only evidence growth, refreshes
  packet source/evidence state, and returns a new external authorization
  anchor.
- Completion reconciliation enforces verification-matrix, review, and Gitflow
  evidence, plus aggregate Definition of Done: all stories before epic
  completion and all epics before theme completion.
- Story authority is validated against the canonical BDD traceability and
  acceptance-criteria contract before a packet is built.

## Symptoms

1. `docs/plan/backlog.yaml` identifies TH1.E2.US6 as the active incomplete
   FIFO item, but cockpit queue state is independent and cannot derive or
   reconcile that status.
2. An overseer must manually duplicate story identity, dependencies, and
   status into `cockpit-queue` items.
3. Worker sessions started from implementation checkouts cannot necessarily
   read the authoritative parent planning workspace, even when an absolute path
   is supplied.
4. A planning-only mission can still lead a worker to stage broad copy commands
   into the implementation checkout.
5. The methodology can say "one developer session = one story" without a
   machine-readable packet that identifies the story, authoritative source,
   writable root, allowed actions, required evidence, and review gate.

## Reproduction

1. Create an active story in an unlocked theme with dependencies in
   `docs/plan/backlog.yaml`.
2. Launch a cockpit worker from a separate implementation checkout.
3. Provide the worker paths to the parent VP, architecture, BDD stories, and
   backlog.
4. Request a planning or review task that requires those artifacts.

Observed behavior:

- the worker's accessible workspace lacks the parent planning paths;
- there is no standard machine-readable mission packet or preflight that
  declares the roots and permitted mutation scope;
- the cockpit cannot prove that its independently queued item matches the
  backlog's earliest eligible story.

## Root Cause

The methodology specifies state ownership and human process gates but does not
publish an interoperable control-plane contract for deriving dispatchable work
from the backlog. The packet/source-hashing model does not currently require
planning and implementation roots, capability grants, or an access preflight as
dispatch prerequisites.

As a result, a cockpit must invent a parallel queue and workers receive prose
paths rather than an enforceable workspace contract. This leaves FIFO ordering,
story scope, state transitions, and artifact access dependent on agent memory
and terminal context.

## Required Fix

1. Define a versioned **Backlog Dispatch Projection** contract that:
   - reads `docs/plan/backlog.yaml` as the sole product-work authority;
   - derives the earliest dependency-eligible story in FIFO order;
   - includes theme lock state, story status, dependencies, risk/review
     requirements, and evidence requirements;
   - never maintains an independently editable product-status queue.
2. Define a versioned **Mission Packet** contract with:
   - immutable story ID and source backlog revision/hash;
   - read-only planning roots;
   - explicit writable implementation root;
   - permitted mutation scope and denied paths;
   - required skills, acceptance criteria, test/review gates, trace ID, and
     expected result locations.
3. Add a mandatory pre-dispatch workspace/capability check. It must fail before
   worker assignment if the worker cannot read required planning artifacts or
   write only to its declared implementation root.
4. Require the orchestrator to reject a transition or review claim unless its
   mission packet still matches the current backlog revision or the change is
   explicitly reconciled.
5. Specify the adapter boundary with CopilotCockpit: Cockpit owns durable
   delivery/lifecycle; Autopilot owns backlog eligibility, packet generation,
   and post-review status proposals.

## Acceptance Criteria

- [x] A tool can project exactly one next eligible story from a valid unlocked
  backlog without hand-maintained duplicate queue state.
- [x] The projection refuses ambiguous, stale, locked, blocked, failed, or
  dependency-ineligible stories with actionable reasons.
- [x] Every dispatchable story produces a validated packet containing source
  backlog revision/hash, planning roots, writable implementation root, scope,
  required gates, and trace ID.
- [x] Dispatch is refused when a worker cannot access all declared read-only
  planning roots or when its writable root is absent/outside allowed scope.
- [x] A planning-only packet cannot authorize source, CI, Docker, DAG, or test
  mutations.
- [x] A developer packet authorizes exactly one story and binds completion to
  required test/review evidence.
- [x] Evidence may be appended during delivery but cannot be removed,
  reordered, or replaced; empty completion evidence fails closed.
- [x] Epic and theme completion is rejected while any child remains
  unfinished.
- [x] The integration boundary allows Cockpit to consume the projection and
  return lifecycle evidence without becoming a second product backlog.

## Regression Coverage

- Unit tests for dependency/FIFO projection, lock handling, stale revision
  detection, and one-story packet generation.
- Integration tests using separate planning and implementation workspaces,
  including inaccessible planning roots and overly broad writable roots.
- Contract tests between the Autopilot projection/packet output and Cockpit
  queue/dispatch input.
- Negative tests proving a worker cannot turn a planning packet into a broad
  checkout-copy or implementation command.

## Scope Boundary

This report does not implement Cockpit's root bootstrap, durable dispatch,
worker acknowledgement, tmux status, or wake lifecycle. Those transport and
control-store concerns are owned by
`~/git/copilotcockpit/docs/plan/BUG-001-control-plane-bootstrap-and-durable-dispatch.md`.
