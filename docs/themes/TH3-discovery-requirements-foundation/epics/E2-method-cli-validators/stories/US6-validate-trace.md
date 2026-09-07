---
id: TH3.E2.US6
title: "validate trace check"
type: standard
priority: medium
size: M
agents: [developer]
skills: [bdd-stories, the-copilot-build-method]
traceability:
  vision: [VO-007]
  requirements: [PR-011, PR-015, QR-002, QR-003, QR-006]
  adrs: [ADR-003, ADR-002]
  invariants: [INV-004]
acceptance-criteria:
  - AC1: "`method validate trace` builds the VP-scoped graph from PRD-owned VO records to DQ to EV, ASM, DEC, INV, RSK and dossier-owned DEF references to PR and QR to ADR to story to evidence, using declared IDs in each prefix's canonical owning file and schema only."
  - AC2: "Every declared ID resolves in the citing VP; a dangling, counterfeit, or cross-VP reference fails closed with exit 2 and names the citing file and record."
  - AC3: "Every consequential record family with schema-defined `Traces` requires a resolving upstream link; legacy accepted requirements derive consequentiality from their content, while a genuinely low-impact detail may use a relevant document reference within the canonical same-VP product roots."
  - AC4: "Once downstream work exists, a consequential record with no downstream link is reported as a finding."
  - AC5: "Story frontmatter `traceability` blocks are authoritative; malformed backlog data, missing required frontmatter, and disagreement between unlocked-theme backlog entries and story-file inventory fail closed without fallback."
  - AC6: "`.github/skills/bdd-stories/SKILL.md` defines the `traceability` frontmatter block as required for `standard` and `spike` stories, naming its keys `vision`, `requirements`, `adrs`, and `invariants`, each a list of record IDs, and states that `trivial` stories may declare an empty list per key."
  - AC7: "The same skill states the allowed ID prefixes per key, `VO-` for vision, `PR-` and `QR-` for requirements, `ADR-` for adrs, and `INV-` for invariants, and gives one worked example block."
  - AC8: "`method validate trace` reads its accepted key set and ID prefixes from the block defined in `bdd-stories`; a story missing the `traceability` block or using an undefined key fails closed with exit 2 naming the story file and the offending key."
  - AC9: "Evidence edges are created only for the five defined evidence keys and resolving contained path references; exact TH3 packet paths are reserved future declarations, not resolved evidence."
depends-on: [TH3.E2.US2]
---

As a reviewer, I want traceability validation so that consequential decisions,
requirements, and stories stay connected instead of drifting apart.

## Acceptance criteria

- [ ] AC1: VP-scoped graph uses canonical owning files and schemas.
- [ ] AC2: Dangling, counterfeit, and cross-VP references fail closed.
- [ ] AC3: Consequential records require upstream links; eligible same-VP
      low-impact document references pass.
- [ ] AC4: Missing downstream links reported once work exists.
- [ ] AC5: Story frontmatter and unlocked-theme inventory fail closed.
- [ ] AC6: `bdd-stories` defines the `traceability` block and its four keys.
- [ ] AC7: Allowed ID prefixes per key documented with a worked example.
- [ ] AC8: Validator pinned to the skill definition; missing or unknown keys fail closed.
- [ ] AC9: Only resolving evidence paths create edges; reserved packets do not.

## BDD scenarios

### Happy path: canonical same-VP records resolve

Given an unlocked theme has a valid backlog inventory
And its PRD owns canonical same-VP Vision outcomes
And its stories declare records from canonical same-VP owners in frontmatter
And completion evidence names resolving contained paths
When `method validate trace` runs
Then each declared ID resolves to an existing record
And the command exits 0.

### Edge case: document-level reference

Given a low-impact formatting detail for the exclusions list cites
`DOC:docs/discovery/VP3-discovery-led-cost-aware-methodology/prd-recommendations.md#recommended-exclusions`
rather than a record ID
When the check runs
Then the reference is accepted as a document-level link
And no consequential traceability failure is reported.

### Error case: counterfeit and cross-VP IDs

Given `VO-999` appears only in a Vision-sketch copy or another VP
When a story declares `VO-999`
Then the command exits 2
And no counterfeit or cross-VP record satisfies the declaration.

### Error case: malformed backlog or unlisted story

Given the active backlog is malformed or an unlocked-theme story file is not
listed
When the check runs
Then the command exits 2
And validation does not fall back to an incomplete story scan.

### Edge case: reserved packet declaration

Given a TH3 story declares its exact future packet directory
And the packet directory does not yet exist
When the check runs
Then no evidence edge is created for that declaration
And other invalid or missing evidence paths remain findings.

### Error case: dangling requirement reference

Given a story frontmatter declares `PR-999`
When the check runs
Then the command exits 2
And the finding names the story file and the unresolved ID.

### Error case: undefined traceability key

Given a standard story declares `traceability.stories` instead of the keys defined in `bdd-stories`
When the check runs
Then the command exits 2
And the finding names the story file, the key `stories`, and the four keys defined by `.github/skills/bdd-stories/SKILL.md`.

### Edge case: trivial story with empty declarations

Given a `trivial` story declares each `traceability` key with an empty list
When the check runs
Then the block is accepted as complete for a trivial story
And no missing-declaration finding is raised.
