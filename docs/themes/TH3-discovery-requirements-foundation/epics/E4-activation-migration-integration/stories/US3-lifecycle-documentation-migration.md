---
id: TH3.E4.US3
title: "Lifecycle documentation migration to the six-stage lifecycle"
type: standard
priority: high
size: M
agents: [developer]
skills: [bdd-stories, the-copilot-build-method]
traceability:
  vision: [VO-007]
  requirements: [PR-015, QR-006, QR-012]
  adrs: [ADR-002, ADR-003]
  invariants: [INV-002]
acceptance-criteria:
  - AC1: "`README.md` and `.github/copilot-instructions.md` describe the six-stage lifecycle and its five entrypoints and contain no four-stage statement."
  - AC2: "Every active skill under `.github/skills/` and every active agent under `.github/agents/` that names lifecycle stages defers to the stage map owned by `the-copilot-build-method` and restates no stage list of its own."
  - AC3: "`.github/skills/kickstart/SKILL.md` hands off to `discover` instead of `plan`, and the handoff names the Discovery gate that must be accepted before `plan` stage 1 runs."
  - AC4: "Archived and locked content, namely TH1 and TH2 artefacts, `docs/architecture/history/`, `.github/agents/archive/`, and `.github/ISSUE_TEMPLATE/archive/`, is left unchanged and is listed in this story as excluded from migration."
  - AC5: "A migration inventory table in the pull request records every active file inspected and its verdict, migrated or already-consistent, so TH3.E4.US6 has a known expected set."
depends-on: []
---

As a reader of the method, I want the active documentation migrated to one six-stage
lifecycle so that no active document, skill, or agent still describes the superseded
four-stage flow.

This story migrates content only. The `method validate docs` check and its tests are
delivered by TH3.E4.US6.

## Acceptance criteria

- [ ] AC1: Root README and copilot instructions state the six-stage lifecycle.
- [ ] AC2: Active skills and agents defer to the single owned stage map.
- [ ] AC3: `kickstart` hands off to `discover` with the Discovery gate named.
- [ ] AC4: Archived and locked content untouched and listed as excluded.
- [ ] AC5: Migration inventory recorded with a verdict per active file.

## BDD scenarios

### Happy path: active content migrated

Given the active README, copilot instructions, skills, and agents are inspected
When the migration is applied
Then every active file states or defers to the six-stage lifecycle
And the migration inventory lists each file with a migrated or already-consistent verdict.

### Edge case: locked theme keeps its historical text

Given a locked TH2 story file still describes the four-stage lifecycle
When the migration runs
Then the file is left byte-identical
And it is listed in the inventory as excluded locked history.

### Edge case: skill that only references stages indirectly

Given an active skill mentions the lifecycle without enumerating stages
When the migration runs
Then the skill is recorded as already-consistent
And no edit is made to it.

### Error case: an active skill still lists four phases

Given `.github/skills/kickstart/SKILL.md` hands off to `plan` and lists four phases
When the migration runs
Then the four-phase list is replaced by a reference to the owned stage map
And the handoff target becomes `discover` with the Discovery gate named.
