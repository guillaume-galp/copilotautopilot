"""Deterministic, fail-closed validation of lifecycle stage-entry gates.

Repository Markdown is untrusted data.  This module only performs bounded
filesystem reads, structural Markdown parsing, hashing, and date comparison.
It never imports, evaluates, executes, or retrieves repository content.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

import yaml


Finding = dict[str, object]

CHECK = "gates"
MAX_MARKDOWN_BYTES = 2 * 1024 * 1024
VP_PATTERN = re.compile(r"VP[1-9][0-9]*")
STAGES = ("discovery", "requirements", "architecture", "planning")
REQUIRED_GATE_FIELDS = (
    "Actor",
    "Timestamp",
    "Scope",
    "Verdict",
    "Rationale",
    "Source revision",
)
WORKING_FIELDS = ("Status", "Open items", "Accepted so far", "Next action")
ACTIVE_WORKING_STATUSES = frozenset({"in-progress", "awaiting-human"})
DISCOVERY_VERDICTS = frozenset(
    {"READY", "READY_WITH_DEFERRALS", "BLOCKED"}
)
LIFECYCLE_EXPIRY = re.compile(
    r"until (?:TH[1-9][0-9]* (?:acceptance|release)"
    r"|VP[1-9][0-9]* (?:acceptance|Discovery reclassification))"
)
IMMUTABLE_REVISION = re.compile(
    r"(?:git:[0-9a-f]{40}|sha256:[0-9a-f]{64})"
)
PLACEHOLDER = re.compile(r"<[^<>\n]+>")
REGISTERED_HUMAN_AUTHORITIES: Mapping[str, str] = {
    "Human: product owner": "product-owner",
    "Human: designer": "designer",
}
LEGITIMATE_AUTHORITY_MAPPINGS: Mapping[str, str] = {
    # This spelling exists only in the independently pinned VP3 evidence
    # below.  It is never accepted for a new or changed gate.
    "Human product owner": "Human: product owner",
}
LEGACY_VP3_EVIDENCE = {
    "discovery-readiness": {
        "gate-evidence-sha256": (
            "01a4bff6de520712a6d57408ae9456c876124fdb917bed5c99382893b9fc1990"
        ),
        "artifact-state": (
            "sha256:d69fd30d276774a49dc0aa196698d01709c77e6d9c6d03a7de857bb43387ba1e"
        ),
    },
    "prd-approval": {
        "gate-evidence-sha256": (
            "87c023843e42cb1a75f243bfe20cf4397f3efc5374ce45e9cdcd2dc9466c2528"
        ),
        "artifact-state": (
            "sha256:bfd503bd90e042d053a1f909d9bdd77144595f3fdc4db4e455a39dcd4a202ab3"
        ),
    },
    "architecture-acceptance": {
        "gate-evidence-sha256": (
            "62395cdb47517b556cecedcf9ff6e8be84e87ed4599c66a161fc62c6d5a9dd0b"
        ),
        "artifact-state": (
            "sha256:20845d152f9110f1cfa4d9e8ae89cfbc5e2a4734592caea378990d62bc804d04"
        ),
    },
}
PRD_IDENTITY_FIELDS = (
    "Schema version",
    "Product",
    "Vision",
    "Status",
    "Version",
    "Date",
    "Discovery verdict",
    "Discovery source revision",
    "Delivery mapping",
)
PRD_REQUIRED_SECTIONS = (
    "## Approval",
    "## Product promise",
    "## Vision outcomes",
    "## Lifecycle",
    "## Release scope",
    "## Functional requirements",
    "## Quality requirements",
    "## Acceptance scenarios",
    "## Success measures",
    "## Constraints and deferrals",
    "## Non-goals",
    "## Change control",
)
REQUIREMENT_FIELDS = (
    "ID",
    "Schema version",
    "Requirement",
    "Measure",
    "Impact",
    "Impact rationale",
    "Traces",
)
PCR_FIELDS = (
    "Schema version",
    "Requirement operation",
    "Change",
    "Reason",
    "Requestor",
    "Affected PR",
    "Affected QR",
    "Affected decisions",
    "Affected assumptions",
    "Affected risks",
    "Affected themes",
    "Discovery impact",
    "Architecture impact",
    "Migration impact",
    "Replanning impact",
    "Supersedes",
    "Human actor",
    "Human timestamp",
    "Human scope",
    "Human verdict",
    "Human rationale",
    "Baseline revision",
    "Source revision",
)
DR_FIELDS = (
    "Schema version",
    "Classification",
    "Reason",
    "Requestor",
    "Affected records",
    "Downstream impact set",
    "Invalidated gates",
    "Actor",
    "Timestamp",
    "Scope",
    "Verdict",
    "Rationale",
    "Source revision",
    "Provenance",
    "Confidence / limitations",
    "Owner",
    "Disposition",
)

DISCOVERY_OWNERS: Mapping[str, str] = {
    "DQ": "discovery-questions.md",
    "DEC": "decisions.md",
    "INV": "risks-and-failure-modes.md",
    "RSK": "risks-and-failure-modes.md",
}
DISCOVERY_HEADERS: Mapping[str, frozenset[tuple[str, ...]]] = {
    "DQ": frozenset(
        {
            ("ID", "Question"),
            (
                "ID",
                "Schema version",
                "Traces",
                "Question",
                "Consequence",
                "Method",
                "Budget",
                "Stop condition",
                "Outcome",
                "Resolved records",
                "Classification",
                "Provenance",
                "Confidence / limitations",
                "Owner",
                "Disposition",
            ),
        }
    ),
    "DEC": frozenset(
        {
            ("ID", "Decision"),
            (
                "ID",
                "Schema version",
                "Decision",
                "Rationale",
                "Consequence",
                "Alternatives",
                "Traces",
                "Classification",
                "Provenance",
                "Confidence / limitations",
                "Owner",
                "Disposition",
            ),
        }
    ),
    "INV": frozenset(
        {
            ("ID", "Invariant"),
            (
                "ID",
                "Schema version",
                "Invariant",
                "Rationale",
                "Failure consequence",
                "Traces",
                "Classification",
                "Provenance",
                "Confidence / limitations",
                "Owner",
                "Disposition",
            ),
        }
    ),
    "RSK": frozenset(
        {
            ("ID", "Risk"),
            (
                "ID",
                "Schema version",
                "Risk",
                "Impact",
                "Likelihood",
                "Treatment",
                "Trigger",
                "Traces",
                "Classification",
                "Provenance",
                "Confidence / limitations",
                "Owner",
                "Disposition",
            ),
        }
    ),
}
DISCOVERY_ACCEPTANCE_SUFFIX = (
    "Acceptance actor",
    "Acceptance timestamp",
    "Acceptance scope",
    "Acceptance verdict",
    "Acceptance rationale",
    "Acceptance source revision",
)


@dataclass(frozen=True)
class GateRecord:
    """A parsed formal gate and the artefact containing it."""

    name: str
    file: str
    section: str
    values: Mapping[str, str]
    current_schema: bool = False

    def as_payload(self, status: str) -> dict[str, object]:
        return {
            "name": self.name,
            "file": self.file,
            "section": self.section,
            "status": status,
            "actor": self.values.get("Actor"),
            "timestamp": self.values.get("Timestamp"),
            "scope": self.values.get("Scope"),
            "verdict": self.values.get("Verdict"),
            "source_revision": self.values.get("Source revision"),
        }


@dataclass(frozen=True)
class ValidationResult:
    """Complete stage-scoped gate report."""

    payload: Mapping[str, object]
    findings: tuple[Finding, ...]

    @property
    def valid(self) -> bool:
        return not self.findings


@dataclass(frozen=True)
class _PCRCollectionState:
    """Validation findings and the exact effective approved PCR path set."""

    findings: tuple[Finding, ...]
    applicable_paths: tuple[Path, ...]
    valid_paths: tuple[Path, ...] = ()
    evidence: Mapping[Path, str] | None = None


@dataclass(frozen=True)
class _DRCollectionState:
    """Validation findings and canonical DR paths, including rejected history."""

    findings: tuple[Finding, ...]
    valid_paths: tuple[Path, ...]
    accepted_paths: tuple[Path, ...]
    evidence: Mapping[Path, str]


class UnsafeSourceError(ValueError):
    """An expected source cannot safely be read beneath the repository."""


def _finding(
    *,
    file: str,
    record: str | None,
    message: str,
    remediation: str,
) -> Finding:
    safe_file = "".join(
        character
        if character.isprintable()
        else rf"\u{ord(character):04x}"
        for character in file
    )
    return {
        "check": CHECK,
        "severity": "error",
        "file": safe_file,
        "record": record,
        "message": message,
        "remediation": remediation,
    }


def _display(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _contained(path: Path, root: Path) -> Path:
    try:
        resolved_root = root.resolve()
        resolved = path.resolve()
        resolved.relative_to(resolved_root)
    except (OSError, RuntimeError, ValueError) as error:
        raise UnsafeSourceError("path is outside the repository boundary") from error
    return resolved


def _read_text(path: Path, root: Path) -> str:
    resolved = _contained(path, root)
    if path.is_symlink() or resolved != path.absolute():
        raise UnsafeSourceError("symbolic-link sources are not accepted")
    try:
        if not resolved.is_file():
            raise UnsafeSourceError("file is missing")
        if resolved.stat().st_size > MAX_MARKDOWN_BYTES:
            raise UnsafeSourceError(
                f"file exceeds the {MAX_MARKDOWN_BYTES}-byte safety limit"
            )
        return resolved.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise UnsafeSourceError("file is unreadable or not valid UTF-8") from error


def _exact_source_state_digest(
    root: Path, sources: Sequence[Path]
) -> str | None:
    """Hash exact source paths and UTF-8 content for immutable exceptions."""

    try:
        state = [
            {
                "path": source.relative_to(root).as_posix(),
                "content": _read_text(source, root),
            }
            for source in sources
        ]
    except (UnsafeSourceError, ValueError):
        return None
    encoded = json.dumps(state, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _strip_html_comments(text: str) -> str:
    """Remove rendered-invisible HTML comments, preserving line boundaries.

    Markdown permits multiline comments.  Although HTML itself does not nest
    comments, treating nested openers as depth changes is the fail-closed
    choice for adversarial Markdown: no inner terminator can expose a hidden
    gate before the outer comment closes.  An unclosed comment remains hidden
    through end of file.
    """

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


def _visible_lines(text: str) -> tuple[tuple[str, bool], ...]:
    result: list[tuple[str, bool]] = []
    active: tuple[str, int] | None = None
    for line in _strip_html_comments(text).splitlines():
        if active is not None:
            character, length = active
            result.append((line, False))
            if re.fullmatch(
                rf" {{0,3}}{re.escape(character * length)}[ \t]*", line
            ):
                active = None
            continue
        opening = re.match(r"^ {0,3}(?P<fence>`{3,}|~{3,})", line)
        if opening:
            delimiter = opening.group("fence")
            active = (delimiter[0], len(delimiter))
            result.append((line, False))
            continue
        result.append((line, True))
    return tuple(result)


def _split_row(line: str) -> list[str] | None:
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


def _is_separator(row: Sequence[str] | None, width: int) -> bool:
    return bool(
        row
        and len(row) == width
        and all(re.fullmatch(r":?-{3,}:?", cell) for cell in row)
    )


def _tables(text: str) -> tuple[list[list[str]], ...]:
    tables: list[list[list[str]]] = []
    current: list[list[str]] = []
    for line, visible in (*_visible_lines(text), ("", True)):
        row = _split_row(line) if visible else None
        if row is not None:
            current.append(row)
        elif current:
            tables.append(current)
            current = []
    return tuple(tables)


def _sections(text: str, heading: str) -> tuple[str, ...]:
    visible_lines = _visible_lines(text)
    lines = [item[0] for item in visible_lines]
    visible = [item[1] for item in visible_lines]
    level = len(heading) - len(heading.lstrip("#"))
    starts = [
        index
        for index, line in enumerate(lines)
        if visible[index] and line == heading
    ]
    sections: list[str] = []
    for start in starts:
        end = len(lines)
        for index in range(start + 1, len(lines)):
            match = re.match(r"^(#{1,6}) ", lines[index])
            if visible[index] and match and len(match.group(1)) <= level:
                end = index
                break
        sections.append("\n".join(lines[start + 1 : end]) + "\n")
    return tuple(sections)


def _field_table(
    text: str,
    *,
    heading: str,
    file: str,
    record: str,
) -> tuple[dict[str, str] | None, list[str], list[Finding]]:
    findings: list[Finding] = []
    sections = _sections(text, heading)
    if not sections:
        findings.append(
            _finding(
                file=file,
                record=record,
                message=f"{heading} gate record is missing.",
                remediation=(
                    f"Add one {heading} section with the six canonical gate "
                    "fields and an attributable authority verdict."
                ),
            )
        )
        return None, [], findings
    if len(sections) != 1:
        findings.append(
            _finding(
                file=file,
                record=record,
                message=f"{heading} gate record is duplicated.",
                remediation=f"Keep exactly one authoritative {heading} section.",
            )
        )
        return None, [], findings

    candidates = [
        table
        for table in _tables(sections[0])
        if table and table[0] == ["Field", "Value"]
    ]
    if len(candidates) != 1:
        findings.append(
            _finding(
                file=file,
                record=record,
                message=(
                    f"{heading} must contain exactly one Field | Value table."
                ),
                remediation=(
                    "Use the canonical gate template with one two-column table."
                ),
            )
        )
        return None, [], findings

    table = candidates[0]
    if len(table) < 2 or not _is_separator(table[1], 2):
        findings.append(
            _finding(
                file=file,
                record=record,
                message=f"{heading} gate table has an invalid separator.",
                remediation="Place |---|---| immediately below its header.",
            )
        )
        return None, [], findings

    fields: list[str] = []
    values: dict[str, str] = {}
    for row in table[2:]:
        if len(row) != 2:
            findings.append(
                _finding(
                    file=file,
                    record=record,
                    message=f"{heading} gate table contains a malformed row.",
                    remediation="Use exactly one field cell and one value cell.",
                )
            )
            continue
        name, value = row
        fields.append(name)
        if name in values:
            findings.append(
                _finding(
                    file=file,
                    record=record,
                    message=f"Gate field {name!r} is duplicated.",
                    remediation=f"Keep exactly one {name} row.",
                )
            )
        else:
            values[name] = value
    return values, fields, findings


def _identity_values(text: str) -> dict[str, str]:
    visible_text = "\n".join(
        line for line, visible in _visible_lines(text) if visible
    )
    first_heading = next(
        (
            index
            for index, line in enumerate(visible_text.splitlines())
            if line.startswith("## ")
        ),
        len(visible_text.splitlines()),
    )
    prefix = "\n".join(visible_text.splitlines()[:first_heading])
    candidates = [
        table
        for table in _tables(prefix)
        if table and table[0] == ["Field", "Value"]
        and len(table) > 1
        and _is_separator(table[1], 2)
    ]
    if not candidates:
        return {}
    result: dict[str, str] = {}
    for row in candidates[0][2:]:
        if len(row) == 2 and row[0] not in result:
            result[row[0]] = row[1]
    return result


def _valid_timestamp(value: str) -> bool:
    if "T" not in value or not re.search(r"(?:Z|[+-]\d{2}:\d{2})$", value):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.utcoffset() is not None


def _human_authority(value: str) -> bool:
    """Accept only identities explicitly registered by the gate contract."""

    return value in REGISTERED_HUMAN_AUTHORITIES


def _gate_evidence_digest(
    record: GateRecord, fields: Sequence[str]
) -> str:
    encoded = json.dumps(
        {"fields": list(fields), "values": dict(record.values)},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _legacy_vp3_record(
    record: GateRecord,
    fields: Sequence[str],
    vp: str,
    *,
    artifact_state: str | None,
) -> bool:
    """Recognize only byte-derived, independently pinned accepted evidence.

    A path, actor spelling, timestamp, or mutable source label is never enough
    to trigger the prospective-schema exception.  Any change to the accepted
    artefact set or its gate evidence falls through to current validation.
    """

    expected = LEGACY_VP3_EVIDENCE.get(record.name)
    if vp != "VP3" or expected is None or artifact_state is None:
        return False
    return (
        _gate_evidence_digest(record, fields)
        == expected["gate-evidence-sha256"]
        and artifact_state == expected["artifact-state"]
        and (
            record.values.get("Actor", "") in REGISTERED_HUMAN_AUTHORITIES
            or LEGITIMATE_AUTHORITY_MAPPINGS.get(
                record.values.get("Actor", "")
            )
            in REGISTERED_HUMAN_AUTHORITIES
        )
    )


def _scope_covers_vp(value: str, vp: str) -> bool:
    return re.search(
        rf"(?<![A-Za-z0-9]){re.escape(vp)}(?![A-Za-z0-9])", value
    ) is not None


def _validate_common_fields(
    record: GateRecord,
    fields: Sequence[str],
    *,
    expected_fields: Sequence[str],
    legacy_vp3: bool = False,
) -> list[Finding]:
    findings: list[Finding] = []
    if tuple(fields) != tuple(expected_fields):
        findings.append(
            _finding(
                file=record.file,
                record=record.name,
                message=(
                    "Gate fields are incomplete or out of order; expected "
                    + ", ".join(expected_fields)
                    + "."
                ),
                remediation=(
                    "Replace the table with the canonical template and fill "
                    "every expected field exactly once in the stated order."
                ),
            )
        )

    for field in expected_fields:
        value = record.values.get(field, "")
        if not value or PLACEHOLDER.search(value):
            findings.append(
                _finding(
                    file=record.file,
                    record=record.name,
                    message=f"Required gate field {field} is missing or unfilled.",
                    remediation=(
                        f"Record a non-placeholder {field} value from the "
                        "applicable authority."
                    ),
                )
            )

    actor = record.values.get("Actor", "")
    authority_valid = _human_authority(actor) or (
        legacy_vp3
        and LEGITIMATE_AUTHORITY_MAPPINGS.get(actor)
        in REGISTERED_HUMAN_AUTHORITIES
    )
    if actor and not PLACEHOLDER.search(actor) and not authority_valid:
        findings.append(
            _finding(
                file=record.file,
                record=record.name,
                message="Actor is not an attributable human authority.",
                remediation=(
                    "Use an exact registered authority identity: "
                    "'Human: product owner' or 'Human: designer'. Qualifiers, "
                    "suffixes, and unregistered identities are not accepted."
                ),
            )
        )

    timestamp = record.values.get("Timestamp", "")
    if timestamp and not PLACEHOLDER.search(timestamp) and not _valid_timestamp(
        timestamp
    ):
        findings.append(
            _finding(
                file=record.file,
                record=record.name,
                message="Timestamp is not a real ISO-8601 timestamp with an offset.",
                remediation=(
                    "Record a valid timestamp such as "
                    "2026-09-06T18:56:37+01:00."
                ),
            )
        )
    revision = record.values.get("Source revision", "")
    if revision and not PLACEHOLDER.search(revision) and not (
        IMMUTABLE_REVISION.fullmatch(revision)
        or legacy_vp3
    ):
        findings.append(
            _finding(
                file=record.file,
                record=record.name,
                message="Source revision is not an immutable accepted revision.",
                remediation=(
                    "Record git:<40 lowercase hex> or sha256:<64 lowercase "
                    "hex>; arbitrary dates, tags, branches, and labels are "
                    "not trusted."
                ),
            )
        )
    return findings


def _resolve_scope(
    root: Path,
    parent: str,
    vp: str,
    *,
    required: bool,
    record: str,
) -> tuple[Path | None, list[Finding]]:
    base = root / parent
    file = f"{parent}/{vp}-<slug>"
    findings: list[Finding] = []
    try:
        resolved_base = _contained(base, root)
    except UnsafeSourceError:
        findings.append(
            _finding(
                file=parent,
                record=record,
                message="Canonical scope root resolves outside the repository.",
                remediation=(
                    f"Restore {parent} as an in-repository directory, not a "
                    "symbolic link."
                ),
            )
        )
        return None, findings
    candidates: list[Path] = []
    try:
        if resolved_base.is_dir():
            candidates = sorted(
                (
                    child
                    for child in resolved_base.iterdir()
                    if child.name.startswith(f"{vp}-")
                ),
                key=lambda item: item.name,
            )
    except OSError:
        candidates = []

    safe_candidates: list[Path] = []
    for candidate in candidates:
        try:
            resolved = _contained(candidate, root)
            if (
                candidate.is_symlink()
                or resolved != candidate.absolute()
                or not resolved.is_dir()
            ):
                raise UnsafeSourceError
            safe_candidates.append(candidate)
        except UnsafeSourceError:
            findings.append(
                _finding(
                    file=_display(candidate, root),
                    record=record,
                    message="VP scope resolves outside the repository boundary.",
                    remediation="Replace the symbolic link with an in-repository directory.",
                )
            )

    if len(safe_candidates) > 1:
        findings.append(
            _finding(
                file=file,
                record=record,
                message=(
                    f"{vp} resolves ambiguously to "
                    + ", ".join(path.name for path in safe_candidates)
                    + "."
                ),
                remediation=(
                    f"Keep exactly one canonical {vp}-<slug> directory under "
                    f"{parent}."
                ),
            )
        )
        return None, findings
    if not safe_candidates:
        if required and not findings:
            findings.append(
                _finding(
                    file=file,
                    record=record,
                    message=f"Required {vp} scope is missing.",
                    remediation=f"Create the canonical {parent}/{vp}-<slug>/ scope.",
                )
            )
        return None, findings
    return safe_candidates[0], findings


def _working_state(
    text: str,
    *,
    file: str,
    source_kind: str,
) -> tuple[dict[str, object] | None, list[Finding]]:
    sections = _sections(text, "## Working state")
    if not sections:
        return None, []
    if len(sections) != 1:
        return None, [
            _finding(
                file=file,
                record="working-state",
                message="Working state is duplicated.",
                remediation="Keep one canonical ## Working state section.",
            )
        ]
    candidates = [
        table
        for table in _tables(sections[0])
        if table and table[0] == ["Field", "Value"]
    ]
    if (
        len(candidates) != 1
        or len(candidates[0]) < 2
        or not _is_separator(candidates[0][1], 2)
    ):
        return None, [
            _finding(
                file=file,
                record="working-state",
                message="Working state does not contain one valid Field | Value table.",
                remediation=(
                    "Use the canonical working-state template with Status, "
                    "Open items, Accepted so far, and Next action."
                ),
            )
        ]
    rows = candidates[0][2:]
    fields = [row[0] for row in rows if len(row) == 2]
    values = {row[0]: row[1] for row in rows if len(row) == 2}
    if tuple(fields) != WORKING_FIELDS:
        return None, [
            _finding(
                file=file,
                record="working-state",
                message="Working-state fields are incomplete or out of order.",
                remediation=(
                    "Use Status, Open items, Accepted so far, and Next action "
                    "exactly once in that order."
                ),
            )
        ]
    status = values["Status"]
    if status not in {
        "not-started",
        "in-progress",
        "awaiting-human",
        "accepted",
        "blocked",
    }:
        return None, [
            _finding(
                file=file,
                record="working-state",
                message=f"Working-state Status {status!r} is unknown.",
                remediation="Use a status from the canonical working-state vocabulary.",
            )
        ]
    findings: list[Finding] = []
    for field in WORKING_FIELDS:
        if not values[field] or PLACEHOLDER.search(values[field]):
            findings.append(
                _finding(
                    file=file,
                    record="working-state",
                    message=f"Working-state field {field} is missing or unfilled.",
                    remediation=f"Record a concrete {field} value.",
                )
            )

    empty_markers = frozenset(
        {"", "none", "n/a", "na", "nil", "null", "tbd", "todo", "-"}
    )
    parsed_open_items = [
        item.strip() for item in values["Open items"].split(",") if item.strip()
    ]
    if status in ACTIVE_WORKING_STATUSES:
        if (
            values["Open items"].strip().casefold() in empty_markers
            or not parsed_open_items
        ):
            findings.append(
                _finding(
                    file=file,
                    record="working-state",
                    message=(
                        f"Paused Working state {status!r} requires at least "
                        "one nonempty open item."
                    ),
                    remediation=(
                        "List each unresolved item with its accountable owner."
                    ),
                )
            )
        allowed_prefixes = (
            ("DQ",) if source_kind == "discovery" else ("PR", "QR", "PCR")
        )
        item_pattern = re.compile(
            rf"(?P<id>(?:{'|'.join(allowed_prefixes)})-"
            r"(?:00[1-9]|0[1-9]\d|[1-9]\d{2})) "
            r"\(owner: (?P<owner>[^()|,]+)\)"
        )
        seen_ids: set[str] = set()
        for item in parsed_open_items:
            match = item_pattern.fullmatch(item)
            owner = match.group("owner").strip() if match else ""
            if (
                match is None
                or match.group("id") in seen_ids
                or owner.casefold() in empty_markers
                or PLACEHOLDER.search(owner)
            ):
                findings.append(
                    _finding(
                        file=file,
                        record="working-state",
                        message=(
                            f"Open item {item!r} is not a unique stable "
                            f"{'/'.join(allowed_prefixes)} ID with an owner."
                        ),
                        remediation=(
                            "Use '<ID> (owner: <accountable owner>)' for each "
                            "comma-separated open item, with no duplicate IDs."
                        ),
                    )
                )
            else:
                seen_ids.add(match.group("id"))
        if values["Next action"].strip().casefold() in empty_markers:
            findings.append(
                _finding(
                    file=file,
                    record="working-state",
                    message=(
                        f"Paused Working state {status!r} requires an "
                        "actionable Next action."
                    ),
                    remediation=(
                        "Name the concrete next action, its actor, and intended "
                        "result; do not use None or a placeholder."
                    ),
                )
            )
        action = re.fullmatch(
            r"Actor: (?P<actor>[^;|]+); "
            r"Action: (?P<action>[^;|]+); "
            r"Intended result: (?P<result>[^;|]+)",
            values["Next action"],
        )
        vague = {
            "continue",
            "follow up",
            "review",
            "work on it",
            "do next step",
            "tbd",
            "todo",
            "none",
        }
        if (
            action is None
            or any(
                not action.group(field).strip()
                or PLACEHOLDER.search(action.group(field))
                or action.group(field).strip().casefold() in vague
                for field in ("actor", "action", "result")
            )
            or len(action.group("action").split()) < 2
            or len(action.group("result").split()) < 2
        ):
            findings.append(
                _finding(
                    file=file,
                    record="working-state",
                    message=(
                        f"Paused Working state {status!r} has a vague or "
                        "unstructured Next action."
                    ),
                    remediation=(
                        "Use 'Actor: <owner>; Action: <concrete action>; "
                        "Intended result: <observable result>' with all three "
                        "parts completed."
                    ),
                )
            )
    if findings:
        return None, findings

    def items(value: str) -> list[str]:
        if value == "None":
            return []
        return [item.strip() for item in value.split(",") if item.strip()]

    return {
        "status": status,
        "open_items": items(values["Open items"]),
        "accepted_so_far": items(values["Accepted so far"]),
        "next_action": values["Next action"],
    }, []


def _parse_gate(
    path: Path,
    root: Path,
    *,
    name: str,
    heading: str,
) -> tuple[GateRecord | None, str | None, list[str], list[Finding]]:
    file = _display(path, root)
    try:
        text = _read_text(path, root)
    except UnsafeSourceError as error:
        return None, None, [], [
            _finding(
                file=file,
                record=name,
                message=f"Gate source is unavailable: {error}.",
                remediation="Restore a regular UTF-8 Markdown file inside the repository.",
            )
        ]
    values, fields, findings = _field_table(
        text, heading=heading, file=file, record=name
    )
    if values is None:
        return None, text, fields, findings
    identity = _identity_values(text)
    return (
        GateRecord(
            name=name,
            file=file,
            section=heading.removeprefix("## "),
            values=values,
            current_schema=identity.get("Schema version") == "1",
        ),
        text,
        fields,
        findings,
    )


def _parse_architecture_gate(
    path: Path,
    root: Path,
) -> tuple[GateRecord | None, str | None, list[str], list[Finding]]:
    file = _display(path, root)
    try:
        text = _read_text(path, root)
    except UnsafeSourceError:
        return _parse_gate(
            path,
            root,
            name="architecture-acceptance",
            heading="## Approval",
        )
    headings = [
        heading
        for heading in ("## Approval", "## Acceptance")
        if _sections(text, heading)
    ]
    if len(headings) > 1:
        return None, text, [], [
            _finding(
                file=file,
                record="architecture-acceptance",
                message=(
                    "Architecture has both Approval and Acceptance gate sections."
                ),
                remediation=(
                    "Keep one authoritative architecture gate using either "
                    "## Approval or ## Acceptance."
                ),
            )
        ]
    return _parse_gate(
        path,
        root,
        name="architecture-acceptance",
        heading=headings[0] if headings else "## Approval",
    )


def _section(text: str, heading: str) -> str | None:
    sections = _sections(text, heading)
    return sections[0] if len(sections) == 1 else None


def _prd_revision(text: str) -> str:
    text = _strip_html_comments(text)
    approval = _section(text, "## Approval")
    if approval is None:
        return ""
    submitted = text.replace("## Approval\n" + approval, "", 1)
    return "sha256:" + hashlib.sha256(submitted.encode()).hexdigest()


def _discovery_revision(
    *,
    vision: Path,
    dossier: Path,
    root: Path,
    requirements: Path | None = None,
) -> str | None:
    """Digest the exact rendered Vision and dossier state submitted to gate.

    The acceptance section itself is excluded to avoid a self-referential
    digest.  Revision records are included: an appended DR therefore requires
    an explicit re-evaluation instead of silently inheriting an old waiver.
    """

    try:
        sources = [vision, *sorted(dossier.rglob("*.md"))]
        if requirements is not None:
            sources.extend(_approved_behavior_pcr_paths(requirements, root))
        state: list[dict[str, str]] = []
        for source in sources:
            text = _strip_html_comments(_read_text(source, root))
            if source == dossier / "README.md":
                acceptance = _section(text, "## Acceptance")
                if acceptance is not None:
                    text = text.replace(
                        "## Acceptance\n" + acceptance, "", 1
                    )
            state.append(
                {
                    "path": source.relative_to(root).as_posix(),
                    "content": text,
                }
            )
    except (UnsafeSourceError, ValueError):
        return None
    encoded = json.dumps(state, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _approved_behavior_pcr_paths(
    requirements: Path | None, root: Path
) -> list[Path]:
    """Return fully valid, approved PCRs in the effective applicable state."""

    if requirements is None:
        return []
    vp_match = re.fullmatch(
        r"(VP[1-9][0-9]*)-[a-z0-9]+(?:-[a-z0-9]+)*",
        requirements.name,
    )
    if vp_match is None:
        return []
    vp = vp_match.group(1)
    prd = requirements / "PRD.md"
    record, text, fields, parse_findings = _parse_gate(
        prd, root, name="prd-approval", heading="## Approval"
    )
    if record is None or text is None:
        return []
    baseline_findings, _legacy = _validate_prd_baseline_gate(
        record,
        fields,
        text,
        root=root,
        requirements=requirements,
        vp=vp,
        parse_findings=parse_findings,
    )
    state = _evaluate_pcr_collection(
        root=root,
        requirements=requirements,
        prd_record=record,
        baseline_revision=record.values.get("Source revision", ""),
        vp=vp,
        resolved_upstream=_same_vp_upstream_ids(root, requirements, vp),
        baseline_gate_findings=baseline_findings,
    )
    return list(state.applicable_paths)


def _requirements_state_revision(
    root: Path, requirements: Path, prd: Path
) -> str | None:
    """Digest the exact accepted PRD and its complete PCR collection."""

    try:
        sources = [prd]
        changes = requirements / "changes"
        if changes.is_dir() and not changes.is_symlink():
            sources.extend(
                sorted(changes.glob("PCR-*.md"), key=lambda item: item.name)
            )
    except OSError:
        return None
    return _exact_source_state_digest(root, sources)


def _git_file(root: Path, revision: str, path: Path) -> str | None:
    """Read one repository file at an immutable commit without a shell."""

    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        return None
    try:
        relative = path.relative_to(root).as_posix()
    except ValueError:
        return None
    try:
        probe = subprocess.run(
            ["git", "-C", str(root), "cat-file", "-e", f"{revision}^{{commit}}"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=2,
        )
        if probe.returncode:
            return None
        result = subprocess.run(
            ["git", "-C", str(root), "show", f"{revision}:{relative}"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode or len(result.stdout) > MAX_MARKDOWN_BYTES:
        return None
    try:
        return result.stdout.decode("utf-8")
    except UnicodeError:
        return None


def _revision_matches_text(
    *,
    root: Path,
    path: Path,
    source_revision: str,
    current_digest: str,
    digest_text,
) -> bool:
    if source_revision.startswith("sha256:"):
        return source_revision == current_digest
    if not source_revision.startswith("git:"):
        return False
    historical = _git_file(root, source_revision.removeprefix("git:"), path)
    return historical is not None and digest_text(historical) == current_digest


def _architecture_revision(root: Path, readme: Path) -> str | None:
    try:
        sources = [
            *sorted((root / "docs/architecture").rglob("*.md")),
            *sorted((root / "docs/ADRs").glob("ADR-*.md")),
        ]
        state: list[dict[str, str]] = []
        for source in sources:
            text = _strip_html_comments(_read_text(source, root))
            if source == readme:
                for heading in ("## Approval", "## Acceptance"):
                    acceptance = _section(text, heading)
                    if acceptance is not None:
                        text = text.replace(heading + "\n" + acceptance, "", 1)
                        break
            state.append(
                {
                    "path": source.relative_to(root).as_posix(),
                    "content": text,
                }
            )
    except (UnsafeSourceError, OSError, ValueError):
        return None
    encoded = json.dumps(state, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _git_tree_matches(
    root: Path,
    revision: str,
    sources: Sequence[Path],
    *,
    scope_paths: Sequence[Path],
    transform,
) -> bool:
    """Compare a bounded current source set with the same files at a commit."""

    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        return False
    try:
        relative_scopes = [
            scope.relative_to(root).as_posix() for scope in scope_paths
        ]
        listing = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "ls-tree",
                "-r",
                "-z",
                "--name-only",
                revision,
                "--",
                *relative_scopes,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=2,
        )
    except (OSError, ValueError, subprocess.SubprocessError):
        return False
    if listing.returncode:
        return False
    try:
        historical_paths = {
            item.decode("utf-8")
            for item in listing.stdout.split(b"\0")
            if item and item.endswith(b".md")
        }
    except UnicodeError:
        return False
    current_paths = {source.relative_to(root).as_posix() for source in sources}
    if historical_paths != current_paths:
        return False

    state: list[dict[str, str]] = []
    for source in sources:
        historical = _git_file(root, revision, source)
        if historical is None:
            return False
        state.append(
            {
                "path": source.relative_to(root).as_posix(),
                "content": transform(source, historical),
            }
        )
    encoded = json.dumps(state, sort_keys=True, separators=(",", ":")).encode()
    historical_digest = "sha256:" + hashlib.sha256(encoded).hexdigest()
    current_state: list[dict[str, str]] = []
    try:
        for source in sources:
            current_state.append(
                {
                    "path": source.relative_to(root).as_posix(),
                    "content": transform(source, _read_text(source, root)),
                }
            )
    except (UnsafeSourceError, ValueError):
        return False
    current_encoded = json.dumps(
        current_state, sort_keys=True, separators=(",", ":")
    ).encode()
    return historical_digest == (
        "sha256:" + hashlib.sha256(current_encoded).hexdigest()
    )


def _without_gate(text: str, headings: Sequence[str]) -> str:
    result = _strip_html_comments(text)
    for heading in headings:
        body = _section(result, heading)
        if body is not None:
            return result.replace(heading + "\n" + body, "", 1)
    return result


def _pcr_revision(
    record_id: str,
    metadata: Mapping[str, str],
    requirement_rows: Sequence[Mapping[str, str]],
) -> str:
    proposed = {
        "id": record_id,
        "metadata": {
            field: metadata.get(field, "")
            for field in PCR_FIELDS[: PCR_FIELDS.index("Human actor")]
        },
        "requirements": list(requirement_rows),
    }
    encoded = json.dumps(
        proposed, sort_keys=True, separators=(",", ":")
    ).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _schema_finding(
    record: GateRecord,
    message: str,
    remediation: str,
    *,
    record_id: str | None = None,
) -> Finding:
    return _finding(
        file=record.file,
        record=record_id or record.name,
        message=message,
        remediation=remediation,
    )


def _same_vp_upstream_ids(
    root: Path, requirements: Path, vp: str
) -> frozenset[str]:
    """Index only valid canonical upstream rows from the same VP scope."""

    result: set[str] = set()
    scope_name = requirements.name
    vision = root / "docs/vision_of_product" / scope_name / f"{vp}.md"
    try:
        vision_text = _read_text(vision, root)
    except UnsafeSourceError:
        vision_text = ""
    for table in _tables(vision_text):
        if (
            table
            and tuple(table[0]) == ("ID", "Outcome")
            and len(table) >= 2
            and table[1] == ["---", "---"]
        ):
            result.update(
                row[0]
                for row in table[2:]
                if len(row) == 2 and re.fullmatch(r"VO-\d{3}", row[0])
            )

    dossier = root / "docs/discovery" / scope_name
    for prefix, owner in DISCOVERY_OWNERS.items():
        try:
            text = _read_text(dossier / owner, root)
        except UnsafeSourceError:
            continue
        for table in _tables(text):
            header = tuple(table[0]) if table else ()
            if (
                header not in DISCOVERY_HEADERS[prefix]
                or len(table) < 2
                or table[1] != ["---"] * len(header)
            ):
                continue
            result.update(
                row[0]
                for row in table[2:]
                if len(row) == len(header)
                and re.fullmatch(rf"{prefix}-\d{{3}}", row[0])
            )
    return frozenset(result)


def _same_vp_document_trace_resolves(
    trace: str,
    *,
    root: Path,
    requirements: Path,
) -> bool:
    match = re.fullmatch(
        r"DOC:(?P<path>docs/[A-Za-z0-9_./-]+\.md)"
        r"#(?P<anchor>[a-z0-9]+(?:-[a-z0-9]+)*)",
        trace,
    )
    if match is None or ".." in Path(match.group("path")).parts:
        return False
    target = root / match.group("path")
    canonical_roots = (
        root / "docs/vision_of_product" / requirements.name,
        root / "docs/discovery" / requirements.name,
        requirements,
    )
    try:
        resolved = _contained(target, root)
        if target.is_symlink() or resolved != target.absolute():
            return False
        if not any(
            resolved.is_relative_to(scope.resolve())
            for scope in canonical_roots
        ):
            return False
        text = _read_text(target, root)
    except (OSError, UnsafeSourceError):
        return False
    visible = _visible_lines(text)
    for index, (line, is_visible) in enumerate(visible):
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if not is_visible or heading is None:
            continue
        anchor = re.sub(
            r"[-\s]+",
            "-",
            re.sub(r"[^\w -]", "", heading.group(2).strip().lower()),
        ).strip("-")
        if anchor != match.group("anchor"):
            continue
        level = len(heading.group(1))
        for candidate, candidate_visible in visible[index + 1 :]:
            next_heading = re.match(r"^(#{1,6})\s+", candidate)
            if (
                candidate_visible
                and next_heading
                and len(next_heading.group(1)) <= level
            ):
                break
            if candidate_visible and candidate.strip():
                return True
        return False
    return False


def _validate_requirement_row(
    row: Mapping[str, str],
    *,
    record: GateRecord,
    resolved_upstream: frozenset[str],
    context: str,
    root: Path,
    requirements: Path,
) -> list[Finding]:
    """Apply the shared current PR/QR row semantics."""

    findings: list[Finding] = []
    identifier = row.get("ID", "")
    if row.get("Schema version") != "1" or any(
        not value or PLACEHOLDER.search(value) for value in row.values()
    ):
        findings.append(
            _schema_finding(
                record,
                f"{context} {identifier!r} is incomplete or not schema version 1.",
                "Complete every requirement field using schema version 1.",
                record_id=identifier or record.name,
            )
        )
    if row.get("Impact") not in {"consequential", "low-impact"}:
        findings.append(
            _schema_finding(
                record,
                f"{context} {identifier!r} has invalid Impact "
                f"{row.get('Impact')!r}.",
                "Use exactly consequential or low-impact.",
                record_id=identifier or record.name,
            )
        )
    trace_value = row.get("Traces", "")
    traces = [
        item.strip() for item in trace_value.split(",")
        if item.strip()
    ]
    ids_resolve = bool(traces) and all(
        re.fullmatch(r"(?:VO|DQ|DEC|INV|RSK)-\d{3}", item) is not None
        and item in resolved_upstream
        for item in traces
    )
    document_resolves = (
        row.get("Impact") == "low-impact"
        and _same_vp_document_trace_resolves(
            trace_value,
            root=root,
            requirements=requirements,
        )
    )
    if (
        not traces
        or trace_value == "None"
        or not (ids_resolve or document_resolves)
    ):
        findings.append(
            _schema_finding(
                record,
                f"{context} {identifier!r} has a None, malformed, dangling, "
                "or cross-VP upstream trace.",
                "Add at least one resolving same-VP VO/DQ/DEC/INV/RSK trace.",
                record_id=identifier or record.name,
            )
        )
    return findings


def _requirement_rows(
    text: str,
    heading: str,
    *,
    record: GateRecord,
    resolved_upstream: frozenset[str],
    root: Path,
    requirements: Path,
) -> tuple[list[dict[str, str]], list[Finding]]:
    findings: list[Finding] = []
    body = _section(text, heading)
    if body is None:
        return [], findings
    candidates = [
        table for table in _tables(body) if tuple(table[0]) == REQUIREMENT_FIELDS
    ]
    if len(candidates) != 1:
        findings.append(
            _schema_finding(
                record,
                f"{heading} must contain exactly one canonical requirement table.",
                "Use the seven-column product-requirements schema exactly once.",
            )
        )
        return [], findings
    table = candidates[0]
    if (
        len(table) < 3
        or table[1] != ["---"] * len(REQUIREMENT_FIELDS)
    ):
        findings.append(
            _schema_finding(
                record,
                f"{heading} has no complete requirement row or separator.",
                "Add a valid separator and at least one complete requirement.",
            )
        )
        return [], findings
    expected_prefix = "PR" if heading == "## Functional requirements" else "QR"
    rows: list[dict[str, str]] = []
    for values in table[2:]:
        if len(values) != len(REQUIREMENT_FIELDS):
            findings.append(
                _schema_finding(
                    record,
                    f"{heading} contains a malformed requirement row.",
                    "Make every row match all seven canonical columns.",
                )
            )
            continue
        row = dict(zip(REQUIREMENT_FIELDS, values, strict=True))
        identifier = row["ID"]
        if not re.fullmatch(rf"{expected_prefix}-\d{{3}}", identifier):
            findings.append(
                _schema_finding(
                    record,
                    f"Requirement ID {identifier!r} is invalid in {heading}.",
                    f"Use the next unique {expected_prefix}-### ID.",
                    record_id=identifier or record.name,
                )
            )
        findings.extend(
            _validate_requirement_row(
                row,
                record=record,
                resolved_upstream=resolved_upstream,
                context="Requirement",
                root=root,
                requirements=requirements,
            )
        )
        rows.append(row)
    return rows, findings


def _metadata_table(
    text: str,
    *,
    expected_fields: Sequence[str],
) -> tuple[dict[str, str], list[str]] | None:
    """Return one canonical file-record metadata table.

    This parser is shared by lock admission and stage-gate validation so a
    record cannot pass the append-only check under a weaker interpretation of
    the owning contract.
    """

    candidates = [
        table for table in _tables(text) if table and table[0] == ["Field", "Value"]
    ]
    if (
        len(candidates) != 1
        or len(candidates[0]) < 2
        or not _is_separator(candidates[0][1], 2)
    ):
        return None
    rows = candidates[0][2:]
    if any(len(row) != 2 for row in rows):
        return None
    fields = [row[0] for row in rows]
    if tuple(fields) != tuple(expected_fields) or len(set(fields)) != len(fields):
        return None
    return {row[0]: row[1] for row in rows}, fields


def _comma_separated_ids(value: str, pattern: str) -> bool:
    return value == "None" or (
        bool(value)
        and all(
            re.fullmatch(pattern, item.strip()) is not None
            for item in value.split(",")
        )
    )


def _discovery_record_ids(dossier: Path, root: Path) -> set[str]:
    """Index IDs only from their canonical same-VP Discovery owners."""

    owners = {
        "DQ": "discovery-questions.md",
        "EV": "evidence-index.md",
        "ASM": "assumptions.md",
        "DEC": "decisions.md",
        "INV": "risks-and-failure-modes.md",
        "RSK": "risks-and-failure-modes.md",
        "DEF": "README.md",
    }
    found: set[str] = set()
    for prefix, relative in owners.items():
        try:
            text = _read_text(dossier / relative, root)
        except UnsafeSourceError:
            continue
        for table in _tables(text):
            if (
                not table
                or not table[0]
                or table[0][0] != "ID"
                or len(table) < 2
                or not _is_separator(table[1], len(table[0]))
            ):
                continue
            found.update(
                row[0]
                for row in table[2:]
                if len(row) == len(table[0])
                and re.fullmatch(rf"{prefix}-\d{{3}}", row[0])
            )
    experiments = dossier / "experiments"
    try:
        experiment_paths = (
            sorted(experiments.glob("EXP-*.md"))
            if experiments.is_dir() and not experiments.is_symlink()
            else []
        )
    except OSError:
        experiment_paths = []
    for path in experiment_paths:
        match = re.fullmatch(
            r"(EXP-(?:00[1-9]|0[1-9]\d|[1-9]\d{2}))"
            r"-[a-z0-9]+(?:-[a-z0-9]+)*\.md",
            path.name,
        )
        if match:
            found.add(match.group(1))
    return found


def validate_discovery_revision_collection(
    *,
    root: Path,
    dossier: Path,
    vp: str,
) -> _DRCollectionState:
    """Apply the canonical Discovery Revision contract to one VP collection."""

    findings: list[Finding] = []
    valid_paths: list[Path] = []
    accepted_paths: list[Path] = []
    evidence: dict[Path, str] = {}
    known_records = _discovery_record_ids(dossier, root)
    revisions = dossier / "revisions"
    try:
        paths = (
            sorted(revisions.glob("DR-*.md"), key=lambda item: item.name)
            if revisions.is_dir() and not revisions.is_symlink()
            else []
        )
    except OSError:
        paths = []

    expected_number = 1
    for path in paths:
        file = _display(path, root)
        filename = re.fullmatch(
            r"(DR-(?:00[1-9]|0[1-9]\d|[1-9]\d{2}))"
            r"-[a-z0-9]+(?:-[a-z0-9]+)*\.md",
            path.name,
        )
        record_id = filename.group(1) if filename else path.stem
        record = GateRecord(record_id, file, "metadata", {})
        start = len(findings)
        try:
            text = _read_text(path, root)
        except UnsafeSourceError as error:
            findings.append(
                _schema_finding(
                    record,
                    f"DR source is unavailable: {error}.",
                    "Restore the DR as a regular in-repository UTF-8 file.",
                )
            )
            continue
        # Accepted pre-schema revisions remain historical under QR-005. They
        # are protected by their immutable VP baseline, but are not rewritten
        # into the prospective schema-v1 form.
        if "| Schema version |" not in text:
            if filename and int(record_id.split("-")[1]) != expected_number:
                findings.append(
                    _schema_finding(
                        record,
                        f"DR sequence is not contiguous at {record_id}.",
                        f"Use DR-{expected_number:03d} as the next reserved ID.",
                    )
                )
            expected_number += 1
            known_records.add(record_id)
            continue

        visible = [line for line, shown in _visible_lines(text) if shown]
        h1 = [line for line in visible if line.startswith("# ")]
        first_content = next(
            (index for index, line in enumerate(visible) if line.strip()), None
        )
        if (
            filename is None
            or len(h1) != 1
            or not re.fullmatch(rf"# {re.escape(record_id)}: \S.*", h1[0])
        ):
            findings.append(
                _schema_finding(
                    record,
                    "DR filename and unique title do not carry the same canonical ID.",
                    "Use revisions/DR-###-<slug>.md and '# DR-###: <title>'.",
                )
            )
        if (
            first_content is None
            or first_content + 2 >= len(visible)
            or visible[first_content + 1] != ""
            or visible[first_content + 2] != "| Field | Value |"
        ):
            findings.append(
                _schema_finding(
                    record,
                    "DR metadata does not immediately follow its title.",
                    "Place one blank line and the metadata table directly after the H1.",
                )
            )
        if filename and int(record_id.split("-")[1]) != expected_number:
            findings.append(
                _schema_finding(
                    record,
                    f"DR sequence is not contiguous at {record_id}.",
                    f"Use DR-{expected_number:03d} as the next reserved ID.",
                )
            )
        expected_number += 1

        parsed = _metadata_table(text, expected_fields=DR_FIELDS)
        if parsed is None:
            findings.append(
                _schema_finding(
                    record,
                    "DR metadata is incomplete, duplicated, or out of order.",
                    "Restore every canonical DR field exactly once and in order.",
                )
            )
            continue
        metadata, _fields = parsed
        record = GateRecord(record_id, file, "metadata", metadata)
        if any(not metadata[field] or PLACEHOLDER.search(metadata[field]) for field in DR_FIELDS):
            findings.append(
                _schema_finding(
                    record,
                    "DR metadata contains a missing or unfilled value.",
                    "Complete every canonical DR field before recording a verdict.",
                )
            )
        if metadata["Schema version"] != "1":
            findings.append(
                _schema_finding(record, "DR Schema version is not 1.", "Use schema version 1.")
            )
        if metadata["Classification"] not in {
            "observed", "inferred", "hypothesis", "assumption",
            "preference", "decision", "unknown",
        }:
            findings.append(
                _schema_finding(
                    record,
                    "DR Classification is outside the canonical vocabulary.",
                    "Use observed, inferred, hypothesis, assumption, preference, decision, or unknown.",
                )
            )
        affected = [
            item.strip() for item in metadata["Affected records"].split(",")
            if item.strip() != "None"
        ]
        if (
            not affected
            or not _comma_separated_ids(
                metadata["Affected records"],
                r"(?:DQ|EV|ASM|DEC|INV|RSK|DEF|EXP|DR)-\d{3}",
            )
            or any(item not in known_records for item in affected)
        ):
            findings.append(
                _schema_finding(
                    record,
                    "DR Affected records are empty, malformed, forward, or outside the same VP.",
                    "Name one or more existing same-VP Discovery record IDs.",
                )
            )
        if not _comma_separated_ids(
            metadata["Downstream impact set"],
            r"(?:(?:PR|QR|ADR)-\d{3}|TH[1-9]\d*\.E[1-9]\d*\.US[1-9]\d*)",
        ):
            findings.append(
                _schema_finding(
                    record,
                    "DR Downstream impact set contains a malformed ID.",
                    "Use PR/QR/ADR/story IDs or the exact value None.",
                )
            )
        if not _comma_separated_ids(
            metadata["Invalidated gates"],
            r"(?:discovery|requirements|architecture|planning)",
        ):
            findings.append(
                _schema_finding(
                    record,
                    "DR Invalidated gates is outside the canonical gate vocabulary.",
                    "Use discovery, requirements, architecture, planning, or None.",
                )
            )
        if (
            not metadata["Actor"].startswith("Human: ")
            or len(metadata["Actor"].removeprefix("Human: ").strip()) < 2
        ):
            findings.append(
                _schema_finding(
                    record,
                    "DR Actor is not a completed attributable human identity.",
                    "Use Human: <name or accountable role>.",
                )
            )
        if not _valid_timestamp(metadata["Timestamp"]):
            findings.append(
                _schema_finding(
                    record,
                    "DR Timestamp is not ISO-8601 with an offset.",
                    "Record a real offset-aware human decision timestamp.",
                )
            )
        if not _scope_covers_vp(metadata["Scope"], vp):
            findings.append(
                _schema_finding(
                    record,
                    f"DR Scope does not cover {vp}.",
                    f"Record the exact {vp} revision scope.",
                )
            )
        verdict = metadata["Verdict"]
        if verdict not in {"Accepted", "Rejected"}:
            findings.append(
                _schema_finding(
                    record,
                    "DR Verdict is outside Accepted or Rejected.",
                    "Record the exact human verdict.",
                )
            )
        expected_disposition = {
            "Accepted": "accepted", "Rejected": "rejected"
        }.get(verdict)
        if metadata["Disposition"] != expected_disposition:
            findings.append(
                _schema_finding(
                    record,
                    "DR Disposition does not agree with its human verdict.",
                    "Use accepted for Accepted or rejected for Rejected.",
                )
            )
        if IMMUTABLE_REVISION.fullmatch(metadata["Source revision"]) is None:
            findings.append(
                _schema_finding(
                    record,
                    "DR Source revision is not immutable acceptance evidence.",
                    "Use git:<40 lowercase hex> or sha256:<64 lowercase hex>.",
                )
            )
        if len(findings) == start:
            valid_paths.append(path)
            evidence[path] = metadata["Source revision"]
            if verdict == "Accepted":
                accepted_paths.append(path)
        known_records.add(record_id)

    return _DRCollectionState(
        findings=tuple(findings),
        valid_paths=tuple(valid_paths),
        accepted_paths=tuple(accepted_paths),
        evidence=evidence,
    )


_ARCHITECTURE_CATEGORY = re.compile(
    r"(?i)\b(?:component|service|module|class|process|deployment unit|"
    r"database|storage engine|framework|library|programming language|"
    r"infrastructure product|endpoint|route|port|method signature|"
    r"function signature|class api|wire format|protocol message|"
    r"table layout|implementation schema|python|postgres(?:ql)?|mysql|"
    r"mongodb|redis|kafka|react|django|flask|grpc)\b"
)
_ARCHITECTURE_SELECTION = re.compile(
    r"(?i)\b(?:use|using|select|choose|implement(?:ed)? (?:with|as)|"
    r"deploy(?:ed)? as|store(?:d)? (?:in|by)|process(?:ed)? by|"
    r"expose|listen on|must be|shall be)\b"
)


def _selects_architecture(value: str) -> bool:
    """Conservatively detect an explicit architecture selection."""

    if re.search(
        r"(?i)(?:\b(?:GET|POST|PUT|PATCH|DELETE)\s+/[A-Za-z0-9_./{}-]+"
        r"|\bport\s+\d{1,5}\b"
        r"|\b(?:JSON|XML|protobuf|avro)\s+(?:wire\s+)?(?:format|schema)\b"
        r"|\b[A-Za-z_]\w*\([^()\n]*\)\s*(?:->|returns?\b))",
        value,
    ):
        return True
    if _ARCHITECTURE_CATEGORY.search(value) is None:
        return False
    return _ARCHITECTURE_SELECTION.search(value) is not None or re.search(
        r"(?i)\b(?:python|postgres(?:ql)?|mysql|mongodb|redis|kafka|react|"
        r"django|flask|grpc)\b.{0,40}\b(?:stores?|processes?|implements?|"
        r"serves?|exposes?|runs?)\b",
        value,
    ) is not None


def _evaluate_pcr_collection(
    *,
    root: Path,
    requirements: Path,
    prd_record: GateRecord,
    baseline_revision: str,
    vp: str,
    resolved_upstream: frozenset[str],
    baseline_gate_findings: Sequence[Finding],
) -> _PCRCollectionState:
    """Validate PCRs while deriving their effective approved state.

    A PCR can only become effective when the PRD gate that owns its baseline
    has itself passed complete gate validation.  Passing the findings into
    this shared computation prevents raw, unapproved, or stale baseline labels
    from becoming trusted merely because a PCR repeats the same value.
    """

    findings: list[Finding] = []
    baseline_gate_valid = not baseline_gate_findings
    changes = requirements / "changes"
    try:
        paths = (
            sorted(changes.glob("PCR-*.md"), key=lambda item: item.name)
            if changes.is_dir() and not changes.is_symlink()
            else []
        )
    except OSError:
        paths = []
    expected_number = 1
    effective_requirements: set[str] = set()
    applicable_pcrs: dict[str, Path] = {}
    valid_paths: list[Path] = []
    evidence: dict[Path, str] = {}
    prd_path = requirements / "PRD.md"
    try:
        prd_text = _read_text(prd_path, root)
    except UnsafeSourceError:
        prd_text = ""
    for heading in ("## Functional requirements", "## Quality requirements"):
        body = _section(prd_text, heading) or ""
        for table in _tables(body):
            if table and tuple(table[0]) == REQUIREMENT_FIELDS:
                effective_requirements.update(
                    row[0]
                    for row in table[2:]
                    if len(row) == len(REQUIREMENT_FIELDS)
                )
    reserved_requirements = set(effective_requirements)
    next_requirement_number = {
        prefix: max(
            (
                int(identifier.split("-", 1)[1])
                for identifier in reserved_requirements
                if identifier.startswith(f"{prefix}-")
            ),
            default=0,
        )
        + 1
        for prefix in ("PR", "QR")
    }
    for path in paths:
        file = _display(path, root)
        filename = re.fullmatch(
            r"(PCR-(?:00[1-9]|0[1-9]\d|[1-9]\d{2}))"
            r"-[a-z0-9]+(?:-[a-z0-9]+)*\.md",
            path.name,
        )
        record_id = filename.group(1) if filename else path.stem
        pcr_record = GateRecord(record_id, file, "metadata", {})
        try:
            text = _read_text(path, root)
        except UnsafeSourceError as error:
            findings.append(
                _schema_finding(
                    pcr_record,
                    f"PCR source is unavailable: {error}.",
                    "Restore the PCR as a regular in-repository UTF-8 file.",
                )
            )
            continue
        proposal_findings_start = len(findings)
        visible = [
            line for line, is_visible in _visible_lines(text) if is_visible
        ]
        h1 = [line for line in visible if line.startswith("# ")]
        if (
            filename is None
            or len(h1) != 1
            or not re.fullmatch(rf"# {re.escape(record_id)}: \S.*", h1[0])
        ):
            findings.append(
                _schema_finding(
                    pcr_record,
                    "PCR filename and unique title do not carry the same canonical ID.",
                    "Use changes/PCR-###-<slug>.md and '# PCR-###: <title>'.",
                )
            )
        first_content = next(
            (index for index, line in enumerate(visible) if line.strip()),
            None,
        )
        if (
            first_content is None
            or first_content + 2 >= len(visible)
            or visible[first_content + 1] != ""
            or visible[first_content + 2] != "| Field | Value |"
        ):
            findings.append(
                _schema_finding(
                    pcr_record,
                    "PCR metadata does not immediately follow its title.",
                    "Place one blank line and the metadata table directly after the H1.",
                )
            )
        if filename and int(record_id.split("-")[1]) != expected_number:
            findings.append(
                _schema_finding(
                    pcr_record,
                    f"PCR sequence is not contiguous at {record_id}.",
                    f"Use PCR-{expected_number:03d} as the next reserved ID.",
                )
            )
        expected_number += 1
        candidates = [
            table
            for table in _tables(text)
            if table and table[0] == ["Field", "Value"]
        ]
        if (
            len(candidates) != 1
            or len(candidates[0]) < 2
            or not _is_separator(candidates[0][1], 2)
        ):
            findings.append(
                _schema_finding(
                    pcr_record,
                    "PCR requires exactly one valid Field | Value metadata table.",
                    "Use the canonical PCR metadata table immediately after its title.",
                )
            )
            continue
        table = candidates[0]
        fields = [row[0] for row in table[2:] if len(row) == 2]
        metadata = {
            row[0]: row[1] for row in table[2:] if len(row) == 2
        }
        if tuple(fields) != PCR_FIELDS or any(
            not metadata.get(field) or PLACEHOLDER.search(metadata.get(field, ""))
            for field in PCR_FIELDS
        ):
            findings.append(
                _schema_finding(
                    pcr_record,
                    "PCR metadata is incomplete, duplicated, or out of order.",
                    "Restore every canonical PCR field exactly once and in order.",
                )
            )
            continue
        if metadata["Schema version"] != "1":
            findings.append(
                _schema_finding(
                    pcr_record,
                    "PCR Schema version is not 1.",
                    "Use the current PCR schema version 1.",
                )
            )
        architecture_fields = (
            "Change",
            "Discovery impact",
            "Architecture impact",
            "Migration impact",
            "Replanning impact",
        )
        if any(_selects_architecture(metadata[field]) for field in architecture_fields):
            findings.append(
                _schema_finding(
                    pcr_record,
                    "PCR selects an architecture category outside the product boundary.",
                    "State the observable product need and defer the design selection to Architecture.",
                )
            )
        operation = metadata["Requirement operation"]
        if operation not in {"add", "replace", "remove", "non-requirement"}:
            findings.append(
                _schema_finding(
                    pcr_record,
                    f"PCR Requirement operation {operation!r} is invalid.",
                    "Use add, replace, remove, or non-requirement.",
                )
            )
        id_fields = {
            "Affected PR": r"PR-\d{3}",
            "Affected QR": r"QR-\d{3}",
            "Affected decisions": r"DEC-\d{3}",
            "Affected assumptions": r"ASM-\d{3}",
            "Affected risks": r"RSK-\d{3}",
            "Affected themes": r"TH[1-9]\d*",
            "Supersedes": r"(?:PR|QR|PCR)-\d{3}",
        }
        for field, pattern in id_fields.items():
            value = metadata[field]
            if value != "None" and any(
                re.fullmatch(pattern, item.strip()) is None
                for item in value.split(",")
            ):
                findings.append(
                    _schema_finding(
                        pcr_record,
                        f"PCR field {field} contains a malformed ID list.",
                        f"Use comma-separated {pattern} IDs or None.",
                    )
                )
        if not _human_authority(metadata["Human actor"]):
            findings.append(
                _schema_finding(
                    pcr_record,
                    "PCR Human actor is not an allowed accountable human authority.",
                    "Use Human: product owner or Human: designer.",
                )
            )
        if not _valid_timestamp(metadata["Human timestamp"]):
            findings.append(
                _schema_finding(
                    pcr_record,
                    "PCR Human timestamp is not ISO-8601 with an offset.",
                    "Record a real offset-aware human approval timestamp.",
                )
            )
        if metadata["Human verdict"] not in {"Approved", "Rejected"}:
            findings.append(
                _schema_finding(
                    pcr_record,
                    "PCR Human verdict is outside Approved or Rejected.",
                    "Record the exact accountable human verdict.",
                )
            )
        expected_scope = (
            f"{vp} {record_id} proposed content against PRD baseline "
            f"{metadata['Baseline revision']}"
        )
        if metadata["Human scope"] != expected_scope:
            findings.append(
                _schema_finding(
                    pcr_record,
                    "PCR Human scope does not cover its exact proposal and baseline.",
                    f"Set Human scope to {expected_scope!r}.",
                )
            )
        if metadata["Baseline revision"] != baseline_revision:
            findings.append(
                _schema_finding(
                    pcr_record,
                    "PCR Baseline revision is stale or does not match the approved PRD.",
                    "Rebase the proposal on the exact approved PRD baseline.",
                )
            )
        all_tables = _tables(text)
        malformed_requirement_tables = [
            candidate
            for candidate in all_tables
            if candidate
            and (
                candidate[0][:1] == ["ID"]
                or "Requirement" in candidate[0]
            )
            and tuple(candidate[0]) != REQUIREMENT_FIELDS
        ]
        for _candidate in malformed_requirement_tables:
            findings.append(
                _schema_finding(
                    pcr_record,
                    "PCR proposed requirement table has non-canonical columns.",
                    "Use exactly ID, Schema version, Requirement, Measure, "
                    "Impact, Impact rationale, and Traces in that order.",
                )
            )
        replacement_rows = [
            dict(zip(REQUIREMENT_FIELDS, row, strict=True))
            for candidate in all_tables
            if candidate and tuple(candidate[0]) == REQUIREMENT_FIELDS
            for row in candidate[2:]
            if len(row) == len(REQUIREMENT_FIELDS)
        ]
        replacement_tables = [
            candidate
            for candidate in all_tables
            if candidate and tuple(candidate[0]) == REQUIREMENT_FIELDS
        ]
        replacement_ids: set[str] = set()
        for candidate in replacement_tables:
            if (
                len(candidate) < 3
                or candidate[1] != ["---"] * len(REQUIREMENT_FIELDS)
            ):
                findings.append(
                    _schema_finding(
                        pcr_record,
                        "PCR replacement table is empty or malformed.",
                        "Use the complete seven-column requirement schema.",
                    )
                )
            for row in candidate[2:]:
                if len(row) != len(REQUIREMENT_FIELDS):
                    findings.append(
                        _schema_finding(
                            pcr_record,
                            "PCR replacement row has the wrong number of fields.",
                            "Complete all seven requirement fields.",
                        )
                    )
                    continue
                values = dict(zip(REQUIREMENT_FIELDS, row, strict=True))
                identifier = values["ID"]
                identifier_match = re.fullmatch(
                    r"(?P<prefix>PR|QR)-(?P<number>\d{3})", identifier
                )
                if identifier_match is None:
                    findings.append(
                        _schema_finding(
                            pcr_record,
                            f"PCR proposed requirement {identifier!r} is malformed.",
                            "Use a unique PR/QR ID and complete schema version 1 row.",
                        )
                    )
                findings.extend(
                    _validate_requirement_row(
                        values,
                        record=pcr_record,
                        resolved_upstream=resolved_upstream,
                        context="PCR proposed requirement",
                        root=root,
                        requirements=requirements,
                    )
                )
                if any(
                    _selects_architecture(values[field])
                    for field in (
                        "Requirement",
                        "Measure",
                        "Impact rationale",
                    )
                ):
                    findings.append(
                        _schema_finding(
                            pcr_record,
                            f"PCR proposed requirement {identifier!r} selects architecture.",
                            "Rewrite it as implementation-neutral observable behavior.",
                            record_id=identifier or record_id,
                        )
                    )
                if identifier in reserved_requirements | replacement_ids:
                    findings.append(
                        _schema_finding(
                            pcr_record,
                            f"PCR proposed requirement ID {identifier!r} is reused.",
                            "Allocate the next unused VP-wide requirement ID.",
                        )
                    )
                if identifier_match is not None:
                    prefix = identifier_match.group("prefix")
                    expected_id = (
                        f"{prefix}-{next_requirement_number[prefix]:03d}"
                    )
                    if identifier != expected_id:
                        findings.append(
                            _schema_finding(
                                pcr_record,
                                f"PCR proposed requirement ID {identifier!r} "
                                f"is not the deterministic next ID {expected_id}.",
                                "Allocate IDs consecutively across the baseline "
                                "and every earlier proposal, regardless of verdict.",
                                record_id=identifier,
                            )
                        )
                    next_requirement_number[prefix] += 1
                replacement_ids.add(identifier)
        expected_revision = _pcr_revision(
            record_id, metadata, replacement_rows
        )
        if metadata["Source revision"] != expected_revision:
            findings.append(
                _schema_finding(
                    pcr_record,
                    "PCR Source revision is stale for its proposed content.",
                    "Recompute the proposal digest and obtain a new human verdict.",
                )
            )
        supersedes = (
            set()
            if metadata["Supersedes"] == "None"
            else {
                item.strip() for item in metadata["Supersedes"].split(",")
            }
        )
        superseded_requirements = {
            item for item in supersedes if item.startswith(("PR-", "QR-"))
        }
        superseded_pcrs = {
            item for item in supersedes if item.startswith("PCR-")
        }
        affected_requirements = {
            item.strip()
            for field in ("Affected PR", "Affected QR")
            for item in metadata[field].split(",")
            if item.strip() != "None"
        }
        non_effective_affected = (
            affected_requirements - effective_requirements
            if operation == "non-requirement"
            else set()
        )
        if non_effective_affected:
            findings.append(
                _schema_finding(
                    pcr_record,
                    "PCR non-requirement Affected PR/QR IDs do not resolve "
                    "in the immediately prior effective requirement state: "
                    + ", ".join(sorted(non_effective_affected))
                    + ".",
                    "Name only PR/QR IDs effective immediately before this "
                    "PCR; do not name dangling, removed, rejected-only, or "
                    "merely proposed IDs.",
                )
            )
        operation_valid = False
        if operation == "add":
            operation_valid = (
                bool(replacement_ids)
                and not supersedes
                and affected_requirements == replacement_ids
            )
        elif operation == "replace":
            superseded_prefixes = {
                item.split("-", 1)[0]
                for item in superseded_requirements
            }
            replacement_prefixes = {
                item.split("-", 1)[0] for item in replacement_ids
            }
            operation_valid = (
                bool(replacement_ids)
                and bool(superseded_requirements)
                and not superseded_pcrs
                and superseded_requirements <= effective_requirements
                and superseded_prefixes == replacement_prefixes
                and affected_requirements
                == superseded_requirements | replacement_ids
            )
        elif operation == "remove":
            operation_valid = (
                not replacement_ids
                and bool(superseded_requirements)
                and not superseded_pcrs
                and superseded_requirements <= effective_requirements
                and affected_requirements == superseded_requirements
            )
        elif operation == "non-requirement":
            operation_valid = (
                not replacement_ids
                and not superseded_requirements
                and superseded_pcrs <= applicable_pcrs.keys()
                and not non_effective_affected
            )
        if not operation_valid:
            findings.append(
                _schema_finding(
                    pcr_record,
                    "PCR operation, affected IDs, rows, and supersession do not agree.",
                    "Apply the canonical operation matrix to the effective PRD state.",
                )
            )
        reserved_requirements.update(replacement_ids)
        proposal_valid = len(findings) == proposal_findings_start
        if baseline_gate_valid and proposal_valid:
            valid_paths.append(path)
            evidence[path] = metadata["Source revision"]
        if (
            baseline_gate_valid
            and metadata["Human verdict"] == "Approved"
            and operation_valid
            and proposal_valid
        ):
            effective_requirements.difference_update(superseded_requirements)
            effective_requirements.update(replacement_ids)
            for superseded in superseded_pcrs:
                applicable_pcrs.pop(superseded)
            applicable_pcrs[record_id] = path
    return _PCRCollectionState(
        findings=tuple(findings),
        applicable_paths=tuple(applicable_pcrs.values()),
        valid_paths=tuple(valid_paths),
        evidence=evidence,
    )


def validate_product_change_collection(
    *,
    root: Path,
    requirements: Path,
    vp: str,
) -> _PCRCollectionState:
    """Validate PCRs through the same evaluator used by architecture gates."""

    prd = requirements / "PRD.md"
    record, text, fields, parse_findings = _parse_gate(
        prd, root, name="prd-approval", heading="## Approval"
    )
    if record is None or text is None:
        return _PCRCollectionState(tuple(parse_findings), (), (), {})
    baseline_findings, _legacy = _validate_prd_baseline_gate(
        record,
        fields,
        text,
        root=root,
        requirements=requirements,
        vp=vp,
        parse_findings=parse_findings,
    )
    state = _evaluate_pcr_collection(
        root=root,
        requirements=requirements,
        prd_record=record,
        baseline_revision=record.values.get("Source revision", ""),
        vp=vp,
        resolved_upstream=_same_vp_upstream_ids(root, requirements, vp),
        baseline_gate_findings=baseline_findings,
    )
    return _PCRCollectionState(
        findings=tuple([*baseline_findings, *state.findings]),
        applicable_paths=state.applicable_paths,
        valid_paths=state.valid_paths,
        evidence=state.evidence,
    )


def _validate_effective_prd(
    *,
    root: Path,
    requirements: Path,
    record: GateRecord,
    text: str,
    vp: str,
    baseline_gate_findings: Sequence[Finding],
) -> list[Finding]:
    """Apply the product-requirements schema before architecture admission."""

    findings: list[Finding] = []
    resolved_upstream = _same_vp_upstream_ids(root, requirements, vp)
    visible_lines = [
        line for line, is_visible in _visible_lines(text) if is_visible
    ]
    if visible_lines.count(f"# {vp} Product Requirements Document") != 1:
        findings.append(
            _schema_finding(
                record,
                "PRD must have exactly one canonical VP title.",
                f"Use exactly '# {vp} Product Requirements Document'.",
            )
        )
    identity = _identity_values(text)
    if tuple(identity) != PRD_IDENTITY_FIELDS:
        findings.append(
            _schema_finding(
                record,
                "PRD identity schema is incomplete or out of order.",
                "Restore all current product-requirements identity fields.",
            )
        )
    elif identity.get("Schema version") != "1":
        findings.append(
            _schema_finding(
                record,
                "PRD Schema version is not 1.",
                "Use the current PRD schema version 1.",
            )
        )
    if identity:
        for field in PRD_IDENTITY_FIELDS:
            if (
                not identity.get(field)
                or PLACEHOLDER.search(identity.get(field, ""))
            ):
                findings.append(
                    _schema_finding(
                        record,
                        f"PRD identity field {field} is missing or unfilled.",
                        f"Record a concrete {field} value.",
                    )
                )
        vision = identity.get("Vision", "")
        if re.fullmatch(
            rf"{re.escape(vp)}: [^;|\n]+; "
            rf"docs/vision_of_product/{re.escape(vp)}-[a-z0-9-]+/"
            rf"{re.escape(vp)}\.md",
            vision,
        ) is None:
            findings.append(
                _schema_finding(
                    record,
                    "PRD Vision identity does not resolve the same VP source.",
                    "Use '<VP>: <title>; docs/vision_of_product/<VP>-<slug>/<VP>.md'.",
                )
            )
        if identity.get("Status") != "Approved":
            findings.append(
                _schema_finding(
                    record,
                    "PRD identity Status is not Approved.",
                    "Complete approval and set Status to Approved.",
                )
            )
        try:
            date.fromisoformat(identity.get("Date", ""))
        except ValueError:
            findings.append(
                _schema_finding(
                    record,
                    "PRD identity Date is not a real ISO date.",
                    "Use a real YYYY-MM-DD date.",
                )
            )
        if re.fullmatch(
            r"(?:None|TH[1-9]\d*(?:, TH[1-9]\d*)*)",
            identity.get("Delivery mapping", ""),
        ) is None:
            findings.append(
                _schema_finding(
                    record,
                    "PRD Delivery mapping is malformed.",
                    "Use None or unique comma-separated TH<n> IDs.",
                )
            )
    headings = [
        line for line in visible_lines if re.fullmatch(r"## [^#].*", line)
    ]
    if (
        tuple(headings[: len(PRD_REQUIRED_SECTIONS)])
        != PRD_REQUIRED_SECTIONS
        or any(headings.count(item) != 1 for item in PRD_REQUIRED_SECTIONS)
    ):
        findings.append(
            _schema_finding(
                record,
                "PRD required sections are missing, duplicated, or out of order.",
                "Restore the complete ordered product-requirements section set.",
            )
        )
    for heading in PRD_REQUIRED_SECTIONS[1:]:
        body = _section(text, heading)
        if body is not None and not body.strip():
            findings.append(
                _schema_finding(
                    record,
                    f"PRD section {heading} is empty.",
                    "Complete the required section before approval.",
                )
            )
    seen: set[str] = set()
    for heading in ("## Functional requirements", "## Quality requirements"):
        rows, row_findings = _requirement_rows(
            text,
            heading,
            record=record,
            resolved_upstream=resolved_upstream,
            root=root,
            requirements=requirements,
        )
        findings.extend(row_findings)
        for row in rows:
            if row["ID"] in seen:
                findings.append(
                    _schema_finding(
                        record,
                        f"Requirement ID {row['ID']} is duplicated.",
                        "Keep each VP requirement ID unique.",
                        record_id=row["ID"],
                    )
                )
            seen.add(row["ID"])
    pcr_state = _evaluate_pcr_collection(
        root=root,
        requirements=requirements,
        prd_record=record,
        baseline_revision=record.values.get("Source revision", ""),
        vp=vp,
        resolved_upstream=resolved_upstream,
        baseline_gate_findings=baseline_gate_findings,
    )
    findings.extend(pcr_state.findings)
    return findings


def _validate_discovery_gate(
    record: GateRecord,
    fields: Sequence[str],
    text: str,
    *,
    root: Path,
    dossier: Path,
    vision: Path | None,
    requirements: Path | None,
    vp: str,
    as_of: datetime,
    material_scope_expanded: bool,
    occurred_lifecycle_events: frozenset[str],
    occurred_invalidation_conditions: frozenset[str],
) -> tuple[list[Finding], str]:
    disposition = record.values.get("Disposition")
    accepted_artifact_state = (
        _exact_source_state_digest(
            root, [vision, *sorted(dossier.rglob("*.md"))]
        )
        if vision is not None
        else None
    )
    legacy = _legacy_vp3_record(
        record,
        fields,
        vp,
        artifact_state=accepted_artifact_state,
    )
    expected = list(REQUIRED_GATE_FIELDS)
    if not legacy:
        expected.insert(3, "Disposition")
    if disposition == "WAIVED":
        expected.extend(("Expiry", "Invalidation"))
    findings = _validate_common_fields(
        record,
        fields,
        expected_fields=expected,
        legacy_vp3=legacy,
    )
    findings.extend(
        validate_discovery_revision_collection(
            root=root,
            dossier=dossier,
            vp=vp,
        ).findings
    )
    scope = record.values.get("Scope", "")
    if scope and not _scope_covers_vp(scope, vp):
        findings.append(
            _finding(
                file=record.file,
                record=record.name,
                message=f"Discovery Scope does not cover {vp}.",
                remediation=(
                    f"Have the human authority accept the exact {vp} "
                    "Discovery scope."
                ),
            )
        )

    if not legacy and disposition not in {
        "FULL",
        "LIGHTWEIGHT",
        "WAIVED",
    }:
        findings.append(
            _finding(
                file=record.file,
                record=record.name,
                message="Disposition is missing or outside FULL, LIGHTWEIGHT, WAIVED.",
                remediation="Record exactly one current Discovery disposition.",
            )
        )

    verdict = record.values.get("Verdict", "")
    if verdict not in DISCOVERY_VERDICTS:
        findings.append(
            _finding(
                file=record.file,
                record=record.name,
                message=f"Discovery verdict {verdict!r} is not valid.",
                remediation=(
                    "Have the human authority record READY, "
                    "READY_WITH_DEFERRALS, or BLOCKED."
                ),
            )
        )
    elif verdict == "BLOCKED":
        findings.append(
            _finding(
                file=record.file,
                record=record.name,
                message="Discovery verdict is BLOCKED and does not open a downstream gate.",
                remediation=(
                    "Resolve the blocking Discovery items and obtain a new "
                    "human READY or READY_WITH_DEFERRALS acceptance."
                ),
            )
        )

    revision = record.values.get("Source revision", "")
    expected_revision = (
        _discovery_revision(
            vision=vision,
            dossier=dossier,
            root=root,
            requirements=(
                requirements if disposition == "WAIVED" else None
            ),
        )
        if vision is not None
        else None
    )
    fresh = legacy
    if revision.startswith("sha256:"):
        fresh = expected_revision == revision
    elif revision.startswith("git:") and vision is not None:
        sources = [vision, *sorted(dossier.rglob("*.md"))]
        scope_paths: list[Path] = [vision, dossier]
        if disposition == "WAIVED" and requirements is not None:
            behavior_pcrs = _approved_behavior_pcr_paths(requirements, root)
            sources.extend(behavior_pcrs)
            scope_paths.extend(behavior_pcrs)
        fresh = _git_tree_matches(
            root,
            revision.removeprefix("git:"),
            sources,
            scope_paths=scope_paths,
            transform=lambda source, source_text: (
                _without_gate(source_text, ("## Acceptance",))
                if source == dossier / "README.md"
                else _strip_html_comments(source_text)
            ),
        )
    if revision and not fresh:
        findings.append(
            _finding(
                file=record.file,
                record=record.name,
                message="Discovery acceptance Source revision is stale or unverifiable.",
                remediation=(
                    "Revalidate the exact current Vision and Discovery state "
                    "and record its sha256 digest or a verifiable Git commit."
                ),
            )
        )

    if disposition == "WAIVED":
        expiry = record.values.get("Expiry", "")
        invalidation = record.values.get("Invalidation", "")
        active = True
        material_categories = frozenset(
            {
                "users",
                "outcomes",
                "behavior",
                "integrations",
                "data sensitivity",
                "authority",
                "risk",
                "delivery",
            }
        )
        if "material scope expansion" not in invalidation.casefold():
            active = False
            findings.append(
                _finding(
                    file=record.file,
                    record=record.name,
                    message="WAIVED Invalidation does not name material scope expansion.",
                    remediation=(
                        "Name material scope expansion and all specific "
                        "scope invalidation conditions."
                    ),
                )
            )
        if material_scope_expanded:
            active = False
            findings.append(
                _finding(
                    file=record.file,
                    record=record.name,
                    message="WAIVED Discovery is invalidated by material scope expansion.",
                    remediation=(
                        "Stop downstream work, reclassify Discovery as "
                        "LIGHTWEIGHT or FULL, and obtain a new human acceptance."
                    ),
                )
            )
        recorded_conditions = [
            re.sub(r"^or\s+", "", item.strip(), flags=re.IGNORECASE)
            for item in re.split(r"\s*,\s*|\s+\bor\b\s+", invalidation)
            if item.strip()
        ]
        occurred_normalized = {
            item.strip().casefold()
            for item in occurred_invalidation_conditions
            if item.strip()
        }
        occurred_categories = material_categories & occurred_normalized
        if occurred_categories:
            active = False
            findings.append(
                _finding(
                    file=record.file,
                    record=record.name,
                    message=(
                        "WAIVED Discovery is invalidated by material expansion "
                        "in "
                        + ", ".join(sorted(occurred_categories))
                        + "."
                    ),
                    remediation=(
                        "Stop downstream work and reclassify Discovery as "
                        "LIGHTWEIGHT or FULL for the expanded scope."
                    ),
                )
            )
        category_aliases = {
            "users": {"users", "new users", "user change"},
            "outcomes": {"outcomes", "new outcomes", "outcome change"},
            "behavior": {
                "behavior",
                "behaviour",
                "behavior change",
                "behaviour change",
                "scope behavior",
            },
            "integrations": {
                "integrations",
                "new integration",
                "integration change",
            },
            "data sensitivity": {
                "data sensitivity",
                "data-sensitivity change",
                "sensitive data change",
            },
            "authority": {
                "authority",
                "authority-boundary change",
                "authority boundary change",
            },
            "risk": {"risk", "risk change", "new risk"},
            "delivery": {
                "delivery",
                "delivery impact",
                "delivery change",
            },
        }
        for condition in recorded_conditions:
            normalized = condition.casefold()
            condition_categories = {
                category
                for category, aliases in category_aliases.items()
                if normalized in aliases
            }
            if (
                normalized in occurred_normalized
                or any(
                    category in occurred_normalized
                    for category in condition_categories
                )
            ):
                active = False
                findings.append(
                    _finding(
                        file=record.file,
                        record=record.name,
                        message=(
                            "WAIVED Discovery named Invalidation condition "
                            f"occurred: {condition}."
                        ),
                        remediation=(
                            "Stop downstream work and obtain a new FULL or "
                            "LIGHTWEIGHT Discovery acceptance."
                        ),
                    )
                )
        behavior_pcrs = _approved_behavior_pcr_paths(requirements, root)
        if behavior_pcrs and not fresh:
            active = False
            findings.append(
                _finding(
                    file=record.file,
                    record=record.name,
                    message=(
                        "WAIVED Discovery is invalidated by an effective "
                        "approved PCR behavior/scope change not covered by "
                        "the waiver acceptance source: "
                        + ", ".join(path.stem.split("-", 2)[0] + "-"
                                    + path.stem.split("-", 2)[1]
                                    for path in behavior_pcrs)
                        + "."
                    ),
                    remediation=(
                        "Reclassify Discovery or obtain a fresh human waiver "
                        "whose immutable source revision covers the exact "
                        "effective PCR state; None impact claims do not bypass "
                        "behavior invalidation."
                    ),
                )
            )
        expiry_active, expiry_message = _expiry_active(
            expiry, as_of=as_of, occurred=occurred_lifecycle_events
        )
        if not expiry_active:
            active = False
            findings.append(
                _finding(
                    file=record.file,
                    record=record.name,
                    message=expiry_message,
                    remediation=(
                        "Obtain a new bounded human waiver or reclassify "
                        "Discovery as LIGHTWEIGHT or FULL."
                    ),
                )
            )
        if not active:
            return findings, "invalid"

    return findings, "open" if not findings else "closed"


def _expiry_active(
    value: str,
    *,
    as_of: datetime,
    occurred: frozenset[str],
) -> tuple[bool, str]:
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        try:
            expiry_date = date.fromisoformat(value)
        except ValueError:
            return False, "WAIVED Expiry is not a real ISO date."
        if as_of.date() <= expiry_date:
            return True, ""
        return False, f"WAIVED Discovery expired after {value}."
    if _valid_timestamp(value):
        expiry = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if as_of.astimezone(timezone.utc) <= expiry.astimezone(timezone.utc):
            return True, ""
        return False, f"WAIVED Discovery expired at {value}."
    if LIFECYCLE_EXPIRY.fullmatch(value):
        if value in occurred:
            return False, f"WAIVED Discovery expired when {value.removeprefix('until ')} occurred."
        return True, ""
    return (
        False,
        "WAIVED Expiry is missing, malformed, or not a bounded lifecycle event.",
    )


def _validate_prd_baseline_gate(
    record: GateRecord,
    fields: Sequence[str],
    text: str,
    *,
    root: Path,
    requirements: Path,
    vp: str,
    parse_findings: Sequence[Finding] = (),
) -> tuple[list[Finding], bool]:
    """Validate every approval property required to trust a PCR baseline."""

    legacy = _legacy_vp3_record(
        record,
        fields,
        vp,
        artifact_state=_requirements_state_revision(
            root, requirements, requirements / "PRD.md"
        ),
    )
    findings = list(parse_findings)
    findings.extend(
        _validate_common_fields(
            record,
            fields,
            expected_fields=REQUIRED_GATE_FIELDS,
            legacy_vp3=legacy,
        )
    )
    verdict = record.values.get("Verdict", "")
    if verdict != "Approved":
        findings.append(
            _finding(
                file=record.file,
                record=record.name,
                message=f"PRD verdict {verdict!r} does not approve architecture entry.",
                remediation="Have the human authority issue an Approved PRD gate.",
            )
        )

    if not legacy:
        identity = _identity_values(text)
        expected_scope = f"{vp} PRD version {identity.get('Version', '')}"
        if record.values.get("Scope") != expected_scope:
            findings.append(
                _finding(
                    file=record.file,
                    record=record.name,
                    message=f"PRD Scope does not equal {expected_scope!r}.",
                    remediation="Record the exact VP and identity-table PRD version.",
                )
            )
        revision = record.values.get("Source revision", "")
        current_revision = _prd_revision(text)
        if not _revision_matches_text(
            root=root,
            path=requirements / "PRD.md",
            source_revision=revision,
            current_digest=current_revision,
            digest_text=_prd_revision,
        ):
            findings.append(
                _finding(
                    file=record.file,
                    record=record.name,
                    message="PRD approval Source revision is stale or unverifiable.",
                    remediation=(
                        "Recompute the complete submitted-PRD digest or use a "
                        "verifiable Git commit and renew human approval."
                    ),
                )
            )
    elif not _scope_covers_vp(record.values.get("Scope", ""), vp):
        findings.append(
            _finding(
                file=record.file,
                record=record.name,
                message=f"PRD Scope does not cover {vp}.",
                remediation=f"Obtain human PRD approval explicitly covering {vp}.",
            )
        )
    return findings, legacy


def _validate_prd_gate(
    record: GateRecord,
    fields: Sequence[str],
    text: str,
    *,
    root: Path,
    requirements: Path,
    vp: str,
    discovery: GateRecord | None,
    parse_findings: Sequence[Finding] = (),
) -> tuple[list[Finding], str]:
    baseline_findings, legacy = _validate_prd_baseline_gate(
        record,
        fields,
        text,
        root=root,
        requirements=requirements,
        vp=vp,
        parse_findings=parse_findings,
    )
    findings = list(baseline_findings)
    if not legacy:
        identity = _identity_values(text)
        if discovery is not None:
            cross_checks = {
                "Discovery verdict": discovery.values.get("Verdict"),
                "Discovery source revision": discovery.values.get(
                    "Source revision"
                ),
            }
            for field, expected in cross_checks.items():
                if identity.get(field) != expected:
                    findings.append(
                        _finding(
                            file=record.file,
                            record=record.name,
                            message=f"PRD identity {field} is stale or mismatched.",
                            remediation=(
                                f"Set {field} to the accepted same-VP Discovery "
                                "gate value and renew PRD approval."
                            ),
                        )
                    )
        findings.extend(
            _validate_effective_prd(
                root=root,
                requirements=requirements,
                record=record,
                text=text,
                vp=vp,
                baseline_gate_findings=baseline_findings,
            )
        )
    return findings, "open" if not findings else "closed"


def _validate_architecture_gate(
    record: GateRecord,
    fields: Sequence[str],
    *,
    root: Path,
    path: Path,
    vp: str,
) -> tuple[list[Finding], str]:
    legacy = _legacy_vp3_record(
        record,
        fields,
        vp,
        artifact_state=_exact_source_state_digest(
            root,
            [
                *sorted((root / "docs/architecture").rglob("*.md")),
                *sorted((root / "docs/ADRs").glob("ADR-*.md")),
            ],
        ),
    )
    findings = _validate_common_fields(
        record,
        fields,
        expected_fields=REQUIRED_GATE_FIELDS,
        legacy_vp3=legacy,
    )
    if record.section != "Approval" and not legacy:
        findings.append(
            _finding(
                file=record.file,
                record=record.name,
                message=(
                    "Canonical ## Approval architecture acceptance record "
                    "is missing."
                ),
                remediation=(
                    "Record prospective human architecture acceptance under "
                    "exactly one ## Approval section."
                ),
            )
        )
    verdict = record.values.get("Verdict", "")
    if verdict != "Accepted":
        findings.append(
            _finding(
                file=record.file,
                record=record.name,
                message=f"Architecture verdict {verdict!r} does not open planning.",
                remediation="Obtain human architecture acceptance with verdict Accepted.",
            )
        )
    scope = record.values.get("Scope", "")
    if scope and not _scope_covers_vp(scope, vp):
        findings.append(
            _finding(
                file=record.file,
                record=record.name,
                message=f"Architecture Scope does not cover {vp}.",
                remediation=f"Obtain an Accepted architecture record covering {vp}.",
            )
        )
    if not legacy:
        revision = record.values.get("Source revision", "")
        expected_revision = _architecture_revision(root, path)
        sources = [
            *sorted((root / "docs/architecture").rglob("*.md")),
            *sorted((root / "docs/ADRs").glob("ADR-*.md")),
        ]
        fresh = revision == expected_revision
        if revision.startswith("git:"):
            fresh = _git_tree_matches(
                root,
                revision.removeprefix("git:"),
                sources,
                scope_paths=(
                    root / "docs/architecture",
                    root / "docs/ADRs",
                ),
                transform=lambda source, source_text: (
                    _without_gate(
                        source_text, ("## Approval", "## Acceptance")
                    )
                    if source == path
                    else _strip_html_comments(source_text)
                ),
            )
        if not fresh:
            findings.append(
                _finding(
                    file=record.file,
                    record=record.name,
                    message=(
                        "Architecture Source revision is stale or does not "
                        "cover the deterministic architecture and ADR state."
                    ),
                    remediation=(
                        "Digest the complete current architecture/ADR source "
                        "set or reference a verifiable immutable Git commit, "
                        "then renew acceptance."
                    ),
                )
            )
    return findings, "open" if not findings else "closed"


def _read_working(
    source: Path | None,
    root: Path,
    *,
    source_kind: str = "discovery",
) -> tuple[dict[str, object] | None, list[Finding]]:
    if source is None:
        return None, []
    readme = source / "README.md"
    try:
        text = _read_text(readme, root)
    except UnsafeSourceError:
        return None, []
    return _working_state(
        text,
        file=_display(readme, root),
        source_kind=source_kind,
    )


def _read_prd_working(
    requirements: Path | None, root: Path
) -> tuple[dict[str, object] | None, list[Finding]]:
    if requirements is None:
        return None, []
    prd = requirements / "PRD.md"
    try:
        text = _read_text(prd, root)
    except UnsafeSourceError:
        return None, []
    return _working_state(
        text,
        file=_display(prd, root),
        source_kind="prd",
    )


def _authoritative_waiver_invalidations(
    dossier: Path | None,
    requirements: Path | None,
    root: Path,
) -> frozenset[str]:
    """Derive scope changes from accepted structured Discovery revisions.

    Free-form keyword scanning is deliberately avoided.  The affected-record,
    and invalidated-gate fields are the authoritative declarations from which
    the finite material-expansion categories are derived.  Effective behavior
    PCRs are handled by exact source-state coverage in the waiver validator.
    """

    del requirements
    occurred: set[str] = set()
    if dossier is not None:
        revisions = dossier / "revisions"
        try:
            paths = (
                sorted(revisions.glob("DR-*.md"), key=lambda item: item.name)
                if revisions.is_dir() and not revisions.is_symlink()
                else []
            )
        except OSError:
            paths = []
        for path in paths:
            try:
                text = _read_text(path, root)
            except UnsafeSourceError:
                continue
            for table in _tables(text):
                if (
                    not table
                    or table[0] != ["Field", "Value"]
                    or len(table) < 2
                    or not _is_separator(table[1], 2)
                ):
                    continue
                values = {
                    row[0]: row[1] for row in table[2:] if len(row) == 2
                }
                if values.get("Verdict") != "Accepted":
                    continue
                invalidated = values.get("Invalidated gates", "None")
                if invalidated != "None":
                    occurred.add("material scope expansion")
                    occurred.update(
                        item.strip().casefold()
                        for item in invalidated.split(",")
                        if item.strip()
                    )
                affected = values.get("Affected records", "None")
                prefixes = {
                    item.strip().split("-", 1)[0]
                    for item in affected.split(",")
                    if "-" in item
                }
                if "VO" in prefixes:
                    occurred.update({"outcomes", "material scope expansion"})
                if "RSK" in prefixes:
                    occurred.update({"risk", "material scope expansion"})

    return frozenset(occurred)


def _repository_lifecycle_events(root: Path, vp: str) -> frozenset[str]:
    """Derive only lifecycle events represented by local authoritative state."""

    events: set[str] = set()
    plan = root / "docs/plan"
    try:
        resolved_plan = _contained(plan, root)
        if plan.is_symlink() or resolved_plan != plan.absolute():
            return frozenset()
        release_files = sorted(plan.glob("RELEASE-TH*.md"))
    except (OSError, UnsafeSourceError):
        release_files = []
    for path in release_files:
        match = re.fullmatch(r"RELEASE-(TH[1-9][0-9]*)\.md", path.name)
        if match:
            events.add(f"until {match.group(1)} release")

    backlog_path = plan / "backlog.yaml"
    try:
        text = _read_text(backlog_path, root)
        document = yaml.safe_load(text)
    except (UnsafeSourceError, yaml.YAMLError, RecursionError):
        return frozenset(events)
    if not isinstance(document, dict) or not isinstance(
        document.get("backlog"), dict
    ):
        return frozenset(events)
    backlog = document["backlog"]
    accepted_themes: set[str] = set()
    mapped: list[bool] = []
    active = backlog.get("active-themes", [])
    if isinstance(active, list):
        for theme in active:
            if not isinstance(theme, dict):
                continue
            theme_id = theme.get("id")
            accepted = theme.get("locked") is True
            if isinstance(theme_id, str) and accepted:
                accepted_themes.add(theme_id)
            vision_ref = theme.get("vision-ref")
            if isinstance(vision_ref, str) and f"/{vp}-" in vision_ref:
                mapped.append(accepted)
    archived = backlog.get("archived-themes", [])
    if isinstance(archived, list):
        for theme in archived:
            if not isinstance(theme, dict):
                continue
            theme_id = theme.get("id")
            if isinstance(theme_id, str) and re.fullmatch(
                r"TH[1-9][0-9]*", theme_id
            ):
                accepted_themes.add(theme_id)
    events.update(f"until {theme} acceptance" for theme in accepted_themes)
    if mapped and all(mapped):
        events.add(f"until {vp} acceptance")
    return frozenset(events)


def validate_repository(
    repository_root: Path,
    *,
    vp: str,
    stage: str,
    as_of: datetime | None = None,
    material_scope_expanded: bool = False,
    occurred_lifecycle_events: frozenset[str] | None = None,
    occurred_invalidation_conditions: frozenset[str] | None = None,
) -> ValidationResult:
    """Validate only the formal upstream gate(s) for ``stage``.

    Discovery is intentionally different: Vision is the lifecycle root, so
    its entry check verifies that the Vision artefact exists and reports any
    Discovery working state.  It does not require Discovery's own completion
    gate.  Requirements validates that completion gate.
    """

    root = repository_root.resolve()
    now = as_of or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("as_of must be an offset-aware datetime")
    occurred = _repository_lifecycle_events(root, vp) | (
        occurred_lifecycle_events or frozenset()
    )
    occurred_invalidations = occurred_invalidation_conditions or frozenset()
    findings: list[Finding] = []
    upstream: list[dict[str, object]] = []

    # Planning has exactly one formal upstream gate.  In particular, it does
    # not re-resolve Discovery or PRD as substitutes for architecture
    # acceptance.
    if stage == "planning":
        architecture = root / "docs/architecture/README.md"
        record, _text, fields, gate_findings = _parse_architecture_gate(
            architecture, root
        )
        findings.extend(gate_findings)
        if record is not None:
            validation, state = _validate_architecture_gate(
                record, fields, root=root, path=architecture, vp=vp
            )
            findings.extend(validation)
            upstream.append(record.as_payload(state))
        payload: dict[str, object] = {
            "command": "validate",
            "check": CHECK,
            "status": "failed" if findings else "ok",
            "vp": vp,
            "stage": stage,
            "stage_entry": "closed" if findings else "open",
            "upstream_gates": upstream,
            "working_state": None,
            "findings": findings,
        }
        return ValidationResult(payload, tuple(findings))

    if stage == "discovery":
        vision_scope, scope_findings = _resolve_scope(
            root,
            "docs/vision_of_product",
            vp,
            required=True,
            record="vision-sketch",
        )
        findings.extend(scope_findings)
        vision = (
            vision_scope / f"{vp}.md"
            if vision_scope is not None
            else None
        )
        if vision is not None:
            try:
                _read_text(vision, root)
            except UnsafeSourceError as error:
                findings.append(
                    _finding(
                        file=_display(vision, root),
                        record="vision-sketch",
                        message=f"Vision sketch is unavailable: {error}.",
                        remediation=(
                            f"Restore the canonical {vp}.md as a regular "
                            "UTF-8 file inside its Vision scope."
                        ),
                    )
                )
            else:
                upstream.append(
                    {
                        "name": "vision-sketch",
                        "file": _display(vision, root),
                        "status": "present",
                        "formal_gate": False,
                    }
                )

        discovery_entry_open = not findings
        dossier, dossier_findings = _resolve_scope(
            root,
            "docs/discovery",
            vp,
            required=False,
            record="discovery-readiness",
        )
        completion_findings: list[Finding] = list(dossier_findings)
        completion_requirements, _ = _resolve_scope(
            root,
            "docs/requirements",
            vp,
            required=False,
            record="prd-approval",
        )
        working_state, working_findings = _read_working(dossier, root)
        completion_findings.extend(working_findings)
        active = (
            working_state is not None
            and working_state["status"] in ACTIVE_WORKING_STATUSES
        )
        downstream_gate: dict[str, object] = {
            "stage": "requirements",
            "status": "closed",
            "reason": (
                "Discovery is paused and requires its recorded next action."
                if active
                else "Requirements opens only after human Discovery acceptance."
            ),
        }
        if dossier is not None and not active:
            readme = dossier / "README.md"
            try:
                dossier_text = _read_text(readme, root)
            except UnsafeSourceError:
                dossier_text = ""
            if _sections(dossier_text, "## Acceptance"):
                record, text, fields, gate_findings = _parse_gate(
                    readme,
                    root,
                    name="discovery-readiness",
                    heading="## Acceptance",
                )
                completion_findings.extend(gate_findings)
                if record is not None and text is not None:
                    authoritative = _authoritative_waiver_invalidations(
                        dossier, None, root
                    )
                    gate_validation, gate_state = _validate_discovery_gate(
                        record,
                        fields,
                        text,
                        root=root,
                        dossier=dossier,
                        vision=vision,
                        requirements=completion_requirements,
                        vp=vp,
                        as_of=now,
                        material_scope_expanded=material_scope_expanded,
                        occurred_lifecycle_events=occurred,
                        occurred_invalidation_conditions=(
                            occurred_invalidations | authoritative
                        ),
                    )
                    completion_findings.extend(gate_validation)
                    downstream_gate = {
                        "stage": "requirements",
                        **record.as_payload(gate_state),
                    }
        if completion_findings:
            downstream_gate = {
                **downstream_gate,
                "status": "closed",
                "findings": completion_findings,
            }
        payload = {
            "command": "validate",
            "check": CHECK,
            "status": "failed" if findings else "ok",
            "vp": vp,
            "stage": stage,
            "stage_entry": "open" if discovery_entry_open else "closed",
            "upstream_gates": upstream,
            "working_state": working_state,
            "downstream_gate": downstream_gate,
            "findings": findings,
            "completion_findings": completion_findings,
        }
        return ValidationResult(payload, tuple(findings))

    dossier, dossier_findings = _resolve_scope(
        root,
        "docs/discovery",
        vp,
        required=True,
        record="discovery-readiness",
    )
    findings.extend(dossier_findings)
    vision = (
        root / "docs/vision_of_product" / dossier.name / f"{vp}.md"
        if dossier is not None
        else None
    )
    if vision is not None:
        try:
            _read_text(vision, root)
        except UnsafeSourceError:
            vision = None
    working_state, working_findings = _read_working(dossier, root)
    findings.extend(working_findings)
    requirements_for_invalidations, _ = _resolve_scope(
        root,
        "docs/requirements",
        vp,
        required=False,
        record="prd-approval",
    )

    discovery_record: GateRecord | None = None
    if dossier is not None:
        readme = dossier / "README.md"
        record, text, fields, gate_findings = _parse_gate(
            readme,
            root,
            name="discovery-readiness",
            heading="## Acceptance",
        )
        findings.extend(gate_findings)
        if record is not None and text is not None:
            discovery_record = record
            authoritative = _authoritative_waiver_invalidations(
                dossier, requirements_for_invalidations, root
            )
            validation, state = _validate_discovery_gate(
                record,
                fields,
                text,
                root=root,
                dossier=dossier,
                vision=vision,
                requirements=requirements_for_invalidations,
                vp=vp,
                as_of=now,
                material_scope_expanded=material_scope_expanded,
                occurred_lifecycle_events=occurred,
                occurred_invalidation_conditions=(
                    occurred_invalidations | authoritative
                ),
            )
            findings.extend(validation)
            if (
                working_state is not None
                and working_state["status"] in ACTIVE_WORKING_STATUSES
            ):
                findings.append(
                    _finding(
                        file=record.file,
                        record="working-state",
                        message=(
                            "Discovery is still in a working state and cannot "
                            f"open {stage}."
                        ),
                        remediation=(
                            "Complete the listed open items and next action, "
                            "set Working state to accepted or remove it, and "
                            "renew human acceptance if the source changed."
                        ),
                    )
                )
                state = "closed"
            upstream.append(record.as_payload(state))

    if stage == "requirements":
        payload = {
            "command": "validate",
            "check": CHECK,
            "status": "failed" if findings else "ok",
            "vp": vp,
            "stage": stage,
            "stage_entry": "closed" if findings else "open",
            "upstream_gates": upstream,
            "gate": upstream[-1] if discovery_record is not None else None,
            "working_state": working_state,
            "findings": findings,
        }
        return ValidationResult(payload, tuple(findings))

    requirements, requirements_findings = _resolve_scope(
        root,
        "docs/requirements",
        vp,
        required=True,
        record="prd-approval",
    )
    findings.extend(requirements_findings)
    prd_working_state, prd_working_findings = _read_prd_working(
        requirements, root
    )
    findings.extend(prd_working_findings)
    if dossier is not None and requirements is not None:
        if dossier.name.removeprefix(f"{vp}-") != requirements.name.removeprefix(
            f"{vp}-"
        ):
            findings.append(
                _finding(
                    file=_display(requirements, root),
                    record="prd-approval",
                    message="Discovery and requirements scopes use different VP slugs.",
                    remediation=(
                        "Use matching canonical VP number and slug directories "
                        "for Vision, Discovery, and requirements."
                    ),
                )
            )

    if requirements is not None:
        prd = requirements / "PRD.md"
        record, text, fields, gate_findings = _parse_gate(
            prd, root, name="prd-approval", heading="## Approval"
        )
        if record is not None and text is not None:
            validation, state = _validate_prd_gate(
                record,
                fields,
                text,
                root=root,
                requirements=requirements,
                vp=vp,
                discovery=discovery_record,
                parse_findings=gate_findings,
            )
            findings.extend(validation)
            upstream.append(record.as_payload(state))
        else:
            findings.extend(gate_findings)

    if (
        prd_working_state is not None
        and prd_working_state["status"] in ACTIVE_WORKING_STATUSES
    ):
        open_item_values = prd_working_state["open_items"]
        open_items = ", ".join(
            str(item)
            for item in (
                open_item_values
                if isinstance(open_item_values, list)
                else []
            )
        )
        next_action = str(prd_working_state["next_action"])
        findings.append(
            _finding(
                file=(
                    _display(requirements / "PRD.md", root)
                    if requirements is not None
                    else f"docs/requirements/{vp}-<slug>/PRD.md"
                ),
                record="prd-working-state",
                message=(
                    f"PRD is {prd_working_state['status']} with open items "
                    f"{open_items}; architecture is blocked. Next action: "
                    f"{next_action}"
                ),
                remediation=(
                    "Complete the owned PRD items and concrete next action, "
                    "set Working state to accepted or remove it, then renew "
                    "approval for the resulting exact PRD."
                ),
            )
        )

    if stage == "architecture":
        if any(
            finding["record"] in {"discovery-readiness", "working-state"}
            for finding in findings
        ):
            findings.append(
                _finding(
                    file=(
                        _display(dossier / "README.md", root)
                        if dossier is not None
                        else f"docs/discovery/{vp}-<slug>/README.md"
                    ),
                    record="architecture-entry",
                    message=(
                        "Architecture cannot begin before an accepted "
                        "readiness verdict (READY or READY_WITH_DEFERRALS)."
                    ),
                    remediation=(
                        "Resolve Discovery findings and obtain attributable "
                        "human readiness acceptance before architecture."
                    ),
                )
            )
        payload = {
            "command": "validate",
            "check": CHECK,
            "status": "failed" if findings else "ok",
            "vp": vp,
            "stage": stage,
            "stage_entry": "closed" if findings else "open",
            "upstream_gates": upstream,
            "working_state": working_state,
            "working_states": {
                "discovery": working_state,
                "prd": prd_working_state,
            },
            "findings": findings,
        }
        return ValidationResult(payload, tuple(findings))

    raise AssertionError(f"unhandled gate stage: {stage}")


__all__ = [
    "Finding",
    "GateRecord",
    "STAGES",
    "ValidationResult",
    "validate_repository",
]
