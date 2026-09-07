"""Validate active lifecycle documentation without executing repository content.

The scanner has a deliberately closed scope.  It reads the two workspace
entry documents, active skill entry files, active top-level agent files, and
Python/Markdown test sources.  Historical and generated-template directories
are therefore outside the traversal rather than being filtered after a broad
repository walk.
"""

from __future__ import annotations

import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping


Finding = dict[str, object]
PathValue = str | Path

CHECK = "docs"
MAX_TEXT_BYTES = 2 * 1024 * 1024
CANONICAL_SKILL = Path(
    ".github/skills/the-copilot-build-method/SKILL.md"
)
FIXTURE_MARKER = "<!-- method-validate-docs: fixture -->"

# This executable representation is an enforcement rule, not a second
# documentation owner.  Its values are pinned to the table owned by
# ``the-copilot-build-method`` by contract tests.
REQUIRED_STAGE_MAP: tuple[tuple[str, str], ...] = (
    ("Vision sketch", "kickstart"),
    ("Discovery", "discover"),
    ("PRD finalization", "requirements"),
    ("Architecture", "plan stage 1"),
    ("Planning", "plan stage 2"),
    ("Autopilot", "autopilot"),
)
REQUIRED_STAGE_MAP_PAYLOAD = tuple(
    {"stage": stage, "entrypoint": entrypoint}
    for stage, entrypoint in REQUIRED_STAGE_MAP
)
REQUIRED_STAGE_MAP_TEXT = " -> ".join(
    f"{stage} ({entrypoint})" for stage, entrypoint in REQUIRED_STAGE_MAP
)

# These are stated in the result so callers can verify that retained history
# is intentionally out of scope.  The traversal below never enters them.
EXCLUDED_SCOPES = (
    "docs/themes/TH1-methodology-improvements/**",
    "docs/plan/backlog-archive/TH1.yaml",
    "docs/themes/TH2-gitflow-operator/**",
    "docs/plan/backlog-archive/TH2.yaml",
    "docs/architecture/history/**",
    ".github/agents/archive/**",
    ".github/ISSUE_TEMPLATE/archive/**",
)

ACTIVE_ROOTS: tuple[tuple[Path, str], ...] = (
    (Path(".github/skills"), "*/SKILL.md"),
    (Path(".github/agents"), "*.md"),
    (Path("tests"), "**/*"),
)

FOUR_STAGE = re.compile(
    r"\b(?:four|4)(?:[- ]stage(?:s)?|[- ]phase(?:s)?| stages| phases)\b",
    flags=re.IGNORECASE,
)
LEGACY_INLINE_MAP = re.compile(
    r"\bvision(?:\s+sketch)?\b"
    r"(?:(?!\b(?:discovery|prd|requirements)\b).){0,180}"
    r"\barchitecture\b"
    r"(?:(?!\b(?:discovery|prd|requirements)\b).){0,180}"
    r"\bplanning\b"
    r"(?:(?!\b(?:discovery|prd|requirements)\b).){0,180}"
    r"\bautopilot\b",
    flags=re.IGNORECASE | re.DOTALL,
)
STAGE_ITEM = re.compile(
    r"^\s*(?:[-*+]\s+|\d+[.)]\s+|\|\s*)"
    r"(?:phase\s*[1-6]\s*[:.)-]?\s*)?"
    r"(?P<stage>vision(?:\s+sketch)?|discovery|"
    r"prd(?:\s+finalization)?|requirements|architecture|planning|autopilot)"
    r"\b",
    flags=re.IGNORECASE,
)
HANDOFF_PATTERNS = (
    re.compile(
        r"\bkickstart\b"
        r"(?:(?!\b(?:discover(?:y)?|requirements?|prd)\b).){0,120}"
        r"(?:hand\s*[- ]?off|handoff|hands?\s+off|"
        r"routes?|passes?|continues?|proceeds?|transitions?|leads?|moves?|"
        r"flows?|is\s+(?:immediately\s+|directly\s+)?followed|then|->|→)"
        r"(?:(?!\b(?:discover(?:y)?|requirements?|prd)\b).){0,100}\bplan\b",
        flags=re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"(?:hand\s*[- ]?off|handoff).{0,80}\bfrom\s+kickstart\b"
        r".{0,80}\bto\s+plan\b",
        flags=re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\bafter\s+kickstart\b.{0,100}"
        r"(?:run|use|invoke|start|continue|proceed).{0,50}\bplan\b",
        flags=re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\b(?:immediately\s+|directly\s+)?after\s+(?:the\s+)?kickstart\b"
        r"(?:(?!\b(?:discover(?:y)?|requirements?|prd)\b).){0,80}"
        r"\bplan(?:\s+stage(?:\s+[12])?)?\b"
        r".{0,40}\b(?:begins?|starts?|runs?|proceeds?)\b",
        flags=re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\bplan(?:\s+stage(?:\s+[12])?)?\b"
        r"(?:(?!\b(?:discover(?:y)?|requirements?|prd)\b).){0,80}"
        r"\b(?:begins?|starts?|runs?|follows?|comes?|proceeds?)\b"
        r"(?:(?!\b(?:discover(?:y)?|requirements?|prd)\b).){0,50}"
        r"\b(?:after|following)\s+(?:the\s+)?kickstart\b",
        flags=re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\bplan(?:\s+stage(?:\s+[12])?)?\b"
        r"(?:(?!\b(?:discover(?:y)?|requirements?|prd)\b).){0,50}"
        r"\b(?:directly\s+|immediately\s+)?follows?\s+"
        r"(?:the\s+)?kickstart\b",
        flags=re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\bplan(?:\s+stage(?:\s+[12])?)?\b"
        r"(?:(?!\b(?:discover(?:y)?|requirements?|prd)\b).){0,60}"
        r"\b(?:is|becomes?)\b"
        r"(?:(?!\b(?:discover(?:y)?|requirements?|prd)\b).){0,40}"
        r"\b(?:next|immediate)\b"
        r"(?:(?!\b(?:discover(?:y)?|requirements?|prd)\b).){0,30}"
        r"\b(?:after|following)\s+(?:the\s+)?kickstart\b",
        flags=re.IGNORECASE | re.DOTALL,
    ),
)
NEGATED_HANDOFF = re.compile(
    r"\b(?:never|not|must\s+not|do\s+not|does\s+not|"
    r"instead\s+of|rather\s+than|without)\b",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class ValidationResult:
    findings: tuple[Finding, ...]
    checked_files: tuple[str, ...]
    fixture_exclusions: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not self.findings

    @property
    def payload(self) -> Mapping[str, object]:
        return {
            "command": "validate",
            "check": CHECK,
            "status": "ok" if self.valid else "failed",
            "checked_files": list(self.checked_files),
            "excluded_scopes": list(EXCLUDED_SCOPES),
            "fixture_exclusions": list(self.fixture_exclusions),
            "findings": list(self.findings),
        }


def _finding(
    file: str,
    line: int,
    record: str,
    message: str,
    remediation: str,
) -> Finding:
    return {
        "check": CHECK,
        "severity": "error",
        "file": file,
        "line": line,
        "record": record,
        "message": message,
        "required_stage_map": [
            dict(item) for item in REQUIRED_STAGE_MAP_PAYLOAD
        ],
        "remediation": remediation,
    }


def _regular_files(
    directory: Path,
    *,
    glob: str,
) -> Iterable[Path]:
    if not directory.is_dir() or directory.is_symlink():
        return ()
    return (
        path
        for path in directory.glob(glob)
        if (path.is_file() or path.is_symlink())
        and "__pycache__" not in path.parts
    )


def _contains_symlink(root: Path, path: Path) -> bool:
    current = root
    for part in path.relative_to(root).parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _active_root_problem(root: Path, relative: Path) -> str | None:
    """Return why a required scan root cannot be traversed safely."""

    path = root / relative
    if _contains_symlink(root, path):
        return "is a symbolic link, or contains a symbolic-link component"
    try:
        status = path.stat(follow_symlinks=False)
    except OSError as error:
        return f"cannot be inspected: {error}"
    if not stat.S_ISDIR(status.st_mode):
        return "is not a directory"

    permissions = stat.S_IMODE(status.st_mode)
    if not permissions & 0o444 or not permissions & 0o111:
        return "is not readable and traversable"
    try:
        with os.scandir(path) as entries:
            next(entries, None)
    except OSError as error:
        return f"cannot be read: {error}"
    return None


def active_files(repository_root: PathValue) -> tuple[Path, ...]:
    """Return the deterministic, closed active-document scan inventory."""

    root = Path(repository_root)
    candidates: list[Path] = [
        root / "README.md",
        root / ".github/copilot-instructions.md",
    ]
    for relative, glob in ACTIVE_ROOTS:
        if _active_root_problem(root, relative) is None:
            candidates.extend(_regular_files(root / relative, glob=glob))
    return tuple(
        sorted(
            set(candidates),
            key=lambda path: path.relative_to(root).as_posix(),
        )
    )


def _visible_text(text: str) -> str:
    """Replace HTML comments while preserving line offsets."""

    def hide(match: re.Match[str]) -> str:
        return re.sub(r"[^\n]", " ", match.group(0))

    return re.sub(r"<!--.*?-->", hide, text, flags=re.DOTALL)


def _paragraphs(text: str) -> Iterable[tuple[int, str]]:
    lines = text.splitlines()
    start: int | None = None
    body: list[str] = []
    for number, line in enumerate(lines, start=1):
        if line.strip():
            if start is None:
                start = number
            body.append(line)
            continue
        if start is not None:
            yield start, "\n".join(body)
            start = None
            body = []
    if start is not None:
        yield start, "\n".join(body)


def _physical_line(start: int, text: str, offset: int) -> int:
    return start + text.count("\n", 0, offset)


def _clauses(text: str) -> Iterable[tuple[int, str]]:
    """Yield sentence-like clauses with their exact paragraph offsets."""

    for match in re.finditer(
        r".*?(?:[.;!?](?=\s|$)|$)",
        text,
        flags=re.DOTALL,
    ):
        if match.group(0).strip():
            yield match.start(), match.group(0)


def _legacy_stage_list_lines(text: str) -> tuple[int, ...]:
    stage_items: list[tuple[str, int]] = []
    names = {
        "vision": "vision",
        "vision sketch": "vision",
        "architecture": "architecture",
        "planning": "planning",
        "autopilot": "autopilot",
        "discovery": "discovery",
        "prd": "prd",
        "prd finalization": "prd",
        "requirements": "prd",
    }
    for number, line in enumerate(text.splitlines(), start=1):
        match = STAGE_ITEM.match(line.replace("`", ""))
        if match is not None:
            stage_items.append(
                (
                    names[" ".join(match.group("stage").lower().split())],
                    number,
                )
            )

    legacy = ("vision", "architecture", "planning", "autopilot")
    return tuple(
        stage_items[index][1]
        for index in range(len(stage_items) - len(legacy) + 1)
        if tuple(
            stage for stage, _line in stage_items[index : index + len(legacy)]
        )
        == legacy
    )


def _stale_stage_lines(text: str) -> tuple[int, ...]:
    lines: set[int] = set(_legacy_stage_list_lines(text))
    for start, paragraph in _paragraphs(text):
        searchable = paragraph.replace("`", " ")
        for pattern in (FOUR_STAGE, LEGACY_INLINE_MAP):
            for match in pattern.finditer(searchable):
                lines.add(_physical_line(start, searchable, match.start()))
    return tuple(sorted(lines))


def _stale_handoff_lines(text: str) -> tuple[int, ...]:
    lines: set[int] = set()
    for start, paragraph in _paragraphs(text):
        searchable = paragraph.replace("`", " ")
        # Clauses keep a nearby negative statement from accidentally licensing
        # a different positive handoff in the same paragraph.
        for clause_offset, clause in _clauses(searchable):
            if NEGATED_HANDOFF.search(clause):
                continue
            for pattern in HANDOFF_PATTERNS:
                for match in pattern.finditer(clause):
                    lines.add(
                        _physical_line(
                            start,
                            searchable,
                            clause_offset + match.start(),
                        )
                    )
    return tuple(sorted(lines))


def _scan_text(relative: str, text: str) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    for line in _stale_stage_lines(text):
        findings.append(
            _finding(
                relative,
                line,
                "stale-stage-list",
                "Active content describes the obsolete four-stage lifecycle.",
                "Replace the statement with, or defer to, the canonical "
                f"six-stage map: {REQUIRED_STAGE_MAP_TEXT}.",
            )
        )
    for line in _stale_handoff_lines(text):
        findings.append(
            _finding(
                relative,
                line,
                "stale-entrypoint-handoff",
                "Active content hands off from kickstart directly to plan.",
                "Hand off from kickstart to discover; require a human-accepted "
                "Discovery readiness verdict and an approved PRD before plan "
                f"stage 1. Required map: {REQUIRED_STAGE_MAP_TEXT}.",
            )
        )
    return tuple(findings)


def _read_text(path: Path) -> str:
    size = path.stat().st_size
    if size > MAX_TEXT_BYTES:
        raise ValueError(
            f"file exceeds the {MAX_TEXT_BYTES}-byte documentation limit"
        )
    return path.read_text(encoding="utf-8")


def validate_repository(repository_root: PathValue) -> ValidationResult:
    """Validate the closed active scope and report every file actually read."""

    root = Path(repository_root)
    findings: list[Finding] = []
    checked: list[str] = []
    fixture_exclusions: list[str] = []

    for relative, _glob in ACTIVE_ROOTS:
        problem = _active_root_problem(root, relative)
        if problem is not None:
            findings.append(
                _finding(
                    relative.as_posix(),
                    1,
                    "unreadable-active-root",
                    f"Required active root {problem}.",
                    "Restore this path as a readable, traversable, real "
                    "directory inside the repository and re-run validate "
                    "docs.",
                )
            )

    for path in active_files(root):
        try:
            relative = path.relative_to(root).as_posix()
        except ValueError:
            continue
        if _contains_symlink(root, path):
            checked.append(relative)
            findings.append(
                _finding(
                    relative,
                    1,
                    "unreadable-active-document",
                    "Active content is a symbolic link and is not read.",
                    "Replace the symbolic link with a bounded UTF-8 regular "
                    "file inside the repository.",
                )
            )
            continue
        if not path.exists():
            findings.append(
                _finding(
                    relative,
                    1,
                    "unreadable-active-document",
                    "Required active content is missing.",
                    "Restore the active document and re-run validate docs.",
                )
            )
            continue
        try:
            text = _read_text(path)
        except (OSError, UnicodeError, ValueError) as error:
            checked.append(relative)
            findings.append(
                _finding(
                    relative,
                    1,
                    "unreadable-active-document",
                    f"Active content cannot be checked safely: {error}.",
                    "Restore a bounded UTF-8 regular file and re-run validate "
                    "docs.",
                )
            )
            continue

        checked.append(relative)
        first_content = next(
            (line.strip() for line in text.splitlines() if line.strip()),
            "",
        )
        if (
            relative.startswith("tests/fixtures/")
            and first_content == FIXTURE_MARKER
        ):
            fixture_exclusions.append(relative)
            continue
        findings.extend(_scan_text(relative, _visible_text(text)))

    return ValidationResult(
        tuple(
            sorted(
                findings,
                key=lambda item: (
                    str(item["file"]),
                    int(item["line"]),
                    str(item["record"]),
                ),
            )
        ),
        tuple(checked),
        tuple(fixture_exclusions),
    )
