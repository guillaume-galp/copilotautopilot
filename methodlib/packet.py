"""Backlog dispatch projection and mission packet validation."""

from __future__ import annotations

import hashlib
import copy
import json
import math
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Mapping, Sequence, cast

import yaml

from methodlib import exits, trace
from methodlib.backlog import (
    BACKLOG_PATH,
    EPIC_ID,
    MAX_YAML_BYTES,
    STORY_ID,
    UniqueKeyLoader,
    validate_repository,
)


Finding = dict[str, object]
PathValue = str | os.PathLike[str]

PACKET_VERSION = 1
DEFAULT_RUNTIME_DIRECTORY = Path("docs/plan/runtime/packets")
MAX_PACKET_BYTES = 2 * 1024 * 1024
MAX_SOURCE_FILES = 256
MAX_RECONCILIATIONS = 32
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
PACKET_TASK_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
AUTHORIZATION_HASH_PATTERN = re.compile(r"sha256:[0-9a-f]{64}")
PLANNING_AGENT_ROLES = frozenset({"product-owner", "architect", "reviewer"})
STORY_STATUS_TRANSITIONS = frozenset(
    {
        ("todo", "in-progress"),
        ("in-progress", "done"),
        ("in-progress", "blocked"),
        ("in-progress", "failed"),
        ("blocked", "in-progress"),
        ("failed", "in-progress"),
    }
)
PARENT_STATUS_TRANSITIONS = frozenset(
    {
        ("todo", "in-progress"),
        ("in-progress", "done"),
    }
)
RECONCILIATION_FIELDS = {
    "from-revision",
    "to-revision",
    "from-backlog-sha256",
    "to-backlog-sha256",
    "from-status",
    "to-status",
    "timestamp",
    "reason",
}
RECONCILIATION_REASONS = frozenset(
    {
        "status-transition",
        "evidence-update",
        "parent-completion",
        "status-transition+evidence-update",
    }
)
STATUS_FIELDS = {"theme", "epic", "story"}
AUTHORIZATION_FIELDS = (
    "mission-packet-version",
    "packet-kind",
    "story",
    "backlog",
    "theme",
    "epic",
    "dependencies",
    "risk",
    "model-route",
    "verification",
    "review-profile",
    "evidence-requirements",
    "evidence-snapshot",
    "evidence-current",
    "mode",
    "workspace",
    "required-gates",
    "required-skills",
    "scope",
    "traceability",
    "trace-metadata",
    "expected-result-locations",
    "integration-boundary",
    "acceptance-criteria",
    "story-frontmatter",
    "required-report",
    "expansions",
    "sources",
    "composite-hash",
    "reconciliations",
)
PACKET_FIELDS = {
    "mission-packet-version",
    "packet-kind",
    "task",
    "mode",
    "trace-id",
    "generated-at",
    "story",
    "backlog",
    "theme",
    "epic",
    "dependencies",
    "risk",
    "model-route",
    "verification",
    "review-profile",
    "evidence-requirements",
    "evidence-snapshot",
    "evidence-current",
    "workspace",
    "scope",
    "story-frontmatter",
    "traceability",
    "required-skills",
    "required-gates",
    "acceptance-criteria",
    "expected-result-locations",
    "sources",
    "required-report",
    "expansions",
    "integration-boundary",
    "composite-hash",
    "authorization-hash",
    "reconciliations",
}
EPIC_PACKET_FIELDS = {"work-item", "acceptance-children", "backlog-snapshot"}


def _epic_packet(packet: Mapping[object, object]) -> bool:
    return "work-item" in packet


def _unit_key(packet: Mapping[object, object]) -> str:
    return "work-item" if _epic_packet(packet) else "story"


def _unit(packet: Mapping[object, object]) -> object:
    return packet.get(_unit_key(packet))


def _parent_levels(packet: Mapping[object, object]) -> tuple[str, ...]:
    return ("theme",) if _epic_packet(packet) else ("theme", "epic")


@dataclass(frozen=True)
class PacketResult:
    exit_code: int
    payload: dict[str, object]
    diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True)
class StoryCandidate:
    theme: Mapping[object, object]
    epic: Mapping[object, object]
    story: Mapping[object, object]
    theme_index: int
    epic_index: int
    story_index: int

    @property
    def story_id(self) -> str:
        return str(self.story["id"])

    @property
    def epic_first(self) -> bool:
        return self.theme.get("schema-version") == 3

    @property
    def unit_key(self) -> str:
        return "work-item" if self.epic_first else "story"


@dataclass(frozen=True)
class CompletionIndex:
    themes: frozenset[str]
    epics: frozenset[str]
    stories: frozenset[str]


@dataclass(frozen=True)
class StoryAuthority:
    story_id: str
    title: str
    story_type: str
    priority: str | None
    size: str | None
    acceptance_criteria: tuple[object, ...]
    agents: tuple[str, ...]
    skills: tuple[str, ...]
    dependencies: tuple[str, ...]
    traceability: Mapping[str, tuple[str, ...]]


EVIDENCE_KEYS = ("packets", "verification", "review", "gitflow", "usage")
NOT_APPLICABLE_EVIDENCE = re.compile(
    r"not-applicable: (?P<rationale>\S(?:.{0,254}\S)?)",
    re.IGNORECASE,
)
FAILURE_EVIDENCE = re.compile(
    r"\b(?:fail(?:ed|ure|ures|ing)?|errors?|skipped|not\s+pass(?:ed)?)\b",
    re.IGNORECASE,
)
REVIEW_APPROVAL_TOKENS = frozenset({"approve", "approved"})
GITFLOW_SUCCESS_TOKENS = frozenset({"committed", "merged", "squash-merged"})
GITFLOW_FAILURE_EVIDENCE = re.compile(
    r"\b(?:not\s+(?:committed|merged)|"
    r"fail(?:ed|ure|ures|ing)?|errors?|skipped)\b",
    re.IGNORECASE,
)
STORY_FRONTMATTER_REQUIRED_KEYS = frozenset(
    {
        "id",
        "title",
        "type",
        "agents",
        "skills",
        "traceability",
        "acceptance-criteria",
        "depends-on",
    }
)
STORY_FRONTMATTER_OPTIONAL_KEYS = frozenset({"priority", "size"})


class StrictPacketLoader(UniqueKeyLoader):
    """Duplicate-free safe loader that rejects every YAML alias."""

    def compose_node(
        self,
        parent: yaml.nodes.Node | None,
        index: object,
    ) -> yaml.nodes.Node:
        if self.check_event(yaml.AliasEvent):
            event = self.get_event()
            raise yaml.composer.ComposerError(
                "while composing a packet",
                None,
                f"YAML aliases are not allowed: *{event.anchor}",
                event.start_mark,
            )
        return super().compose_node(parent, index)


class PacketDumper(yaml.SafeDumper):
    """Emit the canonical packet tree without YAML aliases."""

    def ignore_aliases(self, data: object) -> bool:
        return True


def project_next(
    repository_root: PathValue,
    *,
    expected_revision: int | None = None,
) -> PacketResult:
    """Project one executable epic, or a legacy story, from the active backlog."""

    root = _repository_root(repository_root)
    if root is None:
        return _failed(
            "projection-refused",
            "repository root is missing or unreadable",
            "Run from a readable repository checkout.",
        )
    try:
        document, document_error = _load_backlog(root)
        if document_error is not None:
            return document_error
        backlog = cast(Mapping[object, object], document["backlog"])
        current_revision = backlog.get("revision")
        if (
            expected_revision is not None
            and isinstance(current_revision, int)
            and current_revision != expected_revision
        ):
            return _failed(
                "STALE",
                (
                    f"backlog revision is {current_revision}, expected "
                    f"{expected_revision}"
                ),
                "Regenerate the projection from the current backlog revision.",
            )
        candidate, refusals = _next_candidate(root, backlog)
        if candidate is None:
            return _failed(
                "projection-refused",
                "no dispatchable work item found",
                "Resolve the listed status, lock, or dependency blockers.",
                refusals,
                backlog=backlog,
                root=root,
            )
        projection = _projection_payload(root, backlog, candidate)
    except (
        OSError,
        UnicodeError,
        RuntimeError,
        ValueError,
        TypeError,
        KeyError,
        yaml.YAMLError,
    ) as error:
        return _failed(
            "projection-refused",
            f"projection could not read authoritative inputs: {error}",
            "Restore readable backlog, archive, and story source files.",
            action="project",
        )
    return PacketResult(
        exits.SUCCESS,
        {
            "command": "packet",
            "action": "project",
            "status": "ok",
            "projection": projection,
        },
    )


def build_packet(
    repository_root: PathValue,
    *,
    task: str,
    story_id: str | None = None,
    epic_id: str | None = None,
    mode: str,
    implementation_root: str,
    allowed_implementation_root: str,
    planning_roots: Sequence[str],
    output: str | None = None,
    trace_id: str | None = None,
    expected_revision: int | None = None,
) -> PacketResult:
    """Build a packet while framing every filesystem race as one JSON result."""

    try:
        if story_id is not None and STORY_ID.fullmatch(story_id) is None:
            return _failed(
                "packet-refused", "legacy story selector requires TH<n>.E<m>.US<l>",
                "Use --epic for an executable epic.",
            )
        if epic_id is not None and (
            story_id is not None or EPIC_ID.fullmatch(epic_id) is None
        ):
            return _failed(
                "packet-refused", "select exactly one canonical epic or legacy story",
                "Use --epic TH<n>.E<m> or --story TH<n>.E<m>.US<l>.",
            )
        return _build_packet_impl(
            repository_root,
            task=task,
            story_id=epic_id or story_id,
            mode=mode,
            implementation_root=implementation_root,
            allowed_implementation_root=allowed_implementation_root,
            planning_roots=planning_roots,
            output=output,
            trace_id=trace_id,
            expected_revision=expected_revision,
        )
    except (
        OSError,
        UnicodeError,
        RuntimeError,
        ValueError,
        TypeError,
        KeyError,
        yaml.YAMLError,
    ) as error:
        return _failed(
            "packet-refused",
            f"packet build could not access authoritative inputs: {error}",
            "Restore stable readable sources and writable runtime directories.",
            action="build",
        )


def _build_packet_impl(
    repository_root: PathValue,
    *,
    task: str,
    story_id: str | None,
    mode: str,
    implementation_root: str,
    allowed_implementation_root: str,
    planning_roots: Sequence[str],
    output: str | None = None,
    trace_id: str | None = None,
    expected_revision: int | None = None,
) -> PacketResult:
    """Build one validated mission packet for a dependency-eligible work item."""

    root = _repository_root(repository_root)
    if root is None:
        return _failed(
            "packet-refused",
            "repository root is missing or unreadable",
            "Run from a readable repository checkout.",
        )
    if PACKET_TASK_PATTERN.fullmatch(task) is None:
        return _failed(
            "packet-refused",
            "task must match [A-Za-z0-9][A-Za-z0-9._-]{0,79}",
            "Use a short stable task identifier.",
        )
    if story_id is not None and not (
        STORY_ID.fullmatch(story_id) or EPIC_ID.fullmatch(story_id)
    ):
        return _failed(
            "packet-refused",
            "story must have the form TH<n>.E<m>.US<l>",
            "Pass a fully-qualified story ID.",
        )
    if mode not in {"developer", "planning"}:
        return _failed(
            "packet-refused",
            "mode must be developer or planning",
            "Select the mission capability grant explicitly.",
        )

    document, document_error = _load_backlog(root)
    if document_error is not None:
        return document_error
    backlog = cast(Mapping[object, object], document["backlog"])
    current_revision = backlog.get("revision")
    if (
        expected_revision is not None
        and isinstance(current_revision, int)
        and current_revision != expected_revision
    ):
        return _failed(
            "STALE",
            (
                f"backlog revision is {current_revision}, expected "
                f"{expected_revision}"
            ),
            "Regenerate the mission packet from the current backlog revision.",
        )

    selected, refusals = _select_candidate(root, backlog, story_id)
    if selected is None:
        return _failed(
            "packet-refused",
            "work item is not dispatchable",
            "Select the projected epic or legacy story, or resolve its blockers.",
            refusals,
            backlog=backlog,
            root=root,
        )
    if selected.epic_first:
        trace_result = trace.validate_repository(root)
        if not trace_result.valid:
            return _failed(
                "packet-refused", "epic trace does not resolve accepted sources",
                "Resolve every declared trace reference before dispatch.",
                list(trace_result.findings),
            )

    try:
        authority = _story_authority(
            root,
            str(selected.story["file"]),
            expected_story=selected.story,
        )
        authorized_mode = _authorized_mode(authority.agents)
    except (OSError, UnicodeError, RuntimeError, ValueError, yaml.YAMLError) as error:
        return _failed(
            "packet-refused",
            str(error),
            "Restore the story frontmatter with valid agents and acceptance criteria.",
        )
    if authorized_mode != mode:
        return _failed(
            "packet-refused",
            (
                f"story agents authorize {authorized_mode or 'no supported mode'}, "
                f"not requested {mode} mode"
            ),
            "Select the mode authorized by the authoritative story agents.",
        )

    roots_result = _workspace_payload(
        root,
        planning_roots=planning_roots,
        implementation_root=implementation_root,
        allowed_implementation_root=allowed_implementation_root,
        mode=mode,
    )
    if roots_result.exit_code != exits.SUCCESS:
        return roots_result
    workspace = roots_result.payload["workspace"]
    assert isinstance(workspace, dict)

    try:
        packet = _packet_payload(
            root,
            backlog,
            selected,
            task=task,
            mode=mode,
            trace_id=trace_id or f"{selected.story_id}:{task}",
            workspace=workspace,
            authority=authority,
        )
    except (OSError, UnicodeError, RuntimeError, ValueError, yaml.YAMLError) as error:
        return _failed(
            "packet-refused",
            str(error),
            "Restore the packet source file or repair the backlog story file.",
        )
    destination = _packet_destination(
        root,
        selected.story_id,
        task,
        output=output,
    )
    if destination is None:
        return _failed(
            "packet-refused",
            "output path is not the canonical packet location",
            "Use docs/plan/runtime/packets/<story-id>/<task>.yaml exactly.",
        )
    try:
        serialized = _serialize_packet(packet)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            serialized,
            encoding="utf-8",
        )
    except OSError as error:
        return _failed(
            "packet-refused",
            f"packet cannot be written: {error}",
            "Choose a writable runtime packet destination.",
        )

    return PacketResult(
        exits.SUCCESS,
        {
            "command": "packet",
            "action": "build",
            "status": "ok",
            "packet": _display(destination, root),
            selected.unit_key: selected.story_id,
            "backlog_revision": backlog["revision"],
            "backlog_sha256": cast(Mapping[str, object], packet["backlog"])[
                "sha256"
            ],
            "trace_id": packet["trace-id"],
            "authorization_hash": packet["authorization-hash"],
        },
    )


def verify_packet(
    repository_root: PathValue,
    *,
    packet_path: str,
    allowed_implementation_root: str,
    expected_authorization_hash: str,
) -> PacketResult:
    """Validate a packet and reject stale backlog/source revisions."""

    root = _repository_root(repository_root)
    if root is None:
        return _failed(
            "packet-invalid",
            "repository root is missing or unreadable",
            "Run from a readable repository checkout.",
        )
    expected_allowed = _resolve_existing_directory(
        allowed_implementation_root,
        base=root,
    )
    if expected_allowed is None:
        return _failed(
            "packet-invalid",
            (
                "caller allowed implementation root is missing, unreadable, "
                "or not a directory"
            ),
            "Provide the caller-authorized implementation boundary.",
            action="verify",
        )
    try:
        packet, packet_error = _load_packet(root, packet_path)
        if packet_error is not None:
            return packet_error
        backlog_document, backlog_error = _load_backlog(root)
        if backlog_error is not None:
            return _verification_load_failure("verify", backlog_error)
        current_backlog = cast(
            Mapping[object, object],
            backlog_document["backlog"],
        )
        findings = _packet_findings(
            root,
            packet,
            current_backlog,
            expected_allowed_root=expected_allowed,
            expected_authorization_hash=expected_authorization_hash,
            packet_path=packet_path,
        )
    except (
        OSError,
        UnicodeError,
        RuntimeError,
        ValueError,
        TypeError,
        KeyError,
        yaml.YAMLError,
    ) as error:
        return _failed(
            "packet-invalid",
            f"packet verification could not read authoritative inputs: {error}",
            "Restore readable packet, backlog, archive, and source files.",
            action="verify",
        )
    status = "ok" if not findings else "STALE" if _has_stale(findings) else "failed"
    exit_code = exits.SUCCESS if not findings else exits.VALIDATION_FAILURE
    diagnostics = tuple(
        f"method packet verify: {finding['message']}" for finding in findings
    )
    return PacketResult(
        exit_code,
        {
            "command": "packet",
            "action": "verify",
            "status": status,
            _unit_key(packet): _story_value(packet),
            "findings": findings,
        },
        diagnostics,
    )


def preflight_packet(
    repository_root: PathValue,
    *,
    packet_path: str,
    allowed_implementation_root: str,
    expected_authorization_hash: str,
) -> PacketResult:
    """Verify packet freshness and workspace/capability access before dispatch."""

    root = _repository_root(repository_root)
    if root is None:
        return _failed(
            "preflight-refused",
            "repository root is missing or unreadable",
            "Run from a readable repository checkout.",
        )
    expected_allowed = _resolve_existing_directory(
        allowed_implementation_root,
        base=root,
    )
    if expected_allowed is None:
        return _failed(
            "preflight-refused",
            (
                "caller allowed implementation root is missing, unreadable, "
                "or not a directory"
            ),
            "Provide the caller-authorized implementation boundary.",
            action="preflight",
        )
    try:
        packet, packet_error = _load_packet(root, packet_path)
        if packet_error is not None:
            return packet_error
        backlog_document, backlog_error = _load_backlog(root)
        if backlog_error is not None:
            return _verification_load_failure("preflight", backlog_error)
        current_backlog = cast(
            Mapping[object, object],
            backlog_document["backlog"],
        )
        findings = _packet_findings(
            root,
            packet,
            current_backlog,
            expected_allowed_root=expected_allowed,
            expected_authorization_hash=expected_authorization_hash,
            packet_path=packet_path,
        )
        findings.extend(
            _workspace_findings(
                root,
                packet,
                expected_allowed_root=expected_allowed,
            )
        )
        if _epic_packet(packet) and _nested(packet, "work-item", "status") not in {
            "todo", "in-progress",
        }:
            findings.append(_finding(
                "packet", "epic-status", "epic is not dispatchable",
                "Recover failed/blocked epics explicitly; do not redispatch completed epics.",
            ))
    except (
        OSError,
        UnicodeError,
        RuntimeError,
        ValueError,
        TypeError,
        KeyError,
        yaml.YAMLError,
    ) as error:
        return _failed(
            "preflight-refused",
            f"packet preflight could not read authoritative inputs: {error}",
            "Restore readable packet, backlog, archive, source, and workspace paths.",
            action="preflight",
        )
    status = "ok" if not findings else "STALE" if _has_stale(findings) else "failed"
    exit_code = exits.SUCCESS if not findings else exits.VALIDATION_FAILURE
    diagnostics = tuple(
        f"method packet preflight: {finding['message']}" for finding in findings
    )
    return PacketResult(
        exit_code,
        {
            "command": "packet",
            "action": "preflight",
            "status": status,
            _unit_key(packet): _story_value(packet),
            "findings": findings,
        },
        diagnostics,
    )


def reconcile_packet(
    repository_root: PathValue,
    *,
    packet_path: str,
    allowed_implementation_root: str,
    expected_authorization_hash: str,
) -> PacketResult:
    """Rebind one valid canonical packet to an authoritative status transition."""

    root = _repository_root(repository_root)
    if root is None:
        return _failed(
            "reconciliation-refused",
            "repository root is missing or unreadable",
            "Run from a readable repository checkout.",
            action="reconcile",
        )
    expected_allowed = _resolve_existing_directory(
        allowed_implementation_root,
        base=root,
    )
    if expected_allowed is None:
        return _failed(
            "reconciliation-refused",
            (
                "caller allowed implementation root is missing, unreadable, "
                "or not a directory"
            ),
            "Provide the caller-authorized implementation boundary.",
            action="reconcile",
        )
    try:
        old_packet, packet_error = _load_packet(root, packet_path)
        if packet_error is not None:
            return _verification_load_failure("reconcile", packet_error)
        backlog_document, backlog_error = _load_backlog(root)
        if backlog_error is not None:
            return _verification_load_failure("reconcile", backlog_error)
        current_backlog = cast(
            Mapping[object, object],
            backlog_document["backlog"],
        )
        candidate, candidate_findings = _find_current_story(
            current_backlog,
            _story_value(old_packet),
        )
        if candidate is None:
            return _reconciliation_failure(
                old_packet,
                candidate_findings,
                "packet story is not unique in the current authoritative backlog",
            )
        try:
            authority = _story_authority(
                root,
                str(candidate.story["file"]),
                expected_story=candidate.story,
            )
        except (OSError, UnicodeError, RuntimeError, ValueError, yaml.YAMLError) as error:
            return _reconciliation_failure(
                old_packet,
                [
                    _finding(
                        "packet",
                        "story",
                        f"authoritative story contract changed: {error}",
                        "Restore immutable story authority or build a new packet.",
                        stale=True,
                    )
                ],
                "packet cannot be reconciled with changed story authority",
            )
        findings, event_kind = _reconcile_old_packet_findings(
            root,
            old_packet,
            current_backlog,
            candidate,
            authority=authority,
            expected_allowed_root=expected_allowed,
            expected_authorization_hash=expected_authorization_hash,
            packet_path=packet_path,
        )
        if findings:
            return _reconciliation_failure(
                old_packet,
                findings,
                "packet cannot be reconciled with the authoritative backlog",
            )

        updated = dict(old_packet)
        old_backlog = cast(Mapping[object, object], old_packet["backlog"])
        old_theme = cast(Mapping[object, object], old_packet["theme"])
        old_epic = cast(Mapping[object, object], old_packet["epic"])
        old_story = cast(Mapping[object, object], _unit(old_packet))
        current_hash = _sha256_file(root / BACKLOG_PATH)
        record = {
            "from-revision": old_backlog["revision"],
            "to-revision": current_backlog["revision"],
            "from-backlog-sha256": old_backlog["sha256"],
            "to-backlog-sha256": current_hash,
            "from-status": {
                "theme": old_theme["status"],
                "epic": old_epic["status"],
                "story": old_story["status"],
            },
            "to-status": {
                "theme": candidate.theme["status"],
                "epic": candidate.epic["status"],
                "story": candidate.story["status"],
            },
            "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
            "reason": event_kind,
        }
        reconciliations = list(cast(list[object], old_packet["reconciliations"]))
        reconciliations.append(record)
        sources = _authoritative_sources(root, candidate, authority)
        updated.update(
            {
                candidate.unit_key: _story_payload(candidate),
                "backlog": {
                    "path": BACKLOG_PATH.as_posix(),
                    "revision": current_backlog["revision"],
                    "sha256": current_hash,
                },
                "theme": {
                    **cast(Mapping[str, object], old_theme),
                    "status": candidate.theme["status"],
                },
                "epic": {
                    **cast(Mapping[str, object], old_epic),
                    "status": candidate.epic["status"],
                },
                "evidence-current": _evidence_snapshot(candidate.story),
                "sources": sources,
                "composite-hash": _composite_hash(sources),
                "reconciliations": reconciliations,
            }
        )
        if candidate.epic_first:
            updated["backlog-snapshot"] = copy.deepcopy(current_backlog)
        updated["authorization-hash"] = _authorization_hash(updated)
        destination = _safe_packet_path(root, packet_path)
        if destination is None:
            raise ValueError("canonical packet path disappeared before rewrite")
        _atomic_write_packet(destination, updated)
    except (
        OSError,
        UnicodeError,
        RuntimeError,
        ValueError,
        TypeError,
        KeyError,
        yaml.YAMLError,
    ) as error:
        return _failed(
            "reconciliation-refused",
            f"packet reconciliation could not read or rewrite inputs: {error}",
            "Restore stable packet, backlog, source, and workspace inputs.",
            action="reconcile",
        )
    return PacketResult(
        exits.SUCCESS,
        {
            "command": "packet",
            "action": "reconcile",
            "status": "ok",
            "packet": packet_path,
            candidate.unit_key: candidate.story_id,
            "backlog_revision": current_backlog["revision"],
            "backlog_sha256": current_hash,
            "authorization_hash": updated["authorization-hash"],
            "reconciliation": record,
        },
    )


def _repository_root(repository_root: PathValue) -> Path | None:
    try:
        root = Path(repository_root).resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        return None
    return root if root.is_dir() else None


def _load_backlog(root: Path) -> tuple[Mapping[str, object], PacketResult | None]:
    validation = validate_repository(root)
    if not validation.valid:
        return {}, PacketResult(
            exits.VALIDATION_FAILURE,
            {
                "command": "packet",
                "status": "schema-invalid",
                "findings": list(validation.findings),
            },
            tuple(
                "method packet: "
                f"{finding['file']} {finding['record']}: {finding['message']}"
                for finding in validation.findings
            ),
        )
    path = root / BACKLOG_PATH
    try:
        document = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        return {}, _failed(
            "schema-invalid",
            f"backlog cannot be loaded: {error}",
            "Restore docs/plan/backlog.yaml as valid UTF-8 YAML.",
        )
    if (
        not isinstance(document, Mapping)
        or not isinstance(document.get("backlog"), Mapping)
    ):
        return {}, _failed(
            "schema-invalid",
            "backlog document root is invalid",
            "Run method validate schema and repair the backlog.",
        )
    return document, None


def _next_candidate(
    root: Path,
    backlog: Mapping[object, object],
) -> tuple[StoryCandidate | None, list[Finding]]:
    candidates, refusals = _candidate_status(root, backlog)
    if not candidates:
        return None, refusals
    recovering = [
        finding for finding in refusals
        if finding.get("record") == "epic-recovery-required"
    ]
    if recovering:
        return None, recovering
    ongoing = [
        candidate for candidate in candidates
        if candidate.epic_first and candidate.story.get("status") == "in-progress"
    ]
    if ongoing:
        candidates = ongoing
    candidates.sort(
        key=lambda candidate: (
            PRIORITY_ORDER.get(str(candidate.story.get("priority", "medium")), 1),
            _story_number(candidate.story_id),
            0 if candidate.epic_first else 1,
            candidate.theme_index,
            candidate.epic_index,
            candidate.story_index,
        )
    )
    best = candidates[0]
    ties = [
        candidate
        for candidate in candidates
        if (
            PRIORITY_ORDER.get(str(candidate.story.get("priority", "medium")), 1),
            _story_number(candidate.story_id),
            candidate.epic_first,
        )
        == (
            PRIORITY_ORDER.get(str(best.story.get("priority", "medium")), 1),
            _story_number(best.story_id),
            best.epic_first,
        )
    ]
    if len(ties) > 1:
        return None, [
            _finding(
                "backlog",
                "ambiguous-projection",
                (
                    "multiple dependency-eligible work items of the same kind "
                    "share the same priority and FIFO number"
                ),
                "Add an explicit dependency or adjust priority before dispatch.",
                {"stories": [candidate.story_id for candidate in ties]},
            )
        ]
    return best, refusals


def _select_candidate(
    root: Path,
    backlog: Mapping[object, object],
    story_id: str | None,
) -> tuple[StoryCandidate | None, list[Finding]]:
    if story_id is None:
        return _next_candidate(root, backlog)
    candidates, refusals = _candidate_status(root, backlog)
    for candidate in candidates:
        if candidate.story_id == story_id:
            next_candidate, _next_refusals = _next_candidate(root, backlog)
            if next_candidate is None or next_candidate.story_id != story_id:
                return None, [
                    _finding(
                        "backlog",
                        story_id,
                        "story is eligible but is not the next FIFO projection",
                        "Dispatch the projected story before later eligible work.",
                    )
                ]
            return candidate, refusals
    return None, [
        finding
        for finding in refusals
        if finding.get("record") == story_id or story_id in str(finding.get("details"))
    ] or [
        _finding(
            "backlog",
            story_id,
            "story is missing or not eligible",
            "Use method packet project to discover the next dispatchable story.",
        )
    ]


def _find_current_story(
    backlog: Mapping[object, object],
    story_id: object,
) -> tuple[StoryCandidate | None, list[Finding]]:
    if not isinstance(story_id, str) or not (
        STORY_ID.fullmatch(story_id) or EPIC_ID.fullmatch(story_id)
    ):
        return None, [
            _finding(
                BACKLOG_PATH.as_posix(),
                "story",
                "packet story ID is invalid",
                "Use a canonical packet built for one fully-qualified story.",
            )
        ]
    matches: list[StoryCandidate] = []
    themes = backlog.get("active-themes")
    if isinstance(themes, list):
        for theme_index, theme in enumerate(themes):
            if not isinstance(theme, Mapping):
                continue
            epics = theme.get("epics")
            if not isinstance(epics, list):
                continue
            for epic_index, epic in enumerate(epics):
                if not isinstance(epic, Mapping):
                    continue
                if theme.get("schema-version") == 3:
                    if epic.get("id") == story_id:
                        matches.append(StoryCandidate(
                            theme, epic, epic, theme_index, epic_index, -1
                        ))
                    continue
                stories = epic.get("stories")
                if not isinstance(stories, list):
                    continue
                for story_index, story in enumerate(stories):
                    if isinstance(story, Mapping) and story.get("id") == story_id:
                        matches.append(
                            StoryCandidate(
                                theme=theme,
                                epic=epic,
                                story=story,
                                theme_index=theme_index,
                                epic_index=epic_index,
                                story_index=story_index,
                            )
                        )
    if len(matches) == 1:
        return matches[0], []
    message = (
        "story is absent from the current active backlog"
        if not matches
        else "story occurs more than once in the current active backlog"
    )
    return None, [
        _finding(
            BACKLOG_PATH.as_posix(),
            story_id,
            message,
            "Restore exactly one authoritative active story with this identity.",
        )
    ]


def _candidate_status(
    root: Path,
    backlog: Mapping[object, object],
) -> tuple[list[StoryCandidate], list[Finding]]:
    themes = backlog.get("active-themes")
    active_themes = themes if isinstance(themes, list) else []
    completion, completion_findings = _completion_index(root, backlog)
    if completion is None:
        return [], completion_findings
    candidates: list[StoryCandidate] = []
    refusals: list[Finding] = list(completion_findings)
    for theme_index, theme in enumerate(active_themes):
        if not isinstance(theme, Mapping):
            continue
        theme_id = theme.get("id")
        theme_path = f"backlog.active-themes[{theme_index}]"
        if theme.get("locked") is True:
            refusals.append(
                _finding(
                    BACKLOG_PATH.as_posix(),
                    str(theme_id or theme_path),
                    "theme is locked",
                    "Do not dispatch locked theme work.",
                )
            )
            continue
        if theme.get("status") == "done":
            continue
        if theme.get("status") not in {"todo", "in-progress"}:
            refusals.append(
                _finding(
                    BACKLOG_PATH.as_posix(),
                    str(theme_id or theme_path),
                    f"theme status {theme.get('status')!r} is not dispatchable",
                    "Move the theme to todo or in-progress before dispatch.",
                )
            )
            continue
        theme_dependencies = _strings(theme.get("depends-on"))
        missing_theme_dependencies = [
            dependency
            for dependency in theme_dependencies
            if dependency not in completion.themes
        ]
        if missing_theme_dependencies:
            refusals.append(
                _finding(
                    BACKLOG_PATH.as_posix(),
                    str(theme_id or theme_path),
                    "theme dependencies are not done",
                    "Complete dependent themes before dispatch.",
                    {"depends-on": missing_theme_dependencies},
                )
            )
            continue
        epics = theme.get("epics")
        if not isinstance(epics, list):
            continue
        for epic_index, epic in enumerate(epics):
            if not isinstance(epic, Mapping):
                continue
            epic_id = epic.get("id")
            if epic.get("status") == "done":
                continue
            if epic.get("status") not in {"todo", "in-progress"}:
                refusals.append(
                    _finding(
                        BACKLOG_PATH.as_posix(),
                        str(epic_id or f"{theme_path}.epics[{epic_index}]"),
                        f"epic status {epic.get('status')!r} is not dispatchable",
                        "Move the epic to todo or in-progress before dispatch.",
                    )
                )
                if theme.get("schema-version") == 3:
                    refusals.append(_finding(
                        BACKLOG_PATH.as_posix(), "epic-recovery-required",
                        f"epic {epic_id} requires explicit recovery",
                        "Resolve the failure or blocker and transition to in-progress.",
                    ))
                continue
            missing_epic_dependencies = [
                dependency
                for dependency in _strings(epic.get("depends-on"))
                if _canonical_epic_id(str(theme_id), dependency)
                not in completion.epics
            ]
            if missing_epic_dependencies:
                refusals.append(
                    _finding(
                        BACKLOG_PATH.as_posix(),
                        str(epic_id or f"{theme_path}.epics[{epic_index}]"),
                        "epic dependencies are not done",
                        "Complete dependent epics before dispatch.",
                        {"depends-on": missing_epic_dependencies},
                    )
                )
                continue
            if theme.get("schema-version") == 3:
                children = epic.get("stories", [])
                internal = {child["id"] for child in children}
                unmet = [
                    dependency
                    for child in children
                    for dependency in _strings(child.get("depends-on"))
                    if dependency not in internal and dependency not in completion.stories
                ]
                if unmet:
                    refusals.append(_finding(
                        BACKLOG_PATH.as_posix(), str(epic_id),
                        "external acceptance-child dependencies are not done",
                        "Complete dependencies outside this epic before dispatch.",
                        {"depends-on": unmet},
                    ))
                    continue
                candidates.append(StoryCandidate(
                    theme, epic, epic, theme_index, epic_index, -1
                ))
                continue
            stories = epic.get("stories")
            if not isinstance(stories, list):
                continue
            for story_index, story in enumerate(stories):
                if not isinstance(story, Mapping):
                    continue
                story_identifier = str(
                    story.get("id")
                    or f"{theme_path}.epics[{epic_index}].stories[{story_index}]"
                )
                status = story.get("status")
                if status != "todo":
                    if status in {"blocked", "failed", "in-progress"}:
                        refusals.append(
                            _finding(
                                BACKLOG_PATH.as_posix(),
                                story_identifier,
                                f"story status {status!r} is not dispatchable",
                                "Resolve, reconcile, or resume the story before dispatch.",
                            )
                        )
                    continue
                missing_story_dependencies = [
                    dependency
                    for dependency in _strings(story.get("depends-on"))
                    if dependency not in completion.stories
                ]
                if missing_story_dependencies:
                    refusals.append(
                        _finding(
                            BACKLOG_PATH.as_posix(),
                            story_identifier,
                            "story dependencies are not done",
                            "Complete dependent stories before dispatch.",
                            {"depends-on": missing_story_dependencies},
                        )
                    )
                    continue
                candidates.append(
                    StoryCandidate(
                        theme=theme,
                        epic=epic,
                        story=story,
                        theme_index=theme_index,
                        epic_index=epic_index,
                        story_index=story_index,
                    )
                )
    return candidates, refusals


def _completion_index(
    root: Path,
    backlog: Mapping[object, object],
) -> tuple[CompletionIndex | None, list[Finding]]:
    """Index completed dependencies across active and validated archive data."""

    active = backlog.get("active-themes")
    active_themes = active if isinstance(active, list) else []
    themes: list[Mapping[object, object]] = [
        theme for theme in active_themes if isinstance(theme, Mapping)
    ]
    archived = backlog.get("archived-themes")
    archived_themes = archived if isinstance(archived, list) else []
    for index, summary in enumerate(archived_themes):
        if not isinstance(summary, Mapping):
            continue
        archive = _archive_path(root, summary.get("archive-ref"))
        if archive is None:
            return None, [
                _finding(
                    BACKLOG_PATH.as_posix(),
                    f"backlog.archived-themes[{index}].archive-ref",
                    "archive snapshot is missing, unreadable, broad, or outside the repository",
                    "Restore the indexed archive snapshot before projecting work.",
                )
            ]
        try:
            snapshot = yaml.load(
                archive.read_text(encoding="utf-8"),
                Loader=UniqueKeyLoader,
            )
        except (OSError, UnicodeError, yaml.YAMLError, RecursionError) as error:
            return None, [
                _finding(
                    _display(archive, root),
                    "theme",
                    f"archive snapshot cannot be loaded: {error}",
                    "Restore the indexed archive as bounded duplicate-free YAML.",
                )
            ]
        theme = snapshot.get("theme") if isinstance(snapshot, Mapping) else None
        if (
            not isinstance(theme, Mapping)
            or theme.get("id") != summary.get("id")
            or theme.get("status") != "done"
            or theme.get("locked") is not True
        ):
            return None, [
                _finding(
                    _display(archive, root),
                    "theme",
                    "archive snapshot is not a matching completed locked theme",
                    "Restore the valid snapshot indexed by the authoritative backlog.",
                )
            ]
        themes.append(theme)

    done_themes: set[str] = set()
    done_epics: set[str] = set()
    done_stories: set[str] = set()
    for theme in themes:
        theme_id = theme.get("id")
        if not isinstance(theme_id, str):
            continue
        if theme.get("status") == "done":
            done_themes.add(theme_id)
        epics = theme.get("epics")
        if not isinstance(epics, list):
            continue
        for epic in epics:
            if not isinstance(epic, Mapping):
                continue
            epic_id = epic.get("id")
            if isinstance(epic_id, str) and epic.get("status") == "done":
                done_epics.add(_canonical_epic_id(theme_id, epic_id))
            stories = epic.get("stories")
            if not isinstance(stories, list):
                continue
            for story in stories:
                if (
                    isinstance(story, Mapping)
                    and story.get("status") == "done"
                    and isinstance(story.get("id"), str)
                ):
                    done_stories.add(str(story["id"]))
    return (
        CompletionIndex(
            frozenset(done_themes),
            frozenset(done_epics),
            frozenset(done_stories),
        ),
        [],
    )


def _archive_path(root: Path, value: object) -> Path | None:
    if not isinstance(value, str):
        return None
    pure = PurePosixPath(value)
    if (
        pure.is_absolute()
        or "." in pure.parts
        or ".." in pure.parts
        or pure.parts[:3] != ("docs", "plan", "backlog-archive")
    ):
        return None
    try:
        path = root.joinpath(*pure.parts).resolve(strict=True)
        path.relative_to(root.resolve(strict=True))
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_YAML_BYTES:
            return None
    except (OSError, RuntimeError, ValueError):
        return None
    return path


def _canonical_epic_id(theme_id: str, epic_id: str) -> str:
    if re.fullmatch(r"TH[1-9][0-9]*\.E[1-9][0-9]*", epic_id):
        return epic_id
    return f"{theme_id}.{epic_id}"


def _strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, str))


def _story_number(identifier: str) -> int:
    try:
        return int(re.split(r"\.(?:US|E)", identifier)[-1])
    except (IndexError, ValueError):
        return 0


def _projection_payload(
    root: Path,
    backlog: Mapping[object, object],
    candidate: StoryCandidate,
) -> dict[str, object]:
    return {
        "contract-version": 1,
        "source": {
            "path": BACKLOG_PATH.as_posix(),
            "revision": backlog["revision"],
            "sha256": _sha256_file(root / BACKLOG_PATH),
        },
        candidate.unit_key: _story_payload(candidate),
        "theme": {
            "id": candidate.theme["id"],
            "status": candidate.theme["status"],
            "locked": candidate.theme["locked"],
            "vision-ref": candidate.theme.get("vision-ref"),
            "discovery-ref": candidate.theme.get("discovery-ref"),
            "requirements-ref": candidate.theme.get("requirements-ref"),
        },
        "epic": {
            "id": candidate.epic["id"],
            "status": candidate.epic["status"],
            "depends-on": list(_strings(candidate.epic.get("depends-on"))),
        },
        "dependencies": {
            "theme": list(_strings(candidate.theme.get("depends-on"))),
            "epic": list(_strings(candidate.epic.get("depends-on"))),
            "story": list(_strings(candidate.story.get("depends-on"))),
        },
        "review": {
            "risk-tier": _nested(candidate.story, "risk", "tier"),
            "profile": candidate.story.get("review-profile"),
            "verification": candidate.story.get("verification"),
            "evidence-requirements": _evidence_requirements(candidate.story),
            "evidence-current": _evidence_snapshot(candidate.story),
        },
    }


def _story_payload(candidate: StoryCandidate) -> dict[str, object]:
    return {
        "id": candidate.story["id"],
        "title": candidate.story.get("title", candidate.story.get("name")),
        "status": candidate.story["status"],
        "priority": candidate.story.get("priority", "medium"),
        "file": candidate.story["file"],
    }


def _packet_payload(
    root: Path,
    backlog: Mapping[object, object],
    candidate: StoryCandidate,
    *,
    task: str,
    mode: str,
    trace_id: str,
    workspace: Mapping[str, object],
    authority: StoryAuthority,
) -> dict[str, object]:
    sources = _authoritative_sources(root, candidate, authority)
    packet: dict[str, object] = {
        "mission-packet-version": PACKET_VERSION,
        "packet-kind": "backlog-dispatch-mission",
        "task": task,
        "mode": mode,
        "trace-id": trace_id,
        "generated-at": datetime.now().astimezone().isoformat(timespec="seconds"),
        candidate.unit_key: _story_payload(candidate),
        "backlog": {
            "path": BACKLOG_PATH.as_posix(),
            "revision": backlog["revision"],
            "sha256": _sha256_file(root / BACKLOG_PATH),
        },
        "theme": {
            "id": candidate.theme["id"],
            "status": candidate.theme["status"],
            "locked": candidate.theme["locked"],
            "vision-ref": candidate.theme.get("vision-ref"),
            "discovery-ref": candidate.theme.get("discovery-ref"),
            "requirements-ref": candidate.theme.get("requirements-ref"),
        },
        "epic": {
            "id": candidate.epic["id"],
            "status": candidate.epic["status"],
            "depends-on": list(_strings(candidate.epic.get("depends-on"))),
        },
        "dependencies": {
            "theme": list(_strings(candidate.theme.get("depends-on"))),
            "epic": list(_strings(candidate.epic.get("depends-on"))),
            "story": list(_strings(candidate.story.get("depends-on"))),
        },
        "risk": candidate.story.get("risk"),
        "model-route": candidate.story.get("model-route"),
        "verification": candidate.story.get("verification"),
        "review-profile": candidate.story.get("review-profile"),
        "evidence-requirements": _evidence_requirements(candidate.story),
        "evidence-snapshot": _evidence_snapshot(candidate.story),
        "evidence-current": _evidence_snapshot(candidate.story),
        "workspace": dict(workspace),
        "scope": _scope(candidate, mode),
        "story-frontmatter": _story_frontmatter_payload(authority),
        "traceability": {
            key: list(values) for key, values in authority.traceability.items()
        },
        "required-skills": _required_skills(mode, authority.skills),
        "required-gates": _required_gates(mode, candidate.story),
        "acceptance-criteria": list(authority.acceptance_criteria),
        "expected-result-locations": _expected_result_locations(candidate.story),
        "sources": sources,
        "required-report": _required_report(),
        "expansions": [],
        "reconciliations": [],
        "integration-boundary": _integration_boundary(),
    }
    if candidate.epic_first:
        packet.update(_epic_authority_payload(root, backlog, candidate))
    packet["composite-hash"] = _composite_hash(sources)
    packet["authorization-hash"] = _authorization_hash(
        cast(Mapping[object, object], packet)
    )
    return packet


def _required_skills(mode: str, declared: Sequence[str] = ()) -> list[str]:
    base = ["the-copilot-build-method", "backlog-management", "bdd-stories"]
    base.extend(skill for skill in declared if skill not in base)
    if mode == "developer":
        if "code-quality" not in base:
            base.append("code-quality")
    return base


def _story_frontmatter_payload(authority: StoryAuthority) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": authority.story_id,
        "title": authority.title,
        "type": authority.story_type,
        "agents": list(authority.agents),
        "skills": list(authority.skills),
        "traceability": {
            key: list(values) for key, values in authority.traceability.items()
        },
        "acceptance-criteria": list(authority.acceptance_criteria),
        "depends-on": list(authority.dependencies),
    }
    if authority.priority is not None:
        payload["priority"] = authority.priority
    if authority.size is not None:
        payload["size"] = authority.size
    return payload


def _scope(candidate: StoryCandidate, mode: str | None) -> dict[str, object]:
    if candidate.epic_first:
        return {
            "epic-id": candidate.story_id,
            "epic-file": candidate.story["file"],
            "maximum-epics": 1,
            "optional-children": [
                {"id": child["id"], "file": child["file"]}
                for child in candidate.epic.get("stories", [])
            ],
            "child-dispatch": "none",
            "mutation": "implementation-root-only" if mode == "developer" else "none",
        }
    return {
        "story-id": candidate.story_id,
        "story-file": candidate.story["file"],
        "maximum-stories": 1,
        "mutation": "implementation-root-only" if mode == "developer" else "none",
    }


def _epic_authority_payload(
    root: Path,
    backlog: Mapping[object, object],
    candidate: StoryCandidate,
) -> dict[str, object]:
    children = []
    for child in candidate.epic.get("stories", []):
        authority = _story_authority(
            root, str(child["file"]), expected_story=child, acceptance_child=True
        )
        children.append({
            "id": child["id"], "file": child["file"],
            "acceptance-criteria": list(authority.acceptance_criteria),
            "traceability": {key: list(value) for key, value in authority.traceability.items()},
            "depends-on": list(authority.dependencies),
        })
    return {
        "work-item": _story_payload(candidate),
        "acceptance-children": children,
        "backlog-snapshot": copy.deepcopy(backlog),
    }


def _required_gates(
    mode: str,
    story: Mapping[object, object],
) -> list[str]:
    if mode == "planning":
        return ["no-implementation-mutations", "review-of-plan"]
    verification = story.get("verification")
    matrix = (
        verification.get("matrix")
        if isinstance(verification, Mapping)
        else ["unit"]
    )
    return [*(str(item) for item in _strings(matrix)), "review"]


def _evidence_requirements(
    story: Mapping[object, object],
) -> dict[str, object]:
    """Derive completion evidence from controls, never from current evidence."""

    verification = story.get("verification")
    matrix = (
        list(_strings(verification.get("matrix")))
        if isinstance(verification, Mapping)
        else []
    )
    review: dict[str, object] = {
        "required": True,
        "profile": story.get("review-profile"),
    }
    if EPIC_ID.fullmatch(str(story.get("id"))) is not None:
        review["accepted-approval-tokens"] = sorted(_epic_review_tokens(story))
    return {
        "verification": matrix,
        "review": review,
        "gitflow": {
            "required": True,
            "not-applicable": "not-applicable: <rationale>",
        },
    }


def _epic_review_tokens(epic: Mapping[object, object]) -> frozenset[str]:
    if (
        epic.get("review-profile") == "standard"
        and _nested(epic, "risk", "tier") in {"R0", "R1"}
    ):
        return frozenset({
            "independent approved", "native review approved", "self-review approved",
        })
    return frozenset({"independent approved"})


def _evidence_snapshot(
    story: Mapping[object, object],
) -> dict[str, list[str]]:
    evidence = story.get("evidence")
    if not isinstance(evidence, Mapping):
        return {key: [] for key in EVIDENCE_KEYS}
    return {key: list(_strings(evidence.get(key))) for key in EVIDENCE_KEYS}


def _expected_result_locations(
    story: Mapping[object, object],
) -> dict[str, object]:
    story_id = story.get("id")
    return {
        "packets": (
            [f"{DEFAULT_RUNTIME_DIRECTORY.as_posix()}/{story_id}/"]
            if isinstance(story_id, str)
            else []
        ),
        "verification": "docs/plan/runtime/",
        "review": "docs/plan/runtime/",
    }


def _required_report() -> dict[str, object]:
    return {
        "fields": [
            "outcome",
            "changes",
            "verification-evidence",
            "review-evidence",
            "usage",
            "open-questions",
        ]
    }


def _integration_boundary() -> dict[str, object]:
    return {
        "autopilot-owns": [
            "backlog eligibility",
            "mission packet generation",
            "post-review status proposals",
        ],
        "cockpit-owns": [
            "durable delivery lifecycle",
            "worker acknowledgement",
            "runtime evidence return",
        ],
        "cockpit-must-not-maintain": "independently editable product backlog status",
    }


def _authoritative_sources(
    root: Path,
    candidate: StoryCandidate,
    authority: StoryAuthority,
) -> list[Mapping[str, object]]:
    """Resolve the complete authoritative source closure, fail closed."""

    trusted = {
        f".github/skills/{skill}/SKILL.md"
        for skill in _required_skills(
            _authorized_mode(authority.agents) or "planning",
            authority.skills,
        )
    }
    untrusted = {BACKLOG_PATH.as_posix(), str(candidate.story["file"])}
    if candidate.epic_first:
        document = yaml.load(
            (root / BACKLOG_PATH).read_text(encoding="utf-8"), Loader=StrictPacketLoader
        )
        for summary in document["backlog"]["archived-themes"]:
            archive = _archive_path(root, summary.get("archive-ref"))
            if archive is None:
                raise ValueError("epic dependency archive is missing or unsafe")
            untrusted.add(archive.relative_to(root).as_posix())
        for child in candidate.epic.get("stories", []):
            child_authority = _story_authority(
                root, str(child["file"]), expected_story=child, acceptance_child=True
            )
            untrusted.add(str(child["file"]))
            for adr in child_authority.traceability.get("adrs", ()):
                matches = sorted((root / "docs/ADRs").glob(f"{adr}-*.md"))
                if len(matches) != 1 or _safe_regular_markdown(root, matches[0]) is None:
                    raise ValueError(f"child traceability ADR {adr!r} is missing or ambiguous")
                untrusted.add(matches[0].relative_to(root).as_posix())
    for field in ("vision-ref", "discovery-ref", "requirements-ref"):
        reference = candidate.theme.get(field)
        if not isinstance(reference, str) or not reference:
            raise ValueError(f"theme {field} is missing")
        untrusted.update(_expand_source_reference(root, reference))
    untrusted.update(_expand_source_reference(root, "docs/architecture"))
    for adr in authority.traceability.get("adrs", ()):
        matches = sorted((root / "docs/ADRs").glob(f"{adr}-*.md"))
        safe_matches = [
            path for path in matches if _safe_regular_markdown(root, path) is not None
        ]
        if len(safe_matches) != 1:
            raise ValueError(
                f"traceability ADR {adr!r} is missing or ambiguous"
            )
        untrusted.add(safe_matches[0].relative_to(root).as_posix())

    all_paths = trusted | untrusted
    if len(all_paths) > MAX_SOURCE_FILES:
        raise ValueError("authoritative source manifest exceeds its file bound")
    return [
        _source(
            root,
            relative,
            trust=(
                "trusted"
                if relative in trusted and relative not in untrusted
                else "untrusted"
            ),
        )
        for relative in sorted(all_paths)
    ]


def _expand_source_reference(root: Path, reference: str) -> set[str]:
    pure = PurePosixPath(reference)
    if pure.is_absolute() or "." in pure.parts or ".." in pure.parts:
        raise ValueError(f"source reference {reference!r} is outside the repository")
    try:
        repository = root.resolve(strict=True)
        candidate = root.joinpath(*pure.parts)
        if _has_symlink_component(root, candidate):
            raise ValueError("symlinked source reference")
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(repository)
    except (OSError, RuntimeError, ValueError) as error:
        raise ValueError(f"source reference {reference!r} is missing or unsafe") from error
    if resolved.is_symlink():
        raise ValueError(f"source reference {reference!r} may not be a symlink")
    if resolved.is_file():
        safe = _safe_regular_markdown(root, resolved)
        if safe is None:
            raise ValueError(f"source reference {reference!r} is not Markdown")
        return {safe.relative_to(repository).as_posix()}
    if not resolved.is_dir():
        raise ValueError(f"source reference {reference!r} is not a file or directory")
    files: set[str] = set()
    for path in sorted(resolved.rglob("*.md")):
        safe = _safe_regular_markdown(root, path)
        if safe is None:
            raise ValueError(
                f"source directory {reference!r} contains an unsafe Markdown entry"
            )
        files.add(safe.relative_to(repository).as_posix())
        if len(files) > MAX_SOURCE_FILES:
            raise ValueError(f"source directory {reference!r} exceeds its file bound")
    if not files:
        raise ValueError(f"source directory {reference!r} contains no Markdown files")
    return files


def _safe_regular_markdown(root: Path, path: Path) -> Path | None:
    try:
        repository = root.resolve(strict=True)
        if _has_symlink_component(root, path):
            return None
        resolved = path.resolve(strict=True)
        resolved.relative_to(repository)
        if (
            not resolved.is_file()
            or resolved.suffix.lower() != ".md"
            or resolved.stat().st_size > MAX_YAML_BYTES
        ):
            return None
    except (OSError, RuntimeError, ValueError):
        return None
    return resolved


def _has_symlink_component(root: Path, path: Path) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return True
    current = root
    for part in relative.parts:
        current = current / part
        try:
            if current.is_symlink():
                return True
        except OSError:
            return True
    return False


def _story_authority(
    root: Path,
    relative: str,
    *,
    expected_story: Mapping[object, object],
    acceptance_child: bool = False,
) -> StoryAuthority:
    path = _source_path(root, relative)
    if path is None:
        raise ValueError(f"story source {relative!r} is not a repository file")
    if path.stat().st_size > MAX_YAML_BYTES:
        raise ValueError("story source exceeds the YAML safety limit")
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("story must begin with YAML frontmatter")
    closing = next(
        (index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"),
        None,
    )
    if closing is None:
        raise ValueError("story frontmatter has no closing delimiter")
    try:
        frontmatter = yaml.load(
            "\n".join(lines[1:closing]),
            Loader=StrictPacketLoader,
        )
    except (yaml.YAMLError, RecursionError) as error:
        raise ValueError(
            "story frontmatter must be duplicate-free inert YAML"
        ) from error
    if not isinstance(frontmatter, Mapping):
        raise ValueError("story frontmatter root must be a mapping")
    epic_first = EPIC_ID.fullmatch(str(expected_story.get("id"))) is not None
    if epic_first or acceptance_child:
        frontmatter = dict(frontmatter)
        frontmatter.setdefault("agents", ["developer"])
        frontmatter.setdefault("skills", ["bdd-stories"])
        frontmatter.setdefault("depends-on", list(_strings(expected_story.get("depends-on"))))
        if acceptance_child:
            frontmatter.setdefault("type", "standard")
            frontmatter.setdefault("traceability", {
                key: [] for key in ("vision", "requirements", "adrs", "invariants")
            })
    domain_error = _json_domain_error(frontmatter)
    if domain_error is not None:
        raise ValueError(f"story frontmatter is outside the JSON domain: {domain_error}")
    keys = set(frontmatter)
    allowed_keys = STORY_FRONTMATTER_REQUIRED_KEYS | STORY_FRONTMATTER_OPTIONAL_KEYS
    missing = sorted(STORY_FRONTMATTER_REQUIRED_KEYS - keys)
    unknown = sorted((key for key in keys if key not in allowed_keys), key=str)
    if missing or unknown:
        raise ValueError(
            "story frontmatter must contain exactly the required canonical keys "
            "and optional priority/size"
            f"; missing={missing}, unknown={unknown}"
        )
    expected_story_id = expected_story.get("id")
    if frontmatter.get("id") != expected_story_id:
        raise ValueError(
            "story frontmatter ID does not match its authoritative backlog story"
        )
    title = frontmatter.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("story frontmatter requires a non-empty title")
    if title != expected_story.get("title", expected_story.get("name")):
        raise ValueError(
            "story frontmatter title does not match its authoritative backlog story"
        )
    contract = trace.load_contract(root)
    required_types = set(cast(list[str], contract["required-story-types"]))
    story_type = frontmatter.get("type")
    if story_type not in {"standard", "trivial", "spike"}:
        raise ValueError(
            "story frontmatter type must be standard, spike, or trivial"
        )
    priority = frontmatter.get("priority")
    if priority is not None and priority not in {"high", "medium", "low"}:
        raise ValueError("story frontmatter priority must be high, medium, or low")
    if priority is not None and priority != expected_story.get("priority", "medium"):
        raise ValueError(
            "story frontmatter priority does not match its authoritative backlog story"
        )
    size = frontmatter.get("size")
    if size is not None and size not in {"S", "M", "L"}:
        raise ValueError("story frontmatter size must be S, M, or L")
    criteria = trace.acceptance_criteria(frontmatter.get("acceptance-criteria"))
    agents = frontmatter.get("agents")
    if (
        not isinstance(agents, list)
        or not agents
        or any(not isinstance(agent, str) or not agent.strip() for agent in agents)
        or len(set(agents)) != len(agents)
    ):
        raise ValueError(
            "story frontmatter requires a non-empty unique agents string list"
        )
    skills = frontmatter.get("skills")
    if (
        not isinstance(skills, list)
        or not skills
        or any(not isinstance(skill, str) or not skill.strip() for skill in skills)
        or len(set(skills)) != len(skills)
    ):
        raise ValueError(
            "story frontmatter requires a non-empty unique skills string list"
        )
    dependencies = frontmatter.get("depends-on")
    if (
        not isinstance(dependencies, list)
        or any(
            not isinstance(dependency, str)
            or (EPIC_ID if epic_first else STORY_ID).fullmatch(dependency) is None
            for dependency in dependencies
        )
        or len(set(dependencies)) != len(dependencies)
    ):
        raise ValueError(
            "story frontmatter depends-on must be a unique canonical story ID list"
        )
    authoritative_dependencies = list(_strings(expected_story.get("depends-on")))
    if dependencies != authoritative_dependencies:
        raise ValueError(
            "story frontmatter depends-on does not exactly match its authoritative "
            "backlog story"
        )
    traceability = frontmatter.get("traceability")
    if not isinstance(traceability, Mapping):
        raise ValueError("story frontmatter traceability must be a mapping")
    definitions = cast(Mapping[str, Mapping[str, object]], contract["keys"])
    if set(traceability) != set(definitions):
        raise ValueError(
            "story frontmatter traceability must contain exactly "
            + ", ".join(definitions)
        )
    normalized_traceability: dict[str, tuple[str, ...]] = {}
    for key, definition in definitions.items():
        values = traceability.get(key)
        if (
            not isinstance(values, list)
            or any(not isinstance(value, str) or not value.strip() for value in values)
            or len(set(values)) != len(values)
        ):
            raise ValueError(
                "story frontmatter traceability values must be unique string lists"
            )
        if (
            story_type in required_types and not values and not acceptance_child
            and (not epic_first or key == "requirements")
        ):
            raise ValueError(
                f"{story_type} story traceability.{key} must contain at least "
                "one record ID"
            )
        prefixes = set(cast(list[str], definition["prefixes"]))
        for value in values:
            prefix = (
                value.split("-", 1)[0]
                if trace.ID_PATTERN.fullmatch(value) is not None
                else None
            )
            if prefix not in prefixes:
                raise ValueError(
                    f"traceability.{key} value {value!r} has an invalid prefix"
                )
        normalized_traceability[key] = tuple(values)
    return StoryAuthority(
        cast(str, expected_story_id),
        title,
        cast(str, story_type),
        cast(str | None, priority),
        cast(str | None, size),
        tuple(criteria),
        tuple(agents),
        tuple(skills),
        tuple(dependencies),
        normalized_traceability,
    )


def _authorized_mode(agents: Sequence[str]) -> str | None:
    if "developer" in agents:
        return "developer"
    if PLANNING_AGENT_ROLES.intersection(agents):
        return "planning"
    return None


def _authorization_hash(packet: Mapping[object, object]) -> str:
    trace_metadata = {
        "task": packet.get("task"),
        "trace-id": packet.get("trace-id"),
        "generated-at": packet.get("generated-at"),
    }
    authorization = {
        "mission-packet-version": packet.get("mission-packet-version"),
        "packet-kind": packet.get("packet-kind"),
        "story": packet.get("story"),
        "backlog": packet.get("backlog"),
        "theme": packet.get("theme"),
        "epic": packet.get("epic"),
        "dependencies": packet.get("dependencies"),
        "risk": packet.get("risk"),
        "model-route": packet.get("model-route"),
        "verification": packet.get("verification"),
        "review-profile": packet.get("review-profile"),
        "evidence-requirements": packet.get("evidence-requirements"),
        "evidence-snapshot": packet.get("evidence-snapshot"),
        "evidence-current": packet.get("evidence-current"),
        "mode": packet.get("mode"),
        "workspace": packet.get("workspace"),
        "required-gates": packet.get("required-gates"),
        "required-skills": packet.get("required-skills"),
        "scope": packet.get("scope"),
        "traceability": packet.get("traceability"),
        "trace-metadata": trace_metadata,
        "expected-result-locations": packet.get("expected-result-locations"),
        "integration-boundary": packet.get("integration-boundary"),
        "acceptance-criteria": packet.get("acceptance-criteria"),
        "story-frontmatter": packet.get("story-frontmatter"),
        "required-report": packet.get("required-report"),
        "expansions": packet.get("expansions"),
        "sources": packet.get("sources"),
        "composite-hash": packet.get("composite-hash"),
        "reconciliations": packet.get("reconciliations"),
    }
    if _epic_packet(packet):
        authorization.update({
            key: packet.get(key) for key in EPIC_PACKET_FIELDS
        })
    encoded = json.dumps(
        authorization,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _is_offset_timestamp(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _workspace_payload(
    root: Path,
    *,
    planning_roots: Sequence[str],
    implementation_root: str,
    allowed_implementation_root: str,
    mode: str,
) -> PacketResult:
    roots = list(planning_roots)
    normalized_roots: list[str] = []
    findings: list[Finding] = []
    for value in roots:
        path = _resolve_existing_directory(value, base=root)
        if path is None or not os.access(path, os.R_OK | os.X_OK):
            findings.append(
                _finding(
                    "workspace",
                    "planning-roots",
                    f"planning root {value!r} is not readable",
                    "Provide only readable authoritative planning roots.",
                )
            )
        else:
            normalized_roots.append(path.as_posix())
    repository_path = root.resolve(strict=True)
    if normalized_roots != [repository_path.as_posix()] or len(roots) != 1:
        findings.append(
            _finding(
                "workspace",
                "planning-roots",
                (
                    "planning roots must be exactly the authoritative "
                    "repository root"
                ),
                "Provide the exact repository root as the only planning root.",
            )
        )
    allowed = _resolve_existing_directory(allowed_implementation_root, base=root)
    if allowed is None:
        findings.append(
            _finding(
                "workspace",
                "allowed-implementation-root",
                f"allowed implementation root {allowed_implementation_root!r} is absent",
                "Provide the explicit directory that bounds implementation work.",
            )
        )
    implementation = _resolve_existing_directory(implementation_root, base=root)
    if implementation is None:
        findings.append(
            _finding(
                "workspace",
                "implementation-root",
                f"implementation root {implementation_root!r} is absent",
                "Create or select the writable implementation checkout.",
            )
        )
    elif not os.access(implementation, os.W_OK | os.X_OK):
        findings.append(
            _finding(
                "workspace",
                "implementation-root",
                f"implementation root {implementation.as_posix()!r} is not writable",
                "Grant write access to the declared implementation root.",
            )
        )
    allowed_overlaps_planning = (
        allowed is not None
        and any(_paths_overlap(allowed, Path(value)) for value in normalized_roots)
    )
    if allowed is not None and (
        _is_broad_allowed_root(allowed, repository_path)
        or allowed_overlaps_planning
    ):
        findings.append(
            _finding(
                "workspace",
                "allowed-implementation-root",
                f"allowed implementation root {allowed.as_posix()!r} is overly broad",
                "Use a dedicated implementation workspace that excludes planning roots.",
            )
        )
    if implementation is not None and allowed is not None:
        if not _is_within(implementation, allowed):
            findings.append(
                _finding(
                    "workspace",
                    "implementation-root",
                    "implementation root is outside allowed implementation root",
                    "Choose an implementation root inside the explicit allowed root.",
                )
            )
        for planning in normalized_roots:
            planning_path = Path(planning)
            if _paths_overlap(implementation, planning_path):
                findings.append(
                    _finding(
                        "workspace",
                        "implementation-root",
                        "implementation root overlaps a read-only planning root",
                        "Use disjoint planning and implementation workspaces.",
                    )
                )
    if findings:
        return PacketResult(
            exits.VALIDATION_FAILURE,
            {
                "command": "packet",
                "action": "preflight",
                "status": "failed",
                "findings": findings,
            },
            tuple(f"method packet preflight: {item['message']}" for item in findings),
        )
    assert implementation is not None
    assert allowed is not None
    denied_paths = normalized_roots if mode == "developer" else [implementation.as_posix()]
    return PacketResult(
        exits.SUCCESS,
        {
            "workspace": {
                "planning-roots": [
                    {"path": path, "access": "read-only"} for path in normalized_roots
                ],
                "allowed-implementation-root": allowed.as_posix(),
                "implementation-root": implementation.as_posix(),
                "permitted-actions": (
                    ["read", "write-implementation", "test", "review"]
                    if mode == "developer"
                    else ["read", "propose"]
                ),
                "mutation-scope": [implementation.as_posix()] if mode == "developer" else [],
                "denied-paths": denied_paths,
            }
        },
    )


def _resolve_existing_directory(value: str, *, base: Path) -> Path | None:
    try:
        path = Path(value)
        if not path.is_absolute():
            path = base / path
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        return None
    return resolved if resolved.is_dir() else None


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _paths_overlap(first: Path, second: Path) -> bool:
    return _is_within(first, second) or _is_within(second, first)


def _is_broad_allowed_root(allowed: Path, repository_root: Path) -> bool:
    return allowed == Path(allowed.anchor) or _is_within(repository_root, allowed)


def _packet_destination(
    root: Path,
    story_id: str,
    task: str,
    *,
    output: str | None,
) -> Path | None:
    canonical = DEFAULT_RUNTIME_DIRECTORY / story_id / f"{task}.yaml"
    if (
        output is not None
        and PurePosixPath(output) != PurePosixPath(canonical.as_posix())
    ):
        return None
    candidate = root / canonical
    try:
        if _has_symlink_component(root, candidate):
            return None
        resolved = candidate.resolve(strict=False)
        resolved.relative_to(root.resolve(strict=True))
        resolved.relative_to((root / DEFAULT_RUNTIME_DIRECTORY).resolve(strict=False))
    except (OSError, RuntimeError, ValueError):
        return None
    return candidate


def _serialize_packet(document: Mapping[object, object]) -> str:
    serialized = yaml.dump(dict(document), Dumper=PacketDumper, sort_keys=False)
    if len(serialized.encode("utf-8")) > MAX_PACKET_BYTES:
        raise ValueError(f"serialized packet exceeds the {MAX_PACKET_BYTES}-byte safety limit")
    return serialized


def _atomic_write_packet(path: Path, document: Mapping[object, object]) -> None:
    """Durably replace a packet without exposing a partially written manifest."""

    serialized = _serialize_packet(document)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor: int | None = None
    try:
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            descriptor = None
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _load_packet(
    root: Path,
    packet_path: str,
) -> tuple[Mapping[object, object], PacketResult | None]:
    path = _safe_packet_path(root, packet_path)
    if path is None:
        return {}, _failed(
            "packet-invalid",
            "packet path is missing, too large, or outside the repository",
            "Use a repository-relative packet path under docs/plan/runtime/packets.",
        )
    try:
        document = yaml.load(
            path.read_text(encoding="utf-8"),
            Loader=StrictPacketLoader,
        )
    except (OSError, UnicodeError, yaml.YAMLError, RecursionError) as error:
        return {}, _failed(
            "packet-invalid",
            f"packet cannot be loaded: {error}",
            "Regenerate the mission packet.",
        )
    domain_error = _json_domain_error(document)
    if domain_error is not None:
        return {}, _failed(
            "packet-invalid",
            f"packet must contain only JSON-domain values: {domain_error}",
            "Regenerate the mission packet without YAML-native values or aliases.",
        )
    if not isinstance(document, Mapping):
        return {}, _failed(
            "packet-invalid",
            "packet root must be a YAML mapping",
            "Regenerate the mission packet.",
        )
    return document, None


def _json_domain_error(
    value: object,
    path: str = "$",
    active: set[int] | None = None,
) -> str | None:
    """Return the first reason a loaded value cannot be emitted as strict JSON."""

    if value is None or isinstance(value, (str, bool)):
        return None
    if isinstance(value, int):
        return None
    if isinstance(value, float):
        return None if math.isfinite(value) else f"{path} is not a finite number"
    if active is None:
        active = set()
    if isinstance(value, list):
        identity = id(value)
        if identity in active:
            return f"{path} is a recursive container"
        active.add(identity)
        try:
            for index, item in enumerate(value):
                error = _json_domain_error(item, f"{path}[{index}]", active)
                if error is not None:
                    return error
        finally:
            active.remove(identity)
        return None
    if isinstance(value, Mapping):
        identity = id(value)
        if identity in active:
            return f"{path} is a recursive container"
        active.add(identity)
        try:
            for key, item in value.items():
                if not isinstance(key, str):
                    return f"{path} has a non-string mapping key"
                error = _json_domain_error(item, f"{path}.{key}", active)
                if error is not None:
                    return error
        finally:
            active.remove(identity)
        return None
    return f"{path} has unsupported YAML type {type(value).__name__}"


def _safe_packet_path(root: Path, value: str) -> Path | None:
    try:
        pure = PurePosixPath(value)
        if pure.is_absolute() or "." in pure.parts or ".." in pure.parts:
            return None
        candidate = root.joinpath(*pure.parts)
        if _has_symlink_component(root, candidate):
            return None
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root.resolve(strict=True))
        if not resolved.is_file() or resolved.is_symlink():
            return None
        if resolved.stat().st_size > MAX_PACKET_BYTES:
            return None
    except (OSError, RuntimeError, ValueError):
        return None
    return resolved


def _packet_findings(
    root: Path,
    packet: Mapping[object, object],
    current_backlog: Mapping[object, object],
    *,
    expected_allowed_root: Path,
    expected_authorization_hash: str,
    packet_path: str,
) -> list[Finding]:
    findings: list[Finding] = []
    story_for_path = _unit(packet)
    expected_location = (
        DEFAULT_RUNTIME_DIRECTORY
        / str(story_for_path.get("id"))
        / f"{packet.get('task')}.yaml"
        if isinstance(story_for_path, Mapping)
        else None
    )
    if (
        expected_location is None
        or packet_path != expected_location.as_posix()
    ):
        findings.append(
            _finding(
                "packet",
                "path",
                "packet path does not exactly match its story and task",
                "Use docs/plan/runtime/packets/<story-id>/<task>.yaml.",
                stale=True,
            )
        )
    packet_keys = {key for key in packet if isinstance(key, str)}
    fields = (
        (PACKET_FIELDS - {"story"}) | EPIC_PACKET_FIELDS
        if _epic_packet(packet) else PACKET_FIELDS
    )
    for missing_field in sorted(fields - packet_keys):
        findings.append(
            _finding(
                "packet",
                missing_field,
                "required packet field is missing",
                "Regenerate the packet with the current method runtime.",
            )
        )
    unknown_keys = [key for key in packet if key not in fields]
    for unknown_field in sorted(unknown_keys, key=str):
        findings.append(
            _finding(
                "packet",
                str(unknown_field),
                "unknown packet field is not permitted",
                "Regenerate the packet instead of extending its authority.",
            )
        )
    if packet.get("mission-packet-version") != PACKET_VERSION:
        findings.append(
            _finding(
                "packet",
                "mission-packet-version",
                "unsupported mission packet version",
                "Regenerate the packet with the current method runtime.",
            )
        )
    if packet.get("packet-kind") != "backlog-dispatch-mission":
        findings.append(
            _finding(
                "packet",
                "packet-kind",
                "packet is not a backlog dispatch mission",
                "Use a mission packet generated by method packet build.",
            )
        )
    task = packet.get("task")
    if not isinstance(task, str) or PACKET_TASK_PATTERN.fullmatch(task) is None:
        findings.append(
            _finding(
                "packet",
                "task",
                "packet task identifier is invalid",
                "Regenerate the packet with a bounded task identifier.",
            )
        )
    mode = packet.get("mode")
    if mode not in {"developer", "planning"}:
        findings.append(
            _finding(
                "packet",
                "mode",
                "packet mode must be developer or planning",
                "Regenerate the packet with an explicit supported mode.",
            )
        )
    if not isinstance(packet.get("trace-id"), str) or not packet.get("trace-id"):
        findings.append(
            _finding(
                "packet",
                "trace-id",
                "packet trace ID must be a non-empty string",
                "Regenerate the packet with attributable trace metadata.",
            )
        )
    if not _is_offset_timestamp(packet.get("generated-at")):
        findings.append(
            _finding(
                "packet",
                "generated-at",
                "packet generated-at must be an ISO-8601 timestamp with an offset",
                "Regenerate the packet with valid trace metadata.",
            )
        )
    authorization_hash = packet.get("authorization-hash")
    if (
        not isinstance(expected_authorization_hash, str)
        or AUTHORIZATION_HASH_PATTERN.fullmatch(expected_authorization_hash) is None
        or authorization_hash != expected_authorization_hash
    ):
        findings.append(
            _finding(
                "packet",
                "authorization-hash",
                "packet authorization does not match the caller-provided anchor",
                "Pass the authorization hash returned by the original build.",
                stale=True,
            )
        )
    if (
        not isinstance(authorization_hash, str)
        or AUTHORIZATION_HASH_PATTERN.fullmatch(authorization_hash) is None
        or authorization_hash != _authorization_hash(packet)
    ):
        findings.append(
            _finding(
                "packet",
                "authorization-hash",
                "authorization-bearing packet fields were changed or are unbound",
                "Regenerate the packet; do not modify its authorization grant.",
                {"bound-fields": [
                    *AUTHORIZATION_FIELDS,
                    *(sorted(EPIC_PACKET_FIELDS) if _epic_packet(packet) else []),
                ]},
                stale=True,
            )
        )
    findings.extend(_reconciliation_schema_findings(packet))
    findings.extend(_packet_evidence_findings(packet))
    story = _unit(packet)
    if (
        not isinstance(story, Mapping)
        or not isinstance(story.get("id"), str)
        or (EPIC_ID if _epic_packet(packet) else STORY_ID).fullmatch(story["id"]) is None
    ):
        findings.append(
            _finding(
                "packet",
                "story",
                "packet must authorize exactly one fully-qualified story",
                "Regenerate a one-story mission packet.",
            )
        )
    backlog = packet.get("backlog")
    if not isinstance(backlog, Mapping):
        findings.append(
            _finding(
                "packet",
                "backlog",
                "packet is missing backlog source metadata",
                "Regenerate the packet from the current backlog.",
            )
        )
    else:
        current_sha = _sha256_file(root / BACKLOG_PATH)
        if backlog.get("path") != BACKLOG_PATH.as_posix():
            findings.append(
                _finding(
                    "packet",
                    "backlog.path",
                    "packet backlog path is not docs/plan/backlog.yaml",
                    "Regenerate the packet from the authoritative backlog.",
                )
            )
        if backlog.get("sha256") != current_sha:
            findings.append(
                _finding(
                    "packet",
                    "backlog.sha256",
                    "packet backlog hash is stale",
                    "Regenerate or reconcile the packet before transition or review.",
                    {"expected": backlog.get("sha256"), "actual": current_sha},
                    stale=True,
                )
            )
        current_revision = current_backlog.get("revision")
        if current_revision != backlog.get("revision"):
            findings.append(
                _finding(
                    "packet",
                    "backlog.revision",
                    "packet backlog revision is stale",
                    "Regenerate or reconcile the packet before transition or review.",
                    {
                        "expected": backlog.get("revision"),
                        "actual": current_revision,
                    },
                    stale=True,
                )
            )
    reconciliations = packet.get("reconciliations")
    if isinstance(reconciliations, list) and reconciliations:
        candidate, projection_findings = _find_current_story(
            current_backlog,
            _story_value(packet),
        )
    else:
        candidate, projection_findings = _next_candidate(root, current_backlog)
    packet_mode = packet.get("mode")
    expected_mode: str | None = (
        packet_mode if packet_mode in {"developer", "planning"} else None
    )
    if candidate is None:
        findings.append(
            _finding(
                "packet",
                "story",
                "packet does not resolve to exactly one current FIFO-eligible story",
                "Resolve projection blockers and regenerate the packet.",
                {"projection-findings": projection_findings},
                stale=True,
            )
        )
    else:
        authority = _story_authority(
            root,
            str(candidate.story["file"]),
            expected_story=candidate.story,
        )
        expected_mode = _authorized_mode(authority.agents)
        findings.extend(
            _authoritative_findings(
                root,
                packet,
                current_backlog,
                candidate,
                authority=authority,
                expected_mode=expected_mode,
            )
        )
        if candidate.epic_first:
            findings.extend(_epic_runtime_findings(root, current_backlog, candidate))
            if candidate.story.get("status") == "done":
                findings.extend(_evidence_reconciliation_findings(packet, candidate.story))
            findings.extend(trace.validate_repository(root).findings)
    sources = packet.get("sources")
    if not isinstance(sources, list) or not sources:
        findings.append(
            _finding(
                "packet",
                "sources",
                "packet must list hashed sources",
                "Regenerate the packet.",
            )
        )
    else:
        clean_sources: list[Mapping[str, object]] = []
        for index, source in enumerate(sources):
            if not isinstance(source, Mapping):
                findings.append(
                    _finding(
                        "packet",
                        f"sources[{index}]",
                        "source entry must be a mapping",
                        "Regenerate the packet.",
                    )
                )
                continue
            clean_sources.append(cast(Mapping[str, object], source))
            path = _source_path(root, source.get("path"))
            digest = source.get("sha256")
            if (
                path is None
                or not isinstance(digest, str)
                or SHA256_PATTERN.fullmatch(digest) is None
            ):
                findings.append(
                    _finding(
                        "packet",
                        f"sources[{index}]",
                        "source path or hash is invalid",
                        "Regenerate the packet from existing repository files.",
                    )
                )
                continue
            actual = _sha256_file(path)
            if actual != digest:
                findings.append(
                    _finding(
                        "packet",
                        f"sources[{index}].sha256",
                        f"source {source.get('path')!r} hash is stale",
                        "Regenerate or explicitly expand/reconcile the packet.",
                        {"expected": digest, "actual": actual},
                        stale=True,
                    )
                )
        if packet.get("composite-hash") != _composite_hash(clean_sources):
            findings.append(
                _finding(
                    "packet",
                    "composite-hash",
                    "packet composite hash is stale or invalid",
                    "Regenerate the packet from current sources.",
                    stale=True,
                )
            )
    findings.extend(
        _workspace_contract_findings(
            root,
            packet,
            expected_allowed_root=expected_allowed_root,
            expected_mode=expected_mode,
        )
    )
    return findings


def _authoritative_findings(
    root: Path,
    packet: Mapping[object, object],
    backlog: Mapping[object, object],
    candidate: StoryCandidate,
    *,
    authority: StoryAuthority,
    expected_mode: str | None,
) -> list[Finding]:
    """Compare packet authority to the one current backlog projection."""

    story_file = str(candidate.story["file"])
    sources = _authoritative_sources(root, candidate, authority)
    expected: dict[str, object] = {
        candidate.unit_key: _story_payload(candidate),
        "backlog": {
            "path": BACKLOG_PATH.as_posix(),
            "revision": backlog.get("revision"),
            "sha256": _sha256_file(root / BACKLOG_PATH),
        },
        "theme": {
            "id": candidate.theme["id"],
            "status": candidate.theme["status"],
            "locked": candidate.theme["locked"],
            "vision-ref": candidate.theme.get("vision-ref"),
            "discovery-ref": candidate.theme.get("discovery-ref"),
            "requirements-ref": candidate.theme.get("requirements-ref"),
        },
        "epic": {
            "id": candidate.epic["id"],
            "status": candidate.epic["status"],
            "depends-on": list(_strings(candidate.epic.get("depends-on"))),
        },
        "dependencies": {
            "theme": list(_strings(candidate.theme.get("depends-on"))),
            "epic": list(_strings(candidate.epic.get("depends-on"))),
            "story": list(_strings(candidate.story.get("depends-on"))),
        },
        "risk": candidate.story.get("risk"),
        "model-route": candidate.story.get("model-route"),
        "verification": candidate.story.get("verification"),
        "review-profile": candidate.story.get("review-profile"),
        "evidence-requirements": _evidence_requirements(candidate.story),
        "evidence-current": _evidence_snapshot(candidate.story),
        "acceptance-criteria": list(authority.acceptance_criteria),
        "story-frontmatter": _story_frontmatter_payload(authority),
        "scope": _scope(candidate, expected_mode),
        "traceability": {
            key: list(values) for key, values in authority.traceability.items()
        },
        "expected-result-locations": _expected_result_locations(candidate.story),
        "integration-boundary": _integration_boundary(),
        "required-report": _required_report(),
        "expansions": [],
        "sources": sources,
        "composite-hash": _composite_hash(sources),
    }
    findings: list[Finding] = []
    if candidate.epic_first:
        expected.update(_epic_authority_payload(root, backlog, candidate))
    if expected_mode is None:
        findings.append(
            _finding(
                story_file,
                "agents",
                "authoritative story agents do not authorize a supported mode",
                (
                    "Assign developer for developer mode, or a recognized "
                    "planning/review role for planning mode."
                ),
                {"agents": list(authority.agents)},
                stale=True,
            )
        )
    else:
        expected["mode"] = expected_mode
        expected["required-skills"] = _required_skills(expected_mode, authority.skills)
        expected["required-gates"] = _required_gates(
            expected_mode,
            candidate.story,
        )
    for field, value in expected.items():
        if packet.get(field) != value:
            findings.append(
                _finding(
                    "packet",
                    field,
                    "packet field does not match current authoritative backlog data",
                    "Regenerate the packet from the current FIFO projection.",
                    {"expected": value, "actual": packet.get(field)},
                    stale=True,
                )
            )
    return findings


def _reconcile_old_packet_findings(
    root: Path,
    packet: Mapping[object, object],
    backlog: Mapping[object, object],
    candidate: StoryCandidate,
    *,
    authority: StoryAuthority,
    expected_allowed_root: Path,
    expected_authorization_hash: str,
    packet_path: str,
) -> tuple[list[Finding], str]:
    """Validate old authority while allowing only the requested backlog delta."""

    ordinary = _packet_findings(
        root,
        packet,
        backlog,
        expected_allowed_root=expected_allowed_root,
        expected_authorization_hash=expected_authorization_hash,
        packet_path=packet_path,
    )
    findings = [
        finding
        for finding in ordinary
        if not _is_expected_reconciliation_staleness(finding, packet)
    ]
    findings.extend(
        _immutable_reconciliation_findings(
            root,
            packet,
            candidate,
            authority=authority,
        )
    )
    if candidate.epic_first:
        findings.extend(_epic_backlog_delta_findings(packet, backlog, candidate))
        findings.extend(_epic_runtime_findings(root, backlog, candidate))

    packet_backlog = packet.get("backlog")
    old_revision = (
        packet_backlog.get("revision")
        if isinstance(packet_backlog, Mapping)
        else None
    )
    new_revision = backlog.get("revision")
    if (
        not isinstance(old_revision, int)
        or isinstance(old_revision, bool)
        or not isinstance(new_revision, int)
        or isinstance(new_revision, bool)
        or new_revision <= old_revision
    ):
        findings.append(
            _finding(
                "packet",
                "backlog.revision",
                "reconciliation requires a strictly newer backlog revision",
                "Increment the authoritative backlog revision for the transition.",
                {"from": old_revision, "to": new_revision},
            )
        )

    old_status = _packet_status_snapshot(packet)
    new_status = {
        "theme": candidate.theme.get("status"),
        "epic": candidate.epic.get("status"),
        "story": candidate.story.get("status"),
    }
    if old_status is None:
        findings.append(
            _finding(
                "packet",
                "status-transition",
                "packet does not contain a complete prior status snapshot",
                "Regenerate a canonical packet before starting lifecycle work.",
            )
        )
        documented_story_transition = False
        evidence_added = False
        valid_parent_changes: list[tuple[str, object, object]] = []
    else:
        story_transition = (old_status["story"], new_status["story"])
        documented_story_transition = story_transition in STORY_STATUS_TRANSITIONS
        evidence_added = _has_append_only_evidence_addition(packet, candidate.story)
        valid_parent_changes = []
        for level in _parent_levels(packet):
            transition = (old_status[level], new_status[level])
            allowed = transition[0] == transition[1] or (
                transition in PARENT_STATUS_TRANSITIONS
            )
            if (
                story_transition == ("todo", "in-progress")
                and transition == ("todo", "todo")
            ):
                allowed = False
            if transition == ("todo", "in-progress") and new_status["story"] != "in-progress":
                allowed = False
            if transition == ("in-progress", "done") and new_status["story"] != "done":
                allowed = False
            if not allowed:
                findings.append(
                    _finding(
                        "packet",
                        f"status-transition.{level}",
                        f"{level} transition {transition!r} is not applicable",
                        "Apply only the parent transition corresponding to the story.",
                    )
                )
            elif transition[0] != transition[1]:
                valid_parent_changes.append((level, *transition))

        parent_completions = [
            level
            for level, before, after in valid_parent_changes
            if before != "done" and after == "done"
        ]
        if parent_completions and story_transition != ("done", "done"):
            findings.append(
                _finding(
                    "packet",
                    "status-transition.completion",
                    (
                        "story and parent completion cannot be reconciled in "
                        "the same backlog revision"
                    ),
                    (
                        "Reconcile story completion first with both parents "
                        "not done, then complete one parent in a later revision."
                    ),
                )
            )
        if len(parent_completions) > 1:
            findings.append(
                _finding(
                    "packet",
                    "status-transition.completion",
                    (
                        "epic and theme completion require distinct backlog "
                        "revisions"
                    ),
                    (
                        "Reconcile epic completion first, then reconcile theme "
                        "completion in a later revision."
                    ),
                )
            )
        if (
            "theme" in parent_completions
            and old_status["epic"] != "done"
        ):
            findings.append(
                _finding(
                    "packet",
                    "status-transition.theme",
                    "theme completion requires the epic to be done beforehand",
                    (
                        "Complete and reconcile the epic in an earlier "
                        "parent-only revision."
                    ),
                )
            )

        same_status_evidence_update = (
            story_transition == ("in-progress", "in-progress")
            and evidence_added
            and not valid_parent_changes
        )
        same_status_parent_completion = (
            story_transition == ("done", "done")
            and not evidence_added
            and len(valid_parent_changes) == 1
            and all(after == "done" for _level, _before, after in valid_parent_changes)
        )
        if not (
            documented_story_transition
            or same_status_evidence_update
            or same_status_parent_completion
        ):
            findings.append(
                _finding(
                    "packet",
                    "status-transition.story",
                    f"story transition {story_transition!r} is not authorized",
                    (
                        "Use a documented story transition, append evidence while "
                        "in progress, or complete parents after the story is done."
                    ),
                )
            )
        if not (
            documented_story_transition
            or evidence_added
            or valid_parent_changes
        ):
            findings.append(
                _finding(
                    "packet",
                    "reconciliation",
                    "newer backlog revision contains no authorized lifecycle change",
                    "Do not reconcile a no-op revision bump.",
                )
            )

    findings.extend(_evidence_reconciliation_findings(packet, candidate.story))
    if old_status is not None:
        findings.extend(
            _aggregate_done_findings(candidate, old_status, new_status)
        )

    reconciliations = packet.get("reconciliations")
    if (
        isinstance(reconciliations, list)
        and len(reconciliations) >= MAX_RECONCILIATIONS
    ):
        findings.append(
            _finding(
                "packet",
                "reconciliations",
                f"reconciliation history is bounded to {MAX_RECONCILIATIONS} records",
                "Close or replace the packet instead of extending its lifecycle.",
            )
        )
    parent_completion = len(valid_parent_changes) == 1 and any(
        after == "done" for _level, _before, after in valid_parent_changes
    )
    reason_parts = [
        name
        for name, present in (
            ("status-transition", documented_story_transition),
            ("evidence-update", evidence_added),
            ("parent-completion", parent_completion),
        )
        if present
    ]
    return findings, "+".join(reason_parts) or "status-transition"


def _has_append_only_evidence_addition(
    packet: Mapping[object, object],
    current_story: Mapping[object, object],
) -> bool:
    """Return true only when at least one evidence list has a valid append."""

    previous = packet.get("evidence-current")
    if not isinstance(previous, Mapping):
        return False
    current = _evidence_snapshot(current_story)
    added = False
    for key in EVIDENCE_KEYS:
        before = previous.get(key)
        after = current[key]
        if not isinstance(before, list) or after[: len(before)] != before:
            return False
        added = added or len(after) > len(before)
    return added


def _epic_runtime_findings(
    root: Path,
    backlog: Mapping[object, object],
    candidate: StoryCandidate,
) -> list[Finding]:
    completion, findings = _completion_index(root, backlog)
    if completion is None:
        return findings
    children = candidate.epic.get("stories", [])
    internal = {child["id"] for child in children}
    unmet = [
        dependency for dependency in _strings(candidate.theme.get("depends-on"))
        if dependency not in completion.themes
    ] + [
        dependency for dependency in _strings(candidate.epic.get("depends-on"))
        if dependency not in completion.epics
    ] + [
        dependency for child in children
        for dependency in _strings(child.get("depends-on"))
        if dependency not in internal and dependency not in completion.stories
    ]
    if candidate.theme.get("locked") is True:
        return [_finding(
            BACKLOG_PATH.as_posix(), candidate.story_id,
            "epic belongs to a locked theme",
            "Preserve the accepted theme; plan new work in a new theme.",
            {"theme": candidate.theme["id"], "locked": True},
        )]
    if unmet:
        return [_finding(
            BACKLOG_PATH.as_posix(), candidate.story_id,
            "epic external dependencies are unfinished",
            "Complete the named external dependencies before dispatch.",
            {"depends-on": unmet},
        )]
    return []


def _epic_backlog_delta_findings(
    packet: Mapping[object, object],
    backlog: Mapping[object, object],
    candidate: StoryCandidate,
) -> list[Finding]:
    """Permit only this epic's lifecycle delta, not unrelated backlog edits."""

    previous = packet.get("backlog-snapshot")
    if not isinstance(previous, Mapping):
        return [_finding(
            "packet", "backlog-snapshot", "epic backlog snapshot is missing",
            "Build an anchored epic packet before changing lifecycle state.",
        )]
    expected = copy.deepcopy(dict(previous))
    expected["revision"] = backlog.get("revision")
    expected["last-updated"] = backlog.get("last-updated")
    themes = expected.get("active-themes")
    if isinstance(themes, list):
        for theme in themes:
            if not isinstance(theme, dict) or theme.get("id") != candidate.theme.get("id"):
                continue
            theme["status"] = candidate.theme.get("status")
            for epic in theme.get("epics", []):
                if not isinstance(epic, dict) or epic.get("id") != candidate.story_id:
                    continue
                epic["status"] = candidate.epic.get("status")
                epic["evidence"] = copy.deepcopy(candidate.epic.get("evidence"))
                current_children = {
                    child["id"]: child for child in candidate.epic.get("stories", [])
                }
                if candidate.epic.get("status") == "done":
                    for child in epic.get("stories", []):
                        current_child = current_children.get(child.get("id"))
                        if current_child is not None and current_child.get("status") == "done":
                            child["status"] = "done"
    if expected != backlog:
        return [_finding(
            BACKLOG_PATH.as_posix(), "backlog-snapshot",
            "revision changes data outside the authorized epic lifecycle scope",
            "Reconcile only epic status/evidence and atomic child completion; "
            "build fresh authority for other edits.",
            stale=True,
        )]
    return []


def _is_expected_reconciliation_staleness(
    finding: Finding,
    packet: Mapping[object, object],
) -> bool:
    record = finding.get("record")
    message = str(finding.get("message"))
    if record in {"backlog.sha256", "backlog.revision", "composite-hash"}:
        return True
    if record == "story" and (
        "FIFO-eligible" in message
        or "current authoritative backlog data" in message
    ):
        return True
    if "current authoritative backlog data" in message:
        return True
    if isinstance(record, str) and re.fullmatch(r"sources\[[0-9]+\]\.sha256", record):
        sources = packet.get("sources")
        if isinstance(sources, list):
            index = int(record.split("[", 1)[1].split("]", 1)[0])
            if index < len(sources):
                source = sources[index]
                return (
                    isinstance(source, Mapping)
                    and source.get("path") == BACKLOG_PATH.as_posix()
                )
    return False


def _immutable_reconciliation_findings(
    root: Path,
    packet: Mapping[object, object],
    candidate: StoryCandidate,
    *,
    authority: StoryAuthority,
) -> list[Finding]:
    expected_mode = _authorized_mode(authority.agents)
    expected_story = _story_payload(candidate)
    actual_story = _unit(packet)
    expected_theme = {
        "id": candidate.theme["id"],
        "locked": candidate.theme["locked"],
        "vision-ref": candidate.theme.get("vision-ref"),
        "discovery-ref": candidate.theme.get("discovery-ref"),
        "requirements-ref": candidate.theme.get("requirements-ref"),
    }
    expected_epic = {
        "id": candidate.epic["id"],
        "depends-on": list(_strings(candidate.epic.get("depends-on"))),
    }
    comparisons: list[tuple[str, object, object]] = [
        (
            "story",
            (
                {key: value for key, value in actual_story.items() if key != "status"}
                if isinstance(actual_story, Mapping)
                else actual_story
            ),
            {key: value for key, value in expected_story.items() if key != "status"},
        ),
        (
            "theme",
            (
                {
                    key: value
                    for key, value in cast(Mapping[object, object], packet.get("theme", {})).items()
                    if key != "status"
                }
                if isinstance(packet.get("theme"), Mapping)
                else packet.get("theme")
            ),
            expected_theme,
        ),
        (
            "epic",
            (
                {
                    key: value
                    for key, value in cast(Mapping[object, object], packet.get("epic", {})).items()
                    if key != "status"
                }
                if isinstance(packet.get("epic"), Mapping)
                else packet.get("epic")
            ),
            expected_epic,
        ),
        (
            "dependencies",
            packet.get("dependencies"),
            {
                "theme": list(_strings(candidate.theme.get("depends-on"))),
                "epic": list(_strings(candidate.epic.get("depends-on"))),
                "story": list(_strings(candidate.story.get("depends-on"))),
            },
        ),
        ("risk", packet.get("risk"), candidate.story.get("risk")),
        ("model-route", packet.get("model-route"), candidate.story.get("model-route")),
        ("verification", packet.get("verification"), candidate.story.get("verification")),
        (
            "review-profile",
            packet.get("review-profile"),
            candidate.story.get("review-profile"),
        ),
        (
            "evidence-requirements",
            packet.get("evidence-requirements"),
            _evidence_requirements(candidate.story),
        ),
        ("mode", packet.get("mode"), expected_mode),
        (
            "story-frontmatter",
            packet.get("story-frontmatter"),
            _story_frontmatter_payload(authority),
        ),
        (
            "acceptance-criteria",
            packet.get("acceptance-criteria"),
            list(authority.acceptance_criteria),
        ),
        (
            "traceability",
            packet.get("traceability"),
            {
                key: list(values)
                for key, values in authority.traceability.items()
            },
        ),
        (
            "required-skills",
            packet.get("required-skills"),
            _required_skills(expected_mode or "planning", authority.skills),
        ),
        (
            "required-gates",
            packet.get("required-gates"),
            _required_gates(expected_mode or "planning", candidate.story),
        ),
        ("scope", packet.get("scope"), _scope(candidate, expected_mode)),
        (
            "expected-result-locations",
            packet.get("expected-result-locations"),
            _expected_result_locations(candidate.story),
        ),
        (
            "integration-boundary",
            packet.get("integration-boundary"),
            _integration_boundary(),
        ),
        ("required-report", packet.get("required-report"), _required_report()),
    ]
    findings: list[Finding] = []
    if candidate.epic_first:
        children = _epic_authority_payload(root, {}, candidate)["acceptance-children"]
        comparisons.append(("acceptance-children", packet.get("acceptance-children"), children))
    for field, actual, expected in comparisons:
        if actual != expected:
            findings.append(
                _finding(
                    "packet",
                    field,
                    "immutable packet authority changed since build",
                    "Restore the original authority or build a new packet.",
                    {"expected": expected, "actual": actual},
                    stale=True,
                )
            )

    packet_backlog = packet.get("backlog")
    packet_sources = packet.get("sources")
    expected_sources = _authoritative_sources(root, candidate, authority)
    if isinstance(packet_backlog, Mapping) and isinstance(packet_sources, list):
        old_hash = packet_backlog.get("sha256")
        adjusted_sources = []
        for source in expected_sources:
            adjusted = dict(source)
            if adjusted.get("path") == BACKLOG_PATH.as_posix():
                adjusted["sha256"] = old_hash
            adjusted_sources.append(adjusted)
        if packet_sources != adjusted_sources:
            findings.append(
                _finding(
                    "packet",
                    "sources",
                    "immutable authoritative source manifest changed",
                    "Restore unchanged source files or build a new packet.",
                    stale=True,
                )
            )
        clean_sources = [
            cast(Mapping[str, object], source)
            for source in packet_sources
            if isinstance(source, Mapping)
        ]
        if (
            len(clean_sources) != len(packet_sources)
            or packet.get("composite-hash") != _composite_hash(clean_sources)
        ):
            findings.append(
                _finding(
                    "packet",
                    "composite-hash",
                    "old packet source composite is invalid",
                    "Restore the original canonical packet.",
                    stale=True,
                )
            )
        backlog_sources = [
            source
            for source in clean_sources
            if source.get("path") == BACKLOG_PATH.as_posix()
        ]
        if (
            packet_backlog.get("path") != BACKLOG_PATH.as_posix()
            or not isinstance(old_hash, str)
            or SHA256_PATTERN.fullmatch(old_hash) is None
            or len(backlog_sources) != 1
            or backlog_sources[0].get("sha256") != old_hash
        ):
            findings.append(
                _finding(
                    "packet",
                    "backlog",
                    "old backlog metadata is not bound to its source entry",
                    "Restore the original canonical packet.",
                    stale=True,
                )
            )
    return findings


def _packet_status_snapshot(
    packet: Mapping[object, object],
) -> dict[str, object] | None:
    containers = {
        "theme": packet.get("theme"),
        "epic": packet.get("epic"),
        "story": _unit(packet),
    }
    if any(not isinstance(value, Mapping) for value in containers.values()):
        return None
    return {
        level: cast(Mapping[object, object], value).get("status")
        for level, value in containers.items()
    }


def _packet_evidence_findings(
    packet: Mapping[object, object],
) -> list[Finding]:
    """Validate the closed evidence snapshot/current/requirements schema."""

    findings: list[Finding] = []
    evidence_maps: dict[str, Mapping[object, object]] = {}
    for field in ("evidence-snapshot", "evidence-current"):
        value = packet.get(field)
        if not isinstance(value, Mapping) or set(value) != set(EVIDENCE_KEYS):
            findings.append(
                _finding(
                    "packet",
                    field,
                    f"{field} must contain exactly {', '.join(EVIDENCE_KEYS)}",
                    "Regenerate the packet from authoritative backlog evidence.",
                )
            )
            continue
        evidence_maps[field] = value
        for key in EVIDENCE_KEYS:
            entries = value.get(key)
            if (
                not isinstance(entries, list)
                or any(not isinstance(item, str) or not item.strip() for item in entries)
            ):
                findings.append(
                    _finding(
                        "packet",
                        f"{field}.{key}",
                        "evidence entries must be non-empty strings in a list",
                        "Regenerate the packet from schema-valid backlog evidence.",
                    )
                )

    snapshot = evidence_maps.get("evidence-snapshot")
    current = evidence_maps.get("evidence-current")
    if snapshot is not None and current is not None:
        for key in EVIDENCE_KEYS:
            before = snapshot.get(key)
            after = current.get(key)
            if (
                isinstance(before, list)
                and isinstance(after, list)
                and after[: len(before)] != before
            ):
                findings.append(
                    _finding(
                        "packet",
                        f"evidence-current.{key}",
                        "current evidence does not preserve the initial snapshot",
                        "Restore the append-only evidence history.",
                    )
                )

    requirements = packet.get("evidence-requirements")
    if (
        not isinstance(requirements, Mapping)
        or set(requirements) != {"verification", "review", "gitflow"}
        or not isinstance(requirements.get("verification"), list)
        or not requirements.get("verification")
        or any(
            not isinstance(item, str) or not item
            for item in cast(list[object], requirements.get("verification"))
        )
        or not isinstance(requirements.get("review"), Mapping)
        or requirements["review"].get("required") is not True
        or not isinstance(requirements["review"].get("profile"), str)
        or not isinstance(requirements.get("gitflow"), Mapping)
        or requirements["gitflow"].get("required") is not True
        or requirements["gitflow"].get("not-applicable")
        != "not-applicable: <rationale>"
    ):
        findings.append(
            _finding(
                "packet",
                "evidence-requirements",
                "evidence requirements do not match the closed v1 schema",
                "Regenerate requirements from verification and review controls.",
            )
        )
    return findings


def _evidence_reconciliation_findings(
    packet: Mapping[object, object],
    current_story: Mapping[object, object],
) -> list[Finding]:
    """Allow backlog evidence to grow, but never to remove or replace entries."""

    old = packet.get("evidence-current")
    current = _evidence_snapshot(current_story)
    findings: list[Finding] = []
    if not isinstance(old, Mapping):
        return findings
    for key in EVIDENCE_KEYS:
        before = old.get(key)
        after = current[key]
        if not isinstance(before, list) or after[: len(before)] != before:
            findings.append(
                _finding(
                    BACKLOG_PATH.as_posix(),
                    f"evidence.{key}",
                    "backlog evidence removal, replacement, or reordering is forbidden",
                    "Restore prior entries and append only new lifecycle evidence.",
                    {"before": before, "after": after},
                )
            )

    if current_story.get("status") == "done":
        requirements = _evidence_requirements(current_story)
        verification = current["verification"]
        waiver_checks = _verification_waiver_checks(current_story)
        required_checks = cast(list[str], requirements["verification"])
        for entry in verification:
            affected_checks = {
                check
                for check in required_checks
                if re.search(
                    rf"(?<![a-z0-9]){re.escape(check)}(?![a-z0-9])",
                    entry,
                    re.IGNORECASE,
                )
            }
            if FAILURE_EVIDENCE.search(entry) is not None and (
                not affected_checks or not affected_checks <= waiver_checks
            ):
                findings.append(
                    _finding(
                        BACKLOG_PATH.as_posix(),
                        "evidence.verification",
                        "failure-shaped verification evidence is not success proof",
                        (
                            "Append closed '<check> passed' evidence or use the "
                            "governed verification waiver contract."
                        ),
                        {"entry": entry},
                    )
                )
        for required in required_checks:
            passed = re.compile(
                rf"(?:{re.escape(required)} passed|{re.escape(required)}: passed)",
                re.IGNORECASE,
            )
            if required not in waiver_checks and not any(
                passed.fullmatch(item.strip()) for item in verification
            ):
                findings.append(
                    _finding(
                        BACKLOG_PATH.as_posix(),
                        "evidence.verification",
                        (
                            "done requires positive evidence for verification "
                            f"matrix entry {required!r}"
                        ),
                        (
                            "Append exact '<check> passed' or '<check>: passed' "
                            "evidence, or declare a governed waiver."
                        ),
                    )
                )
        review = current["review"]
        epic_first = EPIC_ID.fullmatch(str(current_story.get("id"))) is not None
        tokens = REVIEW_APPROVAL_TOKENS
        if epic_first:
            tokens = _epic_review_tokens(current_story)
        if not any(entry.strip().casefold() in tokens for entry in review):
            findings.append(
                _finding(
                    BACKLOG_PATH.as_posix(),
                    "evidence.review",
                    "done requires an exact review approval token",
                    (
                        f"Append one of {sorted(tokens)} as its own evidence entry."
                    ),
                )
            )
        gitflow = current["gitflow"]
        valid_gitflow = False
        for entry in gitflow:
            normalized = entry.strip()
            not_applicable = NOT_APPLICABLE_EVIDENCE.fullmatch(normalized)
            positive = normalized.casefold() in GITFLOW_SUCCESS_TOKENS
            if GITFLOW_FAILURE_EVIDENCE.search(normalized) is not None:
                findings.append(
                    _finding(
                        BACKLOG_PATH.as_posix(),
                        "evidence.gitflow",
                        "failure-shaped Gitflow evidence cannot authorize completion",
                        "Append a positive Gitflow result after resolving the failure.",
                        {"entry": entry},
                    )
                )
                continue
            claims_not_applicable = (
                normalized.lower().startswith("not applicable")
                or normalized.lower().startswith("not-applicable")
                or normalized.lower() in {"n/a", "na"}
            )
            if claims_not_applicable and not_applicable is None:
                findings.append(
                    _finding(
                        BACKLOG_PATH.as_posix(),
                        "evidence.gitflow",
                        (
                            "not-applicable Gitflow evidence requires an explicit "
                            "rationale"
                        ),
                        "Use 'not-applicable: <rationale>'.",
                        {"entry": entry},
                    )
                )
                continue
            if not_applicable is not None or positive:
                valid_gitflow = True
                continue
            findings.append(
                _finding(
                    BACKLOG_PATH.as_posix(),
                    "evidence.gitflow",
                    "Gitflow evidence does not contain a closed success result",
                    (
                        "Append exactly 'committed', 'merged', 'squash-merged', "
                        "or 'not-applicable: <rationale>'."
                    ),
                    {"entry": entry},
                )
            )
        if not valid_gitflow:
            findings.append(
                _finding(
                    BACKLOG_PATH.as_posix(),
                    "evidence.gitflow",
                    (
                        "done requires positive Gitflow evidence or a "
                        "not-applicable rationale"
                    ),
                    (
                        "Append exactly 'committed', 'merged', 'squash-merged', "
                        "or 'not-applicable: <rationale>'."
                    ),
                )
            )
    return findings


def _verification_waiver_checks(
    story: Mapping[object, object],
) -> set[str]:
    """Return checks covered by complete governed verification waivers."""

    verification = story.get("verification")
    waivers = (
        verification.get("waivers")
        if isinstance(verification, Mapping)
        else None
    )
    if not isinstance(waivers, list):
        return set()
    governed: set[str] = set()
    required = {"check", "authority", "reviewer", "rationale", "record"}
    for waiver in waivers:
        if (
            isinstance(waiver, Mapping)
            and set(waiver) == required
            and all(
                isinstance(waiver.get(field), str)
                and bool(cast(str, waiver.get(field)).strip())
                for field in required
            )
        ):
            governed.add(cast(str, waiver["check"]).strip().lower())
    return governed


def _aggregate_done_findings(
    candidate: StoryCandidate,
    old_status: Mapping[str, object],
    new_status: Mapping[str, object],
) -> list[Finding]:
    """Enforce aggregate Definition of Done for parent transitions."""

    findings: list[Finding] = []
    if old_status["epic"] != "done" and new_status["epic"] == "done":
        stories = candidate.epic.get("stories")
        unfinished = [
            str(story.get("id"))
            for story in (stories if isinstance(stories, list) else [])
            if isinstance(story, Mapping) and story.get("status") != "done"
        ]
        if unfinished:
            findings.append(
                _finding(
                    BACKLOG_PATH.as_posix(),
                    "definition-of-done.epic",
                    "epic cannot move to done while stories are unfinished",
                    "Complete every story in the epic before its done transition.",
                    {"unfinished": unfinished},
                )
            )
    if old_status["theme"] != "done" and new_status["theme"] == "done":
        epics = candidate.theme.get("epics")
        unfinished = [
            str(epic.get("id"))
            for epic in (epics if isinstance(epics, list) else [])
            if isinstance(epic, Mapping) and epic.get("status") != "done"
        ]
        if unfinished:
            findings.append(
                _finding(
                    BACKLOG_PATH.as_posix(),
                    "definition-of-done.theme",
                    "theme cannot move to done while epics are unfinished",
                    "Complete every epic in the theme before its done transition.",
                    {"unfinished": unfinished},
                )
            )
    return findings


def _reconciliation_schema_findings(
    packet: Mapping[object, object],
) -> list[Finding]:
    records = packet.get("reconciliations")
    if not isinstance(records, list):
        return [
            _finding(
                "packet",
                "reconciliations",
                "reconciliation history must be a list",
                "Regenerate the packet with the current method runtime.",
            )
        ]
    findings: list[Finding] = []
    if len(records) > MAX_RECONCILIATIONS:
        findings.append(
            _finding(
                "packet",
                "reconciliations",
                f"reconciliation history exceeds {MAX_RECONCILIATIONS} records",
                "Replace the packet instead of extending its bounded history.",
            )
        )
    previous: Mapping[object, object] | None = None
    for index, record in enumerate(records):
        path = f"reconciliations[{index}]"
        if not isinstance(record, Mapping) or set(record) != RECONCILIATION_FIELDS:
            findings.append(
                _finding(
                    "packet",
                    path,
                    "reconciliation record has missing or unknown fields",
                    "Restore the exact reconciliation record schema.",
                )
            )
            continue
        from_revision = record.get("from-revision")
        to_revision = record.get("to-revision")
        if (
            not isinstance(from_revision, int)
            or isinstance(from_revision, bool)
            or not isinstance(to_revision, int)
            or isinstance(to_revision, bool)
            or to_revision <= from_revision
        ):
            findings.append(
                _finding(
                    "packet",
                    f"{path}.revision",
                    "reconciliation revisions must increase",
                    "Restore the authoritative from/to revisions.",
                )
            )
        for field in ("from-backlog-sha256", "to-backlog-sha256"):
            digest = record.get(field)
            if not isinstance(digest, str) or SHA256_PATTERN.fullmatch(digest) is None:
                findings.append(
                    _finding(
                        "packet",
                        f"{path}.{field}",
                        "reconciliation backlog hash must be a SHA-256 digest",
                        "Restore the authoritative from/to backlog hashes.",
                    )
                )
        for field in ("from-status", "to-status"):
            status = record.get(field)
            if not isinstance(status, Mapping) or set(status) != STATUS_FIELDS:
                findings.append(
                    _finding(
                        "packet",
                        f"{path}.{field}",
                        "reconciliation status must contain theme, epic, and story",
                        "Restore the complete status snapshot.",
                    )
                )
        from_status = record.get("from-status")
        to_status = record.get("to-status")
        if isinstance(from_status, Mapping) and isinstance(to_status, Mapping):
            for field, allowed_values in (
                ("theme", {"todo", "in-progress", "done"}),
                ("epic", (
                    {"todo", "in-progress", "done", "failed", "blocked"}
                    if _epic_packet(packet) else {"todo", "in-progress", "done"}
                )),
                (
                    "story",
                    {"todo", "in-progress", "blocked", "failed", "done"},
                ),
            ):
                if (
                    from_status.get(field) not in allowed_values
                    or to_status.get(field) not in allowed_values
                ):
                    findings.append(
                        _finding(
                            "packet",
                            f"{path}.status.{field}",
                            "recorded status is outside the documented vocabulary",
                            "Restore statuses from the documented lifecycle machine.",
                        )
                    )
            story_transition = (
                from_status.get("story"),
                to_status.get("story"),
            )
            if (
                story_transition not in STORY_STATUS_TRANSITIONS
                and story_transition
                not in {("in-progress", "in-progress"), ("done", "done")}
            ):
                findings.append(
                    _finding(
                        "packet",
                        f"{path}.status.story",
                        "recorded story transition is not documented",
                        "Restore a transition from the documented status machine.",
                    )
                )
            for level in _parent_levels(packet):
                parent_transition = (
                    from_status.get(level),
                    to_status.get(level),
                )
                allowed_parent = (
                    parent_transition[0] == parent_transition[1]
                    or parent_transition in PARENT_STATUS_TRANSITIONS
                )
                if (
                    story_transition == ("todo", "in-progress")
                    and parent_transition == ("todo", "todo")
                ):
                    allowed_parent = False
                if (
                    parent_transition == ("todo", "in-progress")
                    and to_status.get("story") != "in-progress"
                ):
                    allowed_parent = False
                if (
                    parent_transition == ("in-progress", "done")
                    and to_status.get("story") != "done"
                ):
                    allowed_parent = False
                if not allowed_parent:
                    findings.append(
                        _finding(
                            "packet",
                            f"{path}.status.{level}",
                            "recorded parent transition is not applicable",
                            "Restore the parent transition matching the story.",
                        )
                    )
            parent_completions = [
                level
                for level in _parent_levels(packet)
                if (
                    from_status.get(level) != "done"
                    and to_status.get(level) == "done"
                )
            ]
            if parent_completions and story_transition != ("done", "done"):
                findings.append(
                    _finding(
                        "packet",
                        f"{path}.status.completion",
                        (
                            "recorded story and parent completion share one "
                            "backlog revision"
                        ),
                        (
                            "Restore separate story and parent completion "
                            "reconciliation records."
                        ),
                    )
                )
            if len(parent_completions) > 1:
                findings.append(
                    _finding(
                        "packet",
                        f"{path}.status.completion",
                        (
                            "recorded epic and theme completion share one "
                            "backlog revision"
                        ),
                        (
                            "Restore an epic completion record followed by a "
                            "later theme completion record."
                        ),
                    )
                )
            if (
                "theme" in parent_completions
                and from_status.get("epic") != "done"
            ):
                findings.append(
                    _finding(
                        "packet",
                        f"{path}.status.theme",
                        "recorded theme completion precedes epic completion",
                        (
                            "Restore an earlier parent-only epic completion "
                            "record."
                        ),
                    )
                )
        reason = record.get("reason")
        if reason not in RECONCILIATION_REASONS:
            findings.append(
                _finding(
                    "packet",
                    f"{path}.reason",
                    "reconciliation reason is outside the closed event vocabulary",
                    "Use the closed reconciliation reason vocabulary.",
                )
            )
        elif isinstance(from_status, Mapping) and isinstance(to_status, Mapping):
            story_transition = (
                from_status.get("story"),
                to_status.get("story"),
            )
            has_status_event = "status-transition" in cast(str, reason).split("+")
            has_parent_event = "parent-completion" in cast(str, reason).split("+")
            parent_completed = any(
                from_status.get(level) != "done" and to_status.get(level) == "done"
                for level in _parent_levels(packet)
            )
            if has_status_event != (story_transition in STORY_STATUS_TRANSITIONS):
                findings.append(
                    _finding(
                        "packet",
                        f"{path}.reason",
                        "reconciliation reason does not match its story transition",
                        "Restore the deterministic reconciliation event kind.",
                    )
                )
            if has_parent_event != parent_completed:
                findings.append(
                    _finding(
                        "packet",
                        f"{path}.reason",
                        "reconciliation reason does not match parent completion",
                        "Restore the deterministic reconciliation event kind.",
                    )
                )
            if (
                story_transition == ("in-progress", "in-progress")
                and reason != "evidence-update"
            ):
                findings.append(
                    _finding(
                        "packet",
                        f"{path}.reason",
                        "same-status in-progress reconciliation must be evidence-update",
                        "Restore the deterministic reconciliation event kind.",
                    )
                )
            if (
                story_transition == ("done", "done")
                and reason != "parent-completion"
            ):
                findings.append(
                    _finding(
                        "packet",
                        f"{path}.reason",
                        "same-status done reconciliation must be parent-completion",
                        "Restore the deterministic reconciliation event kind.",
                    )
                )
        if not _is_offset_timestamp(record.get("timestamp")):
            findings.append(
                _finding(
                    "packet",
                    f"{path}.timestamp",
                    "reconciliation timestamp must include an ISO-8601 offset",
                    "Restore an attributable reconciliation timestamp.",
                )
            )
        if previous is not None:
            links = (
                ("revision", previous.get("to-revision"), from_revision),
                (
                    "backlog-sha256",
                    previous.get("to-backlog-sha256"),
                    record.get("from-backlog-sha256"),
                ),
                ("status", previous.get("to-status"), record.get("from-status")),
            )
            for field, prior, current in links:
                if prior != current:
                    findings.append(
                        _finding(
                            "packet",
                            f"{path}.from-{field}",
                            "reconciliation history is not a contiguous chain",
                            "Restore the append-only reconciliation sequence.",
                        )
                    )
        previous = record
    if records and isinstance(records[-1], Mapping):
        final = cast(Mapping[object, object], records[-1])
        backlog = packet.get("backlog")
        status = _packet_status_snapshot(packet)
        if (
            not isinstance(backlog, Mapping)
            or final.get("to-revision") != backlog.get("revision")
            or final.get("to-backlog-sha256") != backlog.get("sha256")
            or final.get("to-status") != status
        ):
            findings.append(
                _finding(
                    "packet",
                    "reconciliations[-1]",
                    "latest reconciliation does not match packet current state",
                    "Restore the packet state bound by its latest reconciliation.",
                )
            )
    return findings


def _reconciliation_failure(
    packet: Mapping[object, object],
    findings: Sequence[Finding],
    message: str,
) -> PacketResult:
    return PacketResult(
        exits.VALIDATION_FAILURE,
        {
            "command": "packet",
            "action": "reconcile",
            "status": "reconciliation-refused",
            "story": _story_value(packet),
            "message": message,
            "findings": list(findings),
        },
        tuple(f"method packet reconcile: {item['message']}" for item in findings),
    )


def _workspace_contract_findings(
    repository_root: Path,
    packet: Mapping[object, object],
    *,
    expected_allowed_root: Path,
    expected_mode: str | None,
) -> list[Finding]:
    workspace = packet.get("workspace")
    if not isinstance(workspace, Mapping):
        return [
            _finding(
                "packet",
                "workspace",
                "packet must declare a workspace contract",
                "Regenerate the packet with planning and implementation roots.",
            )
        ]
    expected_keys = {
        "planning-roots",
        "allowed-implementation-root",
        "implementation-root",
        "permitted-actions",
        "mutation-scope",
        "denied-paths",
    }
    findings: list[Finding] = []
    if set(workspace) != expected_keys:
        findings.append(
            _finding(
                "packet",
                "workspace",
                "workspace capability grant has missing or unknown fields",
                "Regenerate the packet with the exact workspace schema.",
            )
        )
    roots = workspace.get("planning-roots")
    planning_paths: list[Path] = []
    if not isinstance(roots, list) or not roots:
        findings.append(
            _finding(
                "packet",
                "workspace.planning-roots",
                "workspace must contain readable planning root grants",
                "Regenerate with the authoritative repository planning root.",
            )
        )
    else:
        for index, item in enumerate(roots):
            if (
                not isinstance(item, Mapping)
                or set(item) != {"path", "access"}
                or item.get("access") != "read-only"
            ):
                findings.append(
                    _finding(
                        "packet",
                        f"workspace.planning-roots[{index}]",
                        "planning root must be an exact read-only path grant",
                        "Regenerate the packet workspace contract.",
                    )
                )
                continue
            planning = _canonical_workspace_directory(
                item.get("path"),
                f"workspace.planning-roots[{index}].path",
                findings,
            )
            if planning is not None:
                planning_paths.append(planning)
    canonical_root = repository_root.resolve(strict=True)
    if planning_paths != [canonical_root]:
        findings.append(
            _finding(
                "packet",
                "workspace.planning-roots",
                (
                    "planning roots must be exactly the authoritative "
                    "repository root"
                ),
                "Regenerate with only the exact repository root as planning input.",
            )
        )

    allowed_value = workspace.get("allowed-implementation-root")
    implementation_value = workspace.get("implementation-root")
    allowed = _canonical_workspace_directory(
        allowed_value,
        "workspace.allowed-implementation-root",
        findings,
    )
    implementation = _canonical_workspace_directory(
        implementation_value,
        "workspace.implementation-root",
        findings,
    )
    if allowed is not None and allowed != expected_allowed_root:
        findings.append(
            _finding(
                "packet",
                "workspace.allowed-implementation-root",
                (
                    "packet allowed implementation root does not match the "
                    "caller-authorized boundary"
                ),
                "Use a packet built for the caller-authorized implementation root.",
                {
                    "expected": expected_allowed_root.as_posix(),
                    "actual": allowed.as_posix(),
                },
                stale=True,
            )
        )
    if allowed is not None:
        if _is_broad_allowed_root(allowed, canonical_root) or any(
            _paths_overlap(allowed, planning) for planning in planning_paths
        ):
            findings.append(
                _finding(
                    "packet",
                    "workspace.allowed-implementation-root",
                    "allowed implementation root is overly broad",
                    "Use a dedicated implementation workspace excluding planning roots.",
                )
            )
        if implementation is not None and not _is_within(implementation, allowed):
            findings.append(
                _finding(
                    "packet",
                    "workspace.implementation-root",
                    "implementation root is outside allowed implementation root",
                    "Regenerate within the explicit implementation boundary.",
                )
            )
    if implementation is not None:
        for planning in planning_paths:
            if _paths_overlap(implementation, planning):
                findings.append(
                    _finding(
                        "packet",
                        "workspace.implementation-root",
                        "implementation root overlaps a planning root",
                        "Use disjoint planning and implementation workspaces.",
                    )
                )
                break

    expected_actions = (
        ["read", "write-implementation", "test", "review"]
        if expected_mode == "developer"
        else ["read", "propose"]
        if expected_mode == "planning"
        else None
    )
    expected_scope = (
        [implementation.as_posix()]
        if expected_mode == "developer" and implementation is not None
        else []
    )
    expected_denied = (
        [implementation.as_posix()]
        if expected_mode == "planning" and implementation is not None
        else [path.as_posix() for path in planning_paths]
        if expected_mode == "developer"
        else None
    )
    scope_paths = _canonical_workspace_path_list(
        workspace.get("mutation-scope"),
        "workspace.mutation-scope",
        findings,
    )
    denied_paths = _canonical_workspace_path_list(
        workspace.get("denied-paths"),
        "workspace.denied-paths",
        findings,
    )
    actual_values = (
        ("permitted-actions", workspace.get("permitted-actions"), expected_actions),
        (
            "mutation-scope",
            [path.as_posix() for path in scope_paths],
            expected_scope,
        ),
        (
            "denied-paths",
            [path.as_posix() for path in denied_paths],
            expected_denied,
        ),
    )
    for field, actual, expected in actual_values:
        if expected is not None and actual != expected:
            findings.append(
                _finding(
                    "packet",
                    f"workspace.{field}",
                    (
                        f"{expected_mode} workspace {field} does not match "
                        "its capability schema"
                    ),
                    "Regenerate the packet; do not broaden workspace capabilities.",
                )
            )
    return findings


def _canonical_workspace_directory(
    value: object,
    record: str,
    findings: list[Finding],
) -> Path | None:
    if not isinstance(value, str):
        findings.append(
            _finding(
                "packet",
                record,
                "workspace path must be a canonical resolved absolute string",
                "Regenerate the packet with canonical workspace paths.",
            )
        )
        return None
    raw = Path(value)
    if not raw.is_absolute():
        findings.append(
            _finding(
                "packet",
                record,
                "workspace path is relative, not canonical absolute",
                "Regenerate the packet with canonical workspace paths.",
            )
        )
        return None
    try:
        resolved = raw.resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        findings.append(
            _finding(
                "packet",
                record,
                "workspace path is missing or cannot be resolved",
                "Restore the path and regenerate the packet.",
            )
        )
        return None
    if value != resolved.as_posix() or not resolved.is_dir():
        findings.append(
            _finding(
                "packet",
                record,
                (
                    "workspace path is not its canonical resolved absolute "
                    "directory path"
                ),
                "Remove relative segments and symlink aliases, then regenerate.",
                {"canonical": resolved.as_posix()},
            )
        )
    return resolved if resolved.is_dir() else None


def _canonical_workspace_path_list(
    value: object,
    record: str,
    findings: list[Finding],
) -> list[Path]:
    if not isinstance(value, list):
        findings.append(
            _finding(
                "packet",
                record,
                "workspace path grant must be a list",
                "Regenerate the packet with the exact workspace schema.",
            )
        )
        return []
    paths: list[Path] = []
    for index, item in enumerate(value):
        path = _canonical_workspace_directory(
            item,
            f"{record}[{index}]",
            findings,
        )
        if path is not None:
            paths.append(path)
    return paths


def _workspace_findings(
    repository_root: Path,
    packet: Mapping[object, object],
    *,
    expected_allowed_root: Path,
) -> list[Finding]:
    workspace = packet.get("workspace")
    if not isinstance(workspace, Mapping):
        return []
    findings: list[Finding] = []
    roots = workspace.get("planning-roots")
    if not isinstance(roots, list) or not roots:
        findings.append(
            _finding(
                "workspace",
                "planning-roots",
                "packet has no readable planning roots",
                "Regenerate with at least one authoritative planning root.",
            )
        )
    else:
        for index, planning_root in enumerate(roots):
            path = (
                planning_root.get("path")
                if isinstance(planning_root, Mapping)
                else None
            )
            resolved = _canonical_existing_directory(path)
            if resolved is None or not os.access(resolved, os.R_OK | os.X_OK):
                findings.append(
                    _finding(
                        "workspace",
                        f"planning-roots[{index}]",
                        f"planning root {path!r} is not readable",
                        "Mount or expose the authoritative planning workspace before dispatch.",
                    )
                )
    implementation = workspace.get("implementation-root")
    implementation_path = _canonical_existing_directory(implementation)
    if implementation_path is None or not os.access(implementation_path, os.W_OK | os.X_OK):
        findings.append(
            _finding(
                "workspace",
                "implementation-root",
                f"implementation root {implementation!r} is absent or not writable",
                "Create or mount the writable implementation checkout before dispatch.",
            )
        )
    allowed = workspace.get("allowed-implementation-root")
    allowed_path = _canonical_existing_directory(allowed)
    if allowed_path is None or allowed_path != expected_allowed_root:
        findings.append(
            _finding(
                "workspace",
                "allowed-implementation-root",
                f"allowed implementation root {allowed!r} is absent or unreadable",
                "Create or mount the bounded implementation workspace before dispatch.",
            )
        )
    return findings


def _canonical_existing_directory(value: object) -> Path | None:
    if not isinstance(value, str):
        return None
    raw = Path(value)
    if not raw.is_absolute():
        return None
    try:
        resolved = raw.resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        return None
    if value != resolved.as_posix() or not resolved.is_dir():
        return None
    return resolved


def _source(root: Path, relative: str, *, trust: str) -> dict[str, object]:
    path = _source_path(root, relative)
    if path is None:
        raise ValueError(f"source {relative!r} is not a repository file")
    return {
        "path": relative,
        "trust": trust,
        "sha256": _sha256_file(path),
        "git-revision": _git_blob_revision(root, relative),
    }


def _source_path(root: Path, value: object) -> Path | None:
    if not isinstance(value, str):
        return None
    pure = PurePosixPath(value)
    if pure.is_absolute() or "." in pure.parts or ".." in pure.parts:
        return None
    try:
        candidate = root.joinpath(*pure.parts)
        if _has_symlink_component(root, candidate):
            return None
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root.resolve(strict=True))
    except (OSError, RuntimeError, ValueError):
        return None
    return resolved if resolved.is_file() and not resolved.is_symlink() else None


def _git_blob_revision(root: Path, relative: str) -> str | None:
    git = root / ".git"
    if not git.exists():
        return None
    try:
        import subprocess

        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", f"HEAD:{relative}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
    except OSError:
        return None
    value = result.stdout.strip()
    return value if result.returncode == 0 and re.fullmatch(r"[0-9a-f]{40}", value) else None


def _composite_hash(sources: Sequence[Mapping[str, object]]) -> str:
    lines = sorted(
        f"{source.get('path')}:{source.get('sha256')}"
        for source in sources
        if isinstance(source.get("path"), str) and isinstance(source.get("sha256"), str)
    )
    return "sha256:" + hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _nested(mapping: Mapping[object, object], *keys: str) -> object:
    value: object = mapping
    for key in keys:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value


def _display(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _story_value(packet: Mapping[object, object]) -> object:
    story = _unit(packet)
    return story.get("id") if isinstance(story, Mapping) else None


def _has_stale(findings: Sequence[Finding]) -> bool:
    return any(finding.get("stale") is True for finding in findings)


def _finding(
    file: str,
    record: str,
    message: str,
    remediation: str,
    details: Mapping[str, object] | None = None,
    *,
    stale: bool = False,
) -> Finding:
    finding: Finding = {
        "file": file,
        "record": record,
        "message": f"{record}: {message}",
        "remediation": remediation,
    }
    if details is not None:
        finding["details"] = _json_safe(details)
    if stale:
        finding["stale"] = True
    return finding


def _json_safe(value: object, active: set[int] | None = None) -> object:
    """Convert defensive diagnostic detail into a value json.dumps can emit."""

    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    if active is None:
        active = set()
    if isinstance(value, Mapping):
        identity = id(value)
        if identity in active:
            return "<recursive>"
        active.add(identity)
        try:
            return {
                str(key): _json_safe(item, active)
                for key, item in value.items()
            }
        finally:
            active.remove(identity)
    if isinstance(value, (list, tuple, set, frozenset)):
        identity = id(value)
        if identity in active:
            return "<recursive>"
        active.add(identity)
        try:
            return [_json_safe(item, active) for item in value]
        finally:
            active.remove(identity)
    return str(value)


def _failed(
    status: str,
    message: str,
    remediation: str,
    findings: Sequence[Finding] = (),
    *,
    backlog: Mapping[object, object] | None = None,
    root: Path | None = None,
    action: str | None = None,
) -> PacketResult:
    payload: dict[str, object] = {
        "command": "packet",
        "status": status,
        "message": message,
        "remediation": remediation,
        "findings": list(findings),
    }
    if action is not None:
        payload["action"] = action
    if backlog is not None and root is not None:
        payload["backlog_revision"] = backlog.get("revision")
        try:
            payload["backlog_sha256"] = _sha256_file(root / BACKLOG_PATH)
        except (OSError, RuntimeError, ValueError) as error:
            payload["backlog_sha256"] = None
            payload["backlog_enrichment_error"] = str(error)
    return PacketResult(
        exits.VALIDATION_FAILURE,
        payload,
        (f"method packet: {message}",),
    )


def _verification_load_failure(
    action: str,
    result: PacketResult,
) -> PacketResult:
    payload = dict(result.payload)
    payload["command"] = "packet"
    payload["action"] = action
    payload["status"] = (
        "packet-invalid"
        if action == "verify"
        else "reconciliation-refused"
        if action == "reconcile"
        else "preflight-refused"
    )
    return PacketResult(result.exit_code, payload, result.diagnostics)


__all__ = [
    "PACKET_VERSION",
    "PacketResult",
    "build_packet",
    "preflight_packet",
    "project_next",
    "reconcile_packet",
    "verify_packet",
]
