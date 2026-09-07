"""Parse markdown lifecycle records without interpreting repository content.

This module is deliberately a structural parser, not a schema validator.
Current-schema and accepted legacy records are both indexed; later validators
can apply the schema appropriate to each record's VP and schema version.

Repository files are untrusted input.  Parsing consists only of bounded text
and path operations: content is never evaluated, imported, or executed.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping, Sequence


Finding = dict[str, object]
PathValue = str | os.PathLike[str]

CHECK = "records"
RECORD_PREFIXES = frozenset(
    {
        "VO",
        "DQ",
        "EXP",
        "EV",
        "ASM",
        "DEC",
        "INV",
        "RSK",
        "DEF",
        "DR",
        "PR",
        "QR",
        "PCR",
        "ADR",
    }
)

_ID_PATTERN = re.compile(
    r"(?:"
    r"(?P<prefix>VO|DQ|EXP|EV|ASM|DEC|INV|RSK|DEF|DR|PR|QR|PCR|ADR)-"
    r"(?P<number>00[1-9]|0[1-9][0-9]|[1-9][0-9]{2})"
    r"|TH[1-9][0-9]*\.E[1-9][0-9]*\.US[1-9][0-9]*"
    r"|TH[1-9][0-9]*"
    r")"
)
_RECORD_ID_PATTERN = re.compile(
    r"(?P<prefix>VO|DQ|EXP|EV|ASM|DEC|INV|RSK|DEF|DR|PR|QR|PCR|ADR)-"
    r"(?P<number>00[1-9]|0[1-9][0-9]|[1-9][0-9]{2})"
)
_FILE_RECORD_NAME_PATTERN = re.compile(
    r"(?P<id>(?:EXP|DR|PCR)-(?:00[1-9]|0[1-9][0-9]|[1-9][0-9]{2}))"
    r"(?:-[a-z0-9]+(?:-[a-z0-9]+)*)?\.md"
)
_FILE_RECORD_TITLE_PATTERN = re.compile(
    r"# (?P<id>(?:EXP|DR|PCR)-(?:00[1-9]|0[1-9][0-9]|[1-9][0-9]{2}))"
    r": (?P<title>\S(?:.*\S)?)"
)
_HEADER_NAME_PATTERN = re.compile(
    r"[A-Za-z](?:[A-Za-z0-9 /-]*[A-Za-z0-9])?"
)
_SEPARATOR_PATTERN = re.compile(r":?-{3,}:?")
_FENCE_OPEN_PATTERN = re.compile(r" {0,3}(?P<fence>`{3,}|~{3,}).*")


@dataclass(frozen=True)
class Record:
    """One parsed lifecycle record and its source provenance."""

    file: str
    line: int
    prefix: str
    id: str
    columns: Mapping[str, str]
    references: tuple[str, ...] = ()
    reference_columns: Mapping[str, tuple[str, ...]] = field(
        default_factory=dict
    )
    form: str = "table"

    @property
    def source_file(self) -> str:
        """Compatibility spelling for consumers emphasizing provenance."""

        return self.file

    @property
    def record_id(self) -> str:
        """Unambiguous alias for callers that avoid the built-in name."""

        return self.id


@dataclass(frozen=True)
class RecordReference:
    """A normalized reference edge originating in a record cell."""

    source_id: str
    target_id: str
    column: str
    file: str
    line: int


@dataclass(frozen=True)
class ParseResult:
    """Records and structural findings produced from one or more files."""

    records: tuple[Record, ...] = ()
    findings: tuple[Finding, ...] = ()


@dataclass(frozen=True)
class RecordIndex:
    """VP-scoped records, allocation lookup, and incoming references."""

    records: tuple[Record, ...]
    findings: tuple[Finding, ...]
    by_id: Mapping[str, tuple[Record, ...]]
    references: Mapping[str, tuple[RecordReference, ...]]

    def resolve(self, record_id: str) -> Record | None:
        """Return the unique record for *record_id*, otherwise ``None``."""

        matches = self.by_id.get(record_id, ())
        return matches[0] if len(matches) == 1 else None


def _finding(
    *,
    file: str,
    line: int,
    record: str | None,
    message: str,
    remediation: str,
) -> Finding:
    """Create the stable validation-finding shape required by ADR-003."""

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
        "message": f"line {line}: {message}",
        "remediation": remediation,
    }


def split_references(value: str) -> tuple[str, ...]:
    """Split a cell that consists solely of comma-separated stable IDs.

    Free-form prose which happens to mention an ID is not converted into an
    edge.  That keeps this parser structural and prevents prose from silently
    becoming authoritative traceability.
    """

    parts = tuple(part.strip() for part in value.split(","))
    if not parts or any(not part for part in parts):
        return ()
    if all(_ID_PATTERN.fullmatch(part) for part in parts):
        return parts
    return ()


def _record_references(
    columns: Mapping[str, str],
) -> tuple[tuple[str, ...], dict[str, tuple[str, ...]]]:
    by_column: dict[str, tuple[str, ...]] = {}
    ordered: list[str] = []
    seen: set[str] = set()
    for name, value in columns.items():
        if name == "ID":
            continue
        references = split_references(value)
        if not references:
            continue
        by_column[name] = references
        for reference in references:
            if reference not in seen:
                seen.add(reference)
                ordered.append(reference)
    return tuple(ordered), by_column


def _split_pipe_row(line: str) -> list[str] | None:
    """Split a strict outer-pipe row while respecting escaped pipe literals."""

    stripped = line.strip()
    if len(stripped) < 2 or not stripped.startswith("|") or not stripped.endswith("|"):
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
        if character == "\\":
            escaped = not escaped
        else:
            escaped = False
    cells.append("".join(current).strip())
    return cells


def _is_separator(cells: Sequence[str] | None, width: int) -> bool:
    return (
        cells is not None
        and len(cells) == width
        and all(_SEPARATOR_PATTERN.fullmatch(cell) for cell in cells)
    )


def _looks_like_separator(cells: Sequence[str] | None) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-+:?", cell) for cell in cells)


def _fenced_lines(lines: Sequence[str]) -> set[int]:
    """Return zero-based line indexes inside or forming markdown fences."""

    fenced: set[int] = set()
    delimiter: str | None = None
    for index, line in enumerate(lines):
        if delimiter is None:
            opening = _FENCE_OPEN_PATTERN.fullmatch(line)
            if opening is not None:
                delimiter = opening.group("fence")
                fenced.add(index)
            continue

        fenced.add(index)
        if re.fullmatch(rf" {{0,3}}{re.escape(delimiter)}[ \t]*", line):
            delimiter = None
    return fenced


def _parse_id_tables(
    lines: Sequence[str],
    *,
    file: str,
    fenced: set[int],
) -> ParseResult:
    records: list[Record] = []
    findings: list[Finding] = []
    index = 0

    while index < len(lines):
        if index in fenced:
            index += 1
            continue
        header = _split_pipe_row(lines[index])
        if not header or not any(name.casefold() == "id" for name in header):
            index += 1
            continue

        width = len(header)
        header_names_valid = (
            all(_HEADER_NAME_PATTERN.fullmatch(name) for name in header)
            and len(set(header)) == width
            and header.count("ID") == 1
        )
        id_is_first = header[0] == "ID"
        if not header_names_valid:
            findings.append(
                _finding(
                    file=file,
                    line=index + 1,
                    record=None,
                    message=(
                        "ID-prefixed table header names must be non-empty, "
                        "well-formed, and unique, with exactly one canonical ID"
                    ),
                    remediation=(
                        "Use plain ASCII column names and include the exact "
                        "header name 'ID' once."
                    ),
                )
            )
        if not id_is_first:
            findings.append(
                _finding(
                    file=file,
                    line=index + 1,
                    record=None,
                    message=(
                        "ID-prefixed table header must place the canonical "
                        "ID column first"
                    ),
                    remediation=(
                        "Move the exact 'ID' header to the first table column."
                    ),
                )
            )
        header_is_valid = header_names_valid and id_is_first
        separator_index = index + 1
        separator = (
            _split_pipe_row(lines[separator_index])
            if separator_index < len(lines) and separator_index not in fenced
            else None
        )
        has_separator = _is_separator(separator, width)
        if not has_separator:
            findings.append(
                _finding(
                    file=file,
                    line=separator_index + 1,
                    record=None,
                    message=(
                        "ID-prefixed table requires a markdown separator "
                        f"with {width} cells"
                    ),
                    remediation=(
                        "Add one separator cell of at least three hyphens "
                        "for every header column."
                    ),
                )
            )

        row_index = index + (
            2 if has_separator or _looks_like_separator(separator) else 1
        )
        while row_index < len(lines) and row_index not in fenced:
            source = lines[row_index]
            cells = _split_pipe_row(source)
            if cells is None:
                # A malformed pipe-looking row belongs to this table and gets
                # a finding; ordinary prose or a blank ends the table.
                if "|" in source and source.strip():
                    findings.append(
                        _finding(
                            file=file,
                            line=row_index + 1,
                            record=None,
                            message=(
                                "table row must start and end with an ASCII pipe"
                            ),
                            remediation=(
                                "Wrap the row in outer pipes and keep one cell "
                                "for every header column."
                            ),
                        )
                    )
                    row_index += 1
                    continue
                break

            if _is_separator(cells, width):
                findings.append(
                    _finding(
                        file=file,
                        line=row_index + 1,
                        record=None,
                        message="unexpected separator inside record rows",
                        remediation="Keep exactly one separator after the header.",
                    )
                )
                row_index += 1
                continue

            candidate_id = cells[0] if cells else ""
            if len(cells) != width:
                record_id = (
                    candidate_id
                    if _RECORD_ID_PATTERN.fullmatch(candidate_id)
                    else None
                )
                findings.append(
                    _finding(
                        file=file,
                        line=row_index + 1,
                        record=record_id,
                        message=(
                            f"table row has {len(cells)} cells; expected {width}"
                        ),
                        remediation=(
                            "Add or remove cells so the row matches the "
                            f"{width}-column header."
                        ),
                    )
                )
                row_index += 1
                continue

            identifier = _RECORD_ID_PATTERN.fullmatch(candidate_id)
            if identifier is None:
                findings.append(
                    _finding(
                        file=file,
                        line=row_index + 1,
                        record=None,
                        message=(
                            "first cell is not a canonical "
                            "<PREFIX>-<three digits> record ID"
                        ),
                        remediation=(
                            "Use a supported uppercase record prefix and "
                            "exactly three decimal digits."
                        ),
                    )
                )
                row_index += 1
                continue

            if header_is_valid:
                columns = dict(zip(header, cells, strict=True))
                references, reference_columns = _record_references(columns)
                records.append(
                    Record(
                        file=file,
                        line=row_index + 1,
                        prefix=identifier.group("prefix"),
                        id=candidate_id,
                        columns=columns,
                        references=references,
                        reference_columns=reference_columns,
                    )
                )
            row_index += 1

        index = max(row_index, index + 1)

    return ParseResult(tuple(records), tuple(findings))


def _file_record_identity(path: Path) -> tuple[str, str] | None:
    match = _FILE_RECORD_NAME_PATTERN.fullmatch(path.name)
    if match is None:
        return None
    identifier = match.group("id")
    return identifier, identifier.split("-", 1)[0]


def _parse_file_record(
    lines: Sequence[str],
    *,
    path: Path,
    file: str,
    fenced: set[int],
) -> ParseResult:
    identity = _file_record_identity(path)
    if identity is None:
        return ParseResult()

    filename_id, prefix = identity
    findings: list[Finding] = []
    first_content = next(
        (
            index
            for index, line in enumerate(lines)
            if line.strip() and index not in fenced
        ),
        None,
    )
    title_match = (
        _FILE_RECORD_TITLE_PATTERN.fullmatch(lines[first_content])
        if first_content is not None
        else None
    )
    if title_match is None:
        line = 1 if first_content is None else first_content + 1
        return ParseResult(
            findings=(
                _finding(
                    file=file,
                    line=line,
                    record=filename_id,
                    message=(
                        f"file-per-record artefact requires title "
                        f"'# {filename_id}: <title>' as its first content"
                    ),
                    remediation=(
                        "Add the stable ID and a non-empty title as the "
                        "level-one document title."
                    ),
                ),
            )
        )

    title_id = title_match.group("id")
    if title_id != filename_id:
        return ParseResult(
            findings=(
                _finding(
                    file=file,
                    line=first_content + 1,
                    record=title_id,
                    message=(
                        f"title ID {title_id} does not match filename ID "
                        f"{filename_id}"
                    ),
                    remediation=(
                        "Rename the file or correct its title so the IDs match."
                    ),
                ),
            )
        )

    table_header_index = first_content + 1
    while (
        table_header_index < len(lines)
        and not lines[table_header_index].strip()
    ):
        table_header_index += 1

    header = (
        _split_pipe_row(lines[table_header_index])
        if table_header_index < len(lines)
        and table_header_index not in fenced
        else None
    )
    if header != ["Field", "Value"]:
        findings.append(
            _finding(
                file=file,
                line=table_header_index + 1,
                record=title_id,
                message=(
                    "file-per-record title must be followed by a "
                    "'Field | Value' metadata table"
                ),
                remediation=(
                    "Place a two-column '| Field | Value |' table directly "
                    "after the title."
                ),
            )
        )
        return ParseResult(findings=tuple(findings))

    separator_index = table_header_index + 1
    separator = (
        _split_pipe_row(lines[separator_index])
        if separator_index < len(lines) and separator_index not in fenced
        else None
    )
    has_separator = _is_separator(separator, 2)
    if not has_separator:
        findings.append(
            _finding(
                file=file,
                line=separator_index + 1,
                record=title_id,
                message="metadata table requires a two-cell markdown separator",
                remediation=(
                    "Add '|---|---|' immediately below the metadata header."
                ),
            )
        )

    metadata: dict[str, str] = {}
    row_index = table_header_index + (
        2 if has_separator or _looks_like_separator(separator) else 1
    )
    while row_index < len(lines) and row_index not in fenced:
        cells = _split_pipe_row(lines[row_index])
        if cells is None:
            if "|" in lines[row_index] and lines[row_index].strip():
                findings.append(
                    _finding(
                        file=file,
                        line=row_index + 1,
                        record=title_id,
                        message=(
                            "metadata row must start and end with an ASCII pipe"
                        ),
                        remediation=(
                            "Use exactly two outer-pipe cells for each "
                            "metadata row."
                        ),
                    )
                )
                row_index += 1
                continue
            break
        if len(cells) != 2:
            findings.append(
                _finding(
                    file=file,
                    line=row_index + 1,
                    record=title_id,
                    message=f"metadata row has {len(cells)} cells; expected 2",
                    remediation=(
                        "Use exactly one field-name cell and one value cell."
                    ),
                )
            )
            row_index += 1
            continue

        name, value = cells
        if name in metadata:
            findings.append(
                _finding(
                    file=file,
                    line=row_index + 1,
                    record=title_id,
                    message=f"metadata field {name!r} is duplicated",
                    remediation="Keep each metadata field exactly once.",
                )
            )
        else:
            metadata[name] = value
        row_index += 1

    references, reference_columns = _record_references(metadata)
    record = Record(
        file=file,
        line=first_content + 1,
        prefix=prefix,
        id=title_id,
        columns=metadata,
        references=references,
        reference_columns=reference_columns,
        form="file",
    )
    return ParseResult((record,), tuple(findings))


def parse_markdown(
    text: str,
    *,
    file: str = "<memory>",
    path: PathValue | None = None,
) -> ParseResult:
    """Parse records from already-decoded markdown text.

    ``path`` supplies filename semantics for EXP/DR/PCR artefacts.  It does
    not cause any filesystem access.
    """

    lines = text.splitlines()
    fenced = _fenced_lines(lines)
    table_result = _parse_id_tables(lines, file=file, fenced=fenced)
    file_result = (
        _parse_file_record(
            lines,
            path=Path(path),
            file=file,
            fenced=fenced,
        )
        if path is not None
        else ParseResult()
    )
    return ParseResult(
        records=table_result.records + file_result.records,
        findings=table_result.findings + file_result.findings,
    )


def _display_path(path: Path, repository_root: Path) -> str:
    try:
        return path.relative_to(repository_root).as_posix()
    except ValueError:
        return path.as_posix()


def _within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def parse_file(
    path: PathValue,
    *,
    repository_root: PathValue | None = None,
) -> ParseResult:
    """Read and parse one UTF-8 markdown file, returning findings on failure."""

    try:
        source_input = Path(path)
    except (OSError, RuntimeError, ValueError):
        return ParseResult(
            findings=(
                _finding(
                    file="<unavailable>",
                    line=1,
                    record=None,
                    message="source file path is unavailable",
                    remediation="Use a valid filesystem path.",
                ),
            )
        )

    try:
        root_input = (
            Path(repository_root)
            if repository_root is not None
            else source_input.parent
        )
    except (OSError, RuntimeError, ValueError):
        return ParseResult(
            findings=(
                _finding(
                    file=source_input.as_posix(),
                    line=1,
                    record=None,
                    message="repository root is unavailable",
                    remediation="Use an existing, readable repository root.",
                ),
            )
        )
    try:
        root = root_input.resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        return ParseResult(
            findings=(
                _finding(
                    file=root_input.as_posix(),
                    line=1,
                    record=None,
                    message="repository root is unavailable",
                    remediation="Use an existing, readable repository root.",
                ),
            )
        )

    source = (
        root / source_input
        if repository_root is not None and not source_input.is_absolute()
        else source_input
    )
    label = _display_path(source, root)
    try:
        resolved = source.resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        return ParseResult(
            findings=(
                _finding(
                    file=label,
                    line=1,
                    record=None,
                    message="source file could not be resolved",
                    remediation="Restore the file and verify path permissions.",
                ),
            )
        )

    if source.is_symlink() or not _within(resolved, root):
        return ParseResult(
            findings=(
                _finding(
                    file=label,
                    line=1,
                    record=None,
                    message="source path is outside the trusted repository boundary",
                    remediation=(
                        "Use a regular markdown file contained within the "
                        "repository root; do not use symlink escapes."
                    ),
                ),
            )
        )

    try:
        text = resolved.read_text(encoding="utf-8", errors="strict")
    except UnicodeError:
        return ParseResult(
            findings=(
                _finding(
                    file=label,
                    line=1,
                    record=None,
                    message="source file is not valid UTF-8",
                    remediation="Encode the markdown source as valid UTF-8.",
                ),
            )
        )
    except (OSError, RuntimeError, ValueError):
        return ParseResult(
            findings=(
                _finding(
                    file=label,
                    line=1,
                    record=None,
                    message="source file could not be read",
                    remediation="Restore read access and retry.",
                ),
            )
        )

    return parse_markdown(text, file=label, path=source)


def _walk_markdown(root: Path) -> tuple[list[Path], list[tuple[Path, int]]]:
    """List markdown files deterministically without following symlinks."""

    paths: list[Path] = []
    failures: list[tuple[Path, int]] = []

    def on_error(error: OSError) -> None:
        failed = Path(error.filename) if error.filename else root
        failures.append((failed, 1))

    for directory, names, files in os.walk(
        root,
        topdown=True,
        onerror=on_error,
        followlinks=False,
    ):
        names.sort()
        files.sort()
        base = Path(directory)
        retained_names: list[str] = []
        for name in names:
            candidate = base / name
            if candidate.is_symlink():
                failures.append((candidate, 1))
            else:
                retained_names.append(name)
        names[:] = retained_names
        for name in files:
            candidate = base / name
            if candidate.suffix.lower() == ".md":
                paths.append(candidate)
    return paths, failures


def _record_content(record: Record) -> tuple[tuple[str, str], ...]:
    return tuple(
        (name, value)
        for name, value in record.columns.items()
        if name not in {"ID", "Schema version"}
    )


def build_index(
    records: Iterable[Record],
    findings: Iterable[Finding] = (),
) -> RecordIndex:
    """Build deterministic allocation and reference indexes for one VP."""

    ordered_records = tuple(
        sorted(records, key=lambda item: (item.file, item.line, item.id))
    )
    all_findings = list(findings)
    allocations: dict[str, list[Record]] = {}
    incoming: dict[str, list[RecordReference]] = {}
    fingerprints: dict[
        tuple[str, tuple[tuple[str, str], ...]], Record
    ] = {}

    for record in ordered_records:
        prior_allocations = allocations.setdefault(record.id, [])
        if prior_allocations:
            first = prior_allocations[0]
            same_content = _record_content(first) == _record_content(record)
            classification = "duplicated" if same_content else "reused"
            all_findings.append(
                _finding(
                    file=record.file,
                    line=record.line,
                    record=record.id,
                    message=(
                        f"ID {record.id} is {classification}; first allocated "
                        f"at {first.file}:{first.line}"
                    ),
                    remediation=(
                        "Retain the first allocation and assign the next "
                        "unused ID to a genuinely new record."
                    ),
                )
            )
        prior_allocations.append(record)

        content = _record_content(record)
        fingerprint = (record.prefix, content)
        prior_content = fingerprints.get(fingerprint)
        if content and prior_content is not None and prior_content.id != record.id:
            all_findings.append(
                _finding(
                    file=record.file,
                    line=record.line,
                    record=record.id,
                    message=(
                        f"record content is renumbered as {record.id}; "
                        f"it was first allocated as {prior_content.id} at "
                        f"{prior_content.file}:{prior_content.line}"
                    ),
                    remediation=(
                        "Keep the original stable ID; represent a changed fact "
                        "as an append-only DR or PCR where applicable."
                    ),
                )
            )
        elif content:
            fingerprints[fingerprint] = record

        for column, targets in record.reference_columns.items():
            for target in targets:
                incoming.setdefault(target, []).append(
                    RecordReference(
                        source_id=record.id,
                        target_id=target,
                        column=column,
                        file=record.file,
                        line=record.line,
                    )
                )

    return RecordIndex(
        records=ordered_records,
        findings=tuple(all_findings),
        by_id={key: tuple(value) for key, value in sorted(allocations.items())},
        references={
            key: tuple(value) for key, value in sorted(incoming.items())
        },
    )


def index_vp(
    vp_root: PathValue,
    *,
    repository_root: PathValue | None = None,
) -> RecordIndex:
    """Parse and index every markdown record below one VP scope."""

    try:
        scope_argument = Path(vp_root)
    except (OSError, RuntimeError, ValueError):
        finding = _finding(
            file="<unavailable>",
            line=1,
            record=None,
            message="VP scope path is unavailable",
            remediation="Use a valid filesystem path.",
        )
        return build_index((), (finding,))

    try:
        repository_input = (
            Path(repository_root)
            if repository_root is not None
            else scope_argument
        )
    except (OSError, RuntimeError, ValueError):
        finding = _finding(
            file=scope_argument.as_posix(),
            line=1,
            record=None,
            message="repository root is unavailable",
            remediation="Use an existing, readable repository root.",
        )
        return build_index((), (finding,))
    try:
        repository = repository_input.resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        finding = _finding(
            file=repository_input.as_posix(),
            line=1,
            record=None,
            message="repository root is unavailable",
            remediation="Use an existing, readable repository root.",
        )
        return build_index((), (finding,))

    scope_input = (
        repository / scope_argument
        if repository_root is not None and not scope_argument.is_absolute()
        else scope_argument
    )
    scope_label = _display_path(scope_input, repository)
    try:
        scope = scope_input.resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        finding = _finding(
            file=scope_label,
            line=1,
            record=None,
            message="VP scope could not be resolved",
            remediation="Use an existing VP directory inside the repository.",
        )
        return build_index((), (finding,))

    if scope_input.is_symlink() or not _within(scope, repository):
        finding = _finding(
            file=scope_label,
            line=1,
            record=None,
            message="VP scope is outside the trusted repository boundary",
            remediation=(
                "Use a regular VP directory contained within the repository "
                "root; do not use symlink escapes."
            ),
        )
        return build_index((), (finding,))
    if not scope.is_dir():
        finding = _finding(
            file=scope_label,
            line=1,
            record=None,
            message="VP scope is not a directory",
            remediation="Pass the directory that owns the VP artefacts.",
        )
        return build_index((), (finding,))

    try:
        paths, walk_failures = _walk_markdown(scope)
    except (OSError, RuntimeError, ValueError):
        finding = _finding(
            file=scope_label,
            line=1,
            record=None,
            message="source directory could not be read",
            remediation="Restore directory read access and retry.",
        )
        return build_index((), (finding,))
    records: list[Record] = []
    findings: list[Finding] = [
        _finding(
            file=_display_path(path, repository),
            line=line,
            record=None,
            message="source directory could not be read",
            remediation="Restore directory read access and retry.",
        )
        for path, line in sorted(walk_failures)
    ]
    for path in paths:
        result = parse_file(path, repository_root=repository)
        records.extend(result.records)
        findings.extend(result.findings)
    return build_index(records, findings)


# Explicit aliases make the public intent discoverable to later validators.
parse_markdown_file = parse_file
index_records = build_index


__all__ = [
    "CHECK",
    "Finding",
    "ParseResult",
    "Record",
    "RecordIndex",
    "RecordReference",
    "RECORD_PREFIXES",
    "build_index",
    "index_records",
    "index_vp",
    "parse_file",
    "parse_markdown",
    "parse_markdown_file",
    "split_references",
]
