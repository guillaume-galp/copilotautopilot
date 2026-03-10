#!/usr/bin/env bash
# Save session state on session end for resumability
set -euo pipefail

TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
LOG_FILE="docs/plan/session-log.md"

# Ensure the log file directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Count remaining stories
if [ -f docs/plan/backlog.md ]; then
    TODO=$(grep -c 'status: todo' docs/plan/backlog.md 2>/dev/null || echo "0")
    IN_PROGRESS=$(grep -c 'status: in-progress' docs/plan/backlog.md 2>/dev/null || echo "0")
    DONE=$(grep -c 'status: done' docs/plan/backlog.md 2>/dev/null || echo "0")
    FAILED=$(grep -c 'status: failed' docs/plan/backlog.md 2>/dev/null || echo "0")
    echo "### Session ended: ${TIMESTAMP}" >> "$LOG_FILE"
    echo "- Todo: ${TODO} | In-progress: ${IN_PROGRESS} | Done: ${DONE} | Failed: ${FAILED}" >> "$LOG_FILE"
    echo "" >> "$LOG_FILE"
else
    echo "### Session ended: ${TIMESTAMP}" >> "$LOG_FILE"
    echo "- No backlog file found" >> "$LOG_FILE"
    echo "" >> "$LOG_FILE"
fi
