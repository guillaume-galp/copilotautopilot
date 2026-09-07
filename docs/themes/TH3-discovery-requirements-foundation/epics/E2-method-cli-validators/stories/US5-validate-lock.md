---
id: TH3.E2.US5
title: "validate lock check"
type: standard
priority: high
size: M
agents: [developer]
skills: [bdd-stories, the-copilot-build-method]
traceability:
  vision: [VO-007]
  requirements: [PR-012, PR-015, QR-003, QR-004]
  adrs: [ADR-008, ADR-003]
  invariants: [INV-003]
acceptance-criteria:
  - AC1: "`method validate lock` builds a manifest of artefacts owned by each locked theme from `backlog.yaml` and the archived theme snapshots `docs/plan/backlog-archive/TH1.yaml` and `docs/plan/backlog-archive/TH2.yaml`."
  - AC2: "A content change to a locked theme directory, story file, or theme backlog snapshot fails closed with exit 2 and names the changed path."
  - AC3: "A locked ADR body change fails; the only permitted edit is changing `Status` to `Superseded by ADR-<NNN>`."
  - AC4: "VP-level artefacts are reported unlocked while any theme mapped to that VP is unaccepted, and locked once all mapped themes are accepted."
  - AC5: "TH1, TH2, ADR-001, `docs/plan/backlog-archive/TH1.yaml`, and `docs/plan/backlog-archive/TH2.yaml` validate as locked and require no migration."
depends-on: [TH3.E2.US2]
---

As a method maintainer, I want lock validation with split scope so that accepted history
stays immutable while a multi-theme VP can still correct its shared basis.

## Acceptance criteria

- [ ] AC1: Locked-artefact manifest built from backlog and the TH1 and TH2 archive snapshots.
- [ ] AC2: Locked theme content changes fail closed.
- [ ] AC3: Locked ADR bodies immutable except supersession status.
- [ ] AC4: VP-level lock deferred until all mapped themes accept.
- [ ] AC5: TH1, TH2, ADR-001, and both archive snapshots validate without migration.

## BDD scenarios

### Happy path: TH3 work does not disturb locked themes

Given TH3 is unlocked and TH1 and TH2 are locked
And `docs/plan/backlog-archive/TH1.yaml` and `docs/plan/backlog-archive/TH2.yaml` are in the manifest
When `method validate lock` runs after TH3 edits
Then the command exits 0
And no TH1 or TH2 artefact or archive snapshot is reported as changed.

### Edge case: shared VP artefact revised while a mapped theme is open

Given VP3 maps to TH3, TH4, and TH5 and only TH3 is accepted
When the VP3 dossier is amended through an append-only DR record
Then the change is permitted
And the VP3 artefacts are reported unlocked with the reason naming the unaccepted themes.

### Error case: edit inside a locked theme

Given a change modifies a TH2 story file
When `method validate lock` runs
Then the command exits 2
And the finding names the file and instructs the author to extend history with a new theme instead.

### Error case: edit inside a locked archive snapshot

Given a change modifies `docs/plan/backlog-archive/TH2.yaml`
When `method validate lock` runs
Then the command exits 2
And the finding names `docs/plan/backlog-archive/TH2.yaml` as an immutable locked-theme snapshot.
