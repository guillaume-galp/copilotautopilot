"""Deterministic validation of declared lifecycle traceability.

Markdown and YAML are untrusted input.  This module only performs bounded,
inert parsing; it never imports or executes repository content.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Mapping, Sequence

import yaml

from methodlib import records
from methodlib.backlog import UniqueKeyLoader


Finding = dict[str, object]
PathValue = str | os.PathLike[str]

CHECK = "trace"
SKILL_PATH = Path(".github/skills/bdd-stories/SKILL.md")
BACKLOG_PATH = Path("docs/plan/backlog.yaml")
ARCHITECTURE_TRACE_PATH = Path("docs/architecture/README.md")
CONTRACT_START = "<!-- traceability-contract:start -->"
CONTRACT_END = "<!-- traceability-contract:end -->"
ARCHITECTURE_TRACE_START = "<!-- architecture-trace:start -->"
ARCHITECTURE_TRACE_END = "<!-- architecture-trace:end -->"
MAX_TEXT_BYTES = 2 * 1024 * 1024

EXPECTED_CONTRACT: Mapping[str, object] = {
    "contract-version": 1,
    "frontmatter-key": "traceability",
    "required-story-types": ["standard", "spike"],
    "empty-allowed-story-types": ["trivial"],
    "keys": {
        "vision": {"prefixes": ["VO"]},
        "requirements": {"prefixes": ["PR", "QR"]},
        "adrs": {"prefixes": ["ADR"]},
        "invariants": {"prefixes": ["INV"]},
    },
}

ID_PATTERN = re.compile(
    r"(?:VO|DQ|EXP|EV|ASM|DEC|INV|RSK|DEF|PR|QR|ADR)-"
    r"(?:00[1-9]|0[1-9][0-9]|[1-9][0-9]{2})"
    r"|TH[1-9][0-9]*\.E[1-9][0-9]*\.US[1-9][0-9]*"
)
ADR_PATTERN = re.compile(
    r"ADR-(?:00[1-9]|0[1-9][0-9]|[1-9][0-9]{2})"
)
VP_PATTERN = re.compile(r"VP[1-9][0-9]*")
DOC_PATTERN = re.compile(
    r"DOC:(?P<path>docs/[A-Za-z0-9._/-]+\.md)#"
    r"(?P<anchor>[a-z0-9]+(?:-[a-z0-9]+)*)"
)
GRAPH_STAGE = {
    "VO": 0,
    "DQ": 1,
    "EXP": 2,
    "EV": 2,
    "ASM": 2,
    "DEC": 2,
    "INV": 2,
    "RSK": 2,
    "DEF": 2,
    "DR": 2,
    "PR": 3,
    "QR": 3,
    "prd": 3,
    "PCR": 3,
    "ADR": 4,
    "component": 4,
    "story": 5,
    "evidence": 6,
}
GRAPH_PREFIXES = frozenset(
    {
        "VO", "DQ", "EXP", "EV", "ASM", "DEC", "INV", "RSK", "DEF",
        "PR", "QR", "ADR",
    }
)
EVIDENCE_KEYS = ("packets", "verification", "review", "gitflow", "usage")
IMPLEMENTED_STORY_STATUSES = frozenset({"in-progress", "done"})
EVIDENCE_PATH_PATTERN = re.compile(r"[A-Za-z0-9._/-]+")
COMPONENT_REFERENCE_PATTERN = re.compile(
    r"docs/architecture/components\.md#"
    r"[a-z0-9]+(?:-[a-z0-9]+)*"
)
ARCHITECTURE_RECORD_PREFIXES = frozenset(
    {"DQ", "EXP", "EV", "ASM", "DEC", "INV", "RSK", "DEF", "PR", "QR"}
)
RESERVED_PACKET_PATTERN = re.compile(
    r"docs/plan/runtime/packets/"
    r"(?P<story>TH[1-9][0-9]*\.E[1-9][0-9]*\.US[1-9][0-9]*)/"
)
EXP_FILE_PATTERN = re.compile(
    r"(?P<id>EXP-(?:00[1-9]|0[1-9][0-9]|[1-9][0-9]{2}))"
    r"-[a-z0-9]+(?:-[a-z0-9]+)*\.md"
)
EXP_CLAIM_PATTERN = re.compile(r"(?P<id>EXP-[A-Za-z0-9]+)")
EXP_SCHEMA = (
    "Schema version", "Classification", "Question", "Method", "Budget",
    "Stop condition", "Outcome", "Evidence", "Supports", "Provenance",
    "Confidence / limitations", "Owner", "Disposition",
)
VP3_LEGACY_EXP_SCHEMA = ("Outcome", "Question", "Method", "Stop condition")

# A record is indexable only when both its owning file and complete table
# header match one of these prospective or accepted legacy schemas.  This
# deliberately does not treat a matching-looking ID elsewhere as a record.
CANONICAL_DISCOVERY_SCHEMAS: Mapping[str, tuple[tuple[str, ...], ...]] = {
    "DQ": (
        (
            "ID", "Schema version", "Traces", "Question", "Consequence",
            "Method", "Budget", "Stop condition", "Outcome",
            "Resolved records", "Classification", "Provenance",
            "Confidence / limitations", "Owner", "Disposition",
        ),
        (
            "ID", "Vision outcomes", "Question", "Consequence", "Outcome",
            "Resolved by",
        ),
        ("ID", "Question"),
    ),
    "EV": (
        (
            "ID", "Schema version", "Evidence", "Supports",
            "Source revision", "Method", "Observed at", "Reproduction notes",
            "Classification", "Provenance", "Confidence / limitations",
            "Owner", "Disposition",
        ),
        ("ID", "Classification", "Evidence", "Supports"),
    ),
    "ASM": (
        (
            "ID", "Schema version", "Statement", "Evidence", "Impact",
            "Invalidation", "Traces", "Classification", "Provenance",
            "Confidence / limitations", "Owner", "Disposition",
        ),
        (
            "ID", "Classification", "Statement", "Evidence",
            "Status / invalidation",
        ),
    ),
    "DEC": (
        (
            "ID", "Schema version", "Decision", "Rationale", "Consequence",
            "Alternatives", "Traces", "Classification", "Provenance",
            "Confidence / limitations", "Owner", "Disposition",
        ),
        ("ID", "Decision", "Consequence"),
        ("ID", "Decision"),
    ),
    "INV": (
        (
            "ID", "Schema version", "Invariant", "Rationale",
            "Failure consequence", "Traces", "Classification", "Provenance",
            "Confidence / limitations", "Owner", "Disposition",
        ),
        ("ID", "Invariant"),
    ),
    "RSK": (
        (
            "ID", "Schema version", "Risk", "Impact", "Likelihood",
            "Treatment", "Trigger", "Traces", "Classification", "Provenance",
            "Confidence / limitations", "Owner", "Disposition",
        ),
        ("ID", "Risk", "Impact", "Treatment"),
        ("ID", "Risk"),
    ),
    "DEF": (
        (
            "ID", "Schema version", "Deferral", "Reason", "Impact", "Trigger",
            "Treatment", "Traces", "Classification", "Provenance",
            "Confidence / limitations", "Owner", "Disposition",
        ),
        ("ID", "Deferral", "Required disposition"),
    ),
}
DISCOVERY_OWNER = {
    "DQ": "discovery-questions.md",
    "EV": "evidence-index.md",
    "ASM": "assumptions.md",
    "DEC": "decisions.md",
    "INV": "risks-and-failure-modes.md",
    "RSK": "risks-and-failure-modes.md",
    "DEF": "README.md",
}
VISION_SCHEMAS = (("ID", "Outcome"),)
PRD_VISION_HEADINGS = frozenset({"Vision outcomes", "2. Vision outcomes"})
PRD_DEFERRAL_HEADINGS = frozenset(
    {"Constraints and deferrals", "12. Constraints and accepted deferrals"}
)
PRD_DEFERRAL_REFERENCE_SCHEMAS = frozenset(
    {
        ("ID", "Constraint or deferral"),
        ("Constraint or DEF ID", "Product effect"),
    }
)
REQUIREMENT_SCHEMAS: Mapping[str, tuple[tuple[str, ...], ...]] = {
    "PR": (
        (
            "ID", "Schema version", "Requirement", "Measure", "Impact",
            "Impact rationale", "Traces",
        ),
        ("ID", "Requirement", "Traces"),
    ),
    "QR": (
        (
            "ID", "Schema version", "Requirement", "Measure", "Impact",
            "Impact rationale", "Traces",
        ),
        ("ID", "Requirement"),
    ),
}


class ContractError(ValueError):
    """The canonical traceability contract cannot be loaded safely."""


class InertYamlLoader(UniqueKeyLoader):
    """Duplicate-safe loader which also rejects YAML aliases."""

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
class Node:
    identifier: str
    kind: str
    file: str
    record: str
    scope: str | None
    consequential: bool = False

    @property
    def stage(self) -> int:
        return GRAPH_STAGE[self.kind]


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    scope: str | None = None

    def sort_key(self) -> tuple[str, str, str]:
        return self.scope or "", self.source, self.target


@dataclass(frozen=True)
class StorySource:
    path: Path
    expected_id: str | None
    scope: str | None
    evidence: Mapping[str, object]
    status: str | None = None
    error: str | None = None
    label: str | None = None
    theme: str | None = None


@dataclass(frozen=True)
class ArchitectureMapping:
    records: tuple[str, ...]
    theme: str
    requirements: tuple[str, ...]
    adrs: tuple[str, ...]
    components: tuple[str, ...]
    stories: tuple[str, ...]


@dataclass(frozen=True)
class ValidationResult:
    findings: tuple[Finding, ...]
    nodes: tuple[Node, ...] = ()
    edges: tuple[Edge, ...] = ()

    @property
    def valid(self) -> bool:
        return not self.findings

    @property
    def payload(self) -> Mapping[str, object]:
        return {
            "command": "validate",
            "check": CHECK,
            "status": "ok" if self.valid else "failed",
            "graph": {
                "nodes": [
                    {
                        "id": node.identifier,
                        "kind": node.kind,
                        "file": node.file,
                        "scope": node.scope,
                    }
                    for node in self.nodes
                ],
                "edges": [
                    {
                        "from": edge.source,
                        "to": edge.target,
                        "scope": edge.scope,
                    }
                    for edge in self.edges
                ],
            },
            "findings": list(self.findings),
        }


def _safe(value: object) -> str:
    text = str(value)
    return "".join(
        character
        if character.isprintable()
        and not 0xD800 <= ord(character) <= 0xDFFF
        else rf"\u{ord(character):04x}"
        for character in text
    )


def _finding(
    *,
    file: str,
    record: str | None,
    message: str,
    remediation: str,
) -> Finding:
    return {
        "check": CHECK,
        "severity": "error",
        "file": _safe(file),
        "record": record,
        "message": _safe(message),
        "remediation": remediation,
    }


def _within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _display(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _contained_regular_file(path: Path, root: Path) -> bool:
    """Require a regular file and reject every symlink in its relative path."""

    try:
        relative = path.relative_to(root)
    except ValueError:
        return False
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        try:
            if cursor.is_symlink():
                return False
        except OSError:
            return False
    try:
        resolved = path.resolve(strict=True)
        return _within(resolved, root) and resolved.is_file()
    except (OSError, RuntimeError, ValueError):
        return False


def _contained_path(path: Path, root: Path) -> bool:
    """Require an existing regular file/directory without traversing symlinks."""

    try:
        relative = path.relative_to(root)
    except ValueError:
        return False
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        try:
            if cursor.is_symlink():
                return False
        except OSError:
            return False
    try:
        resolved = path.resolve(strict=True)
        return _within(resolved, root) and (resolved.is_file() or resolved.is_dir())
    except (OSError, RuntimeError, ValueError):
        return False


def _read_text(path: Path, root: Path) -> str:
    if not _contained_regular_file(path, root):
        raise ContractError("file is missing, not regular, or leaves the repository")
    try:
        if path.stat().st_size > MAX_TEXT_BYTES:
            raise ContractError(f"file exceeds the {MAX_TEXT_BYTES}-byte safety limit")
        return path.read_text(encoding="utf-8")
    except UnicodeError as error:
        raise ContractError("file is not valid UTF-8") from error
    except OSError as error:
        raise ContractError("file is unreadable") from error


def _load_yaml(text: str) -> object:
    try:
        return yaml.load(text, Loader=InertYamlLoader)
    except (yaml.YAMLError, RecursionError) as error:
        if "aliases are not allowed" in str(error):
            raise ContractError("YAML aliases are not allowed") from error
        raise ContractError("YAML is malformed or contains duplicate keys") from error


def load_contract(repository_root: PathValue) -> dict[str, object]:
    """Load and pin the machine-readable contract owned by bdd-stories."""

    try:
        root = Path(repository_root).resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as error:
        raise ContractError("repository root is missing or unreadable") from error
    text = _read_text(root / SKILL_PATH, root)
    if text.count(CONTRACT_START) != 1 or text.count(CONTRACT_END) != 1:
        raise ContractError("traceability contract markers must occur exactly once")
    try:
        start = text.index(CONTRACT_START) + len(CONTRACT_START)
        end = text.index(CONTRACT_END, start)
    except ValueError as error:
        raise ContractError("traceability contract markers are out of order") from error
    region = text[start:end].strip()
    match = re.fullmatch(r"```yaml[ \t]*\n(.*)\n```", region, re.DOTALL)
    if match is None:
        raise ContractError("traceability contract must be one fenced YAML block")
    loaded = _load_yaml(match.group(1))
    if loaded != EXPECTED_CONTRACT:
        raise ContractError(
            "traceability contract drifted from pinned version 1 fields, "
            "story types, keys, or prefix sets"
        )
    assert isinstance(loaded, dict)
    return loaded


def _frontmatter(text: str) -> object:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ContractError("story must begin with YAML frontmatter")
    closing = next(
        (index for index, line in enumerate(lines[1:], 1) if line.strip() == "---"),
        None,
    )
    if closing is None:
        raise ContractError("story frontmatter has no closing delimiter")
    return _load_yaml("\n".join(lines[1:closing]))


def _scope_from_value(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    match = VP_PATTERN.search(value)
    return match.group(0) if match is not None else None


def _safe_story_path(root: Path, value: object) -> Path | None:
    if not isinstance(value, str) or "\\" in value:
        return None
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts:
        return None
    path = root.joinpath(*pure.parts)
    return path if _contained_regular_file(path, root) else None


def _story_sources_from_backlog(
    root: Path,
) -> tuple[tuple[StorySource, ...], tuple[Finding, ...]]:
    path = root / BACKLOG_PATH
    if not _contained_regular_file(path, root):
        return (), (
            _finding(
                file=BACKLOG_PATH.as_posix(),
                record=None,
                message="authoritative backlog is missing or is not a contained regular file",
                remediation="Restore a valid docs/plan/backlog.yaml.",
            ),
        )
    try:
        document = _load_yaml(_read_text(path, root))
    except ContractError as error:
        return (), (
            _finding(
                file=BACKLOG_PATH.as_posix(),
                record=None,
                message=f"authoritative backlog is invalid: {error}",
                remediation="Repair the backlog YAML; trace validation has no fallback.",
            ),
        )
    if not isinstance(document, Mapping):
        return (), (
            _finding(
                file=BACKLOG_PATH.as_posix(),
                record=None,
                message="authoritative backlog root must be a mapping",
                remediation="Restore the backlog mapping; trace validation has no fallback.",
            ),
        )
    backlog = document.get("backlog")
    if not isinstance(backlog, Mapping):
        return (), (
            _finding(
                file=BACKLOG_PATH.as_posix(),
                record=None,
                message="authoritative backlog has no 'backlog' mapping",
                remediation="Restore the required backlog mapping.",
            ),
        )
    active_themes = backlog.get("active-themes")
    archived_themes = backlog.get("archived-themes", [])
    if not isinstance(active_themes, list) or not isinstance(archived_themes, list):
        return (), (
            _finding(
                file=BACKLOG_PATH.as_posix(),
                record=None,
                message="backlog active-themes and archived-themes must be YAML lists",
                remediation="Declare the canonical active and archived theme collections.",
            ),
        )
    themes = list(active_themes)
    for summary in archived_themes:
        if not isinstance(summary, Mapping) or summary.get("schema-version") != 2:
            continue
        archive = _safe_story_path(root, summary.get("archive-ref"))
        if archive is None:
            continue
        try:
            snapshot = _load_yaml(_read_text(archive, root))
        except ContractError:
            continue
        if (
            isinstance(snapshot, Mapping)
            and set(snapshot) == {"theme"}
            and isinstance(snapshot.get("theme"), Mapping)
            and snapshot["theme"].get("id") == summary.get("id")
            and snapshot["theme"].get("locked") is True
        ):
            themes.append(snapshot["theme"])
    sources: list[StorySource] = []
    findings: list[Finding] = []
    listed_paths: set[Path] = set()
    listed_ids: set[str] = set()
    for theme in themes:
        if not isinstance(theme, Mapping):
            findings.append(
                _finding(
                    file=BACKLOG_PATH.as_posix(),
                    record=None,
                    message="active theme entry must be a mapping",
                    remediation="Replace the malformed active theme entry.",
                )
            )
            continue
        theme_id = theme.get("id")
        if not isinstance(theme_id, str) or re.fullmatch(r"TH[1-9][0-9]*", theme_id) is None:
            findings.append(
                _finding(
                    file=BACKLOG_PATH.as_posix(),
                    record=_safe(theme_id),
                    message="theme has no canonical TH<n> ID",
                    remediation="Declare a canonical theme ID.",
                )
            )
            continue
        vision_ref = theme.get("vision-ref")
        scope = _scope_from_value(vision_ref)
        if scope is None:
            findings.append(
                _finding(
                    file=BACKLOG_PATH.as_posix(),
                    record=theme_id,
                    message="theme has no VP-scoped vision-ref",
                    remediation="Declare the canonical same-VP Vision root.",
                )
            )
        elif (
            not isinstance(vision_ref, str)
            or not vision_ref.startswith(f"docs/vision_of_product/{scope}-")
            or not vision_ref.endswith("/")
            or not _contained_path(root / PurePosixPath(vision_ref), root)
        ):
            findings.append(
                _finding(
                    file=BACKLOG_PATH.as_posix(),
                    record=theme_id,
                    message="vision-ref is not a resolving canonical Vision directory",
                    remediation="Use the exact contained docs/vision_of_product/VP<n>-<slug>/ path.",
                )
            )
        for key, category, suffix in (
            ("discovery-ref", "discovery", "/"),
            ("requirements-ref", "requirements", "/PRD.md"),
        ):
            reference = theme.get(key)
            if not isinstance(reference, str):
                findings.append(
                    _finding(
                        file=BACKLOG_PATH.as_posix(),
                        record=theme_id,
                        message=f"theme has no string {key}",
                        remediation=f"Declare the canonical same-VP {key}.",
                    )
                )
                continue
            reference_scope = _scope_from_value(reference)
            reference_path = root / PurePosixPath(reference)
            expected_start = f"docs/{category}/{scope}-" if scope is not None else ""
            path_valid = (
                reference_scope == scope
                and bool(expected_start)
                and reference.startswith(expected_start)
                and reference.endswith(suffix)
                and (
                    _contained_regular_file(reference_path, root)
                    if key == "requirements-ref"
                    else _contained_path(reference_path, root)
                )
            )
            if not path_valid:
                findings.append(
                    _finding(
                        file=BACKLOG_PATH.as_posix(),
                        record=theme_id,
                        message=f"{key} is not a resolving canonical same-VP path",
                        remediation=f"Use the exact contained same-VP {category} reference.",
                    )
                )
        roots = [
            candidate
            for candidate in sorted((root / "docs/themes").glob(f"{theme_id}-*"))
            if candidate.is_dir() and not candidate.is_symlink()
        ]
        theme_root = roots[0] if len(roots) == 1 else None
        if theme_root is None:
            findings.append(
                _finding(
                    file="docs/themes",
                    record=theme_id,
                    message=f"theme must have exactly one docs/themes/{theme_id}-* root",
                    remediation="Restore one canonical theme directory.",
                )
            )
        epics = theme.get("epics")
        if not isinstance(epics, list):
            findings.append(
                _finding(
                    file=BACKLOG_PATH.as_posix(),
                    record=theme_id,
                    message="unlocked active theme epics must be a YAML list",
                    remediation="Declare the theme's epics and stories as lists.",
                )
            )
            continue
        for epic in epics:
            stories = epic.get("stories") if isinstance(epic, Mapping) else None
            if not isinstance(stories, list):
                findings.append(
                    _finding(
                        file=BACKLOG_PATH.as_posix(),
                        record=theme_id,
                        message="active epic stories must be a YAML list",
                        remediation="Repair the malformed epic entry.",
                    )
                )
                continue
            for story in stories:
                if not isinstance(story, Mapping):
                    findings.append(
                        _finding(
                            file=BACKLOG_PATH.as_posix(),
                            record=theme_id,
                            message="backlog story entry must be a mapping",
                            remediation="Replace the malformed story entry.",
                        )
                    )
                    continue
                expected_id = (
                    story.get("id") if isinstance(story.get("id"), str) else None
                )
                if expected_id is None:
                    findings.append(
                        _finding(
                            file=BACKLOG_PATH.as_posix(),
                            record=theme_id,
                            message="backlog story entry has no string ID",
                            remediation="Declare the canonical story ID.",
                        )
                    )
                elif expected_id in listed_ids:
                    findings.append(
                        _finding(
                            file=BACKLOG_PATH.as_posix(),
                            record=expected_id,
                            message="story ID is listed more than once in the backlog",
                            remediation="Keep exactly one backlog entry per story.",
                        )
                    )
                else:
                    listed_ids.add(expected_id)
                source = _safe_story_path(root, story.get("file"))
                if source is None:
                    raw_path = _safe(story.get("file"))
                    sources.append(
                        StorySource(
                            root / ".invalid-story-path",
                            expected_id,
                            scope,
                            {},
                            story.get("status") if isinstance(story.get("status"), str) else None,
                            (
                                "declared story path is not a regular contained "
                                "repository file"
                            ),
                            raw_path,
                            theme_id,
                        )
                    )
                    continue
                if source in listed_paths:
                    findings.append(
                        _finding(
                            file=_display(source, root),
                            record=expected_id,
                            message="story file is listed more than once in the backlog",
                            remediation="Keep exactly one backlog entry for this file.",
                        )
                    )
                listed_paths.add(source)
                if theme_root is not None and not _within(source, theme_root):
                    findings.append(
                        _finding(
                            file=_display(source, root),
                            record=expected_id,
                            message=f"listed story is outside unlocked theme root {theme_id}",
                            remediation="Point the backlog entry into its owning theme root.",
                        )
                    )
                evidence = story.get("evidence")
                if not isinstance(evidence, Mapping):
                    findings.append(
                        _finding(
                            file=BACKLOG_PATH.as_posix(),
                            record=expected_id,
                            message="story evidence must be a mapping",
                            remediation=(
                                "Declare exactly the evidence keys "
                                + ", ".join(EVIDENCE_KEYS)
                                + "."
                            ),
                        )
                    )
                sources.append(
                    StorySource(
                        source,
                        expected_id,
                        scope,
                        evidence if isinstance(evidence, Mapping) else {},
                        story.get("status") if isinstance(story.get("status"), str) else None,
                        theme=theme_id,
                    )
                )
        if theme_root is not None:
            inventory = {
                candidate
                for candidate in _walk_story_files(theme_root, root)
            }
            for unlisted in sorted(inventory - listed_paths):
                findings.append(
                    _finding(
                        file=_display(unlisted, root),
                        record=None,
                        message=f"story file under unlocked {theme_id} root is not listed in backlog",
                        remediation="List the story file exactly once in the active theme.",
                    )
                )
                sources.append(
                    StorySource(unlisted, None, scope, {}, theme=theme_id)
                )
            for absent in sorted(
                item for item in listed_paths if _within(item, theme_root)
            ):
                if absent not in inventory:
                    findings.append(
                        _finding(
                            file=_display(absent, root),
                            record=None,
                            message=f"backlog story is absent from {theme_id} filesystem inventory",
                            remediation="Make backlog and filesystem story inventory agree.",
                        )
                    )
    return (
        tuple(sorted(sources, key=lambda item: (item.path.as_posix(), item.expected_id or ""))),
        tuple(findings),
    )


def _walk_story_files(base: Path, root: Path) -> tuple[Path, ...]:
    if not base.is_dir() or base.is_symlink():
        return ()
    paths: list[Path] = []
    for directory, names, filenames in os.walk(base, followlinks=False):
        names[:] = sorted(
            name
            for name in names
            if not (Path(directory) / name).is_symlink()
        )
        if Path(directory).name != "stories":
            continue
        for name in sorted(filenames):
            path = Path(directory) / name
            if name.endswith(".md") and _contained_regular_file(path, root):
                paths.append(path)
        names[:] = []
    return tuple(paths)


def _scope_directories(root: Path, category: str, scope: str) -> tuple[Path, ...]:
    base = root / "docs" / category
    if not base.is_dir() or base.is_symlink():
        return ()
    return tuple(
        candidate
        for candidate in sorted(base.glob(f"{scope}-*"))
        if candidate.is_dir() and not candidate.is_symlink()
    )


def _markdown_section_line_ranges(
    text: str,
    headings: frozenset[str],
) -> tuple[range, ...]:
    """Return one-based line ranges owned by matching level-two sections."""

    lines = text.splitlines()
    visible: list[bool] = []
    delimiter: str | None = None
    for line in lines:
        if delimiter is not None:
            visible.append(False)
            if re.fullmatch(rf" {{0,3}}{re.escape(delimiter)}[ \t]*", line):
                delimiter = None
            continue
        opening = re.match(r"^ {0,3}(?P<fence>`{3,}|~{3,})", line)
        if opening is not None:
            delimiter = opening.group("fence")
            visible.append(False)
            continue
        visible.append(True)

    ranges: list[range] = []
    for index, line in enumerate(lines):
        if not visible[index]:
            continue
        match = re.fullmatch(r"##\s+(.+?)\s*", line)
        if match is None or match.group(1) not in headings:
            continue
        end = len(lines)
        for candidate in range(index + 1, len(lines)):
            if visible[candidate] and re.match(r"^#{1,2}\s+", lines[candidate]):
                end = candidate
                break
        ranges.append(range(index + 2, end + 1))
    return tuple(ranges)


def _record_is_in_section(
    record: records.Record,
    text: str,
    headings: frozenset[str],
) -> bool:
    return any(
        record.line in line_range
        for line_range in _markdown_section_line_ranges(text, headings)
    )


def _canonical_record_sources(
    root: Path,
    scopes: frozenset[str],
) -> tuple[
    list[tuple[str, Path, frozenset[str]]],
    set[tuple[str, str]],
    list[Finding],
]:
    sources: list[tuple[str, Path, frozenset[str]]] = []
    claimed_experiments: set[tuple[str, str]] = set()
    findings: list[Finding] = []
    for scope in sorted(scopes):
        for category in ("vision_of_product", "discovery", "requirements"):
            directories = _scope_directories(root, category, scope)
            if len(directories) != 1:
                findings.append(
                    _finding(
                        file=f"docs/{category}",
                        record=scope,
                        message=(
                            f"{scope} must have exactly one canonical {category} root"
                        ),
                        remediation=f"Restore one docs/{category}/{scope}-* root.",
                    )
                )
                continue
            directory = directories[0]
            if category == "vision_of_product":
                candidates = (
                    directory / f"{scope}.md",
                    directory / "README.md",
                )
                path = next(
                    (
                        candidate
                        for candidate in candidates
                        if _contained_regular_file(candidate, root)
                    ),
                    None,
                )
                if path is None:
                    findings.append(
                        _finding(
                            file=_display(directory, root),
                            record=scope,
                            message="canonical Vision file is missing",
                            remediation=f"Restore {scope}.md or README.md in the Vision root.",
                        )
                    )
                else:
                    # The Vision remains a source sketch.  Parse it only so a
                    # record-shaped VO counterfeit cannot satisfy a reference.
                    sources.append((scope, path, frozenset()))
            elif category == "requirements":
                path = directory / "PRD.md"
                if not _contained_regular_file(path, root):
                    findings.append(
                        _finding(
                            file=_display(path, root),
                            record=scope,
                            message="canonical PRD file is missing",
                            remediation="Restore the same-VP requirements/PRD.md.",
                        )
                    )
                else:
                    sources.append((scope, path, frozenset({"VO", "PR", "QR"})))
            else:
                owners: dict[str, set[str]] = {}
                for prefix, filename in DISCOVERY_OWNER.items():
                    owners.setdefault(filename, set()).add(prefix)
                for filename, prefixes in sorted(owners.items()):
                    path = directory / filename
                    if _contained_regular_file(path, root):
                        sources.append((scope, path, frozenset(prefixes)))
                experiments = directory / "experiments"
                if (
                    not experiments.is_dir()
                    or experiments.is_symlink()
                    or not _within(experiments.resolve(), root)
                ):
                    findings.append(
                        _finding(
                            file=_display(experiments, root),
                            record=scope,
                            message=(
                                "canonical EXP owner directory is missing, "
                                "unsafe, or not a directory"
                            ),
                            remediation=(
                                "Restore the contained same-VP "
                                "experiments/ directory."
                            ),
                        )
                    )
                    continue
                try:
                    entries = sorted(experiments.iterdir(), key=lambda item: item.name)
                except OSError:
                    findings.append(
                        _finding(
                            file=_display(experiments, root),
                            record=scope,
                            message="canonical EXP owner directory is unreadable",
                            remediation="Restore read access to the experiments/ directory.",
                        )
                    )
                    continue
                for candidate in entries:
                    if not candidate.name.startswith("EXP-"):
                        continue
                    claim = EXP_CLAIM_PATTERN.match(candidate.name)
                    claimed_id = claim.group("id") if claim is not None else None
                    if claimed_id is not None:
                        claimed_experiments.add((scope, claimed_id))
                    identity = EXP_FILE_PATTERN.fullmatch(candidate.name)
                    if identity is None:
                        findings.append(
                            _finding(
                                file=_display(candidate, root),
                                record=claimed_id,
                                message=(
                                    "canonical EXP file has a malformed filename; "
                                    "expected EXP-###-<slug>.md"
                                ),
                                remediation=(
                                    "Use a canonical EXP ID, lowercase hyphenated "
                                    "slug, and .md extension."
                                ),
                            )
                        )
                        continue
                    identifier = identity.group("id")
                    claimed_experiments.add((scope, identifier))
                    if not _contained_regular_file(candidate, root):
                        findings.append(
                            _finding(
                                file=_display(candidate, root),
                                record=identifier,
                                message=(
                                    "canonical EXP path is not a regular contained file"
                                ),
                                remediation=(
                                    "Replace it with a regular markdown file inside "
                                    "the same-VP experiments/ directory."
                                ),
                            )
                        )
                        continue
                    sources.append((scope, candidate, frozenset({"EXP"})))
                for current, names, filenames in os.walk(
                    directory, followlinks=False
                ):
                    names[:] = sorted(
                        name
                        for name in names
                        if not (Path(current) / name).is_symlink()
                    )
                    for filename in sorted(filenames):
                        candidate = Path(current) / filename
                        if (
                            not filename.startswith("EXP-")
                            or candidate.parent == experiments
                        ):
                            continue
                        claim = EXP_CLAIM_PATTERN.match(filename)
                        claimed_id = (
                            claim.group("id") if claim is not None else None
                        )
                        if claimed_id is not None:
                            claimed_experiments.add((scope, claimed_id))
                        findings.append(
                            _finding(
                                file=_display(candidate, root),
                                record=claimed_id,
                                message=(
                                    "counterfeit EXP file is outside its canonical "
                                    "same-VP experiments/ owner directory"
                                ),
                                remediation=(
                                    "Keep each EXP-### file directly under the "
                                    "owning dossier's experiments/ directory."
                                ),
                            )
                        )
    return sources, claimed_experiments, findings


def _schema_allowed(scope: str, record: records.Record) -> bool:
    header = tuple(record.columns)
    if record.prefix == "EXP":
        values_complete = all(value.strip() for value in record.columns.values())
        if header == EXP_SCHEMA:
            return (
                values_complete
                and record.columns.get("Schema version") == "1"
                and record.form == "file"
            )
        return (
            scope == "VP3"
            and header == VP3_LEGACY_EXP_SCHEMA
            and values_complete
            and record.form == "file"
        )
    if record.prefix == "VO":
        schemas = VISION_SCHEMAS
    elif record.prefix in REQUIREMENT_SCHEMAS:
        schemas = REQUIREMENT_SCHEMAS[record.prefix]
    else:
        schemas = CANONICAL_DISCOVERY_SCHEMAS.get(record.prefix, ())
    acceptance_suffix = (
        "Acceptance actor", "Acceptance timestamp", "Acceptance scope",
        "Acceptance verdict", "Acceptance rationale",
        "Acceptance source revision",
    )
    if scope != "VP3" and record.prefix != "VO":
        # The first schema is the current prospective schema.  Only the
        # accepted VP3 baseline may retain the following legacy forms.
        schemas = schemas[:1]
    return any(
        header == schema
        or header == schema + acceptance_suffix
        for schema in schemas
    )


def _requirement_is_consequential(record: records.Record) -> bool:
    impact = record.columns.get("Impact", "").strip().lower()
    semantic_text = " ".join(
        record.columns.get(column, "")
        for column in ("Requirement", "Measure", "Impact", "Impact rationale")
    ).lower()
    semantic_text = re.sub(r"\s+", " ", semantic_text)
    normative = bool(
        re.search(
            r"\b(shall|must|required|requirement|threshold|gate|block|reject|"
            r"prevent|within|at (?:least|most)|no more than|exactly)\b",
            semantic_text,
        )
        or re.search(r"\b\d+(?:\.\d+)?\s*(?:%|seconds?|minutes?|hours?)?\b", semantic_text)
    )
    if impact == "consequential":
        return True
    if impact == "low-impact":
        return normative
    # Accepted legacy VP3 PR/QR rows predate Impact.  Their normative product
    # obligations remain consequential even though no metadata was backfilled.
    return normative


def _record_is_consequential(record: records.Record) -> bool:
    if record.prefix in {"PR", "QR"}:
        return _requirement_is_consequential(record)
    if record.prefix in {"DQ", "EXP", "DEC", "INV", "RSK", "DEF"}:
        return True
    if record.prefix == "ASM":
        impact = record.columns.get("Impact", "").strip().lower()
        return impact != "low-impact"
    return False


def _record_nodes(
    root: Path,
    scopes: frozenset[str],
) -> tuple[
    list[Node],
    list[tuple[str, records.Record]],
    list[tuple[str, str, str]],
    set[tuple[str, str]],
    list[Finding],
]:
    parsed: list[tuple[str, records.Record]] = []
    prd_deferral_references: list[tuple[str, str, str]] = []
    canonical_sources, claimed_experiments, findings = _canonical_record_sources(
        root, scopes
    )
    invalid_records: set[tuple[str, str]] = set()
    for scope, path, owners in canonical_sources:
        result = records.parse_file(path, repository_root=root)
        try:
            source_text = _read_text(path, root)
        except ContractError:
            source_text = ""
        for finding in result.findings:
            findings.append(
                _finding(
                    file=str(finding["file"]),
                    record=(
                        str(finding["record"])
                        if finding["record"] is not None
                        else None
                    ),
                    message=f"record source is not trace-indexable: {finding['message']}",
                    remediation=str(finding["remediation"]),
                )
            )
        for record in result.records:
            if record.prefix not in GRAPH_PREFIXES - {"ADR"}:
                continue
            is_prd = owners == frozenset({"VO", "PR", "QR"})
            if (
                is_prd
                and record.prefix == "DEF"
                and tuple(record.columns) in PRD_DEFERRAL_REFERENCE_SCHEMAS
                and _record_is_in_section(
                    record, source_text, PRD_DEFERRAL_HEADINGS
                )
            ):
                # The accepted PRD table cites dossier-owned DEF records and
                # states their product effect.  It is an edge declaration,
                # not a second DEF record store.
                prd_deferral_references.append((scope, record.id, record.file))
                continue
            if record.prefix not in owners:
                findings.append(
                    _finding(
                        file=record.file,
                        record=record.id,
                        message=(
                            f"{record.id} is in the wrong canonical owner; "
                            f"{path.name} owns only {', '.join(sorted(owners))}"
                        ),
                        remediation="Move the fact to its prefix-specific owning record set.",
                    )
                )
                continue
            if (
                record.prefix == "VO"
                and not _record_is_in_section(
                    record, source_text, PRD_VISION_HEADINGS
                )
            ):
                invalid_records.add((scope, record.id))
                findings.append(
                    _finding(
                        file=record.file,
                        record=record.id,
                        message=(
                            f"{record.id} is outside the canonical PRD "
                            "Vision outcomes section"
                        ),
                        remediation=(
                            "Declare each VO-### row in the PRD's single "
                            "Vision outcomes table."
                        ),
                    )
                )
                continue
            if not _schema_allowed(scope, record):
                invalid_records.add((scope, record.id))
                schema_name = (
                    "file-per-record metadata schema"
                    if record.prefix == "EXP"
                    else "table schema"
                )
                findings.append(
                    _finding(
                        file=record.file,
                        record=record.id,
                        message=(
                            f"{record.id} does not use an accepted canonical "
                            f"{record.prefix} {schema_name}"
                        ),
                        remediation="Use the exact owning schema for this record prefix.",
                    )
                )
                continue
            parsed.append((scope, record))
        if owners == frozenset({"EXP"}):
            parsed_ids = {
                record.id for record in result.records if record.prefix == "EXP"
            }
            filename = EXP_FILE_PATTERN.fullmatch(path.name)
            if filename is not None and filename.group("id") not in parsed_ids:
                invalid_records.add((scope, filename.group("id")))
    grouped: dict[tuple[str, str], list[records.Record]] = {}
    for scope, record in parsed:
        grouped.setdefault((scope, record.id), []).append(record)
    nodes: list[Node] = []
    usable: list[tuple[str, records.Record]] = []
    for (scope, identifier), matches in sorted(grouped.items()):
        if len(matches) != 1:
            invalid_records.add((scope, identifier))
            locations = ", ".join(
                f"{item.file}:{item.line}" for item in sorted(matches, key=lambda x: x.file)
            )
            findings.append(
                _finding(
                    file=matches[0].file,
                    record=identifier,
                    message=f"{identifier} is duplicated in VP scope {scope}: {locations}",
                    remediation="Keep one authoritative record ID in this VP scope.",
                )
            )
            continue
        record = matches[0]
        consequential = _record_is_consequential(record)
        nodes.append(
            Node(
                identifier,
                record.prefix,
                record.file,
                identifier,
                scope,
                consequential,
            )
        )
        usable.append((scope, record))
    invalid_records.update(claimed_experiments - {
        (scope, record.id) for scope, record in usable
    })
    return (
        nodes,
        usable,
        prd_deferral_references,
        invalid_records,
        findings,
    )


def _adr_nodes(root: Path) -> tuple[list[Node], list[Finding]]:
    directory = root / "docs/ADRs"
    if not directory.is_dir() or directory.is_symlink():
        return [], []
    nodes: list[Node] = []
    findings: list[Finding] = []
    seen: dict[str, str] = {}
    for path in sorted(directory.glob("ADR-*.md")):
        if not _contained_regular_file(path, root):
            findings.append(
                _finding(
                    file=_display(path, root),
                    record=None,
                    message="ADR path is not a regular contained repository file",
                    remediation="Replace the path with a regular ADR file inside the repository.",
                )
            )
            continue
        identity = re.match(r"(?P<id>ADR-[0-9]{3})(?:-|\.md$)", path.name)
        if identity is None:
            continue
        candidate = identity.group("id")
        if ADR_PATTERN.fullmatch(candidate) is None:
            continue
        try:
            text = _read_text(path, root)
        except ContractError as error:
            findings.append(
                _finding(
                    file=_display(path, root),
                    record=candidate,
                    message=str(error),
                    remediation="Restore a readable UTF-8 ADR file.",
                )
            )
            continue
        title = text.splitlines()[0] if text.splitlines() else ""
        if not title.startswith(f"# {candidate}:"):
            findings.append(
                _finding(
                    file=_display(path, root),
                    record=candidate,
                    message=f"ADR title does not declare filename ID {candidate}",
                    remediation=f"Use '# {candidate}: <title>' as the first line.",
                )
            )
            continue
        if candidate in seen:
            findings.append(
                _finding(
                    file=_display(path, root),
                    record=candidate,
                    message=f"ADR ID {candidate} is duplicated",
                    remediation="Keep one authoritative ADR file for this ID.",
                )
            )
            continue
        seen[candidate] = _display(path, root)
        nodes.append(
            Node(candidate, "ADR", _display(path, root), candidate, None, False)
        )
    return nodes, findings


def _story_nodes(
    root: Path,
    contract: Mapping[str, object],
    sources: Sequence[StorySource],
) -> tuple[
    list[Node],
    dict[tuple[str | None, str], tuple[str, ...]],
    list[Finding],
]:
    nodes: list[Node] = []
    declarations: dict[tuple[str | None, str], tuple[str, ...]] = {}
    findings: list[Finding] = []
    keys = contract["keys"]
    assert isinstance(keys, Mapping)
    expected_keys = tuple(keys)
    required_types = set(contract["required-story-types"])
    empty_types = set(contract["empty-allowed-story-types"])

    for source in sources:
        label = source.label or _display(source.path, root)
        if source.error is not None:
            findings.append(
                _finding(
                    file=label,
                    record=source.expected_id,
                    message=source.error,
                    remediation=(
                        "Use a normalized repository-relative path to a "
                        "regular story file; do not use symlinks."
                    ),
                )
            )
            continue
        try:
            data = _frontmatter(_read_text(source.path, root))
        except ContractError as error:
            findings.append(
                _finding(
                    file=label,
                    record=source.expected_id,
                    message=str(error),
                    remediation="Restore inert, duplicate-free YAML story frontmatter.",
                )
            )
            continue
        if not isinstance(data, Mapping):
            findings.append(
                _finding(
                    file=label,
                    record=source.expected_id,
                    message="story frontmatter root must be a mapping",
                    remediation="Declare story fields as a YAML mapping.",
                )
            )
            continue
        required_frontmatter: Mapping[str, type | tuple[type, ...]] = {
            "id": str,
            "title": str,
            "type": str,
            "agents": list,
            "skills": list,
            "traceability": Mapping,
            "acceptance-criteria": list,
            "depends-on": list,
        }
        for field, expected_type in required_frontmatter.items():
            if field not in data or not isinstance(data.get(field), expected_type):
                findings.append(
                    _finding(
                        file=label,
                        record=(
                            data.get("id") if isinstance(data.get("id"), str) else None
                        ),
                        message=f"required frontmatter field {field!r} is missing or malformed",
                        remediation="Restore the required bdd-stories frontmatter schema.",
                    )
                )
        identifier = data.get("id")
        if not isinstance(identifier, str) or not re.fullmatch(
            r"TH[1-9][0-9]*\.E[1-9][0-9]*\.US[1-9][0-9]*", identifier
        ):
            findings.append(
                _finding(
                    file=label,
                    record=None,
                    message="story has no canonical TH<n>.E<m>.US<l> frontmatter ID",
                    remediation="Add the canonical story ID to frontmatter.",
                )
            )
            continue
        if source.expected_id is not None and identifier != source.expected_id:
            findings.append(
                _finding(
                    file=label,
                    record=identifier,
                    message=(
                        f"frontmatter ID {identifier} does not match declared "
                        f"story ID {source.expected_id}"
                    ),
                    remediation="Make the authoritative story ID match its backlog entry.",
                )
            )
        story_type = data.get("type")
        if story_type not in required_types | empty_types:
            findings.append(
                _finding(
                    file=label,
                    record=identifier,
                    message=f"story type {story_type!r} is outside the traceability contract",
                    remediation="Use standard, spike, or trivial as defined by bdd-stories.",
                )
            )
            continue
        traceability = data.get(contract["frontmatter-key"])
        if not isinstance(traceability, Mapping):
            findings.append(
                _finding(
                    file=label,
                    record=identifier,
                    message="required frontmatter key 'traceability' is missing or not a mapping",
                    remediation=(
                        "Declare traceability with exactly the keys "
                        + ", ".join(expected_keys)
                        + "."
                    ),
                )
            )
            traceability = {}
        unknown = sorted(str(key) for key in traceability if key not in keys)
        for key in unknown:
            findings.append(
                _finding(
                    file=label,
                    record=identifier,
                    message=(
                        f"undefined traceability key {key!r}; expected exactly "
                        + ", ".join(expected_keys)
                    ),
                    remediation=f"Remove {key!r} and use only the four contract keys.",
                )
            )

        references: list[str] = []
        for key in expected_keys:
            value = traceability.get(key)
            if not isinstance(value, list):
                findings.append(
                    _finding(
                        file=label,
                        record=identifier,
                        message=f"traceability.{key} must be a YAML list of record IDs",
                        remediation=f"Declare traceability.{key} as a YAML list.",
                    )
                )
                continue
            if story_type in required_types and not value:
                findings.append(
                    _finding(
                        file=label,
                        record=identifier,
                        message=(
                            f"{story_type} story traceability.{key} must contain "
                            "at least one record ID"
                        ),
                        remediation=f"Add an applicable {key} record ID.",
                    )
                )
            definition = keys[key]
            prefixes = (
                definition.get("prefixes")
                if isinstance(definition, Mapping)
                else None
            )
            allowed = set(prefixes) if isinstance(prefixes, list) else set()
            for item in value:
                prefix = (
                    item.split("-", 1)[0]
                    if isinstance(item, str) and ID_PATTERN.fullmatch(item)
                    else None
                )
                if prefix not in allowed:
                    findings.append(
                        _finding(
                            file=label,
                            record=identifier,
                            message=(
                                f"traceability.{key} value {item!r} has an "
                                f"invalid prefix; allowed prefixes are "
                                + ", ".join(sorted(allowed))
                            ),
                            remediation=f"Use only {key} IDs allowed by bdd-stories.",
                        )
                    )
                    continue
                references.append(item)
        nodes.append(
            Node(
                identifier,
                "story",
                label,
                identifier,
                source.scope,
                story_type in required_types,
            )
        )
        declaration_key = _node_key(source.scope, identifier)
        if declaration_key in declarations:
            findings.append(
                _finding(
                    file=label,
                    record=identifier,
                    message=f"story ID is duplicated in VP scope {source.scope}",
                    remediation="Keep one authoritative story per ID and VP scope.",
                )
            )
        else:
            declarations[declaration_key] = tuple(dict.fromkeys(references))
    return nodes, declarations, findings


def _heading_anchors(text: str) -> set[str]:
    anchors: set[str] = set()
    counts: dict[str, int] = {}
    fenced = False
    delimiter = ""
    for line in text.splitlines():
        fence = re.match(r" {0,3}(`{3,}|~{3,})", line)
        if fence:
            token = fence.group(1)
            if not fenced:
                fenced, delimiter = True, token
            elif token[0] == delimiter[0] and len(token) >= len(delimiter):
                fenced = False
            continue
        if fenced:
            continue
        match = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
        if match is None:
            continue
        anchor = match.group(1).strip().lower()
        anchor = re.sub(r"[^\w -]", "", anchor, flags=re.UNICODE)
        anchor = re.sub(r"\s+", "-", anchor)
        occurrence = counts.get(anchor, 0)
        counts[anchor] = occurrence + 1
        anchors.add(anchor if occurrence == 0 else f"{anchor}-{occurrence}")
    return anchors


def _heading_sections(text: str) -> Mapping[str, str]:
    sections: dict[str, list[str]] = {}
    active: str | None = None
    for line in text.splitlines():
        match = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
        if match is not None:
            heading = match.group(1).strip().lower()
            heading = re.sub(r"[^\w -]", "", heading, flags=re.UNICODE)
            active = re.sub(r"\s+", "-", heading)
            sections.setdefault(active, [match.group(1)])
        elif active is not None:
            sections[active].append(line)
    return {anchor: "\n".join(lines) for anchor, lines in sections.items()}


def _document_reference(
    value: str,
    *,
    root: Path,
    scope: str,
    record: records.Record,
) -> tuple[bool, str]:
    match = DOC_PATTERN.fullmatch(value)
    if match is None:
        return False, "use DOC:docs/<path>.md#<heading-anchor>"
    pure = PurePosixPath(match.group("path"))
    if pure.is_absolute() or ".." in pure.parts or "\\" in value:
        return False, "use a normalized repository-relative docs path"
    path = root.joinpath(*pure.parts)
    if not _contained_regular_file(path, root):
        return False, "reference a regular markdown file contained in the repository"
    canonical_roots = tuple(
        directory.resolve()
        for category in ("vision_of_product", "discovery", "requirements")
        for directory in _scope_directories(root, category, scope)
    )
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        return False, "reference a resolvable same-VP markdown file"
    containing_roots = [
        canonical_root
        for canonical_root in canonical_roots
        if _within(resolved, canonical_root)
    ]
    if len(containing_roots) != 1:
        return (
            False,
            "reference exactly one canonical same-VP Vision, Discovery, or requirements root",
        )
    try:
        text = _read_text(path, root)
        anchors = _heading_anchors(text)
    except ContractError:
        return False, "reference a readable UTF-8 markdown file"
    anchor = match.group("anchor")
    if anchor not in anchors:
        return False, "reference an existing non-empty markdown heading anchor"
    section = _heading_sections(text).get(anchor, "")
    if not section.strip():
        return False, "reference a non-empty markdown section"
    if ID_PATTERN.search(section):
        return False, "use the applicable item-level ID present in the referenced section"
    stop_words = {
        "cannot", "changing", "detail", "impact", "low", "only", "shall",
        "the", "this", "uses", "with",
    }
    detail = " ".join(
        record.columns.get(column, "")
        for column in ("Requirement", "Measure", "Impact rationale")
    )
    detail_terms = {
        token
        for token in re.findall(r"[a-z0-9]+", detail.lower())
        if len(token) >= 4 and token not in stop_words
    }
    section_terms = set(re.findall(r"[a-z0-9]+", section.lower()))
    if detail_terms and detail_terms.isdisjoint(section_terms):
        return False, "reference a section relevant to the low-impact detail"
    return True, ""


def _visible_markdown_text(text: str) -> str:
    """Return text outside fenced blocks and HTML comments."""

    output: list[str] = []
    comment_depth = 0
    fence: tuple[str, int] | None = None
    for line in text.splitlines():
        visible_line: list[str] = []
        index = 0
        while index < len(line):
            if line.startswith("<!--", index):
                comment_depth += 1
                index += 4
                continue
            if comment_depth and line.startswith("-->", index):
                comment_depth -= 1
                index += 3
                continue
            if not comment_depth:
                visible_line.append(line[index])
            index += 1
        candidate = "".join(visible_line)
        opening = re.match(r"^ {0,3}(?P<fence>`{3,}|~{3,})", candidate)
        if fence is not None:
            if (
                opening is not None
                and opening.group("fence")[0] == fence[0]
                and len(opening.group("fence")) >= fence[1]
            ):
                fence = None
            output.append("")
            continue
        if opening is not None:
            delimiter = opening.group("fence")
            fence = (delimiter[0], len(delimiter))
            output.append("")
            continue
        output.append(candidate)
    return "\n".join(output)


def _accepted_architecture(text: str) -> bool:
    visible = _visible_markdown_text(text)
    return bool(
        re.search(r"(?m)^\|\s*Verdict\s*\|\s*Accepted\s*\|\s*$", visible)
    )


def _architecture_trace_declaration(
    root: Path,
) -> tuple[str | None, tuple[ArchitectureMapping, ...], bool, list[Finding]]:
    """Parse the sole canonical architecture relationship declaration."""

    path = root / ARCHITECTURE_TRACE_PATH
    if not _contained_regular_file(path, root):
        return None, (), False, []
    try:
        text = _read_text(path, root)
    except ContractError as error:
        return None, (), False, [
            _finding(
                file=ARCHITECTURE_TRACE_PATH.as_posix(),
                record="architecture-trace",
                message=str(error),
                remediation="Restore a readable architecture overview.",
            )
        ]
    accepted = _accepted_architecture(text)
    start_count = text.count(ARCHITECTURE_TRACE_START)
    end_count = text.count(ARCHITECTURE_TRACE_END)
    if start_count == 0 and end_count == 0:
        if not accepted:
            return None, (), False, []
        return None, (), True, [
            _finding(
                file=ARCHITECTURE_TRACE_PATH.as_posix(),
                record="architecture-trace",
                message=(
                    "accepted architecture has no canonical structured trace "
                    "declaration"
                ),
                remediation=(
                    "Add one marked fenced YAML architecture trace declaration."
                ),
            )
        ]
    if start_count != 1 or end_count != 1:
        return None, (), accepted, [
            _finding(
                file=ARCHITECTURE_TRACE_PATH.as_posix(),
                record="architecture-trace",
                message="architecture trace markers must occur exactly once",
                remediation="Keep one canonical marked declaration.",
            )
        ]
    start = text.find(ARCHITECTURE_TRACE_START) + len(ARCHITECTURE_TRACE_START)
    end = text.find(ARCHITECTURE_TRACE_END, start)
    if end < start:
        return None, (), accepted, [
            _finding(
                file=ARCHITECTURE_TRACE_PATH.as_posix(),
                record="architecture-trace",
                message="architecture trace markers are out of order",
                remediation="Place the end marker after the start marker.",
            )
        ]
    region = text[start:end].strip()
    match = re.fullmatch(r"```yaml[ \t]*\n(.*)\n```", region, re.DOTALL)
    if match is None:
        return None, (), accepted, [
            _finding(
                file=ARCHITECTURE_TRACE_PATH.as_posix(),
                record="architecture-trace",
                message="architecture trace declaration must be one fenced YAML block",
                remediation="Use exactly one ```yaml fenced block between the markers.",
            )
        ]
    try:
        loaded = _load_yaml(match.group(1))
    except ContractError as error:
        return None, (), accepted, [
            _finding(
                file=ARCHITECTURE_TRACE_PATH.as_posix(),
                record="architecture-trace",
                message=f"architecture trace declaration is invalid: {error}",
                remediation="Repair the inert, duplicate-free YAML declaration.",
            )
        ]
    findings: list[Finding] = []
    if not isinstance(loaded, Mapping) or set(loaded) != {
        "schema-version", "vp", "mappings"
    }:
        return None, (), accepted, [
            _finding(
                file=ARCHITECTURE_TRACE_PATH.as_posix(),
                record="architecture-trace",
                message=(
                    "architecture trace root must contain exactly "
                    "schema-version, vp, and mappings"
                ),
                remediation="Use the canonical architecture trace schema.",
            )
        ]
    scope = loaded.get("vp")
    raw_mappings = loaded.get("mappings")
    if (
        loaded.get("schema-version") != 1
        or not isinstance(scope, str)
        or VP_PATTERN.fullmatch(scope) is None
        or not isinstance(raw_mappings, list)
    ):
        return None, (), accepted, [
            _finding(
                file=ARCHITECTURE_TRACE_PATH.as_posix(),
                record="architecture-trace",
                message="architecture trace version, VP, or mappings list is malformed",
                remediation="Use schema-version 1, a VP<n> scope, and a mappings list.",
            )
        ]

    expected = {
        "records", "theme", "requirements", "adrs", "components", "stories"
    }
    mappings: list[ArchitectureMapping] = []
    for position, raw in enumerate(raw_mappings):
        record_label = f"architecture-trace[{position}]"
        if not isinstance(raw, Mapping) or set(raw) != expected:
            findings.append(
                _finding(
                    file=ARCHITECTURE_TRACE_PATH.as_posix(),
                    record=record_label,
                    message=(
                        "mapping must contain exactly records, theme, requirements, "
                        "adrs, components, and stories"
                    ),
                    remediation="Use every canonical mapping field exactly once.",
                )
            )
            continue
        theme = raw.get("theme")
        lists = {
            key: raw.get(key)
            for key in ("records", "requirements", "adrs", "components", "stories")
        }
        if (
            not isinstance(theme, str)
            or re.fullmatch(r"TH[1-9][0-9]*", theme) is None
            or any(
                not isinstance(value, list)
                or any(not isinstance(item, str) for item in value)
                for value in lists.values()
            )
        ):
            findings.append(
                _finding(
                    file=ARCHITECTURE_TRACE_PATH.as_posix(),
                    record=record_label,
                    message="mapping theme or reference lists are malformed",
                    remediation="Use a TH<n> theme and YAML lists of string IDs.",
                )
            )
            continue
        values = {
            key: tuple(dict.fromkeys(value))
            for key, value in lists.items()
            if isinstance(value, list)
        }
        malformed = [
            item
            for item in values["records"]
            if (
                ID_PATTERN.fullmatch(item) is None
                or item.split("-", 1)[0] not in ARCHITECTURE_RECORD_PREFIXES
            )
        ]
        malformed.extend(
            item for item in values["requirements"]
            if not re.fullmatch(r"(?:PR|QR)-[0-9]{3}", item)
        )
        malformed.extend(
            item for item in values["adrs"] if ADR_PATTERN.fullmatch(item) is None
        )
        malformed.extend(
            item for item in values["components"]
            if COMPONENT_REFERENCE_PATTERN.fullmatch(item) is None
        )
        malformed.extend(
            item for item in values["stories"]
            if re.fullmatch(
                r"TH[1-9][0-9]*\.E[1-9][0-9]*\.US[1-9][0-9]*", item
            ) is None
        )
        if (
            not values["records"]
            or not values["adrs"]
            or not values["components"]
            or malformed
        ):
            findings.append(
                _finding(
                    file=ARCHITECTURE_TRACE_PATH.as_posix(),
                    record=record_label,
                    message=(
                        "mapping requires records, ADRs, and components with "
                        f"canonical references; invalid: {', '.join(malformed) or 'empty required list'}"
                    ),
                    remediation="Declare only resolving canonical architecture references.",
                )
            )
            continue
        mappings.append(
            ArchitectureMapping(
                values["records"],
                theme,
                values["requirements"],
                values["adrs"],
                values["components"],
                values["stories"],
            )
        )
    return scope, tuple(mappings), accepted, findings


def _node_key(scope: str | None, identifier: str) -> tuple[str | None, str]:
    return scope, identifier


def _resolve(
    index: Mapping[tuple[str | None, str], Node],
    scope: str | None,
    identifier: str,
) -> Node | None:
    exact = index.get(_node_key(scope, identifier))
    if exact is not None:
        return exact
    if identifier.startswith("ADR-"):
        return index.get(_node_key(None, identifier))
    return None


def _edge_for(source: Node, target: Node) -> Edge:
    scope = source.scope if source.scope is not None else target.scope
    if source.stage < target.stage:
        return Edge(source.identifier, target.identifier, scope)
    if target.stage < source.stage:
        return Edge(target.identifier, source.identifier, scope)
    return Edge(source.identifier, target.identifier, scope)


def _evidence_nodes_and_edges(
    root: Path,
    story_sources: Sequence[StorySource],
    stories: Mapping[tuple[str | None, str], Node],
) -> tuple[list[Node], list[Edge], list[Finding]]:
    nodes: list[Node] = []
    edges: list[Edge] = []
    findings: list[Finding] = []
    for source in story_sources:
        story_key = _node_key(source.scope, source.expected_id or "")
        story = stories.get(story_key)
        if story is None:
            continue
        unknown_keys = sorted(
            _safe(key) for key in source.evidence if key not in EVIDENCE_KEYS
        )
        for key in unknown_keys:
            findings.append(
                _finding(
                    file=BACKLOG_PATH.as_posix(),
                    record=source.expected_id,
                    message=(
                        f"undefined evidence key {key!r}; expected exactly "
                        + ", ".join(EVIDENCE_KEYS)
                    ),
                    remediation="Remove the undefined evidence key.",
                )
            )
        for kind in EVIDENCE_KEYS:
            if kind not in source.evidence:
                findings.append(
                    _finding(
                        file=BACKLOG_PATH.as_posix(),
                        record=source.expected_id,
                        message=f"required evidence key {kind!r} is missing",
                        remediation="Declare every defined evidence key as a YAML list.",
                    )
                )
                continue
            values = source.evidence[kind]
            if not isinstance(values, list):
                findings.append(
                    _finding(
                        file=BACKLOG_PATH.as_posix(),
                        record=source.expected_id,
                        message=(
                            f"evidence.{kind} must be a YAML list of "
                            + (
                                "reserved repository paths"
                                if kind == "packets"
                                else "non-empty labels or repository paths"
                            )
                        ),
                        remediation=(
                            "Use reserved packet paths or concise evidence labels "
                            "and contained repository paths, as applicable."
                        ),
                    )
                )
                continue
            for index, value in enumerate(values):
                if not isinstance(value, str) or not value.strip():
                    findings.append(
                        _finding(
                            file=BACKLOG_PATH.as_posix(),
                            record=source.expected_id,
                            message=(
                                f"evidence.{kind}[{index}] must be a non-empty "
                                + ("reserved path" if kind == "packets" else "label or path")
                            ),
                            remediation="Use a non-empty concise evidence value.",
                        )
                    )
                    continue
                value = value.strip()
                if kind != "packets":
                    single_token = not any(
                        character.isspace() for character in value
                    )
                    path_shaped = single_token and (
                        "/" in value
                        or "\\" in value
                        or value.startswith(".")
                        or bool(re.search(r"\.[A-Za-z0-9]{1,12}$", value))
                    )
                    if not path_shaped:
                        # A label is authoritative backlog evidence only after
                        # implementation has started. Planned-work labels and
                        # reserved packet locations never become graph edges.
                        if source.status in IMPLEMENTED_STORY_STATUSES:
                            identifier = (
                                f"evidence:{source.expected_id}:{kind}:{index + 1}"
                            )
                            nodes.append(
                                Node(
                                    identifier,
                                    "evidence",
                                    BACKLOG_PATH.as_posix(),
                                    source.expected_id,
                                    source.scope,
                                )
                            )
                            edges.append(
                                Edge(
                                    source.expected_id or "",
                                    identifier,
                                    source.scope,
                                )
                            )
                        continue
                    syntactically_normal = (
                        EVIDENCE_PATH_PATTERN.fullmatch(value) is not None
                        and "\\" not in value
                    )
                    pure = PurePosixPath(value) if syntactically_normal else None
                    existing_path = (
                        root.joinpath(*pure.parts)
                        if pure is not None
                        and not pure.is_absolute()
                        and ".." not in pure.parts
                        else None
                    )
                    if (
                        existing_path is not None
                        and _contained_path(existing_path, root)
                    ):
                        pass
                    else:
                        strong_path_claim = (
                            value.startswith(("/", "./", "../", ".github/"))
                            or value.endswith("/")
                            or "\\" in value
                            or bool(re.search(r"\.[A-Za-z0-9]{1,12}$", value))
                            or value.startswith(
                                ("bin/", "docs/", "methodlib/", "tests/")
                            )
                        )
                        if not strong_path_claim:
                            continue
                    if not syntactically_normal:
                        findings.append(
                            _finding(
                                file=BACKLOG_PATH.as_posix(),
                                record=source.expected_id,
                                message=(
                                    f"evidence.{kind}[{index}] claims an invalid "
                                    "repository path"
                                ),
                                remediation=(
                                    "Use a normalized contained path, or rewrite "
                                    "the value as a concise evidence label."
                                ),
                            )
                        )
                        continue
                elif EVIDENCE_PATH_PATTERN.fullmatch(value) is None or "\\" in value:
                    findings.append(
                        _finding(
                            file=BACKLOG_PATH.as_posix(),
                            record=source.expected_id,
                            message=(
                                f"evidence.{kind}[{index}] is not a normalized "
                                "reserved repository path"
                            ),
                            remediation=(
                                "Use docs/plan/runtime/packets/<story-id>/."
                            ),
                        )
                    )
                    continue
                pure = PurePosixPath(value)
                if pure.is_absolute() or ".." in pure.parts:
                    findings.append(
                        _finding(
                            file=BACKLOG_PATH.as_posix(),
                            record=source.expected_id,
                            message=f"evidence.{kind}[{index}] leaves repository scope",
                            remediation="Use a normalized contained repository path.",
                        )
                    )
                    continue
                if kind == "packets":
                    reserved = RESERVED_PACKET_PATTERN.fullmatch(value)
                    if reserved is None or reserved.group("story") != source.expected_id:
                        findings.append(
                            _finding(
                                file=BACKLOG_PATH.as_posix(),
                                record=source.expected_id,
                                message="packet evidence path does not match its story",
                                remediation=(
                                    "Use docs/plan/runtime/packets/<story-id>/ "
                                    "for that story."
                                ),
                            )
                        )
                        continue
                evidence_path = root.joinpath(*pure.parts)
                if not _contained_path(evidence_path, root):
                    if (
                        kind == "packets"
                        and source.expected_id is not None
                        and RESERVED_PACKET_PATTERN.fullmatch(value) is not None
                    ):
                        # Packet entries reserve the exact per-story runtime
                        # location. An absent reservation is not completion
                        # evidence and therefore creates no graph edge.
                        continue
                    findings.append(
                        _finding(
                            file=BACKLOG_PATH.as_posix(),
                            record=source.expected_id,
                            message=(
                                f"evidence.{kind}[{index}] claimed path {value!r} "
                                "does not resolve to a contained file or directory"
                            ),
                            remediation="Create valid evidence or remove the placeholder.",
                        )
                    )
                    continue
                if source.status not in IMPLEMENTED_STORY_STATUSES:
                    continue
                identifier = f"evidence:{source.expected_id}:{kind}:{index + 1}"
                nodes.append(
                    Node(
                        identifier,
                        "evidence",
                        BACKLOG_PATH.as_posix(),
                        source.expected_id,
                        source.scope,
                    )
                )
                edges.append(Edge(source.expected_id or "", identifier, source.scope))
    return nodes, edges, findings


def _validate_repository(repository_root: PathValue) -> ValidationResult:
    try:
        root = Path(repository_root).resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        return ValidationResult(
            (
                _finding(
                    file=_safe(repository_root),
                    record=None,
                    message="repository root is missing or unreadable",
                    remediation="Run from a readable repository checkout.",
                ),
            )
        )
    try:
        contract = load_contract(root)
    except ContractError as error:
        return ValidationResult(
            (
                _finding(
                    file=SKILL_PATH.as_posix(),
                    record="traceability-contract",
                    message=str(error),
                    remediation="Restore the pinned machine-readable bdd-stories contract.",
                ),
            )
        )

    findings: list[Finding] = []
    story_sources, backlog_findings = _story_sources_from_backlog(root)
    findings.extend(backlog_findings)
    if backlog_findings and not story_sources:
        return ValidationResult(tuple(backlog_findings))
    active_scopes = frozenset(
        source.scope for source in story_sources if source.scope is not None
    )
    (
        record_nodes,
        parsed_records,
        prd_deferral_references,
        invalid_records,
        record_findings,
    ) = _record_nodes(root, active_scopes)
    findings.extend(record_findings)
    adr_nodes, adr_findings = _adr_nodes(root)
    findings.extend(adr_findings)
    story_nodes, story_declarations, story_findings = _story_nodes(
        root, contract, story_sources
    )
    findings.extend(story_findings)
    (
        architecture_scope,
        architecture_mappings,
        architecture_accepted,
        architecture_findings,
    ) = _architecture_trace_declaration(root)
    findings.extend(architecture_findings)

    prd_nodes = [
        Node(
            f"PRD:{scope}",
            "prd",
            file,
            f"PRD:{scope}",
            scope,
        )
        for scope, file in sorted(
            {
                (scope, file)
                for scope, _, file in prd_deferral_references
            }
        )
    ]
    nodes = record_nodes + prd_nodes + adr_nodes + story_nodes
    index: dict[tuple[str | None, str], Node] = {}
    for node in nodes:
        key = _node_key(node.scope, node.identifier)
        if key in index:
            findings.append(
                _finding(
                    file=node.file,
                    record=node.record,
                    message=f"graph node ID {node.identifier} is duplicated",
                    remediation="Keep one authoritative declaration per ID and VP scope.",
                )
            )
        else:
            index[key] = node

    edges: set[Edge] = set()
    for scope, target_id, file in prd_deferral_references:
        target = _resolve(index, scope, target_id)
        prd = _resolve(index, scope, f"PRD:{scope}")
        if target is None:
            findings.append(
                _finding(
                    file=file,
                    record=f"PRD:{scope}",
                    message=f"declared reference {target_id} does not resolve",
                    remediation=(
                        f"Add the authoritative dossier-owned {target_id} "
                        "record or correct the PRD reference."
                    ),
                )
            )
            continue
        if prd is not None:
            edges.add(_edge_for(target, prd))

    for scope, record in parsed_records:
        source = _resolve(index, scope, record.id)
        if source is None:
            continue
        for target_id in record.references:
            target = _resolve(index, scope, target_id)
            if target is None:
                if (scope, target_id) in invalid_records:
                    # The canonical owner already emitted the precise
                    # structural/schema finding. Do not misreport that
                    # existing-but-invalid record as absent.
                    continue
                findings.append(
                    _finding(
                        file=record.file,
                        record=record.id,
                        message=f"declared reference {target_id} does not resolve",
                        remediation=(
                            f"Add the authoritative {target_id} record or "
                            "correct the reference."
                        ),
                    )
                )
                continue
            edges.add(_edge_for(source, target))

        if not source.consequential or "Traces" not in record.columns:
            continue
        traces = record.columns.get("Traces")
        trace_ids = records.split_references(traces or "")
        valid_upstream = tuple(
            identifier
            for identifier in trace_ids
            if (
                (target := _resolve(index, scope, identifier)) is not None
                and target.stage < source.stage
            )
        )
        if not valid_upstream:
            findings.append(
                _finding(
                    file=record.file,
                    record=record.id,
                    message=(
                        f"consequential {record.prefix} record has no resolving "
                        "upstream record ID in its schema-defined Traces"
                    ),
                    remediation=(
                        "Add at least one canonical same-VP record from an "
                        "earlier graph stage to Traces."
                    ),
                )
            )

    for scope, record in parsed_records:
        source = _resolve(index, scope, record.id)
        if (
            source is None
            or source.consequential
            or record.prefix not in {"PR", "QR"}
            or record.columns.get("Impact", "").strip().lower() != "low-impact"
        ):
            continue
        traces = record.columns.get("Traces", "")
        trace_ids = records.split_references(traces)
        valid_upstream = any(
            (target := _resolve(index, scope, identifier)) is not None
            and target.stage < source.stage
            for identifier in trace_ids
        )
        if not valid_upstream:
            valid, reason = _document_reference(
                traces,
                root=root,
                scope=scope,
                record=record,
            )
            if not valid:
                findings.append(
                    _finding(
                        file=record.file,
                        record=record.id,
                        message=f"low-impact document reference is invalid: {reason}",
                        remediation=(
                            "Use a relevant item ID or one canonical same-VP "
                            "document path with an existing heading anchor."
                        ),
                    )
                )

    story_by_key = {
        _node_key(node.scope, node.identifier): node for node in story_nodes
    }
    for (scope, story_id), references in sorted(
        story_declarations.items(),
        key=lambda item: ((item[0][0] or ""), item[0][1]),
    ):
        story = story_by_key.get(_node_key(scope, story_id))
        if story is None:
            continue
        for target_id in references:
            target = _resolve(index, scope, target_id)
            if target is None:
                if (scope, target_id) in invalid_records:
                    continue
                findings.append(
                    _finding(
                        file=story.file,
                        record=story_id,
                        message=f"declared reference {target_id} does not resolve",
                        remediation=(
                            f"Add the authoritative {target_id} record or "
                            "correct the frontmatter."
                        ),
                    )
                )
                continue
            edges.add(_edge_for(target, story))
        # Co-mention in story frontmatter never infers PR/QR -> ADR. Accepted
        # architecture relationships come only from the canonical declaration.

    evidence_nodes, evidence_edges, evidence_findings = _evidence_nodes_and_edges(
        root, story_sources, story_by_key
    )
    nodes.extend(evidence_nodes)
    edges.update(evidence_edges)
    findings.extend(evidence_findings)

    active_themes = {
        source.theme for source in story_sources if source.theme is not None
    }
    story_status = {
        (source.scope, source.expected_id): source.status
        for source in story_sources
        if source.expected_id is not None
    }
    mapped_records: dict[tuple[str, str], list[ArchitectureMapping]] = {}
    if architecture_mappings:
        if architecture_scope not in active_scopes:
            findings.append(
                _finding(
                    file=ARCHITECTURE_TRACE_PATH.as_posix(),
                    record="architecture-trace",
                    message=(
                        f"architecture trace VP {architecture_scope} is not an "
                        "active backlog VP scope"
                    ),
                    remediation="Declare the exact VP owned by an active mapped theme.",
                )
            )
        assert architecture_scope is not None
        try:
            component_anchors = _heading_anchors(
                _read_text(root / "docs/architecture/components.md", root)
            )
        except ContractError:
            component_anchors = set()

        for mapping in architecture_mappings:
            resolved_records: list[Node] = []
            resolved_requirements: list[Node] = []
            resolved_adrs: list[Node] = []
            resolved_components: list[Node] = []
            resolved_stories: list[Node] = []

            for identifier in mapping.records:
                node = _resolve(index, architecture_scope, identifier)
                if node is None or node.kind not in ARCHITECTURE_RECORD_PREFIXES:
                    findings.append(
                        _finding(
                            file=ARCHITECTURE_TRACE_PATH.as_posix(),
                            record=identifier,
                            message=(
                                f"architecture trace record {identifier} does "
                                "not resolve in its VP"
                            ),
                            remediation="Use a canonical accepted same-VP record ID.",
                        )
                    )
                    continue
                resolved_records.append(node)
                mapped_records.setdefault(
                    (architecture_scope, identifier), []
                ).append(mapping)

            for identifier in mapping.requirements:
                node = _resolve(index, architecture_scope, identifier)
                if node is None or node.kind not in {"PR", "QR"}:
                    findings.append(
                        _finding(
                            file=ARCHITECTURE_TRACE_PATH.as_posix(),
                            record=identifier,
                            message=(
                                f"architecture requirement {identifier} does "
                                "not resolve in its VP"
                            ),
                            remediation="Use a canonical same-VP PR/QR ID.",
                        )
                    )
                else:
                    resolved_requirements.append(node)

            for identifier in mapping.adrs:
                node = _resolve(index, architecture_scope, identifier)
                if node is None or node.kind != "ADR":
                    findings.append(
                        _finding(
                            file=ARCHITECTURE_TRACE_PATH.as_posix(),
                            record=identifier,
                            message=f"architecture ADR {identifier} does not resolve",
                            remediation="Use an accepted canonical ADR ID.",
                        )
                    )
                else:
                    resolved_adrs.append(node)

            for reference in mapping.components:
                anchor = reference.split("#", 1)[1]
                if anchor not in component_anchors:
                    findings.append(
                        _finding(
                            file=ARCHITECTURE_TRACE_PATH.as_posix(),
                            record=reference,
                            message=(
                                f"architecture component {reference} does not "
                                "resolve to a component heading"
                            ),
                            remediation="Use an existing components.md heading anchor.",
                        )
                    )
                    continue
                key = _node_key(architecture_scope, reference)
                component = index.get(key)
                if component is None:
                    component = Node(
                        reference,
                        "component",
                        "docs/architecture/components.md",
                        reference,
                        architecture_scope,
                    )
                    index[key] = component
                    nodes.append(component)
                resolved_components.append(component)

            theme_active = mapping.theme in active_themes
            if theme_active and not mapping.stories:
                findings.append(
                    _finding(
                        file=ARCHITECTURE_TRACE_PATH.as_posix(),
                        record=", ".join(mapping.records),
                        message=(
                            f"mapped active/planned theme {mapping.theme} has "
                            "no applicable story links"
                        ),
                        remediation="Declare at least one applicable active-theme story.",
                    )
                )
            if not theme_active and mapping.stories:
                findings.append(
                    _finding(
                        file=ARCHITECTURE_TRACE_PATH.as_posix(),
                        record=", ".join(mapping.records),
                        message=(
                            f"inactive mapped theme {mapping.theme} must not "
                            "declare story or evidence links"
                        ),
                        remediation=(
                            "Leave stories empty until the mapped theme enters "
                            "the active backlog."
                        ),
                    )
                )
            for identifier in mapping.stories:
                node = _resolve(index, architecture_scope, identifier)
                if (
                    node is None
                    or node.kind != "story"
                    or not identifier.startswith(mapping.theme + ".")
                ):
                    findings.append(
                        _finding(
                            file=ARCHITECTURE_TRACE_PATH.as_posix(),
                            record=identifier,
                            message=(
                                f"architecture story {identifier} does not "
                                f"resolve in mapped theme {mapping.theme}"
                            ),
                            remediation="Use an applicable same-VP story in the mapped theme.",
                        )
                    )
                else:
                    resolved_stories.append(node)

            for source in resolved_records:
                bases = resolved_requirements or [source]
                for requirement in resolved_requirements:
                    if source.identifier != requirement.identifier:
                        edges.add(
                            Edge(
                                source.identifier,
                                requirement.identifier,
                                architecture_scope,
                            )
                        )
                for base in bases:
                    for adr in resolved_adrs:
                        edges.add(
                            Edge(base.identifier, adr.identifier, architecture_scope)
                        )
            for adr in resolved_adrs:
                for component in resolved_components:
                    edges.add(
                        Edge(adr.identifier, component.identifier, architecture_scope)
                    )
            for component in resolved_components:
                for story in resolved_stories:
                    edges.add(
                        Edge(component.identifier, story.identifier, architecture_scope)
                    )

    adjacency: dict[tuple[str | None, str], set[str]] = {}
    for edge in edges:
        adjacency.setdefault(
            _node_key(edge.scope, edge.source), set()
        ).add(edge.target)

    def reachable(scope: str | None, start: str) -> set[str]:
        """Walk only edges in the record's VP scope."""

        visited: set[str] = set()
        pending = list(adjacency.get(_node_key(scope, start), ()))
        while pending:
            identifier = pending.pop()
            if identifier in visited:
                continue
            visited.add(identifier)
            pending.extend(
                adjacency.get(_node_key(scope, identifier), set()) - visited
            )
        return visited

    if architecture_accepted and architecture_scope is not None:
        for node in record_nodes:
            if not node.consequential or node.scope != architecture_scope:
                continue
            downstream = reachable(node.scope, node.identifier)
            mappings = [
                mapping
                for identifier in {node.identifier, *downstream}
                for mapping in mapped_records.get(
                    (architecture_scope, identifier), []
                )
            ]
            if not any(
                (
                    (target := _resolve(index, node.scope, identifier))
                    is not None
                    and target.kind in {"ADR", "component"}
                )
                for identifier in downstream
            ):
                findings.append(
                    _finding(
                        file=node.file,
                        record=node.record,
                        message=(
                            f"consequential {node.kind} record has no transitively "
                            "reachable architecture link"
                        ),
                        remediation="Declare a resolving PR/QR to ADR/component path.",
                    )
                )
            active_mappings = [
                mapping for mapping in mappings if mapping.theme in active_themes
            ]
            if active_mappings and not any(
                identifier.startswith("TH") and ".US" in identifier
                for identifier in downstream
            ):
                findings.append(
                    _finding(
                        file=node.file,
                        record=node.record,
                        message=(
                            f"consequential {node.kind} record has no transitively "
                            "reachable story for its active/planned mapped theme"
                        ),
                        remediation="Declare an applicable mapped-theme story path.",
                    )
                )

        mapped_story_ids = {
            story
            for mapping in architecture_mappings
            if mapping.theme in active_themes
            for story in mapping.stories
        }
        for story_id in sorted(mapped_story_ids):
            if story_status.get((architecture_scope, story_id)) != "done":
                continue
            if not any(
                identifier.startswith("evidence:")
                for identifier in reachable(architecture_scope, story_id)
            ):
                story = _resolve(index, architecture_scope, story_id)
                findings.append(
                    _finding(
                        file=(
                            story.file
                            if story is not None
                            else BACKLOG_PATH.as_posix()
                        ),
                        record=story_id,
                        message=(
                            "completed applicable story has no downstream "
                            "evidence link"
                        ),
                        remediation=(
                            "Record non-empty completion evidence in the "
                            "authoritative backlog."
                        ),
                    )
                )

    ordered_nodes = tuple(
        sorted(
            nodes,
            key=lambda item: (
                item.stage,
                item.scope or "",
                item.identifier,
                item.file,
            ),
        )
    )
    ordered_edges = tuple(sorted(edges, key=Edge.sort_key))
    ordered_findings = tuple(
        sorted(
            findings,
            key=lambda item: (
                str(item["file"]),
                str(item["record"]),
                str(item["message"]),
            ),
        )
    )
    return ValidationResult(ordered_findings, ordered_nodes, ordered_edges)


def validate_repository(repository_root: PathValue) -> ValidationResult:
    """Validate the repository's declared trace graph without network access."""

    try:
        return _validate_repository(repository_root)
    except (ContractError, OSError, RuntimeError, ValueError, yaml.YAMLError) as error:
        return ValidationResult(
            (
                _finding(
                    file="<repository>",
                    record=None,
                    message=f"trace validation could not safely continue: {error}",
                    remediation="Repair malformed or unsafe traceability inputs and retry.",
                ),
            )
        )


__all__ = [
    "CHECK",
    "CONTRACT_END",
    "CONTRACT_START",
    "ContractError",
    "Edge",
    "Node",
    "SKILL_PATH",
    "ValidationResult",
    "load_contract",
    "validate_repository",
]
