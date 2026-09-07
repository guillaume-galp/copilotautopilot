"""Fail-closed validation of accepted theme, VP, and ADR artefacts.

The accepted release commits below are cryptographic roots of trust for the
legacy TH1 and TH2 material.  The validator reads those commits with Git
plumbing, never with branch, index, status, or working-tree operations.  This
keeps the baseline independent of the mutable files being checked and avoids
adding hashes to already locked artefacts.

Repository paths and markdown are untrusted data.  Paths are constrained to
the repository, symlinks are never followed, YAML uses the duplicate-key-safe
loader, and Git is invoked without a shell using a small fixed command set.
"""

from __future__ import annotations

import hashlib
import os
import re
import stat
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Mapping, Protocol, Sequence

import yaml

from methodlib import gates
from methodlib.backlog import UniqueKeyLoader


Finding = dict[str, object]
PathValue = str | os.PathLike[str]

BACKLOG_PATH = "docs/plan/backlog.yaml"
ARCHIVE_DIRECTORY = "docs/plan/backlog-archive"
ADR_INDEX_PATH = "docs/ADRs/README.md"
MAX_CONTROL_BYTES = 2 * 1024 * 1024
MAX_ARTEFACT_BYTES = 32 * 1024 * 1024
GIT_TIMEOUT_SECONDS = 3

THEME_ID = re.compile(r"TH[1-9][0-9]*")
VP_ID = re.compile(r"VP[1-9][0-9]*")
ADR_ID = re.compile(r"ADR-(?:00[1-9]|0[1-9][0-9]|[1-9][0-9]{2})")
REVISION = re.compile(r"[0-9a-f]{40}")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
SAFE_PATH_PART = re.compile(r"[A-Za-z0-9._-]+")
STATUS_VALUE = re.compile(
    rb"(?m)(?P<prefix>^## Status\r?\n\r?\n)"
    rb"(?P<value>[^\r\n]+)(?P<suffix>\r?\n)"
)
PLACEHOLDER = re.compile(r"<[^<>\n]+>")
DR_FIELDS = gates.DR_FIELDS
PCR_FIELDS = gates.PCR_FIELDS


@dataclass(frozen=True)
class ThemeBaseline:
    revision: str | None
    theme_path: str
    archive_path: str
    archive_revision: str | None = None
    archive_sha256: str | None = None
    theme_sha256: str | None = None


@dataclass(frozen=True)
class ArtefactBaseline:
    revision: str | None
    path: str
    sha256: str | None = None


@dataclass(frozen=True)
class VpBaseline:
    revision: str | None
    paths: tuple[str, ...]
    mapped_themes: tuple[str, ...] = ()
    entry_sha256: Mapping[str, str] | None = None
    entry_modes: Mapping[str, str] | None = None


@dataclass(frozen=True)
class Baselines:
    themes: Mapping[str, ThemeBaseline]
    adrs: Mapping[str, ArtefactBaseline]
    vps: Mapping[str, VpBaseline]


@dataclass(frozen=True)
class ProtectedArtefactScope:
    """A lexical scope to which generated content must not be written.

    ``recursive`` distinguishes immutable directories from individual files.
    The scope is derived from the same accepted-theme, dependent-ADR, and
    shared-VP rules used by :func:`validate_repository`; it does not depend on
    mutable file contents matching their baseline before protection applies.
    """

    path: str
    record: str
    kind: str
    recursive: bool


# v0.7.0 is the accepted TH1 release; v0.8.0 is the accepted TH2 release.
# These are the full peeled commit IDs (v0.7.0^{} and v0.8.0^{}), not the
# annotated tag-object IDs or mutable tag names.
LEGACY_BASELINES = Baselines(
    themes={
        "TH1": ThemeBaseline(
            revision="bf22a5aae6573fa9555397a6306dc593e2b28d63",
            theme_path="docs/themes/TH1-methodology-improvements",
            archive_path="docs/plan/backlog-archive/TH1.yaml",
        ),
        "TH2": ThemeBaseline(
            revision="be5fd65ebe098c09c9e9170e616e5820a1b7f07e",
            theme_path="docs/themes/TH2-gitflow-operator",
            archive_path="docs/plan/backlog-archive/TH2.yaml",
            # The compaction snapshot post-dates the release tag.  Its exact
            # bytes are pinned here rather than rewriting the locked archive.
            archive_sha256=(
                "cb4cbfac383ac402ec06b9a8423b5a354"
                "3250e17d823d7dac27a2eae6d8520bd"
            ),
        ),
        # TH3 is accepted from an intentionally uncommitted human checkpoint.
        # Its exact acceptance bytes are pinned with deterministic scope
        # digests, rather than pretending that HEAD contains a release commit.
        "TH3": ThemeBaseline(
            revision=None,
            theme_path="docs/themes/TH3-discovery-requirements-foundation",
            archive_path="docs/plan/backlog-archive/TH3.yaml",
            archive_sha256=(
                "0c79696c8afeb14d21dee96fa5db2818a3377ab84cf7180870538d238072274b"
            ),
            theme_sha256=(
                "b7eca506baf013497d39bc2a09c15151343dd072b7f1095376f4a56afcc980cb"
            ),
        ),
    },
    adrs={
        "ADR-001": ArtefactBaseline(
            revision="be5fd65ebe098c09c9e9170e616e5820a1b7f07e",
            path="docs/ADRs/ADR-001-gitflow-operator.md",
        ),
        "ADR-002": ArtefactBaseline(
            revision=None,
            path="docs/ADRs/ADR-002-six-stage-gated-lifecycle.md",
            sha256="3be2fdf62b98782f30de59da603d33cc667c648efb8a5de77b9ecaab84425637",
        ),
        "ADR-003": ArtefactBaseline(
            revision=None,
            path="docs/ADRs/ADR-003-markdown-records-and-local-validator.md",
            sha256="e64b8a04d83f2b55790266aefd0edd5ac527a4a006fbba42689d2c318d9dab96",
        ),
        "ADR-004": ArtefactBaseline(
            revision=None,
            path="docs/ADRs/ADR-004-backlog-schema-v2-and-transitions.md",
            sha256="c4f819a3ac9908b636205b2637cd15f86ffe1dd3ef6a600bcebd12cd6c893cb3",
        ),
        "ADR-005": ArtefactBaseline(
            revision=None,
            path="docs/ADRs/ADR-005-agent-packets-and-source-hashing.md",
            sha256="09375d6dd783f665ff319d2b50fe67d705234e9e8afb4ea9aace1155cc7eade3",
        ),
        "ADR-006": ArtefactBaseline(
            revision=None,
            path="docs/ADRs/ADR-006-risk-verification-and-model-routing.md",
            sha256="ed5c44564172122a8bd18b7b8c70d1e4fd6aace7eefeb84b5df28a1f1cec324b",
        ),
        "ADR-007": ArtefactBaseline(
            revision=None,
            path="docs/ADRs/ADR-007-usage-adapter-and-budget-enforcement.md",
            sha256="d41382955d558843c53f274ba7a25c6a383704f8f82d8fdd10dfe61d9d56e7a7",
        ),
        "ADR-008": ArtefactBaseline(
            revision=None,
            path="docs/ADRs/ADR-008-multi-theme-lock-and-activation-ledger.md",
            sha256="fe50a45d757218057b77006e31c2a4cb7afaf00b5885ea4c8158bd0f234a5543",
        ),
    },
    vps={
        "VP1": VpBaseline(
            revision="bf22a5aae6573fa9555397a6306dc593e2b28d63",
            paths=("docs/vision_of_product/VP1-mvp",),
            mapped_themes=("TH1",),
        ),
        "VP2": VpBaseline(
            revision="be5fd65ebe098c09c9e9170e616e5820a1b7f07e",
            paths=("docs/vision_of_product/VP2-gitflow-operator",),
            mapped_themes=("TH2",),
        ),
        "VP3": VpBaseline(
            revision=None,
            paths=(
                "docs/vision_of_product/VP3-discovery-led-cost-aware-methodology",
                "docs/discovery/VP3-discovery-led-cost-aware-methodology",
                "docs/requirements/VP3-discovery-led-cost-aware-methodology",
            ),
            mapped_themes=("TH3", "TH4", "TH5"),
            entry_sha256={
                "docs/vision_of_product/VP3-discovery-led-cost-aware-methodology/VP3.md": "42c9361e7337e04803166c50bae3c5ec21165dc375a58b3cecbdf66c2dfde7af",
                "docs/discovery/VP3-discovery-led-cost-aware-methodology/README.md": "ef7267033d2cb30453012731bc512550da1d7e6a81513ac8e44fc7bb8c21c441",
                "docs/discovery/VP3-discovery-led-cost-aware-methodology/architecture-handoff.md": "6768ee88466880e33f3746e07ebad73c8b5fcad3db4ebd30ae6acbfd759d6a90",
                "docs/discovery/VP3-discovery-led-cost-aware-methodology/assumptions.md": "6321415530ac58f08684175143410025121f7b6e37f44df7a41b6835fc95761d",
                "docs/discovery/VP3-discovery-led-cost-aware-methodology/decisions.md": "10d6679686196af31ab6f538f94ebca86520f86219d87095e994e54d49b92041",
                "docs/discovery/VP3-discovery-led-cost-aware-methodology/discovery-questions.md": "a1149c30829798f6f16de039e52b9af13fa390784a2efcb4d00895438bf402fb",
                "docs/discovery/VP3-discovery-led-cost-aware-methodology/domain-ontology.md": "2282236458b3590361fbcc3ee4b924bbba8d9f106365e67c6985d843703afab1",
                "docs/discovery/VP3-discovery-led-cost-aware-methodology/evidence-index.md": "6d0ec0045dee53eed1970468715d51ff4ff94891a597e598122f9ff256e599ab",
                "docs/discovery/VP3-discovery-led-cost-aware-methodology/experiments/EXP-001-usage-telemetry.md": "6dc0b7f05982acd6e11a97c45a220c4d537d7d326c0ad82834cf1f21a3d5e97d",
                "docs/discovery/VP3-discovery-led-cost-aware-methodology/experiments/EXP-002-circuit-breaker-and-routing.md": "4baaa11525104388d0d37223ee59138a265e0370523de91c2f88d8bf50b66f6f",
                "docs/discovery/VP3-discovery-led-cost-aware-methodology/experiments/EXP-003-revisioned-state.md": "70e115301f9fc91623c15f22704a26e7b0b772c1c9deb7515d2180f8f3ba96a2",
                "docs/discovery/VP3-discovery-led-cost-aware-methodology/experiments/EXP-004-packet-staleness.md": "16834b342c2667abac0cf866fc2dc1a2781de16311246e88a90ac3fcb5a174b1",
                "docs/discovery/VP3-discovery-led-cost-aware-methodology/mechanisms.md": "946b8a119667ea39d2c7abeeeb1bb05f967768f6ea22e13b02c382df2a2e9296",
                "docs/discovery/VP3-discovery-led-cost-aware-methodology/prd-recommendations.md": "5970ce82d26db9c24857f670fc1a41e18579f2d1d8928cef3514d67593ba98f5",
                "docs/discovery/VP3-discovery-led-cost-aware-methodology/revisions/DR-001-lifecycle-scope-and-acceptance.md": "0398c88d77f9f2f8b2b1b82e0aa749613a170f5838681afa047b75b105b718b3",
                "docs/discovery/VP3-discovery-led-cost-aware-methodology/risks-and-failure-modes.md": "5fc2e2bcd1df07ed12cfdb6818010856ae8bb996494d468d2111a0ac74e8ff33",
                "docs/discovery/VP3-discovery-led-cost-aware-methodology/system-map.md": "f68c0b9f7bfd891d309e093485913879791cc9f60f3c1000bac3ddccb14239ee",
                "docs/requirements/VP3-discovery-led-cost-aware-methodology/PRD.md": "f4dbb07de57256f82cd1ccd9fc7f70580e6fadb64d165eb328275bce6d2088fd",
            },
            entry_modes={
                "docs/vision_of_product/VP3-discovery-led-cost-aware-methodology/VP3.md": "100644",
                "docs/discovery/VP3-discovery-led-cost-aware-methodology/README.md": "100644",
                "docs/discovery/VP3-discovery-led-cost-aware-methodology/architecture-handoff.md": "100644",
                "docs/discovery/VP3-discovery-led-cost-aware-methodology/assumptions.md": "100644",
                "docs/discovery/VP3-discovery-led-cost-aware-methodology/decisions.md": "100644",
                "docs/discovery/VP3-discovery-led-cost-aware-methodology/discovery-questions.md": "100644",
                "docs/discovery/VP3-discovery-led-cost-aware-methodology/domain-ontology.md": "100644",
                "docs/discovery/VP3-discovery-led-cost-aware-methodology/evidence-index.md": "100644",
                "docs/discovery/VP3-discovery-led-cost-aware-methodology/experiments/EXP-001-usage-telemetry.md": "100644",
                "docs/discovery/VP3-discovery-led-cost-aware-methodology/experiments/EXP-002-circuit-breaker-and-routing.md": "100644",
                "docs/discovery/VP3-discovery-led-cost-aware-methodology/experiments/EXP-003-revisioned-state.md": "100644",
                "docs/discovery/VP3-discovery-led-cost-aware-methodology/experiments/EXP-004-packet-staleness.md": "100644",
                "docs/discovery/VP3-discovery-led-cost-aware-methodology/mechanisms.md": "100644",
                "docs/discovery/VP3-discovery-led-cost-aware-methodology/prd-recommendations.md": "100644",
                "docs/discovery/VP3-discovery-led-cost-aware-methodology/revisions/DR-001-lifecycle-scope-and-acceptance.md": "100644",
                "docs/discovery/VP3-discovery-led-cost-aware-methodology/risks-and-failure-modes.md": "100644",
                "docs/discovery/VP3-discovery-led-cost-aware-methodology/system-map.md": "100644",
                "docs/requirements/VP3-discovery-led-cost-aware-methodology/PRD.md": "100644",
            },
        ),
    },
)


@dataclass(frozen=True)
class BaselineEntry:
    path: str
    mode: str
    content: bytes


@dataclass(frozen=True)
class ValidationResult:
    findings: tuple[Finding, ...]
    manifest: Mapping[str, object]

    @property
    def valid(self) -> bool:
        return not self.findings


class BaselineError(RuntimeError):
    """Immutable baseline evidence cannot be read or authenticated."""


class BaselineReader(Protocol):
    def read(self, revision: str, paths: Sequence[str]) -> tuple[BaselineEntry, ...]:
        """Read exact entries rooted at *paths* from an immutable revision."""

    def read_committed(
        self, paths: Sequence[str], since_revision: str
    ) -> tuple[str, tuple[BaselineEntry, ...]]:
        """Read first-adjudicated post-baseline entries and the current commit."""


def _safe_display(value: str) -> str:
    return "".join(
        character
        if character.isprintable() and not 0xD800 <= ord(character) <= 0xDFFF
        else rf"\u{ord(character):04x}"
        for character in value
    )


def _finding(
    *,
    file: str,
    record: str | None,
    message: str,
    remediation: str,
) -> Finding:
    return {
        "check": "lock",
        "severity": "error",
        "file": _safe_display(file),
        "record": record,
        "message": message,
        "remediation": remediation,
    }


def _valid_relative_path(value: str) -> bool:
    path = PurePosixPath(value)
    return (
        bool(value)
        and not path.is_absolute()
        and ".." not in path.parts
        and "." not in path.parts
        and all(SAFE_PATH_PART.fullmatch(part) for part in path.parts)
    )


class GitBaselineReader:
    """Read committed trees using only fixed, read-only Git plumbing."""

    def __init__(self, repository_root: Path) -> None:
        self.root = repository_root.resolve()
        self.git_executable = self._resolve_git()
        self.environment = {
            "PATH": (
                str(self.git_executable.parent)
                if self.git_executable is not None
                else ""
            ),
            "HOME": os.devnull,
            "LC_ALL": "C",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
        }

    def _resolve_git(self) -> Path | None:
        """Resolve Git once without trusting repository or relative PATH bins."""

        for raw_directory in os.environ.get("PATH", "").split(os.pathsep):
            directory = Path(raw_directory)
            if not raw_directory or not directory.is_absolute():
                continue
            candidate = directory / "git"
            try:
                # Reject a repository path even when it is a symlink to a
                # system binary: repository-controlled argv is never trusted.
                candidate.absolute().relative_to(self.root)
                continue
            except ValueError:
                pass
            try:
                resolved = candidate.resolve(strict=True)
                resolved.relative_to(self.root)
                continue
            except ValueError:
                pass
            except OSError:
                continue
            try:
                info = resolved.stat()
            except OSError:
                continue
            if stat.S_ISREG(info.st_mode) and os.access(resolved, os.X_OK):
                return resolved
        return None

    def _run(self, arguments: Sequence[str]) -> bytes:
        if self.git_executable is None:
            raise BaselineError("trusted Git executable is unavailable")
        try:
            result = subprocess.run(
                [str(self.git_executable), "-C", str(self.root), *arguments],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=GIT_TIMEOUT_SECONDS,
                env=self.environment,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise BaselineError("read-only Git plumbing is unavailable") from error
        if result.returncode:
            raise BaselineError("accepted Git baseline is unavailable or invalid")
        return result.stdout

    def read(self, revision: str, paths: Sequence[str]) -> tuple[BaselineEntry, ...]:
        if REVISION.fullmatch(revision) is None:
            raise BaselineError("baseline revision is not a full commit ID")
        if not paths or any(not _valid_relative_path(path) for path in paths):
            raise BaselineError("baseline contains an unsafe repository path")

        # A 40-hex tag object ID is syntactically indistinguishable from a
        # commit ID. Require the pinned object itself to be the peeled commit,
        # rather than silently dereferencing an annotated tag.
        if self._run(("cat-file", "-t", revision)) != b"commit\n":
            raise BaselineError("baseline revision is not a peeled commit ID")
        entries: dict[str, tuple[str, str]] = {}
        for scope in sorted(set(paths)):
            output = self._run(
                ("ls-tree", "-rz", "--full-tree", revision, "--", scope)
            )
            for raw_entry in output.split(b"\0"):
                if not raw_entry:
                    continue
                try:
                    metadata, raw_path = raw_entry.split(b"\t", 1)
                    mode, kind, raw_oid = metadata.split(b" ", 2)
                    path = raw_path.decode("utf-8")
                    mode_text = mode.decode("ascii")
                    oid = raw_oid.decode("ascii")
                except (ValueError, UnicodeError) as error:
                    raise BaselineError("baseline tree output is malformed") from error
                if (
                    kind != b"blob"
                    or mode_text not in {"100644", "100755", "120000"}
                    or re.fullmatch(r"[0-9a-f]{40,64}", oid) is None
                    or not _valid_relative_path(path)
                ):
                    raise BaselineError("baseline tree contains an unsupported entry")
                entries[path] = (mode_text, oid)

        result: list[BaselineEntry] = []
        for path, (mode, oid) in sorted(entries.items()):
            content = self._run(("cat-file", "blob", oid))
            if len(content) > MAX_ARTEFACT_BYTES:
                raise BaselineError("baseline artefact exceeds the safety limit")
            result.append(BaselineEntry(path=path, mode=mode, content=content))
        return tuple(result)

    def read_committed(
        self, paths: Sequence[str], since_revision: str
    ) -> tuple[str, tuple[BaselineEntry, ...]]:
        """Return first-adjudicated append blobs without consulting the index."""

        head = self._run(("rev-parse", "--verify", "HEAD")).decode("ascii").strip()
        if REVISION.fullmatch(head) is None:
            raise BaselineError("current committed revision is not a full commit ID")
        if REVISION.fullmatch(since_revision) is None:
            raise BaselineError("append baseline is not a full commit ID")
        history = self._run(
            ("rev-list", "--reverse", f"{since_revision}..{head}", "--", *paths)
        )
        revisions = [item.decode("ascii") for item in history.splitlines()]
        first_seen: dict[str, BaselineEntry] = {}
        for revision in revisions:
            if REVISION.fullmatch(revision) is None:
                raise BaselineError("committed append history is malformed")
            entries = self.read(revision, paths)
            adjudicated = _canonical_adjudicated_append_paths(entries, paths)
            for entry in entries:
                if entry.path in adjudicated:
                    first_seen.setdefault(entry.path, entry)
        return head, tuple(first_seen[path] for path in sorted(first_seen))


def _assert_regular_ancestors(root: Path, path: Path) -> None:
    """Reject symlinks and non-directories in every lexical ancestor."""

    try:
        relative = path.absolute().relative_to(root.absolute())
    except ValueError as error:
        raise ValueError("path is outside the repository") from error
    current = root.absolute()
    for part in relative.parts[:-1]:
        current = current / part
        try:
            info = current.lstat()
        except OSError as error:
            raise ValueError("ancestor is missing or unreadable") from error
        if stat.S_ISLNK(info.st_mode):
            raise ValueError(
                f"ancestor {current.relative_to(root.absolute()).as_posix()} is a symlink"
            )
        if not stat.S_ISDIR(info.st_mode):
            raise ValueError(
                f"ancestor {current.relative_to(root.absolute()).as_posix()} is not a directory"
            )


def _read_control(path: Path, root: Path) -> bytes:
    _assert_regular_ancestors(root, path)
    try:
        info = path.lstat()
    except OSError as error:
        raise ValueError("file is missing or unreadable") from error
    if not stat.S_ISREG(info.st_mode) or path.is_symlink():
        raise ValueError("path is not a regular file")
    if info.st_size > MAX_CONTROL_BYTES:
        raise ValueError("file exceeds the safety limit")
    try:
        return path.read_bytes()
    except OSError as error:
        raise ValueError("file is unreadable") from error


def _load_yaml_file(path: Path, root: Path) -> object:
    try:
        raw = _read_control(path, root)
        text = raw.decode("utf-8")
        return yaml.load(text, Loader=UniqueKeyLoader)
    except (UnicodeError, yaml.YAMLError, RecursionError, ValueError) as error:
        raise ValueError("file is not safe, duplicate-free UTF-8 YAML") from error


def _themes_from_backlog(
    root: Path,
    baselines: Baselines,
    findings: list[Finding],
) -> dict[str, dict[str, object]]:
    backlog_file = root / BACKLOG_PATH
    themes: dict[str, dict[str, object]] = {}
    archived_summaries: dict[str, dict[str, object]] = {}
    try:
        loaded = _load_yaml_file(backlog_file, root)
        backlog_data = loaded["backlog"] if isinstance(loaded, dict) else None
        if not isinstance(backlog_data, dict):
            raise ValueError("backlog root is missing")
        active = backlog_data.get("active-themes", [])
        archived = backlog_data.get("archived-themes", [])
        if not isinstance(active, list) or not isinstance(archived, list):
            raise ValueError("theme collections are malformed")
        for item in active:
            if isinstance(item, dict) and THEME_ID.fullmatch(str(item.get("id", ""))):
                themes[str(item["id"])] = item
        for item in archived:
            if isinstance(item, dict) and THEME_ID.fullmatch(str(item.get("id", ""))):
                archived_summaries[str(item["id"])] = item
    except (KeyError, TypeError, ValueError) as error:
        findings.append(
            _finding(
                file=BACKLOG_PATH,
                record="backlog",
                message=f"Cannot build the lock manifest: {error}.",
                remediation="Restore a valid backlog before validating locks.",
            )
        )

    archive_paths: dict[str, str] = {}
    for theme_id, summary in archived_summaries.items():
        archive_ref = summary.get("archive-ref")
        if isinstance(archive_ref, str) and _valid_relative_path(archive_ref):
            archive_paths[theme_id] = archive_ref
        else:
            findings.append(
                _finding(
                    file=BACKLOG_PATH,
                    record=theme_id,
                    message=f"{theme_id} has no safe archive-ref.",
                    remediation="Restore the accepted locked-theme archive reference.",
                )
            )
    for theme_id, baseline in baselines.themes.items():
        summary = archived_summaries.get(theme_id)
        if summary is None:
            findings.append(
                _finding(
                    file=BACKLOG_PATH,
                    record=theme_id,
                    message=f"Accepted theme {theme_id} is missing from archived-themes.",
                    remediation="Restore the archived-theme summary; do not reopen history.",
                )
            )
        elif summary.get("locked") is not True:
            findings.append(
                _finding(
                    file=BACKLOG_PATH,
                    record=theme_id,
                    message=f"Accepted theme {theme_id} is no longer marked locked.",
                    remediation="Restore locked: true for the accepted theme.",
                )
            )
        elif archive_paths.get(theme_id) != baseline.archive_path:
            findings.append(
                _finding(
                    file=BACKLOG_PATH,
                    record=theme_id,
                    message=(
                        f"Accepted theme {theme_id} no longer references "
                        f"{baseline.archive_path}."
                    ),
                    remediation="Restore the accepted archive-ref exactly.",
                )
            )
        archive_paths[theme_id] = baseline.archive_path

    for theme_id, archive_ref in sorted(archive_paths.items()):
        try:
            loaded = _load_yaml_file(root / archive_ref, root)
            snapshot = loaded["theme"] if isinstance(loaded, dict) else None
            if not isinstance(snapshot, dict) or snapshot.get("id") != theme_id:
                raise ValueError("snapshot identity does not match its archive")
            if snapshot.get("locked") is not True:
                raise ValueError("snapshot is not marked locked")
            snapshot = dict(snapshot)
            snapshot["_archive-ref"] = archive_ref
            themes[theme_id] = snapshot
        except (KeyError, TypeError, ValueError) as error:
            findings.append(
                _finding(
                    file=archive_ref,
                    record=theme_id,
                    message=f"Cannot load immutable locked-theme snapshot: {error}.",
                    remediation="Restore the exact accepted archive snapshot.",
                )
            )
    return themes


def _story_paths(theme: Mapping[str, object]) -> tuple[str, ...]:
    paths: list[str] = []
    epics = theme.get("epics", [])
    if not isinstance(epics, list):
        return ()
    for epic in epics:
        if not isinstance(epic, dict):
            continue
        stories = epic.get("stories", [])
        if not isinstance(stories, list):
            continue
        for story in stories:
            if not isinstance(story, dict):
                continue
            path = story.get("file")
            if isinstance(path, str) and _valid_relative_path(path):
                paths.append(path)
    return tuple(sorted(set(paths)))


def _markdown_adr_refs(raw: bytes) -> set[str]:
    try:
        text = raw.decode("utf-8")
    except UnicodeError:
        return set()
    references = set(ADR_ID.findall(text))
    for first, last in re.findall(
        r"(ADR-(?:00[1-9]|0[1-9][0-9]|[1-9][0-9]{2}))"
        r"\s+through\s+"
        r"(ADR-(?:00[1-9]|0[1-9][0-9]|[1-9][0-9]{2}))",
        text,
    ):
        start = int(first[-3:])
        end = int(last[-3:])
        if start <= end and end - start <= 100:
            references.update(f"ADR-{number:03d}" for number in range(start, end + 1))
    return references


def _adr_theme_mapping(
    root: Path,
    themes: Mapping[str, Mapping[str, object]],
) -> dict[str, set[str]]:
    mapping: dict[str, set[str]] = {"ADR-001": {"TH2"}}
    for theme_id, theme in themes.items():
        candidates = list(_story_paths(theme))
        baseline = LEGACY_BASELINES.themes.get(theme_id)
        if baseline is not None:
            candidates.append(f"{baseline.theme_path}/README.md")
        else:
            prefixes = {
                PurePosixPath(path).parts[:3]
                for path in candidates
                if len(PurePosixPath(path).parts) >= 3
            }
            for prefix in prefixes:
                candidates.append(PurePosixPath(*prefix, "README.md").as_posix())
        for candidate in sorted(set(candidates)):
            try:
                raw = _read_control(root / candidate, root)
            except ValueError:
                continue
            for adr_id in _markdown_adr_refs(raw):
                mapping.setdefault(adr_id, set()).add(theme_id)

    try:
        index = _read_control(root / ADR_INDEX_PATH, root).decode("utf-8")
    except (ValueError, UnicodeError):
        return mapping
    for line in index.splitlines():
        adr_match = ADR_ID.search(line)
        if adr_match is None:
            continue
        for theme_id in THEME_ID.findall(line):
            mapping.setdefault(adr_match.group(), set()).add(theme_id)
    return mapping


def _vp_id(reference: object) -> str | None:
    if not isinstance(reference, str) or not _valid_relative_path(reference):
        return None
    for part in PurePosixPath(reference).parts:
        match = re.match(r"(VP[1-9][0-9]*)-", part)
        if match is not None:
            return match.group(1)
    return None


def _vp_mappings_and_paths(
    root: Path,
    themes: Mapping[str, Mapping[str, object]],
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    mapped: dict[str, set[str]] = {}
    paths: dict[str, set[str]] = {}
    for theme_id, theme in themes.items():
        vision = theme.get("vision-ref")
        vp_id = _vp_id(vision)
        if vp_id is None:
            continue
        mapped.setdefault(vp_id, set()).add(theme_id)
        for key in ("vision-ref", "discovery-ref", "requirements-ref"):
            reference = theme.get(key)
            if not isinstance(reference, str) or not _valid_relative_path(reference):
                continue
            path = PurePosixPath(reference)
            if key == "requirements-ref" and path.suffix:
                path = path.parent
            paths.setdefault(vp_id, set()).add(path.as_posix().rstrip("/"))

        if isinstance(vision, str):
            vision_path = root / vision
            candidates = (
                sorted(vision_path.glob("*.md"))
                if vision_path.is_dir() and not vision_path.is_symlink()
                else [vision_path]
            )
            for candidate in candidates:
                try:
                    raw = _read_control(candidate, root).decode("utf-8")
                except (ValueError, UnicodeError):
                    continue
                for line in raw.splitlines():
                    if re.match(r"\|\s*(?:Intended themes|Delivery mapping)\s*\|", line):
                        mapped[vp_id].update(THEME_ID.findall(line))
    return mapped, paths


def _protected_scope(
    root: Path,
    *,
    path: str,
    record: str,
    kind: str,
    force_file: bool = False,
) -> ProtectedArtefactScope | None:
    """Normalize one already repository-relative canonical lock scope."""

    normalized = path.rstrip("/")
    if not _valid_relative_path(normalized):
        return None
    candidate = root / normalized
    recursive = not force_file
    try:
        info = candidate.lstat()
    except OSError:
        # Missing evidence remains protected. Canonical Markdown references are
        # files; every other unresolved lock scope is conservatively a tree.
        recursive = not (force_file or PurePosixPath(normalized).suffix != "")
    else:
        recursive = stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode)
    return ProtectedArtefactScope(
        path=normalized,
        record=record,
        kind=kind,
        recursive=recursive,
    )


def protected_artefact_scopes(
    repository_root: PathValue,
    themes: Mapping[str, Mapping[str, object]],
    *,
    baselines: Baselines = LEGACY_BASELINES,
) -> tuple[ProtectedArtefactScope, ...]:
    """Return scopes protected by the canonical split-lock semantics.

    This is the write-preflight counterpart of ``validate_repository``.  It is
    intentionally independent of Git baseline availability: inability to
    compare immutable bytes must never make a protected output writable.
    Partially accepted shared VP scopes are included because their existing
    basis is immutable and only canonical DR/PCR appends are permitted there;
    a generated migration assessment is not such an append.
    """

    root = Path(repository_root).resolve()
    accepted = {
        theme_id
        for theme_id, theme in themes.items()
        if theme.get("locked") is True
    }
    # Pinned baselines are immutable historical facts even if mutable backlog
    # metadata is missing or damaged.
    accepted.update(baselines.themes)

    protected: dict[tuple[str, str, str], ProtectedArtefactScope] = {}

    def add(
        path: str,
        record: str,
        kind: str,
        *,
        force_file: bool = False,
    ) -> None:
        scope = _protected_scope(
            root,
            path=path,
            record=record,
            kind=kind,
            force_file=force_file,
        )
        if scope is not None:
            protected[(scope.path, scope.record, scope.kind)] = scope

    for theme_id in sorted(accepted, key=lambda item: int(item[2:])):
        baseline = baselines.themes.get(theme_id)
        if baseline is not None:
            add(baseline.theme_path, theme_id, "theme")
            add(
                baseline.archive_path,
                theme_id,
                "theme archive",
                force_file=True,
            )
        theme = themes.get(theme_id)
        if theme is None:
            continue
        archive_ref = theme.get("_archive-ref")
        if isinstance(archive_ref, str):
            add(archive_ref, theme_id, "theme archive", force_file=True)
        # Story declarations resolve the actual theme directory.  A custom
        # directory name is authoritative; protection must not rely on a
        # coincidental ``TH<n>-`` basename.
        for story_path in _story_paths(theme):
            parts = PurePosixPath(story_path).parts
            if len(parts) >= 3 and parts[:2] == ("docs", "themes"):
                add(
                    PurePosixPath(*parts[:3]).as_posix(),
                    theme_id,
                    "theme",
                )

    adr_mapping = _adr_theme_mapping(root, themes)
    locked_adrs = {
        adr_id
        for adr_id, dependent_themes in adr_mapping.items()
        if dependent_themes & accepted
    }
    locked_adrs.update(baselines.adrs)
    adr_directory = root / "docs/ADRs"
    try:
        adr_entries = sorted(os.scandir(adr_directory), key=lambda item: item.name)
    except OSError:
        adr_entries = []
    for adr_id in sorted(locked_adrs):
        baseline = baselines.adrs.get(adr_id)
        if baseline is not None:
            add(baseline.path, adr_id, "ADR", force_file=True)
        for entry in adr_entries:
            if (
                entry.name == f"{adr_id}.md"
                or entry.name.startswith(f"{adr_id}-")
            ) and entry.name.endswith(".md"):
                add(
                    f"docs/ADRs/{entry.name}",
                    adr_id,
                    "ADR",
                    force_file=True,
                )

    vp_mappings, vp_paths = _vp_mappings_and_paths(root, themes)
    for vp_id, baseline in baselines.vps.items():
        vp_paths.setdefault(vp_id, set()).update(baseline.paths)
        vp_mappings.setdefault(vp_id, set()).update(baseline.mapped_themes)
    for vp_id in sorted(
        set(vp_mappings) | set(baselines.vps),
        key=lambda item: int(item[2:]),
    ):
        mapped = vp_mappings.get(vp_id, set())
        accepted_mapped = mapped & accepted
        baseline = baselines.vps.get(vp_id)
        was_locked = baseline is not None and (
            not baseline.mapped_themes
            or set(baseline.mapped_themes) <= accepted
        )
        if not accepted_mapped and not was_locked:
            continue
        for path in sorted(vp_paths.get(vp_id, set())):
            add(path, vp_id, "shared VP")

    return tuple(
        sorted(
            protected.values(),
            key=lambda item: (item.path, item.record, item.kind),
        )
    )


def _mode_and_content(path: Path, root: Path) -> tuple[str, bytes]:
    _assert_regular_ancestors(root, path)
    try:
        info = path.lstat()
    except OSError as error:
        raise ValueError("missing") from error
    if stat.S_ISLNK(info.st_mode):
        try:
            return "120000", os.fsencode(os.readlink(path))
        except OSError as error:
            raise ValueError("unreadable symlink") from error
    if not stat.S_ISREG(info.st_mode):
        raise ValueError("unsupported filesystem object")
    if info.st_size > MAX_ARTEFACT_BYTES:
        raise ValueError("artefact exceeds the safety limit")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
        try:
            opened = os.fstat(descriptor)
            if not stat.S_ISREG(opened.st_mode):
                raise ValueError("filesystem object changed while reading")
            chunks: list[bytes] = []
            remaining = MAX_ARTEFACT_BYTES + 1
            while remaining:
                chunk = os.read(descriptor, min(1024 * 1024, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            content = b"".join(chunks)
            if len(content) > MAX_ARTEFACT_BYTES:
                raise ValueError("artefact exceeds the safety limit")
        finally:
            os.close(descriptor)
    except OSError as error:
        raise ValueError("unreadable") from error
    mode = "100755" if opened.st_mode & 0o111 else "100644"
    return mode, content


def _scan_scope(root: Path, scope: str) -> dict[str, tuple[str, bytes] | ValueError]:
    result: dict[str, tuple[str, bytes] | ValueError] = {}
    start = root / scope
    try:
        _assert_regular_ancestors(root, start)
        start_info = start.lstat()
    except OSError:
        return result
    except ValueError as error:
        result[scope] = error
        return result
    if not stat.S_ISDIR(start_info.st_mode) or stat.S_ISLNK(start_info.st_mode):
        try:
            result[scope] = _mode_and_content(start, root)
        except ValueError as error:
            result[scope] = error
        return result

    pending = [start]
    while pending:
        directory = pending.pop()
        try:
            children = sorted(os.scandir(directory), key=lambda item: item.name)
        except OSError:
            relative = directory.relative_to(root).as_posix()
            result[relative] = ValueError("directory is unreadable")
            continue
        for child in children:
            path = Path(child.path)
            relative = path.relative_to(root).as_posix()
            try:
                if child.is_dir(follow_symlinks=False):
                    pending.append(path)
                else:
                    result[relative] = _mode_and_content(path, root)
            except (OSError, ValueError) as error:
                result[relative] = ValueError(str(error))
    return result


def _markdown_sections(text: str) -> tuple[str, dict[str, str]] | None:
    """Parse the canonical ADR heading and its level-two sections."""

    lines = text.splitlines()
    headings = [
        (index, line)
        for index, line in enumerate(lines)
        if line.startswith("#")
    ]
    h1 = [(index, line) for index, line in headings if line.startswith("# ")]
    if len(h1) != 1:
        return None
    sections: dict[str, str] = {}
    level_two = [
        (index, line[3:])
        for index, line in headings
        if line.startswith("## ") and not line.startswith("### ")
    ]
    for position, (start, name) in enumerate(level_two):
        if name in sections:
            return None
        end = level_two[position + 1][0] if position + 1 < len(level_two) else len(lines)
        sections[name] = "\n".join(lines[start + 1 : end]).strip()
    return h1[0][1], sections


def _canonical_replacement_adr(
    path: Path,
    *,
    root: Path,
    replacement_id: str,
    superseded_id: str,
) -> bool:
    """Require a complete accepted ADR that explicitly replaces the old one."""

    if (
        re.fullmatch(
            rf"{re.escape(replacement_id)}-[a-z0-9]+(?:-[a-z0-9]+)*\.md",
            path.name,
        )
        is None
    ):
        return False
    try:
        mode, raw = _mode_and_content(path, root)
        text = raw.decode("utf-8")
    except (ValueError, UnicodeError):
        return False
    if mode != "100644" or PLACEHOLDER.search(text):
        return False
    parsed = _markdown_sections(text)
    if parsed is None:
        return False
    title, sections = parsed
    title_match = re.fullmatch(
        rf"# {re.escape(replacement_id)}: (?P<title>\S(?:.*\S)?)", title
    )
    required = (
        "Status",
        "Replacement",
        "Context",
        "Decision",
        "Consequences",
        "Alternatives Considered",
    )
    if (
        title_match is None
        or tuple(sections) != required
        or any(not sections[name] for name in required)
        or sections["Status"] != "Accepted"
    ):
        return False
    replacement_metadata = (
        "| Field | Value |\n"
        "|---|---|\n"
        f"| Replaces | {superseded_id} |"
    )
    return sections["Replacement"] == replacement_metadata


def _status_only_supersession(
    baseline: bytes,
    current: bytes,
    *,
    root: Path,
    current_adr: str,
) -> bool:
    old_matches = list(STATUS_VALUE.finditer(baseline))
    new_matches = list(STATUS_VALUE.finditer(current))
    if len(old_matches) != 1 or len(new_matches) != 1:
        return False
    old = old_matches[0]
    new = new_matches[0]
    replacement = new.group("value")
    match = re.fullmatch(rb"Superseded by (ADR-[0-9]{3})", replacement)
    if match is None or old.group("value") == replacement:
        return False
    normalized = current[: new.start("value")] + old.group("value") + current[new.end("value") :]
    if normalized != baseline:
        return False
    replacement_id = match.group(1).decode("ascii")
    if replacement_id in {"ADR-000", current_adr}:
        return False
    matches = list((root / "docs/ADRs").glob(f"{replacement_id}-*.md"))
    return len(matches) == 1 and _canonical_replacement_adr(
        matches[0],
        root=root,
        replacement_id=replacement_id,
        superseded_id=current_adr,
    )


def _compare(
    *,
    root: Path,
    reader: BaselineReader,
    revision: str,
    scopes: Sequence[str],
    record: str,
    kind: str,
    findings: list[Finding],
    allow_adr_status: bool = False,
) -> list[str]:
    try:
        expected_entries = reader.read(revision, scopes)
    except BaselineError as error:
        findings.append(
            _finding(
                file=scopes[0],
                record=record,
                message=f"Immutable baseline evidence is unavailable: {error}.",
                remediation="Restore the accepted commit objects; validation fails closed.",
            )
        )
        return []
    if not expected_entries:
        findings.append(
            _finding(
                file=scopes[0],
                record=record,
                message="Immutable baseline scope contains no artefacts.",
                remediation="Restore the exact accepted baseline scope.",
            )
        )
        return []
    expected = {entry.path: entry for entry in expected_entries}
    current: dict[str, tuple[str, bytes] | ValueError] = {}
    for scope in scopes:
        current.update(_scan_scope(root, scope))

    for path in sorted(set(expected) | set(current)):
        baseline_entry = expected.get(path)
        current_entry = current.get(path)
        problem: str | None = None
        if baseline_entry is None:
            problem = "was added inside locked scope"
        elif current_entry is None:
            problem = "was deleted or renamed"
        elif isinstance(current_entry, ValueError):
            problem = f"cannot be compared safely ({current_entry})"
        else:
            mode, content = current_entry
            if mode != baseline_entry.mode:
                problem = "changed filesystem type or executable mode"
            elif content != baseline_entry.content and not (
                allow_adr_status
                and _status_only_supersession(
                    baseline_entry.content,
                    content,
                    root=root,
                    current_adr=record,
                )
            ):
                problem = "content differs from its accepted baseline"
        if problem is None:
            continue
        if kind == "archive":
            description = "immutable locked-theme snapshot"
            remediation = "Restore the accepted archive snapshot byte-for-byte."
        elif kind == "adr":
            description = "locked ADR body"
            remediation = (
                "Restore the ADR body. Only an exact Status change to "
                "`Superseded by ADR-<NNN>` with a complete, Accepted canonical "
                "replacement ADR that explicitly supersedes this decision is permitted."
            )
        elif kind == "vp":
            description = "locked shared VP artefact"
            remediation = "Restore the accepted shared artefact byte-for-byte."
        else:
            description = "locked theme artefact"
            remediation = (
                "Restore the accepted file and extend history with a new theme "
                "and Discovery dossier instead."
            )
        findings.append(
            _finding(
                file=path,
                record=record,
                message=f"{path} {problem}; it is an {description}.",
                remediation=remediation,
            )
        )
    return sorted(set(expected) | set(current))


def _append_kind(path: str, scopes: Sequence[str]) -> str | None:
    for scope in scopes:
        normalized = scope.rstrip("/")
        if normalized.startswith("docs/discovery/") and re.fullmatch(
            re.escape(normalized)
            + r"/revisions/DR-[0-9]{3}-[a-z0-9]+(?:-[a-z0-9]+)*\.md",
            path,
        ):
            return "DR"
        if normalized.startswith("docs/requirements/") and re.fullmatch(
            re.escape(normalized)
            + r"/changes/PCR-[0-9]{3}-[a-z0-9]+(?:-[a-z0-9]+)*\.md",
            path,
        ):
            return "PCR"
    return None


def _canonical_adjudicated_append_paths(
    entries: Sequence[BaselineEntry],
    scopes: Sequence[str],
) -> set[str]:
    """Return append paths whose committed bytes satisfy their owner contract.

    A path appearing in Git is not acceptance evidence: a DR or PCR may be
    committed repeatedly while it is still a draft. Reconstruct each
    historical VP snapshot in an isolated directory and reuse the canonical
    owner validators. DRs lock only at a valid ``Accepted`` verdict; PCRs lock
    at either valid human adjudication because both ``Approved`` and
    ``Rejected`` records reserve immutable history.
    """

    try:
        with tempfile.TemporaryDirectory(prefix="method-lock-history-") as directory:
            snapshot = Path(directory)
            for entry in entries:
                if (
                    entry.mode not in {"100644", "100755"}
                    or not _valid_relative_path(entry.path)
                ):
                    continue
                destination = snapshot / entry.path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(entry.content)

            adjudicated: set[str] = set()
            for scope in scopes:
                scope_name = PurePosixPath(scope.rstrip("/")).name
                match = re.match(r"(?P<vp>VP[1-9][0-9]*)(?:-|$)", scope_name)
                if match is None:
                    continue
                vp_id = match.group("vp")
                if scope.startswith("docs/discovery/"):
                    state = gates.validate_discovery_revision_collection(
                        root=snapshot,
                        dossier=snapshot / scope,
                        vp=vp_id,
                    )
                    adjudicated.update(
                        path.relative_to(snapshot).as_posix()
                        for path in state.accepted_paths
                    )
                elif scope.startswith("docs/requirements/"):
                    state = gates.validate_product_change_collection(
                        root=snapshot,
                        requirements=snapshot / scope,
                        vp=vp_id,
                    )
                    adjudicated.update(
                        path.relative_to(snapshot).as_posix()
                        for path in state.valid_paths
                    )
            return adjudicated
    except (OSError, ValueError) as error:
        raise BaselineError(
            "committed append history cannot be validated safely"
        ) from error


def _compare_partial_vp(
    *,
    root: Path,
    reader: BaselineReader,
    baseline: VpBaseline,
    vp_id: str,
    findings: list[Finding],
) -> list[str]:
    """Preserve the partial-acceptance baseline and admit valid new records."""

    try:
        expected_entries = reader.read(baseline.revision, baseline.paths)
    except BaselineError as error:
        findings.append(
            _finding(
                file=baseline.paths[0],
                record=vp_id,
                message=f"Immutable baseline evidence is unavailable: {error}.",
                remediation="Restore the accepted commit objects; validation fails closed.",
            )
        )
        return []
    if not expected_entries:
        findings.append(
            _finding(
                file=baseline.paths[0],
                record=vp_id,
                message="Immutable partial-acceptance baseline contains no artefacts.",
                remediation="Restore the exact accepted shared VP baseline.",
            )
        )
        return []

    baseline_expected = {entry.path: entry for entry in expected_entries}
    expected = dict(baseline_expected)
    committed_append_paths: set[str] = set()
    read_committed = getattr(reader, "read_committed", None)
    if callable(read_committed):
        try:
            _committed_revision, committed_entries = read_committed(
                baseline.paths, baseline.revision
            )
        except BaselineError as error:
            findings.append(
                _finding(
                    file=baseline.paths[0],
                    record=vp_id,
                    message=f"Committed append evidence is unavailable: {error}.",
                    remediation=(
                        "Restore the committed Git objects used as immutable "
                        "DR/PCR acceptance evidence."
                    ),
                )
            )
            committed_entries = ()
        for entry in committed_entries:
            if (
                entry.path not in baseline_expected
                and _append_kind(entry.path, baseline.paths) is not None
            ):
                # A committed repository object is durable evidence. Once a
                # DR/PCR path has that evidence, the working tree must retain
                # its exact bytes; no process-local memory is involved.
                expected[entry.path] = entry
                committed_append_paths.add(entry.path)

    current: dict[str, tuple[str, bytes] | ValueError] = {}
    for scope in baseline.paths:
        current.update(_scan_scope(root, scope))
    post_baseline_paths = {
        path
        for path in set(expected) | set(current)
        if path not in baseline_expected
        and _append_kind(path, baseline.paths) is not None
    }
    valid_append_paths: set[str] = set()
    accepted_dr_paths: set[str] = set()
    append_evidence: dict[str, str] = {}
    if any(_append_kind(path, baseline.paths) == "DR" for path in post_baseline_paths):
        dossier_scope = next(
            (
                scope for scope in baseline.paths
                if scope.startswith("docs/discovery/")
            ),
            None,
        )
        if dossier_scope is not None:
            state = gates.validate_discovery_revision_collection(
                root=root,
                dossier=root / dossier_scope,
                vp=vp_id,
            )
            valid_append_paths.update(
                path.relative_to(root).as_posix() for path in state.valid_paths
            )
            accepted_dr_paths.update(
                path.relative_to(root).as_posix() for path in state.accepted_paths
            )
            append_evidence.update(
                {
                    path.relative_to(root).as_posix(): revision
                    for path, revision in state.evidence.items()
                }
            )
            for item in state.findings:
                findings.append({**item, "check": "lock"})
    if any(_append_kind(path, baseline.paths) == "PCR" for path in post_baseline_paths):
        requirements_scope = next(
            (
                scope for scope in baseline.paths
                if scope.startswith("docs/requirements/")
            ),
            None,
        )
        if requirements_scope is not None:
            state = gates.validate_product_change_collection(
                root=root,
                requirements=root / requirements_scope,
                vp=vp_id,
            )
            valid_append_paths.update(
                path.relative_to(root).as_posix() for path in state.valid_paths
            )
            append_evidence.update(
                {
                    path.relative_to(root).as_posix(): revision
                    for path, revision in (state.evidence or {}).items()
                }
            )
            for item in state.findings:
                findings.append({**item, "check": "lock"})

    appended_ids: dict[str, list[int]] = {"DR": [], "PCR": []}
    baseline_ids: dict[str, list[int]] = {"DR": [], "PCR": []}
    for path in baseline_expected:
        kind = _append_kind(path, baseline.paths)
        if kind is not None:
            identifier = re.match(r"(?:DR|PCR)-(?P<number>[0-9]{3})", PurePosixPath(path).name)
            if identifier is not None:
                baseline_ids[kind].append(int(identifier.group("number")))

    # An accepted, uncommitted DR may rely on an approved immutable digest.
    # A git-labelled acceptance must resolve to a real repository object;
    # merely writing forty hexadecimal characters is not evidence.
    for path in sorted(accepted_dr_paths - committed_append_paths):
        revision = append_evidence.get(path, "")
        if not revision.startswith("git:"):
            continue
        try:
            evidence_entries = reader.read(
                revision.removeprefix("git:"), baseline.paths
            )
            if not evidence_entries:
                raise BaselineError("approved revision has no VP artefacts")
        except BaselineError as error:
            valid_append_paths.discard(path)
            findings.append(
                _finding(
                    file=path,
                    record=PurePosixPath(path).name.split("-", 2)[0] + "-"
                    + PurePosixPath(path).name.split("-", 2)[1],
                    message=(
                        "Accepted DR has no immutable repository evidence: "
                        f"{error}."
                    ),
                    remediation=(
                        "Commit the accepted append or cite an existing "
                        "immutable approved revision."
                    ),
                )
            )

    for path in sorted(set(expected) | set(current)):
        baseline_entry = expected.get(path)
        current_entry = current.get(path)
        problem: str | None = None
        if baseline_entry is None:
            kind = _append_kind(path, baseline.paths)
            if (
                isinstance(current_entry, tuple)
                and kind is not None
                and path in valid_append_paths
            ):
                identifier = re.match(
                    r"(?:DR|PCR)-(?P<number>[0-9]{3})",
                    PurePosixPath(path).name,
                )
                if identifier is not None:
                    appended_ids[kind].append(int(identifier.group("number")))
                    continue
                problem = (
                    "is not a complete canonical append-only "
                    f"{kind or 'DR/PCR'} record"
                )
            else:
                problem = "was added outside an append-only DR/PCR collection"
        elif current_entry is None:
            problem = "was deleted or renamed"
        elif isinstance(current_entry, ValueError):
            problem = f"cannot be compared safely ({current_entry})"
        else:
            mode, content = current_entry
            if mode != baseline_entry.mode:
                problem = "changed filesystem type or executable mode"
            elif content != baseline_entry.content:
                problem = "rewrites content preserved at partial acceptance"
            elif path in post_baseline_paths:
                kind = _append_kind(path, baseline.paths)
                if path not in valid_append_paths:
                    problem = (
                        "is not a complete canonical append-only "
                        f"{kind or 'DR/PCR'} record"
                    )
                elif kind is not None:
                    identifier = re.match(
                        r"(?:DR|PCR)-(?P<number>[0-9]{3})",
                        PurePosixPath(path).name,
                    )
                    if identifier is not None:
                        appended_ids[kind].append(
                            int(identifier.group("number"))
                        )
        if problem is not None:
            findings.append(
                _finding(
                    file=path,
                    record=vp_id,
                    message=(
                        f"{path} {problem}; the shared VP basis is append-only "
                        "after partial acceptance."
                    ),
                    remediation=(
                        "Restore the accepted content and append a complete "
                        "canonical DR or PCR without rewriting earlier records."
                    ),
                )
            )

    for kind in ("DR", "PCR"):
        additions = sorted(appended_ids[kind])
        if not additions:
            continue
        expected_next = max(baseline_ids[kind], default=0) + 1
        expected_numbers = list(range(expected_next, expected_next + len(additions)))
        if additions != expected_numbers:
            collection = "revisions" if kind == "DR" else "changes"
            owner = next(
                (
                    scope
                    for scope in baseline.paths
                    if scope.startswith(
                        "docs/discovery/" if kind == "DR" else "docs/requirements/"
                    )
                ),
                baseline.paths[0],
            )
            findings.append(
                _finding(
                    file=f"{owner}/{collection}",
                    record=vp_id,
                    message=(
                        f"New {kind} IDs are not an append-only contiguous sequence."
                    ),
                    remediation=(
                        f"Retain prior {kind} records and allocate "
                        f"{kind}-{expected_next:03d} next."
                    ),
                )
            )
    return sorted(set(expected) | set(current))


def _compare_partial_vp_digests(
    *,
    root: Path,
    baseline: VpBaseline,
    vp_id: str,
    findings: list[Finding],
) -> list[str]:
    """Protect the accepted shared basis while admitting only DR/PCR additions.

    The TH3 checkpoint has no commit.  Its per-entry SHA-256 map is therefore
    the deterministic baseline for existing shared artefacts.  New files are
    still allowed only at the canonical append-only locations and only after
    their owner validator accepts them.
    """

    expected = baseline.entry_sha256 or {}
    expected_modes = baseline.entry_modes or {}
    current: dict[str, tuple[str, bytes] | ValueError] = {}
    for scope in baseline.paths:
        current.update(_scan_scope(root, scope))
    for path, digest in sorted(expected.items()):
        entry = current.get(path)
        invalid = (
            SHA256_PATTERN.fullmatch(digest) is None
            or expected_modes.get(path) not in {"100644", "100755"}
            or not isinstance(entry, tuple)
            or (isinstance(entry, tuple) and entry[0] != expected_modes.get(path))
            or hashlib.sha256(entry[1]).hexdigest() != digest
        )
        if invalid:
            findings.append(
                _finding(
                    file=path,
                    record=vp_id,
                    message=(
                        f"{path} rewrites content preserved at partial acceptance; "
                        "the shared VP basis is append-only after partial acceptance."
                    ),
                    remediation=(
                        "Restore the accepted content and append a complete "
                        "canonical DR or PCR without rewriting earlier records."
                    ),
                )
            )

    valid_appends: set[str] = set()
    discovery = next(
        (scope for scope in baseline.paths if scope.startswith("docs/discovery/")),
        None,
    )
    if discovery is not None:
        state = gates.validate_discovery_revision_collection(
            root=root, dossier=root / discovery, vp=vp_id
        )
        valid_appends.update(
            path.relative_to(root).as_posix() for path in state.valid_paths
        )
        findings.extend({**item, "check": "lock"} for item in state.findings)
    requirements = next(
        (scope for scope in baseline.paths if scope.startswith("docs/requirements/")),
        None,
    )
    if requirements is not None:
        state = gates.validate_product_change_collection(
            root=root, requirements=root / requirements, vp=vp_id
        )
        valid_appends.update(
            path.relative_to(root).as_posix() for path in state.valid_paths
        )
        findings.extend({**item, "check": "lock"} for item in state.findings)

    for path, entry in sorted(current.items()):
        if path in expected:
            continue
        if (
            isinstance(entry, tuple)
            and _append_kind(path, baseline.paths) is not None
            and path in valid_appends
        ):
            continue
        findings.append(
            _finding(
                file=path,
                record=vp_id,
                message=(
                    f"{path} was added outside an append-only DR/PCR collection; "
                    "the shared VP basis is append-only after partial acceptance."
                ),
                remediation=(
                    "Restore the accepted content and append a complete canonical "
                    "DR or PCR without rewriting earlier records."
                ),
            )
        )
    return sorted(current)


def _compare_pinned_file(
    *,
    root: Path,
    path: str,
    sha256: str,
    record: str,
    findings: list[Finding],
) -> list[str]:
    """Compare a legacy file retained before it had a committed baseline."""

    problem: str | None = None
    try:
        mode, content = _mode_and_content(root / path, root)
        if mode != "100644":
            problem = "changed filesystem type or executable mode"
        elif hashlib.sha256(content).hexdigest() != sha256:
            problem = "content differs from its accepted baseline"
    except ValueError as error:
        problem = f"cannot be compared safely ({error})"
    if problem is not None:
        findings.append(
            _finding(
                file=path,
                record=record,
                message=(
                    f"{path} {problem}; it is an immutable locked-theme snapshot."
                ),
                remediation="Restore the accepted archive snapshot byte-for-byte.",
            )
        )
    return [path]


def _scope_sha256(
    entries: Mapping[str, tuple[str, bytes] | ValueError],
) -> str | None:
    """Return a deterministic digest of every path, mode, and byte payload."""

    lines: list[bytes] = []
    for path in sorted(entries):
        entry = entries[path]
        if isinstance(entry, ValueError):
            return None
        mode, content = entry
        lines.append(
            path.encode("utf-8")
            + b":"
            + mode.encode("ascii")
            + b":"
            + hashlib.sha256(content).hexdigest().encode("ascii")
            + b"\n"
        )
    return hashlib.sha256(b"".join(lines)).hexdigest()


def _status_only_supersession_digest(
    *,
    expected_sha256: str,
    current: Mapping[str, tuple[str, bytes] | ValueError],
    root: Path,
    current_adr: str,
) -> bool:
    """Apply the ADR exception while keeping a digest-only baseline exact."""

    if len(current) != 1:
        return False
    path, entry = next(iter(current.items()))
    if isinstance(entry, ValueError):
        return False
    _mode, content = entry
    matches = list(STATUS_VALUE.finditer(content))
    if len(matches) != 1:
        return False
    match = matches[0]
    replacement = match.group("value")
    replacement_id = re.fullmatch(rb"Superseded by (ADR-[0-9]{3})", replacement)
    if replacement_id is None:
        return False
    restored = (
        content[: match.start("value")]
        + b"Accepted"
        + content[match.end("value") :]
    )
    restored_entry = (
        path.encode("utf-8")
        + b":"
        + _mode.encode("ascii")
        + b":"
        + hashlib.sha256(restored).hexdigest().encode("ascii")
        + b"\n"
    )
    if hashlib.sha256(restored_entry).hexdigest() != expected_sha256:
        return False
    identifier = replacement_id.group(1).decode("ascii")
    matches = list((root / "docs/ADRs").glob(f"{identifier}-*.md"))
    return len(matches) == 1 and _canonical_replacement_adr(
        matches[0],
        root=root,
        replacement_id=identifier,
        superseded_id=current_adr,
    )


def _compare_pinned_scope(
    *,
    root: Path,
    scope: str,
    sha256: str,
    record: str,
    kind: str,
    findings: list[Finding],
) -> list[str]:
    """Compare an uncommitted acceptance baseline without weakening locks.

    A scope digest includes every path and mode, so adding, deleting, renaming,
    or changing an artefact necessarily changes the pinned value.  This is the
    deterministic alternative where the human acceptance boundary intentionally
    has no Git commit to serve as its immutable source.
    """

    current = _scan_scope(root, scope)
    observed = _scope_sha256(current)
    expected = sha256.removeprefix("sha256:")
    superseded = (
        kind == "adr"
        and SHA256_PATTERN.fullmatch(expected) is not None
        and _status_only_supersession_digest(
            expected_sha256=expected,
            current=current,
            root=root,
            current_adr=record,
        )
    )
    if (
        SHA256_PATTERN.fullmatch(expected) is None
        or observed is None
        or observed != expected
    ) and not superseded:
        description = "locked ADR body" if kind == "adr" else "locked theme artefact"
        remediation = (
            "Restore the ADR body. Only an exact Status change to "
            "`Superseded by ADR-<NNN>` with a complete, Accepted canonical "
            "replacement ADR that explicitly supersedes this decision is permitted."
            if kind == "adr"
            else "Restore the accepted theme artefacts byte-for-byte."
        )
        findings.append(
            _finding(
                file=scope,
                record=record,
                message=(
                    f"{scope} differs from its deterministic acceptance "
                    f"baseline; it is a {description}."
                ),
                remediation=remediation,
            )
        )
    return sorted(current)


def validate_repository(
    repository_root: PathValue,
    *,
    baselines: Baselines = LEGACY_BASELINES,
    baseline_reader: BaselineReader | None = None,
) -> ValidationResult:
    """Build and validate the repository's split-lock manifest."""

    root = Path(repository_root).resolve()
    findings: list[Finding] = []
    themes = _themes_from_backlog(root, baselines, findings)
    reader = baseline_reader if baseline_reader is not None else GitBaselineReader(root)
    accepted = {
        theme_id
        for theme_id, theme in themes.items()
        if theme.get("locked") is True
    }
    accepted.update(baselines.themes)

    theme_manifest: list[dict[str, object]] = []
    for theme_id in sorted(accepted, key=lambda item: int(item[2:])):
        baseline = baselines.themes.get(theme_id)
        theme = themes.get(theme_id)
        if baseline is None:
            archive = (
                str(theme.get("_archive-ref"))
                if theme is not None and isinstance(theme.get("_archive-ref"), str)
                else f"{ARCHIVE_DIRECTORY}/{theme_id}.yaml"
            )
            findings.append(
                _finding(
                    file=archive,
                    record=theme_id,
                    message=f"{theme_id} is locked but has no immutable baseline revision.",
                    remediation="Record its accepted full commit ID and exact lock scopes.",
                )
            )
            theme_manifest.append(
                {
                    "id": theme_id,
                    "status": "locked",
                    "baseline_revision": None,
                    "artefacts": [],
                }
            )
            continue

        if baseline.revision is not None:
            theme_files = _compare(
                root=root,
                reader=reader,
                revision=baseline.revision,
                scopes=(baseline.theme_path,),
                record=theme_id,
                kind="theme",
                findings=findings,
            )
            theme_evidence = baseline.revision
        elif baseline.theme_sha256 is not None:
            theme_files = _compare_pinned_scope(
                root=root,
                scope=baseline.theme_path,
                sha256=baseline.theme_sha256,
                record=theme_id,
                kind="theme",
                findings=findings,
            )
            theme_evidence = f"sha256:{baseline.theme_sha256}"
        else:
            findings.append(
                _finding(
                    file=baseline.theme_path,
                    record=theme_id,
                    message=f"{theme_id} has no immutable theme baseline.",
                    remediation="Record its accepted full commit ID or deterministic scope digest.",
                )
            )
            theme_files = []
            theme_evidence = None
        if baseline.archive_sha256 is not None:
            archive_files = _compare_pinned_file(
                root=root,
                path=baseline.archive_path,
                sha256=baseline.archive_sha256,
                record=theme_id,
                findings=findings,
            )
            archive_evidence = f"sha256:{baseline.archive_sha256}"
        else:
            archive_revision = baseline.archive_revision or baseline.revision
            archive_files = _compare(
                root=root,
                reader=reader,
                revision=archive_revision,
                scopes=(baseline.archive_path,),
                record=theme_id,
                kind="archive",
                findings=findings,
            )
            archive_evidence = archive_revision
        declared_stories = set(_story_paths(theme or {}))
        baseline_stories = {
            path for path in theme_files if "/stories/" in path
        }
        for path in sorted(declared_stories - baseline_stories):
            findings.append(
                _finding(
                    file=path,
                    record=theme_id,
                    message=f"{path} is not part of the accepted {theme_id} baseline.",
                    remediation="Restore the immutable archive story mapping.",
                )
            )
        theme_manifest.append(
            {
                "id": theme_id,
                "status": "locked",
                "baseline_revision": theme_evidence,
                "archive_baseline": archive_evidence,
                "theme_path": baseline.theme_path,
                "archive_path": baseline.archive_path,
                "artefacts": sorted(set(theme_files + archive_files)),
            }
        )

    adr_mapping = _adr_theme_mapping(root, themes)
    locked_adrs = {
        adr_id
        for adr_id, dependent_themes in adr_mapping.items()
        if dependent_themes & accepted
    }
    locked_adrs.update(baselines.adrs)
    adr_manifest: list[dict[str, object]] = []
    for adr_id in sorted(locked_adrs):
        baseline = baselines.adrs.get(adr_id)
        dependents = sorted(adr_mapping.get(adr_id, set()) & accepted)
        if baseline is None:
            findings.append(
                _finding(
                    file=f"docs/ADRs/{adr_id}-*.md",
                    record=adr_id,
                    message=f"{adr_id} is locked but has no immutable body baseline.",
                    remediation="Record the first dependent theme's accepted commit ID.",
                )
            )
            artefacts: list[str] = []
            revision: str | None = None
        elif baseline.revision is not None:
            artefacts = _compare(
                root=root,
                reader=reader,
                revision=baseline.revision,
                scopes=(baseline.path,),
                record=adr_id,
                kind="adr",
                findings=findings,
                allow_adr_status=True,
            )
            revision = baseline.revision
        elif baseline.sha256 is not None:
            artefacts = _compare_pinned_scope(
                root=root,
                scope=baseline.path,
                sha256=baseline.sha256,
                record=adr_id,
                kind="adr",
                findings=findings,
            )
            revision = f"sha256:{baseline.sha256}"
        else:
            findings.append(
                _finding(
                    file=baseline.path,
                    record=adr_id,
                    message=f"{adr_id} is locked but has no immutable body baseline.",
                    remediation="Record the first dependent theme's accepted commit ID or body digest.",
                )
            )
            artefacts = []
            revision = None
        adr_manifest.append(
            {
                "id": adr_id,
                "status": "locked",
                "dependent_accepted_themes": dependents,
                "baseline_revision": revision,
                "artefacts": artefacts,
            }
        )

    vp_mappings, vp_paths = _vp_mappings_and_paths(root, themes)
    for vp_id, baseline in baselines.vps.items():
        vp_paths.setdefault(vp_id, set()).update(baseline.paths)
        # Accepted baseline mappings are historical facts. Removing them from
        # mutable working files cannot make a partial or final lock disappear.
        vp_mappings.setdefault(vp_id, set()).update(baseline.mapped_themes)
    vp_manifest: list[dict[str, object]] = []
    vp_ids = set(vp_mappings) | set(baselines.vps)
    for vp_id in sorted(vp_ids, key=lambda item: int(item[2:])):
        mapped = sorted(vp_mappings.get(vp_id, set()), key=lambda item: int(item[2:]))
        unaccepted = sorted(set(mapped) - accepted, key=lambda item: int(item[2:]))
        accepted_mapped = sorted(
            set(mapped) & accepted, key=lambda item: int(item[2:])
        )
        paths = sorted(vp_paths.get(vp_id, set()))
        baseline = baselines.vps.get(vp_id)
        baseline_mapped = set(baseline.mapped_themes) if baseline else set()
        was_fully_locked = baseline is not None and (
            not baseline_mapped or baseline_mapped <= accepted
        )
        newly_mapped = (
            set(mapped) - baseline_mapped
            if baseline_mapped
            else set(unaccepted)
        )

        if was_fully_locked:
            if newly_mapped:
                additions = ", ".join(
                    sorted(newly_mapped, key=lambda item: int(item[2:]))
                )
                findings.append(
                    _finding(
                        file=BACKLOG_PATH,
                        record=vp_id,
                        message=(
                            f"{vp_id} was fully locked before mapped theme "
                            f"{additions} was added; a mapping change cannot "
                            "reopen its accepted shared basis."
                        ),
                        remediation=(
                            "Remove the new mapping and use a new VP, or use an "
                            "applicable PCR before the original VP reaches final lock."
                        ),
                    )
                )
            artefacts = _compare(
                root=root,
                reader=reader,
                revision=baseline.revision,
                scopes=baseline.paths,
                record=vp_id,
                kind="vp",
                findings=findings,
            )
            vp_manifest.append(
                {
                    "id": vp_id,
                    "status": "unlocked" if unaccepted else "locked",
                    "mapped_themes": mapped,
                    **(
                        {"accepted_themes": accepted_mapped}
                        if unaccepted
                        else {}
                    ),
                    "artefacts": artefacts,
                    "baseline_revision": baseline.revision,
                    **(
                        {
                            "reason": "unaccepted mapped themes: "
                            + ", ".join(unaccepted)
                        }
                        if unaccepted
                        else {}
                    ),
                }
            )
            continue

        if unaccepted:
            if not accepted_mapped:
                vp_manifest.append(
                    {
                        "id": vp_id,
                        "status": "unlocked",
                        "mapped_themes": mapped,
                        "accepted_themes": accepted_mapped,
                        "artefacts": paths,
                        "baseline_revision": (
                            baseline.revision if baseline is not None else None
                        ),
                        "reason": "unaccepted mapped themes: " + ", ".join(unaccepted),
                    }
                )
                continue
            if baseline is None:
                findings.append(
                    _finding(
                        file=paths[0] if paths else vp_id,
                        record=vp_id,
                        message=(
                            f"{vp_id} has accepted mapped themes but no immutable "
                            "partial-acceptance baseline."
                        ),
                        remediation=(
                            "Record the first accepted theme's peeled full commit "
                            "ID, complete mapped-theme set, and shared VP scopes."
                        ),
                    )
                )
                artefacts = paths
                revision = None
            elif baseline.revision is not None:
                artefacts = _compare_partial_vp(
                    root=root,
                    reader=reader,
                    baseline=baseline,
                    vp_id=vp_id,
                    findings=findings,
                )
                revision = baseline.revision
            elif baseline.entry_sha256 is not None:
                artefacts = _compare_partial_vp_digests(
                    root=root,
                    baseline=baseline,
                    vp_id=vp_id,
                    findings=findings,
                )
                revision = "sha256:per-entry"
            else:
                findings.append(
                    _finding(
                        file=paths[0] if paths else vp_id,
                        record=vp_id,
                        message=(
                            f"{vp_id} has accepted mapped themes but no immutable "
                            "partial-acceptance baseline."
                        ),
                        remediation=(
                            "Record the first accepted theme's peeled full commit "
                            "ID or deterministic shared-artifact digests."
                        ),
                    )
                )
                artefacts = paths
                revision = None
            vp_manifest.append(
                {
                    "id": vp_id,
                    "status": "unlocked",
                    "mapped_themes": mapped,
                    "accepted_themes": accepted_mapped,
                    "artefacts": artefacts,
                    "baseline_revision": revision,
                    "reason": "unaccepted mapped themes: " + ", ".join(unaccepted),
                }
            )
            continue

        if baseline is None:
            findings.append(
                _finding(
                    file=paths[0] if paths else vp_id,
                    record=vp_id,
                    message=f"{vp_id} is fully accepted but has no immutable shared baseline.",
                    remediation="Record the final mapped theme's accepted commit and scopes.",
                )
            )
            artefacts = paths
            revision = None
        else:
            artefacts = _compare(
                root=root,
                reader=reader,
                revision=baseline.revision,
                scopes=baseline.paths,
                record=vp_id,
                kind="vp",
                findings=findings,
            )
            revision = baseline.revision
        vp_manifest.append(
            {
                "id": vp_id,
                "status": "locked",
                "mapped_themes": mapped,
                "artefacts": artefacts,
                "baseline_revision": revision,
            }
        )

    findings.sort(
        key=lambda finding: (
            str(finding["file"]),
            str(finding["record"]),
            str(finding["message"]),
        )
    )
    manifest: dict[str, object] = {
        "themes": theme_manifest,
        "adrs": adr_manifest,
        "vps": vp_manifest,
    }
    return ValidationResult(tuple(findings), manifest)


__all__ = [
    "ArtefactBaseline",
    "BaselineEntry",
    "BaselineError",
    "BaselineReader",
    "Baselines",
    "GitBaselineReader",
    "LEGACY_BASELINES",
    "ThemeBaseline",
    "ValidationResult",
    "VpBaseline",
    "validate_repository",
]
