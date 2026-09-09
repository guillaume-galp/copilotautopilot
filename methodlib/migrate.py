"""Deterministic, prospective migration assessment generation.

Repository content is evidence, not instruction.  Inputs are read without
following symlinks, YAML is bounded and duplicate-key safe, and an assessment
never reconstructs missing historical Discovery, verification, or usage.
"""

from __future__ import annotations

import os
import re
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Mapping, Sequence

import yaml

from methodlib import __version__, lock
from methodlib.backlog import UniqueKeyLoader


Finding = dict[str, object]

CHECK = "migrate"
DEFAULT_OUTPUT = "docs/plan/migration-assessment.md"
BACKLOG_PATH = "docs/plan/backlog.yaml"
LEDGER_PATH = "docs/plan/activation-ledger.yaml"
MAX_INPUT_BYTES = 2 * 1024 * 1024
MAX_RECURSIVE_FILES = 1_024
MAX_RECURSIVE_BYTES = 16 * 1024 * 1024
MAX_RECURSIVE_DEPTH = 16
MAX_RECURSIVE_DIRECTORIES = 1_024
MAX_RECURSIVE_ENTRIES = 2_048
SAFE_PATH_PART = re.compile(r"[A-Za-z0-9._-]+")
VP_PATTERN = re.compile(r"VP[1-9][0-9]*")
THEME_PATTERN = re.compile(r"TH[1-9][0-9]*")
CONTROL_PATTERN = re.compile(r"CTL-(?:00[1-9]|0[1-9][0-9]|[1-9][0-9]{2})")
REQUIRED_GATE_FIELDS = (
    "Actor",
    "Timestamp",
    "Scope",
    "Verdict",
    "Rationale",
    "Source revision",
)


class InertYamlLoader(UniqueKeyLoader):
    """Duplicate-safe YAML loader that also rejects aliases."""

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
class Scope:
    vp: str
    theme: str
    data: Mapping[str, object]
    archived: bool
    locked: bool
    archive_ref: str | None

    @property
    def label(self) -> str:
        return f"{self.vp} / {self.theme}"


@dataclass(frozen=True)
class AssessmentResult:
    output: str
    changed: bool
    findings: tuple[Finding, ...] = ()


class AssessmentError(ValueError):
    """An assessment input or output cannot be handled safely."""

    def __init__(self, finding: Finding) -> None:
        super().__init__(str(finding["message"]))
        self.finding = finding


def _display(value: object) -> str:
    text = str(value)
    return "".join(
        character
        if character.isprintable() and not 0xD800 <= ord(character) <= 0xDFFF
        else rf"\u{ord(character):04x}"
        for character in text
    )


def _finding(
    file: object,
    message: str,
    remediation: str,
    *,
    record: str = "output",
) -> Finding:
    return {
        "check": CHECK,
        "severity": "error",
        "file": _display(file),
        "record": record,
        "message": message,
        "remediation": remediation,
    }


def _raise(
    file: object,
    message: str,
    remediation: str,
    *,
    record: str = "output",
) -> None:
    raise AssessmentError(
        _finding(file, message, remediation, record=record)
    )


def _safe_relative(value: str) -> PurePosixPath | None:
    if "\\" in value or "\x00" in value:
        return None
    path = PurePosixPath(value)
    if (
        not value
        or path.is_absolute()
        or "." in path.parts
        or ".." in path.parts
        or not path.parts
        or any(SAFE_PATH_PART.fullmatch(part) is None for part in path.parts)
    ):
        return None
    return path


def _assert_no_symlink_ancestors(
    root: Path,
    relative: PurePosixPath,
    *,
    include_leaf: bool,
) -> None:
    current = root
    parts = relative.parts if include_leaf else relative.parts[:-1]
    for part in parts:
        current = current / part
        try:
            info = current.lstat()
        except FileNotFoundError:
            return
        except OSError as error:
            _raise(
                relative.as_posix(),
                f"path cannot be inspected safely: {error}.",
                "Use a readable regular path inside the repository.",
            )
        if stat.S_ISLNK(info.st_mode):
            _raise(
                relative.as_posix(),
                "symlinks are not allowed in migration assessment paths.",
                "Use a regular repository directory and regular output file.",
            )


def _safe_input_file(
    root: Path,
    relative_value: str,
    *,
    required: bool,
) -> Path | None:
    relative = _safe_relative(relative_value)
    if relative is None:
        _raise(
            relative_value,
            "input path is absolute, traverses the repository, or is malformed.",
            "Use a canonical repository-relative path.",
            record="input",
        )
    _assert_no_symlink_ancestors(root, relative, include_leaf=True)
    path = root.joinpath(*relative.parts)
    try:
        info = path.lstat()
    except FileNotFoundError:
        if required:
            _raise(
                relative.as_posix(),
                "required migration assessment input is missing.",
                "Restore the required repository record before assessing migration.",
                record="input",
            )
        return None
    except OSError as error:
        _raise(
            relative.as_posix(),
            f"migration assessment input is unreadable: {error}.",
            "Restore a readable regular repository file.",
            record="input",
        )
    if not stat.S_ISREG(info.st_mode):
        _raise(
            relative.as_posix(),
            "migration assessment input is not a regular file.",
            "Replace it with a regular repository file.",
            record="input",
        )
    if info.st_size > MAX_INPUT_BYTES:
        _raise(
            relative.as_posix(),
            f"migration assessment input exceeds {MAX_INPUT_BYTES} bytes.",
            "Reduce the control file to the documented safety bound.",
            record="input",
        )
    return path


def _read_text(root: Path, relative_value: str, *, required: bool = True) -> str | None:
    path = _safe_input_file(root, relative_value, required=required)
    if path is None:
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        _raise(
            relative_value,
            f"migration assessment input is not readable UTF-8: {error}.",
            "Restore a readable UTF-8 repository file.",
            record="input",
        )
    return None


def _read_yaml(
    root: Path,
    relative_value: str,
    *,
    required: bool = True,
) -> object | None:
    text = _read_text(root, relative_value, required=required)
    if text is None:
        return None
    try:
        return yaml.load(text, Loader=InertYamlLoader)
    except (yaml.YAMLError, RecursionError) as error:
        _raise(
            relative_value,
            f"migration assessment input contains unsafe or malformed YAML: {error}.",
            "Correct duplicate keys, aliases, or malformed YAML before assessing.",
            record="input",
        )
    return None


def _output_path(root: Path, value: str) -> tuple[PurePosixPath, Path]:
    relative = _safe_relative(value)
    if relative is None:
        _raise(
            value,
            "output path is absolute, traverses the repository, or is malformed.",
            "Use a canonical repository-relative Markdown path without `.` or `..`.",
        )
    if relative.suffix.lower() != ".md":
        _raise(
            relative.as_posix(),
            "migration assessment output must be a Markdown file.",
            "Choose a repository-relative path ending in `.md`.",
        )
    _assert_no_symlink_ancestors(root, relative, include_leaf=True)
    path = root.joinpath(*relative.parts)
    parent = path.parent
    try:
        parent_info = parent.lstat()
    except OSError:
        _raise(
            relative.as_posix(),
            "output parent directory does not exist or is unreadable.",
            "Create a regular repository directory before running the assessment.",
        )
    if not stat.S_ISDIR(parent_info.st_mode):
        _raise(
            relative.as_posix(),
            "output parent is not a regular directory.",
            "Choose an existing regular repository directory.",
        )
    if path.exists() and not path.is_file():
        _raise(
            relative.as_posix(),
            "output target is not a regular file.",
            "Choose a regular Markdown file target.",
        )
    return relative, path


def _mapping(value: object, *, file: str, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        _raise(
            file,
            f"{name} must be a YAML mapping.",
            f"Restore the documented {name} structure.",
            record="input",
        )
    return value


def _sequence(value: object, *, file: str, name: str) -> Sequence[object]:
    if not isinstance(value, list):
        _raise(
            file,
            f"{name} must be a YAML sequence.",
            f"Restore the documented {name} structure.",
            record="input",
        )
    return value


def _identifier_number(identifier: str) -> int:
    match = re.search(r"[1-9][0-9]*", identifier)
    return int(match.group()) if match is not None else 0


def _vp_from_reference(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    relative = _safe_relative(value.rstrip("/"))
    if relative is None:
        return None
    for part in relative.parts:
        match = re.match(r"(VP[1-9][0-9]*)(?:-|$)", part)
        if match is not None:
            return match.group(1)
    return None


def _load_scopes(root: Path) -> tuple[Mapping[str, object], tuple[Scope, ...]]:
    document = _mapping(
        _read_yaml(root, BACKLOG_PATH),
        file=BACKLOG_PATH,
        name="backlog document",
    )
    body = _mapping(
        document.get("backlog"),
        file=BACKLOG_PATH,
        name="backlog",
    )
    active = _sequence(
        body.get("active-themes", []),
        file=BACKLOG_PATH,
        name="backlog.active-themes",
    )
    archived = _sequence(
        body.get("archived-themes", []),
        file=BACKLOG_PATH,
        name="backlog.archived-themes",
    )
    scopes: list[Scope] = []
    seen: set[str] = set()

    for raw in active:
        theme = _mapping(raw, file=BACKLOG_PATH, name="active theme")
        theme_id = theme.get("id")
        vp = _vp_from_reference(theme.get("vision-ref"))
        if (
            not isinstance(theme_id, str)
            or THEME_PATTERN.fullmatch(theme_id) is None
            or vp is None
            or theme_id in seen
        ):
            _raise(
                BACKLOG_PATH,
                "active theme lacks a unique canonical id or Vision reference.",
                "Restore canonical TH<n> ids and VP<n>-scoped vision-ref values.",
                record="input",
            )
        seen.add(theme_id)
        scopes.append(
            Scope(
                vp=vp,
                theme=theme_id,
                data=theme,
                archived=False,
                locked=theme.get("locked") is True,
                archive_ref=None,
            )
        )

    for raw in archived:
        summary = _mapping(raw, file=BACKLOG_PATH, name="archived theme")
        theme_id = summary.get("id")
        archive_ref = summary.get("archive-ref")
        if (
            not isinstance(theme_id, str)
            or THEME_PATTERN.fullmatch(theme_id) is None
            or theme_id in seen
            or not isinstance(archive_ref, str)
        ):
            _raise(
                BACKLOG_PATH,
                "archived theme lacks a unique canonical id or archive-ref.",
                "Restore canonical archived theme metadata.",
                record="input",
            )
        archive_document = _mapping(
            _read_yaml(root, archive_ref),
            file=archive_ref,
            name="archive document",
        )
        theme = _mapping(
            archive_document.get("theme"),
            file=archive_ref,
            name="archived theme body",
        )
        if theme.get("id") != theme_id:
            _raise(
                archive_ref,
                "archive theme id does not match its backlog index entry.",
                "Restore the archive matching the indexed locked theme.",
                record="input",
            )
        vp = _vp_from_reference(theme.get("vision-ref"))
        if vp is None:
            _raise(
                archive_ref,
                "archived theme has no canonical Vision reference.",
                "Restore its VP<n>-scoped vision-ref.",
                record="input",
            )
        seen.add(theme_id)
        scopes.append(
            Scope(
                vp=vp,
                theme=theme_id,
                data=theme,
                archived=True,
                locked=summary.get("locked") is True or theme.get("locked") is True,
                archive_ref=archive_ref,
            )
        )
    scopes.sort(key=lambda item: (_identifier_number(item.vp), _identifier_number(item.theme)))
    return body, tuple(scopes)


def _reject_locked_output(
    root: Path,
    relative: PurePosixPath,
    scopes: Sequence[Scope],
) -> None:
    themes = {scope.theme: scope.data for scope in scopes}
    protected = lock.protected_artefact_scopes(root, themes)
    match = next(
        (
            item
            for item in protected
            if relative.as_posix() == item.path
            or (
                item.recursive
                and len(relative.parts) > len(PurePosixPath(item.path).parts)
                and relative.parts[: len(PurePosixPath(item.path).parts)]
                == PurePosixPath(item.path).parts
            )
        ),
        None,
    )
    if match is None:
        return
    _raise(
        relative.as_posix(),
        (
            "locked artefacts cannot receive generated content "
            f"({match.record}, {match.kind})."
        ),
        "Write the assessment outside every protected artefact scope.",
        record=match.record,
    )


def _path_has_markdown(root: Path, relative_value: object) -> bool:
    if not isinstance(relative_value, str):
        return False
    relative = _safe_relative(relative_value.rstrip("/"))
    if relative is None:
        return False
    _assert_no_symlink_ancestors(root, relative, include_leaf=True)
    path = root.joinpath(*relative.parts)
    try:
        info = path.lstat()
    except OSError:
        return False
    if stat.S_ISREG(info.st_mode):
        return path.suffix.lower() == ".md"
    if not stat.S_ISDIR(info.st_mode):
        return False
    try:
        children = tuple(os.scandir(path))
    except OSError:
        return False
    for child in children:
        if child.is_symlink():
            _raise(
                relative.as_posix(),
                "symlinks are not allowed in migration assessment inputs.",
                "Replace the symlink with a regular repository artefact.",
                record="input",
            )
        if child.is_file(follow_symlinks=False) and child.name.endswith(".md"):
            return True
    return False


def _canonical_scope(root: Path, base_value: str, vp: str) -> Path | None:
    relative = _safe_relative(base_value)
    assert relative is not None
    _assert_no_symlink_ancestors(root, relative, include_leaf=True)
    base = root.joinpath(*relative.parts)
    try:
        entries = tuple(os.scandir(base))
    except FileNotFoundError:
        return None
    except OSError:
        return None
    matches: list[Path] = []
    for entry in entries:
        if entry.name == vp or entry.name.startswith(vp + "-"):
            if entry.is_symlink():
                _raise(
                    f"{base_value}/{entry.name}",
                    "symlinks are not allowed in migration assessment inputs.",
                    "Replace the symlink with a regular repository scope.",
                    record="input",
                )
            if entry.is_dir(follow_symlinks=False):
                matches.append(Path(entry.path))
    return matches[0] if len(matches) == 1 else None


def _theme_directory(root: Path, scope: Scope) -> Path | None:
    epics = scope.data.get("epics")
    if isinstance(epics, list):
        for epic in epics:
            if not isinstance(epic, Mapping):
                continue
            stories = epic.get("stories")
            if not isinstance(stories, list):
                continue
            for story in stories:
                if not isinstance(story, Mapping):
                    continue
                value = story.get("file")
                if not isinstance(value, str):
                    continue
                relative = _safe_relative(value)
                if (
                    relative is not None
                    and len(relative.parts) >= 3
                    and relative.parts[:2] == ("docs", "themes")
                ):
                    directory = PurePosixPath(*relative.parts[:3])
                    _assert_no_symlink_ancestors(root, directory, include_leaf=True)
                    candidate = root.joinpath(*directory.parts)
                    if candidate.is_dir():
                        return candidate
    base_relative = PurePosixPath("docs/themes")
    _assert_no_symlink_ancestors(root, base_relative, include_leaf=True)
    base = root / base_relative
    try:
        entries = tuple(os.scandir(base))
    except OSError:
        return None
    matches = []
    for entry in entries:
        if entry.name == scope.theme or entry.name.startswith(scope.theme + "-"):
            if entry.is_symlink():
                _raise(
                    f"docs/themes/{entry.name}",
                    "symlinks are not allowed in migration assessment inputs.",
                    "Replace the symlink with a regular theme directory.",
                    record="input",
                )
            if entry.is_dir(follow_symlinks=False):
                matches.append(Path(entry.path))
    return matches[0] if len(matches) == 1 else None


def _has_vp_token(text: str, vp: str) -> bool:
    token = re.compile(rf"(?<![A-Za-z0-9]){re.escape(vp)}(?![A-Za-z0-9])")
    return token.search(text) is not None


def _architecture_presence(
    root: Path,
    vps: Sequence[str],
) -> frozenset[str]:
    base_relative = PurePosixPath("docs/architecture")
    _assert_no_symlink_ancestors(root, base_relative, include_leaf=True)
    base = root / base_relative
    try:
        base_info = base.lstat()
    except FileNotFoundError:
        return frozenset()
    except OSError:
        _raise(
            base_relative.as_posix(),
            "recursive architecture input cannot be inspected safely.",
            "Restore a readable regular architecture directory.",
            record="input",
        )
    if not stat.S_ISDIR(base_info.st_mode):
        _raise(
            base_relative.as_posix(),
            "recursive architecture input is not a regular directory.",
            "Restore a regular architecture directory.",
            record="input",
        )

    pending: list[tuple[Path, int]] = [(base, 0)]
    file_count = 0
    directory_count = 1
    entry_count = 0
    total_bytes = 0
    present: set[str] = set()
    while pending:
        directory, depth = pending.pop()
        try:
            with os.scandir(directory) as iterator:
                entries = []
                for entry in iterator:
                    entry_count += 1
                    if entry_count > MAX_RECURSIVE_ENTRIES:
                        _raise(
                            base_relative.as_posix(),
                            (
                                "recursive architecture input exceeds the "
                                f"entry limit of {MAX_RECURSIVE_ENTRIES}."
                            ),
                            "Reduce the architecture tree before assessing migration.",
                            record="input",
                        )
                    entries.append(entry)
            entries.sort(key=lambda item: item.name)
        except OSError:
            _raise(
                directory.relative_to(root).as_posix(),
                "recursive architecture input cannot be read safely.",
                "Restore a readable regular architecture tree.",
                record="input",
            )
        child_directories: list[Path] = []
        for entry in entries:
            relative = Path(entry.path).relative_to(root).as_posix()
            try:
                info = entry.stat(follow_symlinks=False)
            except OSError:
                _raise(
                    relative,
                    "recursive architecture input cannot be inspected safely.",
                    "Restore a readable regular architecture artefact.",
                    record="input",
                )
            if stat.S_ISLNK(info.st_mode):
                _raise(
                    relative,
                    "symlinks are not allowed in migration assessment inputs.",
                    "Replace the symlink with a regular architecture artefact.",
                    record="input",
                )
            if stat.S_ISDIR(info.st_mode):
                child_depth = depth + 1
                if child_depth > MAX_RECURSIVE_DEPTH:
                    _raise(
                        relative,
                        (
                            "recursive architecture input exceeds the "
                            f"maximum depth of {MAX_RECURSIVE_DEPTH}."
                        ),
                        "Reduce nesting before assessing migration.",
                        record="input",
                    )
                directory_count += 1
                if directory_count > MAX_RECURSIVE_DIRECTORIES:
                    _raise(
                        base_relative.as_posix(),
                        (
                            "recursive architecture input exceeds the "
                            f"directory limit of {MAX_RECURSIVE_DIRECTORIES}."
                        ),
                        "Reduce the architecture tree before assessing migration.",
                        record="input",
                    )
                child_directories.append(Path(entry.path))
            elif stat.S_ISREG(info.st_mode):
                file_count += 1
                if file_count > MAX_RECURSIVE_FILES:
                    _raise(
                        relative,
                        (
                            "recursive architecture input exceeds the "
                            f"file limit of {MAX_RECURSIVE_FILES}."
                        ),
                        "Reduce the architecture input set before assessing migration.",
                        record="input",
                    )
                total_bytes += info.st_size
                if total_bytes > MAX_RECURSIVE_BYTES:
                    _raise(
                        relative,
                        (
                            "recursive architecture input exceeds the aggregate "
                            f"byte limit of {MAX_RECURSIVE_BYTES}."
                        ),
                        "Reduce the architecture input size before assessing migration.",
                        record="input",
                    )
                if entry.name.endswith(".md"):
                    text = _read_text(root, relative)
                    if text is not None:
                        present.update(
                            vp for vp in vps if _has_vp_token(text, vp)
                        )
            else:
                _raise(
                    relative,
                    "recursive architecture input has an unsupported file type.",
                    "Use only regular files and directories in architecture inputs.",
                    record="input",
                )
        # Reverse push preserves lexical depth-first traversal with a LIFO
        # stack, making the first over-limit finding deterministic.
        pending.extend((child, depth + 1) for child in reversed(child_directories))
    return frozenset(present)


def _stories(scope: Scope) -> tuple[Mapping[str, object], ...]:
    """Return executable units (legacy stories or prospective epics)."""
    result: list[Mapping[str, object]] = []
    epics = scope.data.get("epics")
    if not isinstance(epics, list):
        return ()
    for epic in epics:
        if not isinstance(epic, Mapping):
            continue
        if scope.data.get("schema-version") == 3:
            result.append(epic)
            continue
        stories = epic.get("stories")
        if isinstance(stories, list):
            result.extend(story for story in stories if isinstance(story, Mapping))
    return tuple(result)


def _execution_present(scope: Scope) -> bool:
    if scope.data.get("status") == "done":
        return True
    return any(
        story.get("status") in {"in-progress", "blocked", "failed", "done"}
        for story in _stories(scope)
    )


def _structured_evidence(scope: Scope, kind: str) -> str:
    if kind == "usage":
        usage = scope.data.get("usage")
        if (
            isinstance(usage, Mapping)
            and usage.get("confidence") in {"measured", "estimated"}
            and isinstance(usage.get("value"), (int, float))
            and not isinstance(usage.get("value"), bool)
        ):
            return "present"
    for story in _stories(scope):
        evidence = story.get("evidence")
        if not isinstance(evidence, Mapping):
            continue
        values = evidence.get(kind)
        if kind == "usage":
            if isinstance(values, list) and any(
                isinstance(value, str)
                and re.search(r"\b(?:measured|estimated)\b", value, flags=re.IGNORECASE)
                is not None
                for value in values
            ):
                return "present"
            continue
        if isinstance(values, list) and any(
            isinstance(value, str) and value.strip() for value in values
        ):
            return "present"
    return "unknown"


def _field_table(section: str) -> Mapping[str, str] | None:
    rows: list[list[str]] = []
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            rows.append([cell.strip() for cell in stripped[1:-1].split("|")])
        elif rows:
            break
    if (
        len(rows) < 3
        or rows[0] != ["Field", "Value"]
        or len(rows[1]) != 2
        or any(re.fullmatch(r":?-{3,}:?", cell) is None for cell in rows[1])
        or any(len(row) != 2 for row in rows[2:])
    ):
        return None
    return dict(rows[2:])


def _gate_fields(root: Path, path: Path | None, heading: str) -> Mapping[str, str] | None:
    if path is None:
        return None
    try:
        relative = path.relative_to(root).as_posix()
    except ValueError:
        return None
    text = _read_text(root, relative, required=False)
    if text is None:
        return None
    marker = f"## {heading}"
    lines = text.splitlines()
    headings = [index for index, line in enumerate(lines) if line == marker]
    if len(headings) != 1:
        return None
    start = headings[0] + 1
    end = next(
        (
            index
            for index in range(start, len(lines))
            if lines[index].startswith("## ")
        ),
        len(lines),
    )
    section = "\n".join(lines[start:end])
    fields = _field_table(section)
    if fields is None or any(not fields.get(field) for field in REQUIRED_GATE_FIELDS):
        return None
    return fields


def _coverage(
    root: Path,
    scope: Scope,
    architecture_vps: frozenset[str],
) -> tuple[tuple[str, ...], Path | None, Path | None, Path | None]:
    discovery = _canonical_scope(root, "docs/discovery", scope.vp)
    requirements = _canonical_scope(root, "docs/requirements", scope.vp)
    theme = _theme_directory(root, scope)
    values = (
        "present" if _path_has_markdown(root, scope.data.get("vision-ref")) else "unknown",
        (
            "present"
            if discovery is not None and _safe_input_file(
                root,
                (discovery / "README.md").relative_to(root).as_posix(),
                required=False,
            )
            is not None
            else "unknown"
        ),
        (
            "present"
            if requirements is not None and _safe_input_file(
                root,
                (requirements / "PRD.md").relative_to(root).as_posix(),
                required=False,
            )
            is not None
            else "unknown"
        ),
        "present" if scope.vp in architecture_vps else "unknown",
        (
            "present"
            if scope.data.get("epics") or theme is not None
            else "unknown"
        ),
        "present" if _execution_present(scope) else "unknown",
    )
    return values, discovery, requirements, theme


def _gate_rows(
    root: Path,
    scope: Scope,
    discovery: Path | None,
    requirements: Path | None,
    theme: Path | None,
) -> tuple[tuple[str, str, str, str, str], ...]:
    discovery_fields = _gate_fields(
        root,
        discovery / "README.md" if discovery is not None else None,
        "Acceptance",
    )
    prd_fields = _gate_fields(
        root,
        requirements / "PRD.md" if requirements is not None else None,
        "Approval",
    )
    architecture_fields = _gate_fields(
        root,
        root / "docs/architecture/README.md",
        "Acceptance",
    )
    architecture_present = (
        architecture_fields is not None
        and _has_vp_token(architecture_fields.get("Scope", ""), scope.vp)
    )
    admission = theme / "planning-admission.md" if theme is not None else None
    admission_fields = _gate_fields(root, admission, "Acceptance")
    if admission_fields is None:
        admission_fields = _gate_fields(root, admission, "Approval")

    note = (
        "Not recorded; expected for a locked legacy scope and not remediated retroactively."
        if scope.archived and scope.locked
        else "Current six-stage scope; create the gate prospectively before stage entry."
    )
    return (
        (
            scope.label,
            "Requirements",
            "Discovery readiness acceptance",
            "yes" if discovery_fields is not None else "no",
            "Recorded current gate." if discovery_fields is not None else note,
        ),
        (
            scope.label,
            "Architecture",
            "PRD approval",
            "yes" if prd_fields is not None else "no",
            "Recorded current gate." if prd_fields is not None else note,
        ),
        (
            scope.label,
            "Planning",
            "Architecture acceptance",
            "yes" if architecture_present else "no",
            "Recorded current gate." if architecture_present else note,
        ),
        (
            scope.label,
            "Autopilot",
            "Planning-admission acceptance",
            "yes" if admission_fields is not None else "no",
            "Recorded current gate." if admission_fields is not None else note,
        ),
    )


def _control_rows(root: Path) -> tuple[tuple[str, str, str, str], ...]:
    document = _read_yaml(root, LEDGER_PATH, required=False)
    if document is None:
        return (("unknown", "unknown", "unknown", "unknown"),)
    ledger = _mapping(document, file=LEDGER_PATH, name="activation ledger")
    controls = _sequence(
        ledger.get("controls"),
        file=LEDGER_PATH,
        name="activation ledger controls",
    )
    rows: list[tuple[str, str, str, str]] = []
    for raw in controls:
        control = _mapping(raw, file=LEDGER_PATH, name="activation control")
        identifier = control.get("id")
        if not isinstance(identifier, str) or CONTROL_PATTERN.fullmatch(identifier) is None:
            _raise(
                LEDGER_PATH,
                "activation ledger contains a noncanonical control id.",
                "Restore canonical CTL-### control records.",
                record="input",
            )
        name = control.get("name")
        state = control.get("state")
        effective = control.get("effective-point")
        limitations = control.get("limitations")
        rows.append(
            (
                f"{identifier} — {name}" if isinstance(name, str) and name else identifier,
                state if isinstance(state, str) and state else "unknown",
                effective if isinstance(effective, str) and effective else "unknown",
                (
                    "; ".join(str(value) for value in limitations)
                    if isinstance(limitations, list) and limitations
                    else "none recorded"
                ),
            )
        )
    return tuple(rows) or (("unknown", "unknown", "unknown", "unknown"),)


def _adoption_point(scopes: Sequence[Scope]) -> tuple[str, str]:
    prospective = [
        scope
        for scope in scopes
        if not scope.archived
        and isinstance(scope.data.get("schema-version"), int)
        and scope.data.get("schema-version", 0) >= 2
    ]
    if prospective:
        point = prospective[0].label
        return point, f"{point} and later new scopes"
    vp_number = max((_identifier_number(scope.vp) for scope in scopes), default=0) + 1
    theme_number = max(
        (_identifier_number(scope.theme) for scope in scopes),
        default=0,
    ) + 1
    point = f"VP{vp_number} / TH{theme_number} (next new scope)"
    return point, f"VP{vp_number} / TH{theme_number} and later new scopes"


def _cell(value: object) -> str:
    return str(value).replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


def _table(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> list[str]:
    result = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    result.extend(
        "| " + " | ".join(_cell(value) for value in row) + " |"
        for row in rows
    )
    return result


def _render(
    *,
    root: Path,
    backlog_body: Mapping[str, object],
    scopes: Sequence[Scope],
) -> str:
    coverage_rows: list[tuple[object, ...]] = []
    gate_rows: list[tuple[str, str, str, str, str]] = []
    evidence_rows: list[tuple[str, str, str, str]] = []
    unknown_discovery: list[str] = []
    unknown_verification: list[str] = []
    unknown_usage: list[str] = []
    architecture_vps = _architecture_presence(
        root,
        tuple(scope.vp for scope in scopes),
    )

    for scope in scopes:
        coverage, discovery, requirements, theme = _coverage(
            root,
            scope,
            architecture_vps,
        )
        coverage_rows.append((scope.label, *coverage))
        gate_rows.extend(
            _gate_rows(root, scope, discovery, requirements, theme)
        )
        discovery_evidence = coverage[1]
        verification = _structured_evidence(scope, "verification")
        usage = _structured_evidence(scope, "usage")
        evidence_rows.append(
            (scope.label, discovery_evidence, verification, usage)
        )
        if discovery_evidence == "unknown":
            unknown_discovery.append(scope.label)
        if verification == "unknown":
            unknown_verification.append(scope.label)
        if usage == "unknown":
            unknown_usage.append(scope.label)

    maturity_rows = _control_rows(root)
    adoption, prospective = _adoption_point(scopes)
    legacy = [scope for scope in scopes if scope.archived and scope.locked]
    locked_rows = [
        (
            (
                f"{scope.theme} theme and stories"
                + (
                    f", and `{scope.archive_ref}`"
                    if scope.archive_ref is not None
                    else ""
                )
            ),
            "yes",
            "no",
        )
        for scope in legacy
    ]
    if (root / "docs/ADRs/ADR-001-gitflow-operator.md").is_file():
        locked_rows.append(("ADR-001", "yes", "no"))
    if not locked_rows:
        locked_rows.append(("none recorded", "unknown", "unknown"))

    report_findings: list[tuple[str, str, str, str]] = []
    missing_legacy = sum(
        1
        for row in gate_rows
        if row[3] == "no"
        and any(row[0] == scope.label for scope in legacy)
    )
    if missing_legacy:
        report_findings.append(
            (
                "MIG-001",
                f"{missing_legacy} six-stage gate records are not recorded for locked legacy scopes.",
                "information",
                "Keep them missing; do not create retroactive gate history.",
            )
        )
    current_missing = sum(
        1
        for row in gate_rows
        if row[3] == "no"
        and not any(row[0] == scope.label for scope in legacy)
    )
    if current_missing:
        noun = "record is" if current_missing == 1 else "records are"
        report_findings.append(
            (
                "MIG-002",
                f"{current_missing} prospective gate {noun} not currently recorded.",
                "gap",
                "Create each gate only when its real prospective stage reaches human acceptance.",
            )
        )
    unknown_parts = []
    if unknown_discovery:
        unknown_parts.append("Discovery: " + ", ".join(unknown_discovery))
    if unknown_verification:
        unknown_parts.append("verification: " + ", ".join(unknown_verification))
    if unknown_usage:
        unknown_parts.append("usage: " + ", ".join(unknown_usage))
    if unknown_parts:
        report_findings.append(
            (
                "MIG-003",
                "Historical evidence remains unknown (" + "; ".join(unknown_parts) + ").",
                "information",
                "Retain `unknown`; never infer, reconstruct, or substitute zero/success.",
            )
        )
    if not report_findings:
        report_findings.append(
            ("none", "No migration gaps detected.", "information", "None.")
        )

    revision = backlog_body.get("revision", "unknown")
    project = backlog_body.get("project")
    target = project if isinstance(project, str) and project else root.name
    lines = [
        "# Migration Assessment",
        "",
        *_table(
            ("Field", "Value"),
            (
                ("Status", "GENERATED"),
                ("Generator", "`bin/method migrate assess`"),
                ("Target repository", f"`{target}`"),
                (
                    "Assessed at",
                    f"deterministic backlog revision {revision} (no wall-clock timestamp)",
                ),
                ("Method version at assessment", f"`method/{__version__}`"),
            ),
        ),
        "",
        "This assessment is prospective. It reports only repository evidence",
        "available now; absent historical Discovery, verification, and usage remain",
        "`unknown` and are never reconstructed.",
        "",
        "## 1. Stage coverage",
        "",
        *_table(
            (
                "Scope",
                "Vision sketch",
                "Discovery",
                "PRD",
                "Architecture",
                "Planning",
                "Autopilot",
            ),
            coverage_rows or (("none", *(["unknown"] * 6)),),
        ),
        "",
        "Coverage values are `present`, `absent`, `not-applicable`, or `unknown`.",
        "`present` means a current repository record supports the claim. Missing",
        "historical material is `unknown`, not evidence that a stage failed.",
        "",
        "## 2. Missing gate records",
        "",
        *_table(
            ("Scope", "Stage", "Expected gate", "Present", "Note"),
            gate_rows
            or (("none", "unknown", "unknown", "unknown", "No scopes recorded."),),
        ),
        "",
        "A missing gate for a locked legacy scope is expected and is not a",
        "defect. The command records the gap and does not remediate it retroactively.",
        "",
        "## 3. Control maturity snapshot",
        "",
        "Derived verbatim from `docs/plan/activation-ledger.yaml`; the assessment",
        "does not promote controls.",
        "",
        *_table(
            ("Control", "State", "Effective point", "Limitations"),
            maturity_rows,
        ),
        "",
        "## 4. Historical evidence confidence",
        "",
        *_table(
            ("Scope", "Discovery evidence", "Verification evidence", "Usage evidence"),
            evidence_rows or (("none", "unknown", "unknown", "unknown"),),
        ),
        "",
        "Only structured evidence currently recorded for a scope is `present`.",
        "Missing evidence is `unknown`; usage is never represented by a synthetic zero",
        "and delivery status is never substituted for verification evidence.",
        "",
        "## 5. Locked artefacts",
        "",
        *_table(
            ("Artefact class", "Locked", "Migration required"),
            locked_rows,
        ),
        "",
        "Locked artefacts stay valid under their historical schema (QR-004, PR-115).",
        "Absent `schema-version` on a locked or archived theme means version 1.",
        "",
        "## 6. Prospective adoption point",
        "",
        *_table(
            ("Field", "Value"),
            (
                ("Adoption point", adoption),
                ("First scope required to run VP3 Discovery", adoption),
                ("Scopes adopting prospectively only", prospective),
                (
                    "Legacy scopes retained without migration",
                    ", ".join(scope.label for scope in legacy) or "none",
                ),
                ("Retroactive evidence generated", "none, by contract"),
            ),
        ),
        "",
        "## 7. Findings and remediation",
        "",
        *_table(
            ("ID", "Finding", "Severity", "Remediation"),
            report_findings,
        ),
        "",
        "## Regeneration",
        "",
        "```bash",
        "bin/method migrate assess",
        "```",
        "",
        "For unchanged inputs, regeneration is byte-identical and does not rewrite",
        "an already identical output. The command writes no other repository file.",
        "",
    ]
    return "\n".join(lines)


def _write_if_changed(path: Path, content: str) -> bool:
    encoded = content.encode("utf-8")
    if path.exists():
        try:
            if path.read_bytes() == encoded:
                return False
        except OSError as error:
            _raise(
                path,
                f"existing output cannot be read safely: {error}.",
                "Restore a readable regular output file.",
            )
    descriptor = -1
    temporary: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
        )
        temporary = Path(temporary_name)
        stream = os.fdopen(descriptor, "wb")
        descriptor = -1
        with stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except OSError as error:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass
        try:
            if temporary is not None:
                temporary.unlink()
        except OSError:
            pass
        _raise(
            path,
            f"assessment output could not be written atomically: {error}.",
            "Restore write access and atomic replacement support, then retry.",
        )
    return True


def assess_repository(
    repository_root: Path,
    *,
    output: str = DEFAULT_OUTPUT,
) -> AssessmentResult:
    """Generate one deterministic migration assessment inside *repository_root*."""

    try:
        root = repository_root.resolve(strict=True)
    except OSError:
        _raise(
            repository_root,
            "repository root is missing or unreadable.",
            "Run the command from a readable repository root.",
        )
    relative, path = _output_path(root, output)
    backlog_body, scopes = _load_scopes(root)
    _reject_locked_output(root, relative, scopes)
    content = _render(root=root, backlog_body=backlog_body, scopes=scopes)
    changed = _write_if_changed(path, content)
    return AssessmentResult(
        output=relative.as_posix(),
        changed=changed,
    )
