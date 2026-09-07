# EXP-004: Packet Staleness

| Field | Value |
|---|---|
| Outcome | `VALIDATED` |
| Question | Can an agent packet detect changes to its authoritative sources? |
| Method | Build a composite SHA-256 manifest from VP3 and backlog sources, then mutate VP content in memory. |
| Stop condition | Unchanged sources reproduce the manifest; changed sources do not. |

## Results

- Unchanged inputs reproduced the expected composite hash and were accepted.
- An in-memory source mutation produced a different hash and was classified
  `STALE`.

## Disposition

Generated packets must retain source paths, revisions or hashes, and packet
version. Any referenced authoritative source change requires regeneration.

