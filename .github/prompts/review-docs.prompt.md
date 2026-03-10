---
description: "Review documentation quality and completeness. Check READMEs, changelogs, ADRs, architecture docs, and story files for accuracy and consistency. Use when: reviewing docs, checking documentation quality, verifying docs are up-to-date."
agent: "reviewer"
tools: [read, search]
---

Perform a documentation quality review.

## Skills

Load: `the-copilot-build-method`, `code-quality`, `bdd-stories`, `architecture-decisions`

## Review Scope

Evaluate documentation across these areas:

### Project Documentation
- `README.md` — accurate, reflects current capabilities
- `CHANGELOG.md` — entries match what was actually implemented
- `docs/architecture/` — reflects actual system design, no stale content

### Architecture & ADRs
- `docs/ADRs/` — all significant decisions recorded, statuses current
- ADRs not contradicted by implementation
- Architecture diagrams match component structure

### Story Documentation
- `docs/themes/` — story files have valid frontmatter (id, status, agents, skills, acceptance-criteria)
- Acceptance criteria match what was implemented
- BDD scenarios are testable and specific
- Epic-level and theme-level READMEs are complete

### Release Documentation
- Epic changelogs present for completed epics
- Theme release notes present for completed themes
- Vision revalidation documented

## Output

Return a documentation health report:
- **Coverage**: What % of expected docs exist?
- **Accuracy**: Do docs match the implementation?
- **Staleness**: Any docs that reference outdated patterns or removed features?
- **Gaps**: Missing documentation that should exist
