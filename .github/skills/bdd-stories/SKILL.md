---
name: bdd-stories
description: 'Hybrid BDD user story conventions: story format, acceptance criteria writing, Given/When/Then scenario patterns, story sizing, edge case coverage, frontmatter schema. Use when: writing user stories, creating BDD scenarios, defining acceptance criteria, parsing story files.'
---

# BDD Stories Skill

## User Story File Format

Every story file lives at `docs/themes/TH<n>-<slug>/epics/E<m>-<slug>/stories/US<l>-<slug>.md`.

### Required Frontmatter

```yaml
---
id: US<l>
title: "<story title>"
status: todo                    # todo | in-progress | done | failed | blocked
agents: [implementer, tester]   # agents assigned to this story
skills: [bdd-stories]           # skills the agents should load
acceptance-criteria:
  - AC1: "<criterion>"
  - AC2: "<criterion>"
depends-on: []                  # story IDs this depends on (e.g., [US1, US2])
---
```

### Story Body Structure

```markdown
# US<l> — <Title>

**As a** <role>, **I want** <goal>, **so that** <benefit>.

## Acceptance Criteria

- [ ] AC1: <criterion>
- [ ] AC2: <criterion>

## BDD Scenarios

### Scenario: <happy path name>
- **Given** <initial context>
- **When** <action taken>
- **Then** <expected outcome>

### Scenario: <edge case name>
- **Given** <context>
- **When** <action>
- **Then** <outcome>

### Scenario: <error case name>
- **Given** <context>
- **When** <action>
- **Then** <error handling outcome>
```

## Writing Good Acceptance Criteria

- Each AC must be **independently verifiable** — a test can prove it passes or fails
- Use concrete values, not vague language: "responds within 200ms" not "responds quickly"
- Include boundary conditions: "accepts passwords 8-128 characters"
- Separate functional from non-functional: AC for behavior, AC for performance/security

## Writing Good BDD Scenarios

### Happy Path (required)
The main success flow. Always write this first.

### Edge Cases (required)
- Boundary values (empty input, max length, zero, negative)
- Concurrent operations
- Missing optional data

### Error Cases (required)
- Invalid input
- Unauthorized access
- Service unavailable / timeout
- Data not found

### Scenario Patterns

**State transition**: Given state A, When event, Then state B
**Data validation**: Given invalid data, When submitted, Then rejection with reason
**Authorization**: Given user role X, When accessing resource, Then allow/deny
**Integration**: Given external service state, When called, Then handle response

## Story Sizing Rules

A story is correctly sized when:
- It can be implemented in a **single agent session** (~1 focused feature)
- It has **2-6 acceptance criteria** (fewer = too vague, more = too large)
- It has **3-8 BDD scenarios** (fewer = untestable, more = split the story)
- It changes **1-5 source files** (more = likely too large)

## Status State Machine

```
todo → in-progress → done
                   → failed → in-progress (troubleshooter fixes) → done
blocked → todo (when dependency resolves)
```
