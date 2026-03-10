---
description: "Manually trigger troubleshooting for a failed story, broken build, or test failures. Use when: debugging, fixing errors, story failed, test failures, build broken."
agent: "troubleshooter"
tools: [read, edit, search, execute]
---

Diagnose and fix the specified issue.

## Skills

Load: `the-copilot-build-method`, `bdd-stories`, `code-quality`

## Process

1. Read the failure context (story file, error output, test results, reviewer feedback)
2. Diagnose the root cause — categorize as: `LOGIC_ERROR`, `TEST_ERROR`, `BUILD_ERROR`, `INTEGRATION_ERROR`, or `REQUIREMENT_AMBIGUITY`
3. Apply the minimal fix needed
4. Verify the fix by running tests
5. Report diagnosis, fix details, and confidence level

If the issue can't be resolved after thorough investigation, report `CONFIDENCE: LOW` and recommend specific areas for user intervention.
