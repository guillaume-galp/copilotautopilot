from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from test_method_trace import (
    STORY_PATH,
    make_repository,
    story_text,
    trace,
    write,
    write_architecture_trace,
)


EPIC_PATH = "docs/themes/TH9-trace/epics/E1-trace/README.md"
MINIMAL_TRACE = """traceability:
  vision: []
  requirements: [PR-001]
  adrs: []
  invariants: []"""


def make_epic_repository(
    base: Path,
    *,
    epic_type: str = "standard",
    traceability: str = MINIMAL_TRACE,
    child: str | None = None,
    status: str = "done",
) -> Path:
    root = make_repository(base)
    backlog_path = root / trace.BACKLOG_PATH
    document = yaml.safe_load(backlog_path.read_text())
    theme = document["backlog"]["active-themes"][0]
    theme["schema-version"] = 3
    previous = theme["epics"][0]["stories"][0]
    epic = {
        "id": "TH9.E1",
        "file": EPIC_PATH,
        "status": status,
        "evidence": previous["evidence"],
    }
    theme["epics"] = [epic]
    write(
        root,
        EPIC_PATH,
        story_text(story_type=epic_type, traceability=traceability).replace(
            "id: TH9.E1.US1", "id: TH9.E1"
        ),
    )
    if child is None:
        (root / STORY_PATH).unlink()
    else:
        epic["stories"] = [{"id": "TH9.E1.US1", "file": STORY_PATH}]
        write(root, STORY_PATH, child)
    write(root, trace.BACKLOG_PATH.as_posix(), yaml.safe_dump(document))
    return root


def messages(result: trace.ValidationResult) -> str:
    return "\n".join(str(finding["message"]) for finding in result.findings)


@pytest.mark.parametrize("epic_type", ["standard", "spike"])
@pytest.mark.parametrize("empty_stories", [False, True])
def test_epic_without_stories_accepts_empty_inapplicable_trace_lists(
    tmp_path: Path, epic_type: str, empty_stories: bool
):
    root = make_epic_repository(tmp_path, epic_type=epic_type)
    if empty_stories:
        path = root / trace.BACKLOG_PATH
        backlog = yaml.safe_load(path.read_text())
        backlog["backlog"]["active-themes"][0]["epics"][0]["stories"] = []
        write(root, trace.BACKLOG_PATH.as_posix(), yaml.safe_dump(backlog))

    result = trace.validate_repository(root)

    assert result.valid, result.findings
    assert any(node.identifier == "TH9.E1" and node.kind == "epic" for node in result.nodes)
    assert not any(node.kind == "story" for node in result.nodes)
    assert trace.Edge("PR-001", "TH9.E1", "VP9") in result.edges


@pytest.mark.parametrize(
    ("traceability", "expected"),
    [
        (MINIMAL_TRACE.replace("[PR-001]", "[]"), "requirements must contain"),
        (MINIMAL_TRACE.replace("  vision: []\n", ""), "traceability.vision must be a YAML list"),
        (MINIMAL_TRACE.replace("adrs: []", "adrs: [PR-001]"), "invalid prefix"),
        (MINIMAL_TRACE.replace("[PR-001]", "[PR-999]"), "declared reference PR-999 does not resolve"),
        (MINIMAL_TRACE.replace("vision: []", "vision: [VO-999]"), "declared reference VO-999 does not resolve"),
        (MINIMAL_TRACE.replace("adrs: []", "adrs: [ADR-999]"), "declared reference ADR-999 does not resolve"),
        (MINIMAL_TRACE.replace("invariants: []", "invariants: [INV-999]"), "declared reference INV-999 does not resolve"),
        (MINIMAL_TRACE + "\n  invented: []", "undefined traceability key"),
    ],
)
@pytest.mark.parametrize("epic_type", ["standard", "spike"])
def test_epic_declared_references_remain_strict(
    tmp_path: Path, traceability: str, expected: str, epic_type: str
):
    root = make_epic_repository(
        tmp_path, traceability=traceability, epic_type=epic_type
    )
    result = trace.validate_repository(root)
    assert not result.valid
    assert expected in messages(result)


def test_epic_full_trace_resolves_only_canonical_sources(tmp_path: Path):
    root = make_epic_repository(
        tmp_path,
        traceability=MINIMAL_TRACE.replace("adrs: []", "adrs: [ADR-009]"),
    )
    assert trace.validate_repository(root).valid
    write(root, "docs/ADRs/ADR-009-trace.md", "# Unrelated notes\n\nMention ADR-009 here.\n")
    result = trace.validate_repository(root)
    assert not result.valid
    assert "declared reference ADR-009 does not resolve" in messages(result)


@pytest.mark.parametrize(
    ("child_trace", "expected"),
    [
        ("", None),
        (MINIMAL_TRACE, None),
        (MINIMAL_TRACE.replace("[PR-001]", "[PR-999]"), "declared reference PR-999 does not resolve"),
        (MINIMAL_TRACE.replace("adrs: []", "adrs: [VO-001]"), "invalid prefix"),
        ("traceability: null", "missing or not a mapping"),
    ],
)
def test_optional_child_needs_no_governance_but_validates_declared_trace(
    tmp_path: Path, child_trace: str, expected: str | None
):
    child = (
        "---\nid: TH9.E1.US1\ntitle: Implementation detail\n"
        "acceptance-criteria:\n  - AC1: Accept the slice\n"
        f"{child_trace}\n---\n"
    )
    root = make_epic_repository(tmp_path, child=child)
    result = trace.validate_repository(root)
    assert any(node.identifier == "TH9.E1.US1" and node.kind == "story" for node in result.nodes)
    assert not any(node.identifier.startswith("evidence:TH9.E1.US1:") for node in result.nodes)
    if expected is None:
        assert result.valid, result.findings
    else:
        assert not result.valid
        assert expected in messages(result)


@pytest.mark.parametrize("status", ["not-started", "in-progress", "done"])
def test_epic_evidence_paths_and_status_gates(tmp_path: Path, status: str):
    root = make_epic_repository(tmp_path, status=status)
    path = root / trace.BACKLOG_PATH
    document = yaml.safe_load(path.read_text())
    evidence = document["backlog"]["active-themes"][0]["epics"][0]["evidence"]
    evidence["packets"] = ["docs/plan/runtime/packets/TH9.E1/"]
    write(root, trace.BACKLOG_PATH.as_posix(), yaml.safe_dump(document))

    result = trace.validate_repository(root)
    assert result.valid, result.findings
    assert any(node.kind == "evidence" for node in result.nodes) == (status != "not-started")
    assert not any(":packets:" in node.identifier for node in result.nodes)

    evidence["packets"] = ["docs/plan/runtime/packets/TH9.E2/"]
    write(root, trace.BACKLOG_PATH.as_posix(), yaml.safe_dump(document))
    result = trace.validate_repository(root)
    assert "packet evidence path does not match" in messages(result)


def test_architecture_mapping_accepts_epic_without_fabricating_story(tmp_path: Path):
    root = make_epic_repository(tmp_path)
    write_architecture_trace(
        root,
        """  - records: [DEC-001, INV-001]
    theme: TH9
    requirements: [PR-001]
    adrs: [ADR-009]
    components: [docs/architecture/components.md#validator]
    stories: [TH9.E1]""",
    )
    result = trace.validate_repository(root)
    assert result.valid, result.findings
    assert trace.Edge("docs/architecture/components.md#validator", "TH9.E1", "VP9") in result.edges

    path = root / trace.ARCHITECTURE_TRACE_PATH
    write(root, trace.ARCHITECTURE_TRACE_PATH.as_posix(), path.read_text().replace("stories: [TH9.E1]", "stories: [TH9.E2]"))
    result = trace.validate_repository(root)
    assert "TH9.E2 does not resolve in mapped theme TH9" in messages(result)


def test_existing_epic_packet_directory_creates_epic_evidence_edge(tmp_path: Path):
    root = make_epic_repository(tmp_path)
    packet_path = "docs/plan/runtime/packets/TH9.E1/"
    write(root, packet_path + "manifest.yaml", "schema-version: 1\n")
    path = root / trace.BACKLOG_PATH
    document = yaml.safe_load(path.read_text())
    document["backlog"]["active-themes"][0]["epics"][0]["evidence"]["packets"] = [packet_path]
    write(root, trace.BACKLOG_PATH.as_posix(), yaml.safe_dump(document))

    result = trace.validate_repository(root)
    assert result.valid, result.findings
    assert trace.Edge("TH9.E1", "evidence:TH9.E1:packets:1", "VP9") in result.edges


def test_unlisted_epic_is_inventory_error_and_declared_trace_is_validated(tmp_path: Path):
    root = make_epic_repository(tmp_path)
    write(
        root,
        EPIC_PATH.replace("E1-trace", "E2-trace"),
        story_text(traceability=MINIMAL_TRACE.replace("[PR-001]", "[PR-999]")).replace(
            "id: TH9.E1.US1", "id: TH9.E2"
        ),
    )
    result = trace.validate_repository(root)
    assert not result.valid
    assert "epic file under unlocked TH9 root is not listed" in messages(result)
    assert "declared reference PR-999 does not resolve" in messages(result)


def test_mixed_epic_and_legacy_themes_keep_legacy_trace_rules(tmp_path: Path):
    root = make_epic_repository(tmp_path)
    path = root / trace.BACKLOG_PATH
    document = yaml.safe_load(path.read_text())
    epic_theme = document["backlog"]["active-themes"][0]
    legacy_path = STORY_PATH.replace("TH9-trace", "TH10-trace")
    legacy_theme = {
        key: value for key, value in epic_theme.items()
        if key not in {"id", "schema-version", "epics"}
    }
    legacy_theme.update({
        "id": "TH10",
        "schema-version": 2,
        "epics": [{"stories": [{
            "id": "TH10.E1.US1",
            "file": legacy_path,
            "status": "done",
            "evidence": deepcopy(epic_theme["epics"][0]["evidence"]),
        }]}],
    })
    document["backlog"]["active-themes"].append(legacy_theme)
    write(root, trace.BACKLOG_PATH.as_posix(), yaml.safe_dump(document))
    write(root, legacy_path, story_text().replace("TH9.E1.US1", "TH10.E1.US1"))
    result = trace.validate_repository(root)
    assert result.valid, result.findings
    assert {(node.identifier, node.kind) for node in result.nodes} >= {
        ("TH9.E1", "epic"), ("TH10.E1.US1", "story"),
    }

    write(root, legacy_path, story_text(traceability=MINIMAL_TRACE).replace("TH9.E1.US1", "TH10.E1.US1"))
    result = trace.validate_repository(root)
    assert not result.valid
    assert "standard story traceability.vision must contain" in messages(result)
