"""Fail-closed validation of the control activation ledger.

The ledger and its evidence are untrusted repository data.  This module uses
bounded, duplicate-key-safe YAML reads and never executes evidence commands or
imports repository content.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
from dataclasses import dataclass, field as dataclass_field
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Mapping, Sequence

import yaml

from methodlib import backlog as backlog_contract
from methodlib import records, recovery
from methodlib.backlog import UniqueKeyLoader


Finding = dict[str, object]

CHECK = "maturity"
LEDGER_PATH = Path("docs/plan/activation-ledger.yaml")
BACKLOG_PATH = Path("docs/plan/backlog.yaml")
WAIVER_DIRECTORY = Path("docs/plan/waivers")
TH3_USAGE_WAIVER_PATH = WAIVER_DIRECTORY / "TH3-usage-evidence.md"
TH3_RELEASE_PATH = Path("docs/plan/RELEASE-TH3.md")
SESSION_LOG_PATH = Path("docs/plan/session-log.md")
TH3_ARCHIVE_PATH = Path("docs/plan/backlog-archive/TH3.yaml")
MAX_YAML_BYTES = 2 * 1024 * 1024
STATES = ("SPECIFIED", "MANUAL", "INSTRUMENTED", "ENFORCED", "VERIFIED")
STATE_RANK = {state: rank for rank, state in enumerate(STATES)}
REQUIRED_CONTROL_FIELDS = frozenset(
    {
        "id",
        "name",
        "requirements",
        "state",
        "effective-point",
        "limitations",
        "evidence",
        "proposed-by",
        "promoted-by",
    }
)
REQUIRED_CONTROL_IDS = tuple(f"CTL-{number:03d}" for number in range(1, 15))
RECOVERY_CONTROLS: Mapping[str, tuple[str, ...]] = {
    "CTL-001": ("gates",),
    "CTL-002": ("schema",),
    "CTL-003": ("lock", "trace"),
    "CTL-014": ("docs",),
}

# This is an implementation ceiling, not a policy claim.  For enforced
# validators, the separate capability contracts below prove that the CLI still
# exposes the check and that its validator entry point still reaches the
# substantive implementation.  Mere source-file presence is never evidence.
IMPLEMENTATION_SUPPORT: Mapping[str, str] = {
    "CTL-001": "VERIFIED",
    "CTL-002": "VERIFIED",
    "CTL-003": "VERIFIED",
    "CTL-004": "MANUAL",
    **{f"CTL-{number:03d}": "SPECIFIED" for number in range(5, 14)},
    "CTL-014": "ENFORCED",
}
CAPABILITY_CHECKS: Mapping[str, tuple[tuple[str, str], ...]] = {
    "CTL-001": (("gates", "gates"),),
    "CTL-002": (("schema", "backlog"),),
    "CTL-003": (("lock", "lock"), ("trace", "trace")),
    "CTL-014": (("docs", "docs"),),
}
CAPABILITY_FUNCTION_CALLS: Mapping[str, Mapping[str, frozenset[str]]] = {
    "gates": {
        "validate_repository": frozenset(
            {
                "_parse_gate",
                "_parse_architecture_gate",
                "_validate_discovery_gate",
                "_validate_prd_gate",
                "_validate_architecture_gate",
            }
        )
    },
    "backlog": {
        "validate_repository": frozenset({"_validate_repository"}),
        "_validate_repository": frozenset(
            {
                "load_contract",
                "_load_document",
                "SchemaValidator",
                "_validate_archive_index",
                "_validate_story_files",
            }
        ),
    },
    "lock": {
        "validate_repository": frozenset(
            {
                "_themes_from_backlog",
                "_compare",
                "_compare_pinned_file",
                "_vp_mappings_and_paths",
            }
        )
    },
    "trace": {
        "validate_repository": frozenset({"_validate_repository"}),
        "_validate_repository": frozenset(
            {
                "load_contract",
                "_story_sources_from_backlog",
                "_record_nodes",
                "_story_nodes",
                "_evidence_nodes_and_edges",
            }
        ),
    },
    "docs": {
        "validate_repository": frozenset(
            {"active_files", "_read_text", "_scan_text"}
        )
    },
}
EVIDENCE_COMMON_FIELDS = frozenset(
    {"evidence-version", "control-id", "evidence-kind", "observed-at"}
)
RECOVERY_EVIDENCE_FIELDS = EVIDENCE_COMMON_FIELDS | frozenset(
    {
        "validator-check",
        "recovery-case",
        "fixture-path",
        "fixture-sha256",
        "test-reference",
        "test-sha256",
        "runner-path",
        "runner-sha256",
        "source-input-sha256",
        "executed-input-sha256",
        "run-output",
        "run-output-sha256",
        "observed-exit",
    }
)
RECOVERY_OUTPUT_FIELDS = frozenset(
    {
        "run-output-version",
        "runner",
        "control-id",
        "validator-check",
        "recovery-case",
        "evidence-kind",
        "fixture",
        "test",
        "runner-file",
        "source-input-sha256",
        "executed-input-sha256",
        "started-at",
        "completed-at",
        "observed-exit",
        "stderr",
        "result",
    }
)
THEME_EVIDENCE_FIELDS = EVIDENCE_COMMON_FIELDS | frozenset(
    {"theme", "acceptance-record"}
)
CONTROL_ID_PATTERN = re.compile(r"CTL-(?:00[1-9]|0[1-9][0-9]|[1-9][0-9]{2})")
GENERIC_CONTROL_ID_PATTERN = re.compile(r"CTL-\d{3}")
REQUIREMENT_PATTERN = re.compile(r"(?:PR|QR)-(?:00[1-9]|0[1-9][0-9]|[1-9][0-9]{2})")
THEME_PATTERN = re.compile(r"TH[1-9][0-9]*")
STORY_PATTERN = re.compile(r"TH[1-9][0-9]*\.E[1-9][0-9]*\.US[1-9][0-9]*")
HUMAN_ACTOR_PATTERN = re.compile(r"Human:\s+\S.*")
PROMOTION_PATH_PATTERN = re.compile(
    r"docs/plan/control-promotions/"
    r"(?P<record>TH[1-9][0-9]*\.E[1-9][0-9]*\.US[1-9][0-9]*)\.md"
)
PROMOTION_FIELDS = ("Actor", "Timestamp", "Record", "Decision", "Basis", "Limit")
TEST_REFERENCE_PATTERN = re.compile(
    r"(?P<path>tests/(?:[A-Za-z0-9_.-]+/)*test_[A-Za-z0-9_.-]+\.py)"
    r"::(?P<node>test_[A-Za-z0-9_]+)"
)
RECOVERY_RUN_PATTERN = re.compile(r"[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)+")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
PRD_PATH_PATTERN = re.compile(
    r"docs/requirements/(?P<vp>VP[1-9][0-9]*)-[a-z0-9]+"
    r"(?:-[a-z0-9]+)*/PRD\.md"
)
REQUIREMENT_SCHEMAS = frozenset(
    {
        ("ID", "Requirement", "Traces"),
        ("ID", "Requirement"),
        (
            "ID",
            "Schema version",
            "Requirement",
            "Measure",
            "Impact",
            "Impact rationale",
            "Traces",
        ),
    }
)
WAIVER_IDENTITY_FIELDS = (
    "Waiver ID",
    "Control",
    "Theme",
    "Requirement waived",
    "Status",
)
WAIVER_APPROVAL_FIELDS = (
    "Actor",
    "Timestamp",
    "Scope",
    "Verdict",
    "Rationale",
    "Source revision",
    "Expiry",
    "Invalidation",
)
TH3_USAGE_WAIVER_SCOPE = (
    "Missing AI-credit usage evidence for every TH3 story, epic, and theme "
    "gate, for the duration of TH3"
)
TH3_USAGE_WAIVER_EXPIRY = (
    "TH3 acceptance, or earlier if CTL-010 reaches `INSTRUMENTED`"
)
TH3_USAGE_WAIVER_INVALIDATION = (
    "Any of: a usage adapter becomes available and produces `measured` or "
    "`estimated` samples for TH3; the waived scope is extended beyond usage "
    "evidence; TH3 is superseded or re-scoped by a PCR record"
)
TH3_ACCEPTANCE_TIMESTAMP = "2026-09-07T09:22:22.527+01:00"
TH3_ACCEPTANCE_ACTOR = "Human: designer"
TH3_ACCEPTANCE_SOURCE = (
    "backlog revision 67; "
    "sha256:800f69de716dff98a938354128fbd766ee603a5f9b838a1819fef862ef34e6dc"
)
TH3_ACCEPTANCE_RATIONALE = (
    "Explicit human checkpoint acceptance of the completed TH3 release; "
    "WVR-001 is consumed at its contractual expiry, and TH3 usage remains "
    "unknown because no usage instrumentation was available."
)
TH3_ACCEPTANCE_FIELDS = (
    "Actor",
    "Timestamp",
    "Scope",
    "Verdict",
    "Rationale",
    "Source revision",
)
WAIVER_CLOSURE_FIELDS = (
    "Actor",
    "Timestamp",
    "Scope",
    "Verdict",
    "Rationale",
    "Source revision",
)
UNKNOWN_USAGE = {
    "value": None,
    "confidence": "unknown",
    "source": "none",
    "sampled-at": None,
}
WAIVER_ID_PATTERN = re.compile(r"WVR-(?:00[1-9]|0[1-9][0-9]|[1-9][0-9]{2})")
WAIVER_CONTROL_PATTERN = re.compile(
    r"(?P<id>CTL-(?:00[1-9]|0[1-9][0-9]|[1-9][0-9]{2}))(?:\s+\S.*)?"
)
WAIVER_THEME_PATTERN = re.compile(r"(?P<id>TH[1-9][0-9]*)(?:\s+\S.*)?")
FORBIDDEN_USAGE_WAIVER_OBLIGATIONS = (
    "acceptance",
    "quality",
    "verification",
    "review",
    "gitflow",
)


@dataclass(frozen=True)
class ValidationResult:
    findings: tuple[Finding, ...]
    controls: tuple[Mapping[str, object], ...] = ()
    waivers: tuple[Mapping[str, object], ...] = ()
    acceptance_report: Mapping[str, object] | None = None

    @property
    def valid(self) -> bool:
        return not self.findings

    @property
    def payload(self) -> Mapping[str, object]:
        return {
            "command": "validate",
            "check": CHECK,
            "status": "ok" if self.valid else "failed",
            "states": list(STATES),
            "controls": [
                {
                    "id": control.get("id"),
                    "name": control.get("name"),
                    "state": control.get("state"),
                    "effective-point": control.get("effective-point"),
                    "limitations": control.get("limitations"),
                    "evidence": control.get("evidence"),
                }
                for control in self.controls
                if isinstance(control, Mapping)
            ],
            "waivers": [dict(waiver) for waiver in self.waivers],
            "acceptance-report": (
                dict(self.acceptance_report)
                if self.acceptance_report is not None
                else None
            ),
            "findings": list(self.findings),
        }


class LedgerError(ValueError):
    """The ledger or one of its evidence records cannot be read safely."""


class InertYamlLoader(UniqueKeyLoader):
    """Duplicate-safe YAML loader which also rejects aliases."""

    def compose_node(
        self,
        parent: yaml.nodes.Node | None,
        index: object,
    ) -> yaml.nodes.Node:
        if self.check_event(yaml.AliasEvent):
            event = self.peek_event()
            raise yaml.constructor.ConstructorError(
                "while composing inert YAML",
                getattr(event, "start_mark", None),
                "YAML aliases are not allowed",
                getattr(event, "start_mark", None),
            )
        return super().compose_node(parent, index)


@dataclass(frozen=True)
class PromotionRecord:
    actor: str
    timestamp: str
    record: str
    decisions: Mapping[str, str]


@dataclass(frozen=True)
class RepositoryContext:
    requirement_sources: Mapping[str, tuple[str, ...]]
    archived_themes: Mapping[str, tuple[Mapping[str, object], ...]]
    active_themes: tuple[Mapping[str, object], ...] = ()
    archived_theme_payloads: Mapping[str, Mapping[str, object]] = dataclass_field(
        default_factory=dict
    )


def _finding(
    file: str,
    record: str,
    message: str,
    remediation: str,
) -> Finding:
    return {
        "check": CHECK,
        "severity": "error",
        "file": file,
        "record": record,
        "message": message,
        "remediation": remediation,
    }


def _read_yaml(path: Path) -> object:
    try:
        size = path.stat().st_size
    except OSError as error:
        raise LedgerError("file is missing or unreadable") from error
    if size > MAX_YAML_BYTES:
        raise LedgerError(f"file exceeds the {MAX_YAML_BYTES}-byte safety limit")
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise LedgerError("file is unreadable or is not valid UTF-8") from error
    try:
        return yaml.load(text, Loader=InertYamlLoader)
    except (yaml.YAMLError, RecursionError) as error:
        raise LedgerError(
            "file contains malformed YAML, duplicate keys, or aliases"
        ) from error


def _read_json(path: Path) -> object:
    text = _read_text(path)

    def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        value: dict[str, object] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"duplicate JSON key: {key}")
            value[key] = item
        return value

    try:
        return json.loads(text, object_pairs_hook=reject_duplicates)
    except (json.JSONDecodeError, ValueError, RecursionError) as error:
        raise LedgerError(
            "file contains malformed JSON or duplicate keys"
        ) from error


def _read_text(path: Path) -> str:
    try:
        size = path.stat().st_size
    except OSError as error:
        raise LedgerError("file is missing or unreadable") from error
    if size > MAX_YAML_BYTES:
        raise LedgerError(f"file exceeds the {MAX_YAML_BYTES}-byte safety limit")
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise LedgerError("file is unreadable or is not valid UTF-8") from error


def _is_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _valid_timestamp(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _timestamp(value: object) -> datetime | None:
    if not _valid_timestamp(value):
        return None
    assert isinstance(value, str)
    return datetime.fromisoformat(value)


def _sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise LedgerError("file is unreadable") from error


def _test_reference_exists(root: Path, value: object) -> bool:
    if not isinstance(value, str):
        return False
    match = TEST_REFERENCE_PATTERN.fullmatch(value)
    if match is None:
        return False
    path = _safe_file(root, match.group("path"))
    if path is None:
        return False
    try:
        tree = ast.parse(_read_text(path), filename=match.group("path"))
    except (LedgerError, SyntaxError, ValueError):
        return False
    return any(
        isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        and item.name == match.group("node")
        for item in tree.body
    )


def _safe_file(root: Path, value: object) -> Path | None:
    if not _is_text(value):
        return None
    relative = PurePosixPath(str(value))
    if relative.is_absolute() or "." in relative.parts or ".." in relative.parts:
        return None
    candidate = root.joinpath(*relative.parts)
    try:
        root_resolved = root.resolve(strict=True)
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root_resolved)
    except (OSError, RuntimeError, ValueError):
        return None
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return None
    return candidate if candidate.is_file() else None


def _strip_html_comments(text: str) -> str:
    """Hide Markdown comments without allowing nested terminator tricks."""

    output: list[str] = []
    index = 0
    depth = 0
    while index < len(text):
        if text.startswith("<!--", index):
            depth += 1
            output.extend(" " * 4)
            index += 4
            continue
        if depth and text.startswith("-->", index):
            depth -= 1
            output.extend(" " * 3)
            index += 3
            continue
        character = text[index]
        output.append(character if depth == 0 or character == "\n" else " ")
        index += 1
    return "".join(output)


def _visible_markdown_lines(text: str) -> tuple[tuple[str, bool], ...]:
    visible: list[tuple[str, bool]] = []
    active: tuple[str, int] | None = None
    for line in _strip_html_comments(text).splitlines():
        if active is not None:
            character, length = active
            visible.append((line, False))
            if re.fullmatch(rf" {{0,3}}{re.escape(character * length)}[ \t]*", line):
                active = None
            continue
        opening = re.match(r"^ {0,3}(?P<fence>`{3,}|~{3,})", line)
        if opening is not None:
            delimiter = opening.group("fence")
            active = (delimiter[0], len(delimiter))
            visible.append((line, False))
            continue
        visible.append((line, True))
    return tuple(visible)


def _split_markdown_row(line: str) -> list[str] | None:
    stripped = line.strip()
    if not (stripped.startswith("|") and stripped.endswith("|")):
        return None
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for character in stripped[1:-1]:
        if character == "|" and not escaped:
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(character)
        escaped = character == "\\" and not escaped
        if character != "\\":
            escaped = False
    cells.append("".join(current).strip())
    return cells


def _markdown_tables(text: str) -> tuple[list[list[str]], ...]:
    tables: list[list[list[str]]] = []
    current: list[list[str]] = []
    for line, visible in (*_visible_markdown_lines(text), ("", True)):
        row = _split_markdown_row(line) if visible else None
        if row is not None:
            current.append(row)
        elif current:
            tables.append(current)
            current = []
    return tuple(tables)


def _field_table(
    text: str,
    *,
    expected_fields: Sequence[str],
) -> Mapping[str, str] | None:
    candidates = [
        table
        for table in _markdown_tables(text)
        if table and table[0] == ["Field", "Value"]
    ]
    valid: list[dict[str, str]] = []
    for table in candidates:
        if (
            len(table) < 2
            or len(table[1]) != 2
            or any(re.fullmatch(r":?-{3,}:?", cell) is None for cell in table[1])
            or any(len(row) != 2 for row in table[2:])
        ):
            continue
        names = [row[0] for row in table[2:]]
        if tuple(names) != tuple(expected_fields) or len(set(names)) != len(names):
            continue
        valid.append(dict(table[2:]))
    return valid[0] if len(valid) == 1 else None


def _section_text(text: str, heading: str) -> str | None:
    """Return one visible level-two Markdown section, excluding its heading."""

    lines = _visible_markdown_lines(text)
    starts = [
        index
        for index, (line, visible) in enumerate(lines)
        if visible and line.strip() == f"## {heading}"
    ]
    if len(starts) != 1:
        return None
    start = starts[0] + 1
    end = next(
        (
            index
            for index in range(start, len(lines))
            if lines[index][1] and lines[index][0].startswith("## ")
        ),
        len(lines),
    )
    return "\n".join(
        line if visible else "" for line, visible in lines[start:end]
    )


def _single_field_table(text: str) -> tuple[Mapping[str, str] | None, str | None]:
    """Parse one ordinary Field/Value table and retain useful schema errors."""

    candidates = [
        table
        for table in _markdown_tables(text)
        if table and table[0] == ["Field", "Value"]
    ]
    if len(candidates) != 1:
        return None, "must contain exactly one visible Field | Value table"
    table = candidates[0]
    if (
        len(table) < 2
        or len(table[1]) != 2
        or any(re.fullmatch(r":?-{3,}:?", cell) is None for cell in table[1])
        or any(len(row) != 2 for row in table[2:])
    ):
        return None, "contains a malformed Field | Value table"
    names = [row[0] for row in table[2:]]
    if len(set(names)) != len(names):
        return None, "contains duplicate fields"
    return dict(table[2:]), None


def _promotion_decisions(value: str) -> Mapping[str, str] | None:
    sentence = value[:-1] if value.endswith(".") else value
    clauses = sentence.split("; ")
    decisions: dict[str, str] = {}
    for index, clause in enumerate(clauses):
        prefix = "Promote " if index == 0 else "promote "
        if not clause.startswith(prefix):
            return None
        body = clause[len(prefix) :]
        identifiers_text, separator, state = body.rpartition(" to ")
        if not separator or state not in STATES or state == "SPECIFIED":
            return None
        if (
            re.fullmatch(
                r"CTL-\d{3}(?:(?:, CTL-\d{3})*(?:, and | and )CTL-\d{3})?",
                identifiers_text,
            )
            is None
        ):
            return None
        identifiers = GENERIC_CONTROL_ID_PATTERN.findall(identifiers_text)
        if not identifiers or any(
            CONTROL_ID_PATTERN.fullmatch(identifier) is None
            for identifier in identifiers
        ) or any(
            identifier in decisions for identifier in identifiers
        ):
            return None
        decisions.update({identifier: state for identifier in identifiers})
    return decisions


def _parse_promotion_record(
    root: Path,
    reference: str,
) -> tuple[PromotionRecord | None, str | None]:
    identity = PROMOTION_PATH_PATTERN.fullmatch(reference)
    if identity is None:
        return None, "reference is not a canonical control-promotion record path"
    path = _safe_file(root, reference)
    if path is None:
        return None, "record is missing, unsafe, or not a regular repository file"
    try:
        text = _read_text(path)
    except LedgerError as error:
        return None, str(error)
    visible_content = [
        line.strip()
        for line, visible in _visible_markdown_lines(text)
        if visible and line.strip()
    ]
    expected_title = f"# {identity.group('record')} control promotion record"
    if not visible_content or visible_content[0] != expected_title:
        return None, "title does not identify the record named by its path"
    fields = _field_table(text, expected_fields=PROMOTION_FIELDS)
    if fields is None:
        return None, "record must contain one exact canonical Field | Value table"
    if fields["Record"] != identity.group("record"):
        return None, "Record field does not identify the record named by its path"
    if HUMAN_ACTOR_PATTERN.fullmatch(fields["Actor"]) is None:
        return None, "Actor field does not identify a human"
    if not _valid_timestamp(fields["Timestamp"]):
        return None, "Timestamp field is not an offset-aware ISO-8601 value"
    noncanonical_identifiers = sorted(
        {
            identifier
            for identifier in GENERIC_CONTROL_ID_PATTERN.findall(fields["Decision"])
            if CONTROL_ID_PATTERN.fullmatch(identifier) is None
        }
    )
    if noncanonical_identifiers:
        return (
            None,
            "Decision field contains noncanonical control "
            f"{'identifier' if len(noncanonical_identifiers) == 1 else 'identifiers'}: "
            f"{', '.join(noncanonical_identifiers)}",
        )
    decisions = _promotion_decisions(fields["Decision"])
    if decisions is None:
        return None, "Decision field does not use the canonical promotion grammar"
    if not fields["Basis"] or not fields["Limit"]:
        return None, "Basis and Limit must be non-empty"
    return (
        PromotionRecord(
            actor=fields["Actor"],
            timestamp=fields["Timestamp"],
            record=fields["Record"],
            decisions=decisions,
        ),
        None,
    )


def _validate_string_list(
    control: Mapping[str, object],
    key: str,
    *,
    file: str,
    record: str,
    findings: list[Finding],
    allow_empty: bool,
) -> list[str]:
    value = control.get(key)
    if (
        not isinstance(value, list)
        or (not allow_empty and not value)
        or any(not _is_text(item) for item in value)
    ):
        qualifier = "possibly empty " if allow_empty else "non-empty "
        findings.append(
            _finding(
                file,
                record,
                f"{record} field {key!r} must be a {qualifier}list of strings",
                f"Set {key} to the ledger contract's YAML sequence form.",
            )
        )
        return []
    return [str(item) for item in value]


def _validate_promoter(
    control: Mapping[str, object],
    *,
    file: str,
    record: str,
    state: str,
    findings: list[Finding],
) -> None:
    promoter = control.get("promoted-by")
    if state == "SPECIFIED":
        if promoter is not None:
            findings.append(
                _finding(
                    file,
                    record,
                    f"{record} at SPECIFIED must not claim a promotion record",
                    "Set promoted-by to null until a human promotes the control.",
                )
            )
        return
    if not isinstance(promoter, dict):
        findings.append(
            _finding(
                file,
                record,
                f"{record} state {state} requires a human promotion record "
                "with actor, timestamp, and record",
                "Record promoted-by.actor, promoted-by.timestamp, and "
                "promoted-by.record.",
            )
        )
        return
    expected = {"actor", "timestamp", "record"}
    missing = sorted(expected - set(promoter))
    unknown = sorted(set(promoter) - expected)
    if missing or unknown:
        details = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if unknown:
            details.append("unknown " + ", ".join(unknown))
        findings.append(
            _finding(
                file,
                record,
                f"{record} promotion record is invalid: {'; '.join(details)}",
                "Use exactly actor, timestamp, and record in promoted-by.",
            )
        )
    actor = promoter.get("actor")
    if not isinstance(actor, str) or not HUMAN_ACTOR_PATTERN.fullmatch(actor):
        findings.append(
            _finding(
                file,
                record,
                f"{record} promotion actor must identify a human as 'Human: <role>'",
                "Have an accountable human record the promotion actor.",
            )
        )
    if not _valid_timestamp(promoter.get("timestamp")):
        findings.append(
            _finding(
                file,
                record,
                f"{record} promotion timestamp must be an ISO-8601 value "
                "with a timezone",
                "Record the human promotion time including its UTC offset.",
            )
        )
    if not _is_text(promoter.get("record")):
        findings.append(
            _finding(
                file,
                record,
                f"{record} promotion must name its human record reference",
                "Set promoted-by.record to the retained promotion record.",
            )
        )


def _validate_promotion_records(
    root: Path,
    controls: Sequence[Mapping[str, object]],
    findings: list[Finding],
) -> None:
    groups: dict[str, list[Mapping[str, object]]] = {}
    for control in controls:
        if control.get("state") == "SPECIFIED":
            continue
        promoter = control.get("promoted-by")
        if not isinstance(promoter, dict) or not _is_text(promoter.get("record")):
            continue
        groups.setdefault(str(promoter["record"]), []).append(control)

    for reference, promoted_controls in sorted(groups.items()):
        parsed, error = _parse_promotion_record(root, reference)
        if parsed is None:
            for control in promoted_controls:
                control_id = str(control.get("id", "control"))
                findings.append(
                    _finding(
                        reference,
                        control_id,
                        f"{control_id} promotion record cannot be resolved "
                        f"safely: {error}",
                        "Restore the canonical bounded promotion record and "
                        "make its identity and decision match the ledger.",
                    )
                )
            continue

        for control in promoted_controls:
            control_id = str(control.get("id", "control"))
            promoter = control.get("promoted-by")
            assert isinstance(promoter, dict)
            mismatches: list[str] = []
            if promoter.get("actor") != parsed.actor:
                mismatches.append("actor")
            if promoter.get("timestamp") != parsed.timestamp:
                mismatches.append("timestamp")
            if parsed.decisions.get(control_id) != control.get("state"):
                mismatches.append("control/target-state decision")
            if mismatches:
                findings.append(
                    _finding(
                        reference,
                        control_id,
                        f"{control_id} promotion record does not match ledger "
                        f"{', '.join(mismatches)}",
                        "Make the record actor, timestamp, complete decision "
                        "set, control IDs, and target states exactly match the "
                        "ledger entries that cite it.",
                    )
                )


def _attribute_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _attribute_name(node.value)
        return f"{prefix}.{node.attr}" if prefix is not None else None
    return None


def _function_node(
    tree: ast.Module,
    name: str,
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    return next(
        (
            node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == name
        ),
        None,
    )


def _called_names(node: ast.AST) -> set[str]:
    return {
        name
        for item in ast.walk(node)
        if isinstance(item, ast.Call)
        and (name := _attribute_name(item.func)) is not None
    }


def _referenced_names(node: ast.AST) -> set[str]:
    return {
        name for item in ast.walk(node) if (name := _attribute_name(item)) is not None
    }


def _python_tree(root: Path, relative: str) -> ast.Module | None:
    path = _safe_file(root, relative)
    if path is None:
        return None
    try:
        return ast.parse(_read_text(path), filename=relative)
    except (LedgerError, SyntaxError, ValueError):
        return None


def _literal_string_sequence(tree: ast.Module, name: str) -> tuple[str, ...] | None:
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(
            isinstance(target, ast.Name) and target.id == name for target in targets
        ):
            continue
        try:
            value = ast.literal_eval(node.value)
        except (ValueError, TypeError):
            return None
        if isinstance(value, (tuple, list)) and all(
            isinstance(item, str) for item in value
        ):
            return tuple(value)
        return None
    return None


def _check_branch(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
    check: str,
) -> ast.If | None:
    for node in ast.walk(function):
        if not isinstance(node, ast.If) or not isinstance(node.test, ast.Compare):
            continue
        comparison = node.test
        if (
            isinstance(comparison.left, ast.Name)
            and comparison.left.id == "check"
            and len(comparison.ops) == 1
            and isinstance(comparison.ops[0], ast.Eq)
            and len(comparison.comparators) == 1
            and isinstance(comparison.comparators[0], ast.Constant)
            and comparison.comparators[0].value == check
        ):
            return node
    return None


def _cli_capability_available(root: Path, check: str, module: str) -> bool:
    entrypoint = _python_tree(root, "bin/method")
    cli_tree = _python_tree(root, "methodlib/cli.py")
    if entrypoint is None or cli_tree is None:
        return False
    entrypoint_imports_main = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "methodlib.cli"
        and any(alias.name == "main" for alias in node.names)
        for node in entrypoint.body
    )
    if not entrypoint_imports_main or "main" not in _called_names(entrypoint):
        return False
    checks = _literal_string_sequence(cli_tree, "VALIDATE_CHECKS")
    command = _function_node(cli_tree, "_validate_command")
    if checks is None or check not in checks or command is None:
        return False
    imported_modules = {
        alias.name
        for node in cli_tree.body
        if isinstance(node, ast.ImportFrom) and node.module == "methodlib"
        for alias in node.names
    }
    branch = _check_branch(command, check)
    if module not in imported_modules or branch is None:
        return False
    calls = _called_names(branch)
    names = _referenced_names(branch)
    return (
        f"{module}.validate_repository" in calls
        and "result.valid" in names
        and "exits.VALIDATION_FAILURE" in names
    )


def _module_capability_available(root: Path, module: str) -> bool:
    tree = _python_tree(root, f"methodlib/{module}.py")
    contracts = CAPABILITY_FUNCTION_CALLS.get(module)
    if tree is None or contracts is None:
        return False
    for function_name, required_calls in contracts.items():
        function = _function_node(tree, function_name)
        if function is None:
            return False
        calls = _called_names(function)
        if not required_calls <= calls:
            return False
    return True


def _validate_repository_support(
    root: Path,
    control_id: str,
    state: str,
    findings: list[Finding],
) -> None:
    maximum = IMPLEMENTATION_SUPPORT.get(control_id)
    if maximum is None:
        return
    if STATE_RANK[state] > STATE_RANK[maximum]:
        findings.append(
            _finding(
                str(LEDGER_PATH),
                control_id,
                f"{control_id} state {state} contradicts repository "
                f"implementation; repository supports at most {maximum}",
                "Lower the claim to implemented reality or implement and "
                "evidence the control before human promotion.",
            )
        )
        return
    if STATE_RANK[state] < STATE_RANK["ENFORCED"]:
        return
    unavailable = [
        check
        for check, module in CAPABILITY_CHECKS.get(control_id, ())
        if not (
            _cli_capability_available(root, check, module)
            and _module_capability_available(root, module)
        )
    ]
    if unavailable:
        findings.append(
            _finding(
                str(LEDGER_PATH),
                control_id,
                f"{control_id} state {state} contradicts repository "
                "implementation; CLI capability contracts are unavailable "
                f"for {', '.join(unavailable)}",
                "Restore each method validate CLI route and its substantive "
                "validator entry point, or lower the maturity claim.",
            )
        )


def _load_evidence(
    root: Path,
    control_id: str,
    paths: list[str],
    findings: list[Finding],
) -> list[tuple[str, Mapping[str, object]]]:
    loaded: list[tuple[str, Mapping[str, object]]] = []
    for evidence_path in paths:
        path = _safe_file(root, evidence_path)
        if path is None:
            findings.append(
                _finding(
                    str(LEDGER_PATH),
                    control_id,
                    f"{control_id} evidence path {evidence_path!r} is missing, "
                    "unsafe, or not a regular repository file",
                    "Retain the evidence at a repository-relative, non-symlink path.",
                )
            )
            continue
        if path.suffix not in {".yaml", ".yml"}:
            continue
        try:
            document = _read_yaml(path)
        except LedgerError as error:
            findings.append(
                _finding(
                    evidence_path,
                    control_id,
                    f"{control_id} evidence record is invalid: {error}",
                    "Restore a bounded, duplicate-key-free YAML evidence record.",
                )
            )
            continue
        if isinstance(document, dict) and "evidence-kind" in document:
            loaded.append((evidence_path, document))
    return loaded


def _validate_recovery_evidence(
    root: Path,
    control_id: str,
    state: str,
    promotion_timestamp: object,
    evidence: list[tuple[str, Mapping[str, object]]],
    dependency_files: Sequence[str] | None,
    findings: list[Finding],
) -> None:
    if STATE_RANK[state] < STATE_RANK["ENFORCED"]:
        return
    expected_checks = RECOVERY_CONTROLS.get(control_id)
    if not expected_checks:
        expected_checks = ("control",)
    valid: dict[tuple[str, str], dict[str, datetime]] = {}
    for path, record in evidence:
        kind = record.get("evidence-kind")
        if kind not in {"bypass-attempt", "restore-and-pass"}:
            continue
        if set(record) != RECOVERY_EVIDENCE_FIELDS:
            findings.append(
                _finding(
                    path,
                    control_id,
                    f"{control_id} {kind} evidence must contain exactly "
                    f"{', '.join(sorted(RECOVERY_EVIDENCE_FIELDS))}",
                    "Restore the complete recovery evidence record.",
                )
            )
            continue
        expected_exit = 2 if kind == "bypass-attempt" else 0
        values_valid = True
        if record.get("evidence-version") != 2:
            values_valid = False
        if record.get("control-id") != control_id:
            values_valid = False
        if record.get("observed-exit") != expected_exit:
            values_valid = False
        observed_time = _timestamp(record.get("observed-at"))
        if observed_time is None:
            values_valid = False
        check = record.get("validator-check")
        case = record.get("recovery-case")
        test_reference = record.get("test-reference")
        if (
            not _is_text(check)
            or not _is_text(case)
            or not _is_text(test_reference)
        ):
            values_valid = False
        if not isinstance(case, str) or RECOVERY_RUN_PATTERN.fullmatch(case) is None:
            values_valid = False
        if not _test_reference_exists(root, test_reference):
            values_valid = False
        expected_case = (
            recovery.CASE_BY_KEY.get((control_id, str(check)))
            if isinstance(check, str)
            else None
        )
        if (
            expected_case is None
            or case != expected_case.recovery_case
            or record.get("fixture-path") != recovery.FIXTURE_PATH
            or record.get("test-reference") != recovery.TEST_REFERENCE
            or record.get("runner-path") != recovery.RUNNER_PATH
        ):
            values_valid = False

        digest_paths = {
            "fixture-sha256": record.get("fixture-path"),
            "test-sha256": (
                str(test_reference).split("::", 1)[0]
                if isinstance(test_reference, str)
                else None
            ),
            "runner-sha256": record.get("runner-path"),
            "run-output-sha256": record.get("run-output"),
        }
        resolved: dict[str, Path] = {}
        for digest_field, relative in digest_paths.items():
            digest = record.get(digest_field)
            candidate = _safe_file(root, relative)
            if (
                SHA256_PATTERN.fullmatch(str(digest)) is None
                or candidate is None
            ):
                values_valid = False
                continue
            resolved[digest_field] = candidate
            try:
                if _sha256(candidate) != digest:
                    values_valid = False
            except LedgerError:
                values_valid = False

        for field in ("source-input-sha256", "executed-input-sha256"):
            if SHA256_PATTERN.fullmatch(str(record.get(field))) is None:
                values_valid = False
        if expected_case is not None:
            try:
                expected_source = recovery.input_digest(
                    root,
                    expected_case,
                    "restore-and-pass",
                    dependency_files=dependency_files,
                )
                expected_executed = recovery.input_digest(
                    root,
                    expected_case,
                    str(kind),
                    dependency_files=dependency_files,
                )
            except (AssertionError, OSError, ValueError):
                values_valid = False
            else:
                if record.get("source-input-sha256") != expected_source:
                    values_valid = False
                if record.get("executed-input-sha256") != expected_executed:
                    values_valid = False

        output: object = None
        output_path = resolved.get("run-output-sha256")
        if output_path is not None:
            try:
                output = _read_json(output_path)
            except LedgerError:
                values_valid = False
        if not isinstance(output, dict) or set(output) != RECOVERY_OUTPUT_FIELDS:
            values_valid = False
        else:
            fixture = output.get("fixture")
            test = output.get("test")
            runner_file = output.get("runner-file")
            result = output.get("result")
            if (
                output.get("run-output-version") != 1
                or output.get("runner") != "method-recovery-v1"
                or output.get("control-id") != control_id
                or output.get("validator-check") != check
                or output.get("recovery-case") != case
                or output.get("evidence-kind") != kind
                or output.get("source-input-sha256")
                != record.get("source-input-sha256")
                or output.get("executed-input-sha256")
                != record.get("executed-input-sha256")
                or output.get("observed-exit") != expected_exit
                or output.get("completed-at") != record.get("observed-at")
                or not isinstance(output.get("stderr"), str)
                or not isinstance(fixture, dict)
                or set(fixture) != {"path", "sha256"}
                or fixture.get("path") != record.get("fixture-path")
                or fixture.get("sha256") != record.get("fixture-sha256")
                or not isinstance(test, dict)
                or set(test) != {"reference", "sha256"}
                or test.get("reference") != record.get("test-reference")
                or test.get("sha256") != record.get("test-sha256")
                or not isinstance(runner_file, dict)
                or set(runner_file) != {"path", "sha256"}
                or runner_file.get("path") != record.get("runner-path")
                or runner_file.get("sha256") != record.get("runner-sha256")
                or not isinstance(result, dict)
                or result.get("check") != check
                or result.get("status")
                != ("failed" if kind == "bypass-attempt" else "ok")
                or not isinstance(result.get("findings"), list)
                or (
                    kind == "bypass-attempt"
                    and not result.get("findings")
                )
                or (
                    kind == "restore-and-pass"
                    and bool(result.get("findings"))
                )
            ):
                values_valid = False
            started_time = _timestamp(output.get("started-at"))
            completed_time = _timestamp(output.get("completed-at"))
            if (
                started_time is None
                or completed_time is None
                or started_time > completed_time
            ):
                values_valid = False
            if completed_time is not None:
                observed_time = completed_time

        if not values_valid:
            findings.append(
                _finding(
                    path,
                    control_id,
                    f"{control_id} {kind} evidence has contradictory, stale, "
                    "unrelated, or incomplete recovery facts",
                    "Regenerate the evidence with the closed local runner so "
                    "its current input, fixture, test, runner, output, "
                    f"timestamp, and observed exit {expected_exit} all match.",
                )
            )
            continue
        assert isinstance(check, str)
        assert isinstance(case, str)
        assert observed_time is not None
        valid.setdefault((control_id, check), {})[str(kind)] = observed_time

    for validator_check in expected_checks:
        pair = valid.get((control_id, validator_check), {})
        has_bypass = "bypass-attempt" in pair
        has_restore = "restore-and-pass" in pair
        missing = []
        if not has_bypass:
            missing.append("bypass-attempt")
        if not has_restore:
            missing.append("restore-and-pass")
        if missing:
            findings.append(
                _finding(
                    str(LEDGER_PATH),
                    control_id,
                    f"{control_id} state {state} is missing "
                    f"{' and '.join(missing)} evidence for {validator_check}",
                    "Retain a matched corrupt-then-restore run: exit 2 for the "
                    "bypass attempt and exit 0 after restoring the same fixture.",
                )
            )
        elif pair["bypass-attempt"] >= pair["restore-and-pass"]:
            findings.append(
                _finding(
                    str(LEDGER_PATH),
                    control_id,
                    f"{control_id} state {state} recovery evidence for "
                    f"{validator_check} does not record corruption before restore",
                    "Rerun the closed case in corrupt-then-restore order before "
                    "the human promotion.",
                )
            )


def _prd_identity(text: str) -> Mapping[str, str] | None:
    prefix: list[str] = []
    for line, visible in _visible_markdown_lines(text):
        if visible and line.startswith("## "):
            break
        if visible:
            prefix.append(line)
    candidates = [
        table
        for table in _markdown_tables("\n".join(prefix))
        if table
        and table[0] == ["Field", "Value"]
        and len(table) >= 2
        and len(table[1]) == 2
        and all(re.fullmatch(r":?-{3,}:?", cell) is not None for cell in table[1])
        and all(len(row) == 2 for row in table[2:])
    ]
    if len(candidates) != 1:
        return None
    names = [row[0] for row in candidates[0][2:]]
    if len(set(names)) != len(names):
        return None
    return dict(candidates[0][2:])


def _requirement_in_canonical_section(
    text: str,
    record: records.Record,
) -> bool:
    owner: str | None = None
    for number, (line, visible) in enumerate(_visible_markdown_lines(text), start=1):
        if number >= record.line:
            break
        if visible and re.fullmatch(r"##\s+\S(?:.*\S)?", line):
            owner = line[3:].strip().lower()
    if owner is None:
        return False
    if record.prefix == "PR":
        return owner.endswith("functional requirements")
    if record.prefix == "QR":
        return owner.endswith("quality requirements")
    return False


def _canonical_repository_context(
    root: Path,
    findings: list[Finding],
) -> RepositoryContext:
    path = _safe_file(root, BACKLOG_PATH.as_posix())
    if path is None:
        findings.append(
            _finding(
                BACKLOG_PATH.as_posix(),
                "backlog",
                "canonical backlog is missing, unsafe, or unreadable",
                "Restore the canonical duplicate-free backlog before "
                "validating maturity.",
            )
        )
        return RepositoryContext({}, {})
    try:
        document = _read_yaml(path)
    except LedgerError as error:
        findings.append(
            _finding(
                BACKLOG_PATH.as_posix(),
                "backlog",
                f"canonical backlog is invalid: {error}",
                "Restore the canonical duplicate-free backlog before "
                "validating maturity.",
            )
        )
        return RepositoryContext({}, {})
    if (
        not isinstance(document, dict)
        or set(document) != {"backlog"}
        or not isinstance(document.get("backlog"), dict)
    ):
        findings.append(
            _finding(
                BACKLOG_PATH.as_posix(),
                "backlog",
                "canonical backlog must have exactly one backlog mapping",
                "Restore the canonical backlog document root.",
            )
        )
        return RepositoryContext({}, {})
    backlog = document["backlog"]
    active = backlog.get("active-themes")
    archived = backlog.get("archived-themes")
    if (
        backlog.get("schema-version") != 2
        or not isinstance(active, list)
        or not isinstance(archived, list)
    ):
        findings.append(
            _finding(
                BACKLOG_PATH.as_posix(),
                "backlog",
                "canonical backlog requires schema-version 2 and active and "
                "archived theme sequences",
                "Restore the canonical version 2 backlog collections.",
            )
        )
        return RepositoryContext({}, {})

    archived_themes: dict[str, list[Mapping[str, object]]] = {}
    archived_payloads: dict[str, Mapping[str, object]] = {}
    for summary in archived:
        if not isinstance(summary, dict):
            continue
        theme_id = str(summary.get("id", ""))
        archive_ref = summary.get("archive-ref")
        if THEME_PATTERN.fullmatch(theme_id) is None:
            continue
        archived_themes.setdefault(theme_id, []).append(summary)
        archive_path = _safe_file(root, archive_ref)
        if archive_path is None:
            continue
        try:
            snapshot = _read_yaml(archive_path)
        except LedgerError:
            continue
        if (
            isinstance(snapshot, dict)
            and set(snapshot) == {"theme"}
            and isinstance(snapshot.get("theme"), dict)
            and snapshot["theme"].get("id") == theme_id
            and snapshot["theme"].get("schema-version") == 2
        ):
            archived_payloads[theme_id] = snapshot["theme"]

    prd_paths: set[str] = set()
    theme_sources = [
        *(
            (f"active-themes[{index}]", theme)
            for index, theme in enumerate(active)
        ),
        *(
            (f"archived-themes[{theme_id}]", theme)
            for theme_id, theme in sorted(archived_payloads.items())
        ),
    ]
    for location, theme in theme_sources:
        if not isinstance(theme, dict):
            findings.append(
                _finding(
                    BACKLOG_PATH.as_posix(),
                    location,
                    "theme is not a mapping",
                    "Restore the canonical theme record.",
                )
            )
            continue
        theme_id = str(theme.get("id", ""))
        requirement_path = theme.get("requirements-ref")
        vision_path = theme.get("vision-ref")
        match = (
            PRD_PATH_PATTERN.fullmatch(requirement_path)
            if isinstance(requirement_path, str)
            else None
        )
        if (
            THEME_PATTERN.fullmatch(theme_id) is None
            or match is None
            or not isinstance(vision_path, str)
            or f"/{match.group('vp')}-" not in vision_path
            or _safe_file(root, requirement_path) is None
        ):
            findings.append(
                _finding(
                    BACKLOG_PATH.as_posix(),
                    theme_id or location,
                    "theme does not resolve one applicable canonical PRD",
                    "Restore its same-VP docs/requirements/VP<n>-<slug>/PRD.md "
                    "requirements-ref.",
                )
            )
            continue
        prd_paths.add(str(requirement_path))

    requirement_sources: dict[str, list[str]] = {}
    for relative in sorted(prd_paths):
        match = PRD_PATH_PATTERN.fullmatch(relative)
        path = _safe_file(root, relative)
        assert match is not None and path is not None
        try:
            text = _read_text(path)
        except LedgerError as error:
            findings.append(
                _finding(
                    relative,
                    "PRD",
                    f"applicable canonical PRD is invalid: {error}",
                    "Restore the bounded UTF-8 canonical PRD.",
                )
            )
            continue
        identity = _prd_identity(text)
        vision = identity.get("Vision", "") if identity is not None else ""
        if (
            identity is None
            or identity.get("Status") != "Approved"
            or re.match(
                rf"{re.escape(match.group('vp'))}(?:\b|:)",
                vision,
            )
            is None
        ):
            findings.append(
                _finding(
                    relative,
                    "PRD",
                    "applicable canonical PRD identity is missing, unapproved, "
                    "or belongs to another VP",
                    "Restore the approved PRD identity matching its backlog VP.",
                )
            )
            continue
        parsed = records.parse_markdown(text, file=relative, path=path)
        if parsed.findings:
            findings.append(
                _finding(
                    relative,
                    "PRD",
                    "applicable canonical PRD contains malformed record tables",
                    "Restore canonical, structurally valid requirement tables.",
                )
            )
            continue
        for record in parsed.records:
            if record.prefix not in {"PR", "QR"}:
                continue
            if tuple(
                record.columns
            ) not in REQUIREMENT_SCHEMAS or not _requirement_in_canonical_section(
                text, record
            ):
                findings.append(
                    _finding(
                        relative,
                        record.id,
                        f"{record.id} is outside a canonical requirement table",
                        "Declare requirements only in the canonical functional "
                        "or quality requirements sections.",
                    )
                )
                continue
            requirement_sources.setdefault(record.id, []).append(relative)

    return RepositoryContext(
        {identifier: tuple(paths) for identifier, paths in requirement_sources.items()},
        {identifier: tuple(items) for identifier, items in archived_themes.items()},
        tuple(theme for theme in active if isinstance(theme, dict)),
        archived_payloads,
    )


def _validate_requirement_references(
    control_id: str,
    requirements: Sequence[str],
    context: RepositoryContext,
    findings: list[Finding],
) -> None:
    for requirement in requirements:
        sources = context.requirement_sources.get(requirement, ())
        if len(sources) == 1:
            continue
        detail = (
            "does not resolve"
            if not sources
            else "resolves ambiguously in " + ", ".join(sources)
        )
        findings.append(
            _finding(
                str(LEDGER_PATH),
                control_id,
                f"{control_id} requirement {requirement} {detail} in the "
                "applicable canonical PRD",
                "Use one PR-### or QR-### declared by the approved PRD "
                "referenced from the active backlog theme.",
            )
        )


def _accepted_theme_record(
    root: Path,
    context: RepositoryContext,
    theme_id: object,
    acceptance: object,
) -> bool:
    if not isinstance(theme_id, str) or not isinstance(acceptance, str):
        return False
    summaries = context.archived_themes.get(theme_id, ())
    if len(summaries) != 1:
        return False
    summary = summaries[0]
    archive_ref = summary.get("archive-ref")
    canonical_archive_ref = (
        backlog_contract.ARCHIVE_DIRECTORY / f"{theme_id}.yaml"
    ).as_posix()
    if (
        summary.get("status") != "done"
        or summary.get("locked") is not True
        or not _valid_timestamp(summary.get("completed-at"))
        or not isinstance(archive_ref, str)
        or archive_ref != canonical_archive_ref
        or acceptance != canonical_archive_ref
        or not backlog_contract.validate_repository(root).valid
    ):
        return False
    path = _safe_file(root, acceptance)
    if path is None:
        return False
    try:
        document = _read_yaml(path)
    except LedgerError:
        return False
    if (
        not isinstance(document, dict)
        or set(document) != {"theme"}
        or not isinstance(document.get("theme"), dict)
    ):
        return False
    theme = document["theme"]
    return (
        theme.get("id") == theme_id
        and theme.get("status") == "done"
        and theme.get("locked") is True
    )


def _validate_verified_evidence(
    root: Path,
    control_id: str,
    state: str,
    evidence: list[tuple[str, Mapping[str, object]]],
    context: RepositoryContext,
    findings: list[Finding],
) -> None:
    if state != "VERIFIED":
        return
    valid = False
    for path, record in evidence:
        if record.get("evidence-kind") != "completed-theme":
            continue
        if set(record) != THEME_EVIDENCE_FIELDS:
            findings.append(
                _finding(
                    path,
                    control_id,
                    f"{control_id} completed-theme evidence has an invalid schema",
                    "Use the completed-theme evidence contract.",
                )
            )
            continue
        acceptance = record.get("acceptance-record")
        if (
            record.get("evidence-version") == 1
            and record.get("control-id") == control_id
            and _valid_timestamp(record.get("observed-at"))
            and _accepted_theme_record(
                root,
                context,
                record.get("theme"),
                acceptance,
            )
        ):
            valid = True
        else:
            findings.append(
                _finding(
                    path,
                    control_id,
                    f"{control_id} completed-theme evidence does not resolve "
                    "its theme and acceptance record through the canonical backlog",
                    "Use the same done, locked archived theme and its canonical "
                    "archive-ref as the acceptance record.",
                )
            )
    if not valid:
        findings.append(
            _finding(
                str(LEDGER_PATH),
                control_id,
                f"{control_id} state VERIFIED lacks evidence from a completed theme",
                "Retain a completed-theme evidence record whose acceptance "
                "record resolves to the same done and locked archived theme.",
            )
        )


def _theme_id(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    match = WAIVER_THEME_PATTERN.fullmatch(value)
    return match.group("id") if match is not None else None


def _theme_number(value: str) -> int:
    return int(value[2:])


def _value_cites_waiver(value: object, waiver_id: str, path: str) -> bool:
    if isinstance(value, str):
        return waiver_id in value or path in value
    if isinstance(value, Mapping):
        return any(
            _value_cites_waiver(item, waiver_id, path) for item in value.values()
        )
    if isinstance(value, list):
        return any(_value_cites_waiver(item, waiver_id, path) for item in value)
    return False


def _usage_records(
    theme: Mapping[str, object],
) -> tuple[tuple[str, Mapping[str, object] | None], ...]:
    theme_id = str(theme.get("id", "theme"))
    records_to_check: list[tuple[str, Mapping[str, object] | None]] = []
    usage = theme.get("usage")
    records_to_check.append(
        (theme_id, usage if isinstance(usage, Mapping) else None)
    )
    epics = theme.get("epics")
    if not isinstance(epics, list):
        return tuple(records_to_check)
    for epic in epics:
        if not isinstance(epic, Mapping):
            continue
        epic_id = str(epic.get("id", f"{theme_id}.epic"))
        epic_usage = epic.get("usage")
        records_to_check.append(
            (epic_id, epic_usage if isinstance(epic_usage, Mapping) else None)
        )
        stories = epic.get("stories")
        if not isinstance(stories, list):
            continue
        for story in stories:
            if not isinstance(story, Mapping):
                continue
            story_usage = story.get("usage")
            records_to_check.append(
                (
                    str(story.get("id", f"{epic_id}.story")),
                    story_usage if isinstance(story_usage, Mapping) else None,
                )
            )
    return tuple(records_to_check)


def _usage_is_available(usage: Mapping[str, object]) -> bool:
    confidence = usage.get("confidence")
    value = usage.get("value")
    return (
        confidence in {"measured", "estimated"}
        and isinstance(value, (int, float))
        and not isinstance(value, bool)
        and value >= 0
        and _is_text(usage.get("source"))
        and usage.get("source") != "none"
        and _valid_timestamp(usage.get("sampled-at"))
    )


def _usage_is_unknown(usage: Mapping[str, object]) -> bool:
    return (
        usage.get("confidence") == "unknown"
        and usage.get("value") is None
        and usage.get("source") == "none"
        and usage.get("sampled-at") is None
    )


def _waiver_identity_text(text: str) -> str:
    lines: list[str] = []
    for line, visible in _visible_markdown_lines(text):
        if visible and line.strip() == "## Approval":
            break
        lines.append(line if visible else "")
    return "\n".join(lines)


def _waiver_schema_findings(
    path: str,
    text: str,
    findings: list[Finding],
) -> tuple[Mapping[str, str] | None, Mapping[str, str] | None]:
    identity, identity_error = _single_field_table(_waiver_identity_text(text))
    approval_section = _section_text(text, "Approval")
    approval: Mapping[str, str] | None = None
    approval_error = "is missing its unique Approval section"
    if approval_section is not None:
        approval, approval_error = _single_field_table(approval_section)

    record = path
    if identity is not None and _is_text(identity.get("Waiver ID")):
        record = identity["Waiver ID"]
    if identity is None:
        findings.append(
            _finding(
                path,
                record,
                f"waiver identity {identity_error}",
                "Restore one metadata table with Waiver ID, Control, Theme, "
                "Requirement waived, and Status.",
            )
        )
    else:
        missing = [
            field for field in WAIVER_IDENTITY_FIELDS if not _is_text(identity.get(field))
        ]
        unknown = sorted(set(identity) - set(WAIVER_IDENTITY_FIELDS))
        if missing or unknown:
            details = []
            if missing:
                details.append("missing or empty " + ", ".join(missing))
            if unknown:
                details.append("unknown " + ", ".join(unknown))
            findings.append(
                _finding(
                    path,
                    record,
                    "waiver identity fields are invalid: " + "; ".join(details),
                    "Use exactly the complete waiver identity field set.",
                )
            )
    if approval is None:
        findings.append(
            _finding(
                path,
                record,
                f"waiver approval {approval_error}",
                "Restore one Approval table with actor, timestamp, scope, "
                "verdict, rationale, source revision, expiry, and invalidation.",
            )
        )
    else:
        missing = [
            field for field in WAIVER_APPROVAL_FIELDS if not _is_text(approval.get(field))
        ]
        unknown = sorted(set(approval) - set(WAIVER_APPROVAL_FIELDS))
        if missing or unknown:
            details = []
            if missing:
                details.append("missing or empty " + ", ".join(missing))
            if unknown:
                details.append("unknown " + ", ".join(unknown))
            findings.append(
                _finding(
                    path,
                    record,
                    "waiver approval fields are invalid: " + "; ".join(details),
                    "Record exactly actor, timestamp, scope, verdict, rationale, "
                    "source revision, expiry, and invalidation.",
                )
            )
        if not _valid_timestamp(approval.get("Timestamp")):
            findings.append(
                _finding(
                    path,
                    record,
                    "waiver is undated: Timestamp must be offset-aware ISO-8601",
                    "Record the attributable approval date and UTC offset.",
                )
            )
    return identity, approval


def _validate_usage_waiver_contract(
    path: str,
    identity: Mapping[str, str],
    approval: Mapping[str, str],
    text: str,
    findings: list[Finding],
) -> None:
    waiver_id = identity.get("Waiver ID", path)
    theme = _theme_id(identity.get("Theme"))
    control_match = WAIVER_CONTROL_PATTERN.fullmatch(identity.get("Control", ""))
    control_id = control_match.group("id") if control_match is not None else None
    if (
        waiver_id != "WVR-001"
        or path != TH3_USAGE_WAIVER_PATH.as_posix()
        or control_id != "CTL-010"
        or theme != "TH3"
        or "QR-013" not in identity.get("Requirement waived", "")
        or "usage-evidence" not in identity.get("Requirement waived", "").lower()
    ):
        findings.append(
            _finding(
                path,
                str(waiver_id),
                "TH3 usage waiver identity must remain WVR-001 for "
                "CTL-010, TH3, and only QR-013 usage evidence",
                "Restore the existing TH3-scoped WVR-001 identity; do not "
                "fabricate a replacement approval or broaden its scope.",
            )
        )

    if approval.get("Verdict") != "Approved":
        findings.append(
            _finding(
                path,
                str(waiver_id),
                "usage waiver does not carry an Approved verdict",
                "Retain the existing attributable approval or obtain a new "
                "human decision; the validator cannot grant one.",
            )
        )
    scope = approval.get("Scope", "")
    if scope != TH3_USAGE_WAIVER_SCOPE:
        findings.append(
            _finding(
                path,
                str(waiver_id),
                "usage waiver scope is not limited to missing TH3 usage evidence",
                "Limit Scope to missing usage evidence for TH3.",
            )
        )
    expiry = approval.get("Expiry", "")
    if expiry != TH3_USAGE_WAIVER_EXPIRY:
        findings.append(
            _finding(
                path,
                str(waiver_id),
                "usage waiver expiry is not the exact positive contract: "
                "expiry at TH3 acceptance, or earlier when CTL-010 reaches "
                "INSTRUMENTED",
                f"Set Expiry exactly to: {TH3_USAGE_WAIVER_EXPIRY}.",
            )
        )
    invalidation = approval.get("Invalidation", "")
    if invalidation != TH3_USAGE_WAIVER_INVALIDATION:
        findings.append(
            _finding(
                path,
                str(waiver_id),
                "usage waiver invalidation is not the exact positive contract "
                "requiring available measured or estimated TH3 usage evidence",
                f"Set Invalidation exactly to: "
                f"{TH3_USAGE_WAIVER_INVALIDATION}.",
            )
        )

    exclusions = (_section_text(text, "What this waiver does not cover") or "").lower()
    missing_exclusions = [
        obligation
        for obligation in FORBIDDEN_USAGE_WAIVER_OBLIGATIONS
        if obligation not in exclusions
    ]
    if missing_exclusions or not (
        "does not waive" in exclusions or "does not cover" in exclusions
    ):
        findings.append(
            _finding(
                path,
                str(waiver_id),
                "usage waiver does not explicitly preserve "
                + ", ".join(missing_exclusions or FORBIDDEN_USAGE_WAIVER_OBLIGATIONS),
                "State that WVR-001 covers only missing usage and never "
                "acceptance, quality, verification, review, or Gitflow.",
            )
        )


def _validate_consumed_waiver_closure(
        path: str,
        waiver_id: str,
        text: str,
        findings: list[Finding],
) -> bool:
        """Require attributable, exact evidence when TH3 consumes WVR-001."""

        section = _section_text(text, "Closure")
        closure, error = _single_field_table(section or "")
        if closure is None or set(closure) != set(WAIVER_CLOSURE_FIELDS):
            findings.append(
                _finding(
                    path,
                    waiver_id,
                    f"consumed waiver closure {error or 'is missing or invalid'}",
                    "Record one Closure table with actor, timestamp, scope, verdict, "
                    "rationale, and source revision.",
                )
            )
            return False
        expected = _th3_acceptance_values()
        mismatched = [
            field for field, value in expected.items() if closure.get(field) != value
        ]
        if mismatched:
            findings.append(
                _finding(
                    path,
                    waiver_id,
                    "consumed waiver closure is not the attributable TH3 acceptance "
                    "evidence: " + ", ".join(mismatched),
                    "Use the recorded human acceptance actor, timestamp, scope, "
                    "Accepted verdict, source digest, and honest unknown-usage rationale.",
                )
            )
            return False
        return True


def _th3_acceptance_values() -> Mapping[str, str]:
    """Return the immutable, human-attributed TH3 acceptance checkpoint."""

    return {
        "Actor": TH3_ACCEPTANCE_ACTOR,
        "Timestamp": TH3_ACCEPTANCE_TIMESTAMP,
        "Scope": "TH3",
        "Verdict": "Accepted",
        "Rationale": TH3_ACCEPTANCE_RATIONALE,
        "Source revision": TH3_ACCEPTANCE_SOURCE,
    }


def _validate_th3_acceptance_boundary(
    root: Path,
    findings: list[Finding],
) -> None:
    """Require one exact TH3 human decision across its authoritative records.

    Focused pre-acceptance fixtures intentionally omit the release record.  A
    repository that declares the release record, however, must retain every
    cross-record acceptance and the revision-68 archive state; partial state is
    never accepted as evidence.
    """

    release_path = _safe_file(root, TH3_RELEASE_PATH.as_posix())
    session_path = _safe_file(root, SESSION_LOG_PATH.as_posix())
    waiver_path = _safe_file(root, TH3_USAGE_WAIVER_PATH.as_posix())
    if release_path is None and session_path is None:
        backlog_path = _safe_file(root, BACKLOG_PATH.as_posix())
        try:
            document = (
                _read_yaml(backlog_path) if backlog_path is not None else None
            )
        except LedgerError:
            document = None
        body = document.get("backlog") if isinstance(document, dict) else None
        archived = body.get("archived-themes") if isinstance(body, dict) else None
        if not (
            isinstance(archived, list)
            and any(
                isinstance(item, dict) and item.get("id") == "TH3"
                for item in archived
            )
        ):
            return

    expected = _th3_acceptance_values()
    records_to_check: tuple[tuple[str, str, Path | None], ...] = (
        ("release acceptance", "Acceptance", release_path),
        ("session acceptance", "TH3 Human Acceptance Boundary", session_path),
        ("WVR-001 closure", "Closure", waiver_path),
    )
    for label, heading, path in records_to_check:
        relative = (
            path.relative_to(root).as_posix()
            if path is not None
            else (
                TH3_RELEASE_PATH.as_posix()
                if label == "release acceptance"
                else (
                    SESSION_LOG_PATH.as_posix()
                    if label == "session acceptance"
                    else TH3_USAGE_WAIVER_PATH.as_posix()
                )
            )
        )
        try:
            text = _read_text(path) if path is not None else ""
        except LedgerError:
            text = ""
        fields, error = _single_field_table(_section_text(text, heading) or "")
        if fields is None or set(fields) != set(TH3_ACCEPTANCE_FIELDS):
            findings.append(
                _finding(
                    relative,
                    "TH3 acceptance",
                    f"{label} {error or 'is missing or has an invalid schema'}",
                    "Restore one exact TH3 acceptance table with actor, timestamp, "
                    "scope, verdict, rationale, and source revision.",
                )
            )
            continue
        mismatched = [
            field for field, value in expected.items() if fields.get(field) != value
        ]
        if mismatched:
            findings.append(
                _finding(
                    relative,
                    "TH3 acceptance",
                    f"{label} does not match the canonical TH3 human checkpoint: "
                    + ", ".join(mismatched),
                    "Restore the exact Human: designer actor, acceptance timestamp, "
                    "TH3 scope, Accepted verdict, explicit checkpoint rationale, "
                    "and revision-67 SHA-256 source.",
                )
            )

    backlog_path = _safe_file(root, BACKLOG_PATH.as_posix())
    try:
        document = _read_yaml(backlog_path) if backlog_path is not None else None
    except LedgerError:
        document = None
    body = document.get("backlog") if isinstance(document, dict) else None
    archived = body.get("archived-themes") if isinstance(body, dict) else None
    summaries = (
        [item for item in archived if isinstance(item, dict) and item.get("id") == "TH3"]
        if isinstance(archived, list)
        else []
    )
    valid_summary = (
        isinstance(body, dict)
        and body.get("schema-version") == 2
        and body.get("revision") == 68
        and body.get("last-updated") == TH3_ACCEPTANCE_TIMESTAMP
        and len(summaries) == 1
        and summaries[0].get("schema-version") == 2
        and summaries[0].get("status") == "done"
        and summaries[0].get("locked") is True
        and summaries[0].get("completed-at") == TH3_ACCEPTANCE_TIMESTAMP
        and summaries[0].get("archive-ref") == TH3_ARCHIVE_PATH.as_posix()
    )
    if not valid_summary:
        findings.append(
            _finding(
                BACKLOG_PATH.as_posix(),
                "TH3",
                "TH3 archive index is not the canonical schema-v2, done, locked "
                "revision-68 acceptance state",
                "Restore the TH3 archive index at backlog revision 68 with "
                "schema-version 2, the exact authoritative last-updated and "
                "completed-at acceptance timestamp, done status, locked: true, "
                "and the canonical archive-ref.",
            )
        )

    archive_path = _safe_file(root, TH3_ARCHIVE_PATH.as_posix())
    try:
        archive = _read_yaml(archive_path) if archive_path is not None else None
    except LedgerError:
        archive = None
    payload = archive.get("theme") if isinstance(archive, dict) else None
    if not (
        isinstance(archive, dict)
        and set(archive) == {"theme"}
        and isinstance(payload, dict)
        and payload.get("id") == "TH3"
        and payload.get("schema-version") == 2
        and payload.get("status") == "done"
        and payload.get("locked") is True
    ):
        findings.append(
            _finding(
                TH3_ARCHIVE_PATH.as_posix(),
                "TH3",
                "TH3 archive payload is not the canonical schema-v2, done, locked "
                "acceptance state",
                "Restore the canonical TH3 archive payload with schema-version 2, "
                "status done, and locked: true.",
            )
        )

    try:
        waiver_text = _read_text(waiver_path) if waiver_path is not None else ""
    except LedgerError:
        waiver_text = ""
    identity = _field_table(waiver_text, expected_fields=WAIVER_IDENTITY_FIELDS)
    if identity is None or identity.get("Status") != "Consumed":
        findings.append(
            _finding(
                TH3_USAGE_WAIVER_PATH.as_posix(),
                "WVR-001",
                "TH3 acceptance state is not consistent with consumed WVR-001",
                "Retain WVR-001 as Consumed with its exact canonical TH3 closure.",
            )
        )


def _waiver_files(root: Path, findings: list[Finding]) -> tuple[Path, ...]:
    directory = root / WAIVER_DIRECTORY
    try:
        resolved_root = root.resolve(strict=True)
        resolved_directory = directory.resolve(strict=True)
        resolved_directory.relative_to(resolved_root)
    except (OSError, RuntimeError, ValueError):
        findings.append(
            _finding(
                WAIVER_DIRECTORY.as_posix(),
                "waivers",
                "waiver directory is missing, unsafe, or unreadable",
                f"Restore {WAIVER_DIRECTORY.as_posix()} inside the repository.",
            )
        )
        return ()
    if directory.is_symlink() or not directory.is_dir():
        findings.append(
            _finding(
                WAIVER_DIRECTORY.as_posix(),
                "waivers",
                "waiver directory must be a regular repository directory",
                "Replace the symlink or non-directory with the canonical "
                "waiver directory.",
            )
        )
        return ()
    try:
        return tuple(
            sorted(
                (
                    item
                    for item in directory.iterdir()
                    if item.suffix == ".md" and item.is_file() and not item.is_symlink()
                ),
                key=lambda item: item.name,
            )
        )
    except OSError:
        findings.append(
            _finding(
                WAIVER_DIRECTORY.as_posix(),
                "waivers",
                "waiver directory cannot be enumerated safely",
                "Restore readable regular waiver records.",
            )
        )
        return ()


def _validate_waivers(
    root: Path,
    controls: Sequence[Mapping[str, object]],
    context: RepositoryContext,
    findings: list[Finding],
) -> tuple[tuple[Mapping[str, object], ...], Mapping[str, object] | None]:
    parsed: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    files = _waiver_files(root, findings)
    if not any(
        path.relative_to(root).as_posix() == TH3_USAGE_WAIVER_PATH.as_posix()
        for path in files
    ):
        findings.append(
            _finding(
                TH3_USAGE_WAIVER_PATH.as_posix(),
                "WVR-001",
                "required TH3 usage waiver is missing",
                "Restore the existing human-delegated WVR-001 record.",
            )
        )

    controls_by_id = {
        str(control.get("id")): control
        for control in controls
        if CONTROL_ID_PATTERN.fullmatch(str(control.get("id", "")))
    }
    for waiver_path in files:
        relative = waiver_path.relative_to(root).as_posix()
        try:
            text = _read_text(waiver_path)
        except LedgerError as error:
            findings.append(
                _finding(
                    relative,
                    "waiver",
                    f"waiver is invalid: {error}",
                    "Restore a bounded UTF-8 Markdown waiver record.",
                )
            )
            continue
        identity, approval = _waiver_schema_findings(relative, text, findings)
        if identity is None or approval is None:
            continue
        waiver_id = identity.get("Waiver ID", "")
        if WAIVER_ID_PATTERN.fullmatch(waiver_id) is None:
            findings.append(
                _finding(
                    relative,
                    waiver_id or "waiver",
                    "waiver ID is not canonical",
                    "Use WVR-001 through WVR-999.",
                )
            )
            continue
        if waiver_id in seen_ids:
            findings.append(
                _finding(
                    relative,
                    waiver_id,
                    f"waiver ID {waiver_id} is duplicated",
                    "Keep one authoritative waiver record per waiver ID.",
                )
            )
            continue
        seen_ids.add(waiver_id)
        control_match = WAIVER_CONTROL_PATTERN.fullmatch(
            identity.get("Control", "")
        )
        theme = _theme_id(identity.get("Theme"))
        control_id = control_match.group("id") if control_match is not None else None
        if control_id is None or theme is None:
            findings.append(
                _finding(
                    relative,
                    waiver_id,
                    "waiver must name one canonical control and exact theme",
                    "Set Control to CTL-### and Theme to TH<n> plus its name.",
                )
            )
            continue
        if relative == TH3_USAGE_WAIVER_PATH.as_posix() or waiver_id == "WVR-001":
            _validate_usage_waiver_contract(
                relative, identity, approval, text, findings
            )

        controlling = controls_by_id.get(control_id)
        evidence = controlling.get("evidence") if controlling is not None else None
        referenced = isinstance(evidence, list) and relative in evidence
        if not referenced:
            findings.append(
                _finding(
                    relative,
                    waiver_id,
                    f"{waiver_id} is unreferenced by its controlling {control_id}",
                    f"Reference {relative} from {control_id}.evidence in "
                    f"{LEDGER_PATH.as_posix()}.",
                )
            )

        state = controlling.get("state") if controlling is not None else None
        theme_record = next(
            (
                item
                for item in context.active_themes
                if item.get("id") == theme
            ),
            None,
        )
        if theme_record is None:
            theme_record = context.archived_theme_payloads.get(theme)
        usage_records = (
            _usage_records(theme_record) if theme_record is not None else ()
        )
        invalid_unknown_usage = [
            scope
            for scope, usage in usage_records
            if usage is not None
            and not _usage_is_available(usage)
            and not _usage_is_unknown(usage)
        ]
        if invalid_unknown_usage:
            findings.append(
                _finding(
                    BACKLOG_PATH.as_posix(),
                    waiver_id,
                    "missing usage must be confidence unknown with value null, "
                    "source none, and sampled-at null; it is never zero for "
                    + ", ".join(invalid_unknown_usage),
                    "Restore the unknown usage tuple; use numeric zero only "
                    "when an adapter actually measured or estimated zero.",
                )
            )
        known_usage = any(
            usage is not None and _usage_is_available(usage)
            for _, usage in usage_records
        )
        instrumented = state in STATES and (
            STATE_RANK[str(state)] >= STATE_RANK["INSTRUMENTED"]
        )
        archived = theme in context.archived_themes
        effective_status = identity.get("Status", "").lower()
        if instrumented or known_usage:
            effective_status = "invalidated"
            missing_usage = [
                scope
                for scope, usage in usage_records
                if usage is None or not _usage_is_available(usage)
            ]
            if missing_usage:
                findings.append(
                    _finding(
                        relative,
                        waiver_id,
                        f"{waiver_id} is invalidated early because usage is "
                        "available or CTL-010 is INSTRUMENTED, but usage "
                        "evidence is missing or unknown for "
                        + ", ".join(missing_usage),
                        "Record measured or estimated usage evidence for every "
                        "TH3 scope before acceptance.",
                    )
                )
        elif archived:
            if identity.get("Status") != "Consumed":
                findings.append(
                    _finding(
                        relative,
                        waiver_id,
                        "WVR-001 must be consumed when its TH3 acceptance expiry occurs",
                        "Close WVR-001 as Consumed with the attributable TH3 "
                        "acceptance closure record.",
                    )
                )
            elif not _validate_consumed_waiver_closure(
                relative, waiver_id, text, findings
            ):
                effective_status = "invalid"
            else:
                effective_status = "consumed"
        elif identity.get("Status") != "Open":
            findings.append(
                _finding(
                    relative,
                    waiver_id,
                    "WVR-001 may be Consumed only at TH3 acceptance",
                    "Keep WVR-001 Open until TH3 is accepted, then close it as Consumed.",
                )
            )

        parsed.append(
            {
                "id": waiver_id,
                "path": relative,
                "control": control_id,
                "theme": theme,
                "status": effective_status,
                "expiry": approval.get("Expiry"),
                "invalidation": approval.get("Invalidation"),
            }
        )

    for waiver in parsed:
        waiver_id = str(waiver["id"])
        waiver_path = str(waiver["path"])
        waiver_theme = str(waiver["theme"])
        for theme in context.active_themes:
            current_theme = str(theme.get("id", ""))
            if (
                THEME_PATTERN.fullmatch(current_theme)
                and _theme_number(current_theme) > _theme_number(waiver_theme)
                and _value_cites_waiver(theme, waiver_id, waiver_path)
            ):
                findings.append(
                    _finding(
                        BACKLOG_PATH.as_posix(),
                        current_theme,
                        f"{current_theme} cannot reuse {waiver_id}; it is scoped "
                        f"to {waiver_theme} and expires at that theme's acceptance",
                        f"Create and approve a {current_theme}-specific "
                        "usage-evidence waiver and cite that waiver instead.",
                    )
                )
            epics = theme.get("epics")
            if waiver["control"] != "CTL-010":
                continue
            if not isinstance(epics, list):
                continue
            for epic in epics:
                if not isinstance(epic, Mapping):
                    continue
                stories = epic.get("stories")
                if not isinstance(stories, list):
                    continue
                for story in stories:
                    if not isinstance(story, Mapping):
                        continue
                    evidence = story.get("evidence")
                    disallowed = {
                        "acceptance evidence": story.get("acceptance"),
                        "quality evidence": story.get("quality"),
                        "verification waiver": (
                            story.get("verification", {}).get("waivers")
                            if isinstance(story.get("verification"), Mapping)
                            else None
                        ),
                        "verification evidence": (
                            evidence.get("verification")
                            if isinstance(evidence, Mapping)
                            else None
                        ),
                        "review evidence": (
                            evidence.get("review")
                            if isinstance(evidence, Mapping)
                            else None
                        ),
                        "Gitflow evidence": (
                            evidence.get("gitflow")
                            if isinstance(evidence, Mapping)
                            else None
                        ),
                    }
                    for obligation, value in disallowed.items():
                        if _value_cites_waiver(value, waiver_id, waiver_path):
                            story_id = str(story.get("id", "story"))
                            findings.append(
                                _finding(
                                    BACKLOG_PATH.as_posix(),
                                    story_id,
                                    f"{waiver_id} covers usage evidence only "
                                    f"and cannot satisfy {obligation}",
                                    f"Supply {obligation} or obtain its own "
                                    "applicable approval; remove the usage "
                                    "waiver citation.",
                                )
                            )

    th3 = next(
        (theme for theme in context.active_themes if theme.get("id") == "TH3"),
        None,
    )
    if th3 is None:
        th3 = context.archived_theme_payloads.get("TH3")
    if th3 is None:
        acceptance_report = None
    else:
        usage = th3.get("usage")
        actual_usage = (
            dict(usage) if isinstance(usage, Mapping) else dict(UNKNOWN_USAGE)
        )
        reportable_waivers = [
            (
                waiver["status"],
                {
                    "id": waiver["id"],
                    "control": waiver["control"],
                    "path": waiver["path"],
                    "expiry": waiver["expiry"],
                },
            )
            for waiver in parsed
            if waiver["theme"] == "TH3"
        ]
        acceptance_report = {
            "theme": "TH3",
            "theme-status": th3.get("status"),
            "control-maturity": [
                {"id": control.get("id"), "state": control.get("state")}
                for control in controls
            ],
            "usage": actual_usage,
            "open-waivers": [
                waiver for status, waiver in reportable_waivers if status == "open"
            ],
            "invalidated-waivers": [
                waiver
                for status, waiver in reportable_waivers
                if status == "invalidated"
            ],
            "consumed-waivers": [
                waiver for status, waiver in reportable_waivers if status == "consumed"
            ],
        }
    return tuple(parsed), acceptance_report


def validate_repository(repository_root: str | os.PathLike[str]) -> ValidationResult:
    """Validate one repository's activation ledger without side effects."""

    root = Path(repository_root)
    ledger_file = LEDGER_PATH.as_posix()
    path = _safe_file(root, ledger_file)
    if path is None:
        return ValidationResult(
            (
                _finding(
                    ledger_file,
                    "ledger",
                    "activation ledger is missing, unsafe, or unreadable",
                    f"Restore {ledger_file} as a regular repository file.",
                ),
            )
        )
    try:
        document = _read_yaml(path)
    except LedgerError as error:
        return ValidationResult(
            (
                _finding(
                    ledger_file,
                    "ledger",
                    f"activation ledger is invalid: {error}",
                    "Restore a bounded, duplicate-key-free YAML ledger.",
                ),
            )
        )
    if not isinstance(document, dict):
        return ValidationResult(
            (
                _finding(
                    ledger_file,
                    "ledger",
                    "activation ledger root must be a mapping",
                    "Use ledger-version and controls at the document root.",
                ),
            )
        )

    findings: list[Finding] = []
    try:
        recovery_dependencies = recovery.command_dependency_files(root)
    except ValueError:
        recovery_dependencies = ()
    if set(document) != {"ledger-version", "controls"}:
        findings.append(
            _finding(
                ledger_file,
                "ledger",
                "activation ledger must contain exactly ledger-version and controls",
                "Remove unknown root keys and restore required root keys.",
            )
        )
    if document.get("ledger-version") != 1:
        findings.append(
            _finding(
                ledger_file,
                "ledger-version",
                "ledger-version must be 1",
                "Use the supported activation ledger contract version.",
            )
        )
    raw_controls = document.get("controls")
    if not isinstance(raw_controls, list):
        findings.append(
            _finding(
                ledger_file,
                "controls",
                "controls must be a YAML sequence",
                "Record every control as one controls list item.",
            )
        )
        return ValidationResult(tuple(findings))

    controls = tuple(item for item in raw_controls if isinstance(item, dict))
    if len(controls) != len(raw_controls):
        findings.append(
            _finding(
                ledger_file,
                "controls",
                "every controls item must be a mapping",
                "Replace scalar or sequence items with control mappings.",
            )
        )
    for index, control in enumerate(controls):
        identifier = control.get("id")
        if (
            not isinstance(identifier, str)
            or CONTROL_ID_PATTERN.fullmatch(identifier) is None
        ):
            record = identifier if _is_text(identifier) else f"controls[{index}]"
            findings.append(
                _finding(
                    ledger_file,
                    str(record),
                    f"ledger control ID {identifier!r} is not canonical; "
                    "expected CTL-001 through CTL-999",
                    "Use a canonical control ID in the supported range.",
                )
            )
    identifiers = [
        str(control.get("id"))
        for control in controls
        if CONTROL_ID_PATTERN.fullmatch(str(control.get("id", "")))
    ]
    duplicates = sorted(
        identifier
        for identifier in set(identifiers)
        if identifiers.count(identifier) > 1
    )
    if duplicates:
        findings.append(
            _finding(
                ledger_file,
                "controls",
                f"control IDs are duplicated: {', '.join(duplicates)}",
                "Keep exactly one ledger entry per control ID.",
            )
        )
    missing_controls = sorted(set(REQUIRED_CONTROL_IDS) - set(identifiers))
    unexpected_controls = sorted(set(identifiers) - set(REQUIRED_CONTROL_IDS))
    if missing_controls or unexpected_controls:
        details = []
        if missing_controls:
            details.append("missing " + ", ".join(missing_controls))
        if unexpected_controls:
            details.append("unsupported " + ", ".join(unexpected_controls))
        findings.append(
            _finding(
                ledger_file,
                "controls",
                "control inventory is incomplete or unsupported: " + "; ".join(details),
                "Restore the complete CTL-001 through CTL-014 inventory.",
            )
        )

    context = _canonical_repository_context(root, findings)
    for index, control in enumerate(controls):
        identifier = control.get("id")
        record = (
            str(identifier)
            if CONTROL_ID_PATTERN.fullmatch(str(identifier or ""))
            else f"controls[{index}]"
        )
        keys = set(control)
        missing = sorted(REQUIRED_CONTROL_FIELDS - keys)
        unknown = sorted(keys - REQUIRED_CONTROL_FIELDS)
        if missing or unknown:
            details = []
            if missing:
                details.append("missing " + ", ".join(missing))
            if unknown:
                details.append("unknown " + ", ".join(unknown))
            findings.append(
                _finding(
                    ledger_file,
                    record,
                    f"{record} fields violate the ledger contract: "
                    + "; ".join(details),
                    "Use exactly the required control fields.",
                )
            )
        if not _is_text(control.get("name")):
            findings.append(
                _finding(
                    ledger_file,
                    record,
                    f"{record} name must be a non-empty string",
                    "Name the control.",
                )
            )
        if not _is_text(control.get("effective-point")):
            findings.append(
                _finding(
                    ledger_file,
                    record,
                    f"{record} effective-point must be a non-empty string",
                    "Name where the declared state becomes effective.",
                )
            )
        if not _is_text(control.get("proposed-by")):
            findings.append(
                _finding(
                    ledger_file,
                    record,
                    f"{record} proposed-by must name the proposer",
                    "Record the proposing role or actor.",
                )
            )
        requirements = _validate_string_list(
            control,
            "requirements",
            file=ledger_file,
            record=record,
            findings=findings,
            allow_empty=False,
        )
        invalid_requirements = [
            requirement
            for requirement in requirements
            if not REQUIREMENT_PATTERN.fullmatch(requirement)
        ]
        if invalid_requirements or len(set(requirements)) != len(requirements):
            findings.append(
                _finding(
                    ledger_file,
                    record,
                    f"{record} requirements contain invalid or duplicate references",
                    "Use unique canonical PR-### or QR-### references.",
                )
            )
        else:
            _validate_requirement_references(
                record,
                requirements,
                context,
                findings,
            )
        _validate_string_list(
            control,
            "limitations",
            file=ledger_file,
            record=record,
            findings=findings,
            allow_empty=True,
        )
        evidence_paths = _validate_string_list(
            control,
            "evidence",
            file=ledger_file,
            record=record,
            findings=findings,
            allow_empty=False,
        )
        state_value = control.get("state")
        if state_value not in STATES:
            findings.append(
                _finding(
                    ledger_file,
                    record,
                    f"{record} state {state_value!r} is outside the closed "
                    f"vocabulary {', '.join(STATES)}",
                    "Use exactly one supported maturity state.",
                )
            )
            continue
        state = str(state_value)
        _validate_promoter(
            control,
            file=ledger_file,
            record=record,
            state=state,
            findings=findings,
        )
        _validate_repository_support(root, record, state, findings)
        loaded_evidence = _load_evidence(root, record, evidence_paths, findings)
        promoter = control.get("promoted-by")
        promotion_timestamp = (
            promoter.get("timestamp") if isinstance(promoter, dict) else None
        )
        _validate_recovery_evidence(
            root,
            record,
            state,
            promotion_timestamp,
            loaded_evidence,
            recovery_dependencies,
            findings,
        )
        _validate_verified_evidence(
            root, record, state, loaded_evidence, context, findings
        )

    _validate_promotion_records(root, controls, findings)
    waivers, acceptance_report = _validate_waivers(
        root,
        controls,
        context,
        findings,
    )
    _validate_th3_acceptance_boundary(root, findings)
    findings.sort(
        key=lambda item: (
            str(item["record"]),
            str(item["file"]),
            str(item["message"]),
        )
    )
    return ValidationResult(
        tuple(findings),
        controls,
        waivers,
        acceptance_report,
    )


__all__ = [
    "CHECK",
    "LEDGER_PATH",
    "RECOVERY_CONTROLS",
    "REQUIRED_CONTROL_FIELDS",
    "REQUIRED_CONTROL_IDS",
    "STATES",
    "TH3_USAGE_WAIVER_PATH",
    "TH3_USAGE_WAIVER_EXPIRY",
    "TH3_USAGE_WAIVER_INVALIDATION",
    "UNKNOWN_USAGE",
    "WAIVER_DIRECTORY",
    "ValidationResult",
    "validate_repository",
]
