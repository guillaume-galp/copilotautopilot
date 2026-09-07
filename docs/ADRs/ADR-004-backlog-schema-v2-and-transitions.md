# ADR-004: Versioned Backlog Schema v2 and Optimistic Revisioned Transitions

## Status

Accepted

## Context

`docs/plan/backlog.yaml` is the authoritative runtime state (DEC-014, EV-004),
but its current schema carries only status, priority, files, and dependencies.
VP3 requires it to also carry risk tier, model route, verification profile,
budgets, aggregate usage, confidence, and evidence references (PR-113), while
detailed packet and attempt traces stay outside it (PR-114).

Locked TH1 and TH2 themes and the archived TH1 snapshot must remain valid
without migration (QR-004, PR-115), and new schemas must apply prospectively
(QR-005).

VP3 also requires optimistic multi-writer safety: expected revisions that reject
stale writers instead of overwriting (PR-208), atomic recoverable transitions
with prepared and committed evidence and reconciliation after partial failure
(PR-209), and deterministic, testable conflict and recovery behavior (QR-016,
INV-008). EXP-003 validated a local prototype covering conflict rejection,
pre-commit safety, and post-replace recovery. DEF-003 leaves the production
command, schema validation, journal compaction, and conflict experience to
architecture.

## Decision

1. Introduce `schema-version: 2` at the backlog root and per theme. Absent
   `schema-version` on a locked or archived theme means version 1 and remains
   valid. New or unlocked themes must use version 2.
2. Schema v2 adds, per story: `risk` (tier, triggers, assigned-by, validated-by,
   overrides), `model-route`, `verification`, `review-profile`, `budgets`,
   `usage`, `evidence`, and `confidence`; and per theme and epic: `budgets` and
   `usage`. The status machine gains `blocked` for pause dispositions and
   Discovery-escape subgraph pauses.
3. The backlog root carries a monotonic `revision` integer. Every writer
   supplies `--expected-revision`; a mismatch is rejected with exit code 3.
4. `bin/method tx apply` is the only supported writer once the control reaches
   `ENFORCED`. Its protocol is:
   1. create `docs/plan/runtime/.tx.lock` with `O_EXCL` (holder pid and
      timestamp; stale after 60 seconds);
   2. verify the expected revision;
   3. apply a closed op vocabulary (`set`, `append`, `increment`) restricted to
      allowed backlog paths;
   4. validate the resulting document against schema v2;
   5. write `.tx.prepare` with ops digest, base hash, target hash, and new
      revision;
   6. write a temporary file, `fsync`, and `os.replace`;
   7. append a `committed` record to `docs/plan/runtime/journal.ndjson`;
   8. remove `.tx.prepare` and release the lock.
5. `method tx recover` classifies an interrupted transition by comparing the
   current file hash with the prepared base and target hashes: base means
   `aborted` with byte-identical state; target means `recovered-commit`;
   neither means exit code 5 and human reconciliation. Recovery runs before any
   further transition.
6. Detailed traces live in `docs/plan/runtime/` (journal, packets, usage), not
   in the backlog. At theme lock they are compacted into
   `docs/plan/backlog-archive/TH<n>-runtime.yaml`, retaining decision,
   threshold, review, CI, release, and usage summaries.
7. Agents propose transitions; the orchestrator or the relevant authority
   commits them. A transition that lacks required evidence is rejected rather
   than committed with gaps.
8. `method doctor` probes exclusive create, atomic replace, and `fsync` before
   the transition control may be promoted beyond `MANUAL`.

## Consequences

### Positive

- Concurrent writers produce exactly one commit and one explicit conflict.
- Interrupted transitions are recoverable and deterministic, matching EXP-003.
- Locked and archived themes need no migration.
- The backlog stays small and reviewable; volume lives in the runtime store.

### Negative

- Every runtime write becomes a command invocation with an expected revision.
- The journal and prepare files add repository churn during a theme.
- Schema v1 and v2 handling must coexist in the validator and in tooling.

### Risks

- Concurrent writers overwrite transitions (RSK-007). Mitigation: lock plus
  expected revision plus atomic replace plus journal recovery.
- Stale lock files block progress. Mitigation: 60-second staleness with holder
  metadata and an explicit takeover recorded in the journal.
- Filesystem without atomic replace semantics (ASM-006 portability).
  Mitigation: `method doctor` refuses promotion beyond `MANUAL`.
- Runtime store growth (AR-005). Mitigation: theme-lock compaction and growth
  measurement under DEF-005.

## Alternatives Considered

### Single-writer orchestrator with no revisions

- Pros: simplest possible model.
- Cons: cannot detect a second session, a hook, or a manual edit; silent
  overwrite is possible.
- Rejected because: DEC-022 and PR-208 require optimistic multi-writer safety.

### Long-held exclusive lock

- Pros: no conflict handling required.
- Cons: a crashed holder blocks all progress; conflicts surface as timeouts.
- Rejected because: recovery and explicit conflicts are required (INV-008).

### SQLite or another transactional store

- Pros: transactions and integrity for free.
- Cons: binary state is unreviewable in diffs and conflicts with the backlog as
  a human-inspectable authority.
- Rejected because: reviewability of runtime state is a method property.

### Git commits as the transaction boundary

- Pros: durable history for free.
- Cons: couples runtime state to branch state and to delivery Gitflow;
  concurrent index use is not safe.
- Rejected because: runtime transitions must work independently of delivery
  branching (ADR-001 separation).
