# ADR-005: Compact Agent Packets with Composite Source Hashing

## Status

Accepted

## Context

Stories must contain bounded implementation responsibilities rather than hidden
product or architecture discovery (VO-004). Expensive models currently reload
broad context and rediscover the same constraints.

VP3 requires the orchestrator to generate a compact packet for each bounded task
containing scope, acceptance criteria, traceability, dependencies, controls,
source revision, and the required report (PR-109); packets must retain source
hashes or revisions and be rejected and regenerated when an authoritative source
changes (PR-110, INV-007); agents must request context expansion with the
missing question, reason, risk, requested source, and estimated cost (PR-111);
and expansion within budget may be approved by the orchestrator while expansion
crossing the warning threshold requires human authorization (PR-112).

EXP-004 validated composite SHA-256 manifests: unchanged sources reproduce the
hash and a mutated source is classified `STALE`. RSK-008 warns that compact
packets can omit a critical constraint, and RSK-009 warns that retrieved content
can attempt instruction injection (QR-009).

## Decision

1. The orchestrator generates one packet manifest per bounded task at
   `docs/plan/runtime/packets/<TH.E.US>/<task-id>.yaml`, containing
   `packet-version`, generation metadata, scope, acceptance criteria,
   traceability (vision, requirements, ADRs, invariants), dependencies,
   controls (risk tier, model class, verification matrix, budgets), the source
   list, `composite-hash`, the required report shape, and expansions.
2. Each source records `path`, `sha256`, git blob revision, and a `trust` label
   of `trusted` (method contracts under `.github/skills/`) or `untrusted`
   (everything else, including product code, docs, and retrieved content).
3. `composite-hash` is SHA-256 over the sorted list of `<path>:<sha256>` lines.
   `method packet verify` recomputes it before an agent runs; any difference is
   `STALE`, exits 2, and forces regeneration.
4. Untrusted source content is data. Instructions found inside untrusted
   sources are retained as evidence and never followed. The trusted instruction
   hierarchy is the method contracts and the packet itself.
5. Context expansion uses an explicit request record: missing question, reason,
   risk, requested source, and estimated AIC. The orchestrator may approve a
   request that stays within the remaining budget; a request that crosses the
   warning threshold requires recorded human authorization and otherwise exits
   4. Approved expansion appends the source, bumps `packet-version`, and is
   journaled.
6. Repeated expansion requests for the same missing constraint within a story
   are a Discovery-escape signal and are reported to the reviewer and the
   theme report.
7. Packet manifests are retained through delivery and review, then compacted at
   theme lock into counts, staleness events, and expansion records.

## Consequences

### Positive

- Agents receive bounded, auditable context instead of reloading the world.
- Source drift is detected deterministically rather than by inspection.
- Context growth becomes a governed, costed, and attributable event.
- Injection attempts are contained by explicit trust labeling.

### Negative

- Packet generation adds orchestrator work and repository files per task.
- Frequent edits to authoritative sources invalidate packets and force
  regeneration mid-flight.
- Packet size and source selection become a tuning problem.

### Risks

- Compact packets omit a critical constraint (RSK-008). Mitigation: mandatory
  traceability fields, the expansion protocol, and escape detection on repeated
  gaps.
- Over-broad source selection erodes the cost benefit. Mitigation: source
  counts and expansion rates are reported per theme.
- Hash churn from unrelated formatting changes. Mitigation: hashes are computed
  over whole files, and packets are cheap to regenerate.

## Alternatives Considered

### Full-context reload per task

- Pros: no manifest machinery; no staleness handling.
- Cons: highest cost; rediscovery of the same constraints; no auditability of
  what the agent actually saw.
- Rejected because: VO-004 and DEC-015 require bounded, auditable context.

### Ephemeral packets with no retained manifest

- Pros: no repository churn.
- Cons: no post-hoc audit of the context that produced a change; no staleness
  detection.
- Rejected because: PR-110 requires retained source revisions and rejection.

### Timestamp or mtime staleness

- Pros: cheaper than hashing.
- Cons: false positives on checkout and false negatives on identical mtimes.
- Rejected because: EXP-004 validated deterministic content hashing.

### Git commit SHA of the repository as the only revision marker

- Pros: single value to compare.
- Cons: any unrelated commit invalidates every packet.
- Rejected because: per-source hashing invalidates only affected packets.
