#!/usr/bin/env bash
# Save session state on session end for resumability
set -euo pipefail

TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
LOG_FILE="docs/plan/session-log.md"

# Parse structure rather than indentation; optional children are not delivery jobs.
SNAPSHOT=$(python3 - <<'PY'
from collections import Counter
from pathlib import Path

import yaml

path = Path("docs/plan/backlog.yaml")
if not path.exists():
    print("- No backlog file found")
else:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    backlog = document["backlog"]
    themes = backlog["active-themes"]
    if not isinstance(themes, list):
        raise ValueError("backlog.active-themes must be a list")
    counts = {"Epics": Counter(), "Legacy stories": Counter()}
    statuses = ("todo", "in-progress", "blocked", "failed", "done")
    for theme in themes:
        version = theme.get("schema-version", 1)
        if version not in (1, 2, 3):
            raise ValueError(f"unsupported theme schema-version: {version}")
        for epic in theme["epics"]:
            kind = "Epics" if version == 3 else "Legacy stories"
            units = [epic] if version == 3 else epic["stories"]
            for unit in units:
                status = unit["status"]
                if status not in statuses:
                    raise ValueError(f"unknown delivery status: {status}")
                counts[kind][status] += 1
    for kind, values in counts.items():
        summary = " | ".join(f"{status}: {values[status]}" for status in statuses)
        print(f"- {kind}: {summary}")
PY
)

mkdir -p "$(dirname "$LOG_FILE")"
printf '### Session ended: %s\n%s\n\n' "$TIMESTAMP" "$SNAPSHOT" >> "$LOG_FILE"
