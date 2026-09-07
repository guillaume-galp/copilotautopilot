"""Shared process exit codes for every ``method`` subcommand."""

from __future__ import annotations

SUCCESS = 0
USAGE_ERROR = 1
VALIDATION_FAILURE = 2
CONFLICT = 3
PAUSE_OR_BLOCKED = 4
RECOVERY_REQUIRED = 5

ALL = (
    SUCCESS,
    USAGE_ERROR,
    VALIDATION_FAILURE,
    CONFLICT,
    PAUSE_OR_BLOCKED,
    RECOVERY_REQUIRED,
)

__all__ = [
    "SUCCESS",
    "USAGE_ERROR",
    "VALIDATION_FAILURE",
    "CONFLICT",
    "PAUSE_OR_BLOCKED",
    "RECOVERY_REQUIRED",
    "ALL",
]
