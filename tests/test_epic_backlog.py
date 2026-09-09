"""Prospective executable-epic schema without rewriting legacy fixtures."""

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from test_method_backlog import (
    ROOT,
    backlog,
    independently_read_skill_contract,
    v2_archive_theme,
    v2_story,
    v2_theme,
    valid_backlog,
    write_repository,
)


EPIC_PATH = "docs/themes/TH3-current/epics/E1-schema/README.md"


def v3_epic() -> dict:
    epic = v2_story(EPIC_PATH)
    epic["id"] = "TH3.E1"
    epic["name"] = epic.pop("title")
    epic["evidence"]["packets"] = ["docs/plan/runtime/packets/TH3.E1/"]
    return epic


def v3_child(number: int = 1, *, status: str = "todo") -> dict:
    return {
        "id": f"TH3.E1.US{number}",
        "title": f"Acceptance slice {number}",
        "status": status,
        "file": "stories/US1.md",
        "depends-on": [],
    }


def v3_theme() -> dict:
    theme = v2_theme()
    theme["schema-version"] = 3
    theme["epics"] = [v3_epic()]
    return theme


def v3_backlog() -> dict:
    document = valid_backlog()
    document["backlog"]["active-themes"] = [v3_theme()]
    return document


def epic_repository(base: Path, document: dict | None = None) -> Path:
    root = write_repository(base, v3_backlog() if document is None else document)
    epic_file = root / EPIC_PATH
    epic_file.parent.mkdir(parents=True)
    epic_file.write_text(
        "---\nid: TH3.E1\ntitle: Schema story\ntype: standard\n"
        "traceability:\n  vision: []\n  requirements: [PR-001]\n"
        "  adrs: []\n  invariants: []\n"
        "acceptance-criteria:\n  - AC1: Validate executable epics\n---\n",
        encoding="utf-8",
    )
    return root


def messages(result: backlog.ValidationResult) -> str:
    return "\n".join(str(finding["message"]) for finding in result.findings)


@pytest.mark.parametrize("children", [None, [], [v3_child()]])
def test_v3_accepts_zero_or_lean_children_without_changing_root(tmp_path, children):
    document = v3_backlog()
    epic = document["backlog"]["active-themes"][0]["epics"][0]
    if children is not None:
        epic["stories"] = children
    root = epic_repository(tmp_path, document)
    originals = {
        path: path.read_bytes()
        for path in (root / "docs/plan/backlog-archive").glob("*.yaml")
    }

    result = backlog.validate_repository(root)

    assert result.valid, result.findings
    assert document["backlog"]["schema-version"] == 2
    assert all(path.read_bytes() == content for path, content in originals.items())
    assert backlog._iter_entities([v3_theme()])[2] == []


def test_v3_contract_has_all_required_executable_and_lean_keys():
    contract = independently_read_skill_contract()
    schemas = contract["schemas"]
    assert set(schemas["epic-v3"]["required"]) == set(v3_epic())
    assert schemas["epic-v3"]["optional"] == ["stories"]
    assert set(schemas["story-v3"]["required"]) == set(v3_child())
    assert set(schemas["theme-v3"]["required"]) == set(v3_theme())
    assert schemas["backlog-v2"]["properties"]["schema-version"]["enum"] == [2]
    assert schemas["archived-theme"]["properties"]["schema-version"]["enum"] == [1, 2, 3]
    assert contract["status-vocabulary"]["v3"]["epic"] == [
        "todo", "in-progress", "blocked", "failed", "done"
    ]


@pytest.mark.parametrize("status", ["todo", "in-progress", "blocked", "failed", "done"])
def test_v3_epic_status_vocabulary(tmp_path, status):
    document = v3_backlog()
    document["backlog"]["active-themes"][0]["epics"][0]["status"] = status
    result = backlog.validate_repository(epic_repository(tmp_path, document))
    assert result.valid, result.findings


@pytest.mark.parametrize("key", list(v3_epic()))
def test_v3_epic_requires_each_executable_field(tmp_path, key):
    document = v3_backlog()
    del document["backlog"]["active-themes"][0]["epics"][0][key]
    result = backlog.validate_repository(epic_repository(tmp_path, document))
    assert not result.valid
    assert f"backlog.active-themes[0].epics[0].{key}: required key" in messages(result)


@pytest.mark.parametrize("key", list(v3_child()))
def test_v3_child_requires_only_lean_fields(tmp_path, key):
    document = v3_backlog()
    child = v3_child()
    del child[key]
    document["backlog"]["active-themes"][0]["epics"][0]["stories"] = [child]
    result = backlog.validate_repository(epic_repository(tmp_path, document))
    assert not result.valid
    assert f"stories[0].{key}: required key" in messages(result)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("status", "paused"),
        ("priority", "urgent"),
        ("stories", None),
        ("confidence", "high"),
        ("confidence", "medium"),
        ("confidence", "low"),
        ("invented", True),
        ("risk", {}),
        ("model-route", {}),
        ("verification", {}),
        ("review-profile", "unreviewed"),
        ("budgets", {}),
        ("evidence", {}),
    ],
)
def test_v3_rejects_invalid_or_missing_governance(tmp_path, key, value):
    document = v3_backlog()
    document["backlog"]["active-themes"][0]["epics"][0][key] = value
    result = backlog.validate_repository(epic_repository(tmp_path, document))
    assert not result.valid
    assert f"epics[0].{key}" in messages(result)


@pytest.mark.parametrize(
    ("key", "value"),
    [("value", None), ("value", True), ("value", -1), ("source", "none"),
     ("source", " "), ("sampled-at", None), ("sampled-at", "2026-09-09T09:00:00")],
)
def test_v3_retains_measured_usage_strictness(tmp_path, key, value):
    document = v3_backlog()
    document["backlog"]["active-themes"][0]["epics"][0]["usage"][key] = value
    result = backlog.validate_repository(epic_repository(tmp_path, document))
    assert not result.valid
    assert f"usage.{key}" in messages(result)


@pytest.mark.parametrize(
    ("value", "source", "sampled_at", "valid"),
    [
        (None, "none", None, True),
        (0, "none", None, False),
        (None, "session", None, False),
        (None, "none", "2026-09-09T09:00:00Z", False),
    ],
)
def test_v3_unknown_usage_is_not_fabricated_zero(tmp_path, value, source, sampled_at, valid):
    document = v3_backlog()
    document["backlog"]["active-themes"][0]["epics"][0]["usage"] = {
        "value": value, "confidence": "unknown", "source": source,
        "sampled-at": sampled_at,
    }
    result = backlog.validate_repository(epic_repository(tmp_path, document))
    assert result.valid is valid, result.findings


@pytest.mark.parametrize("confidence", ["measured", "estimated"])
def test_v3_zero_is_valid_actual_usage(tmp_path, confidence):
    document = v3_backlog()
    epic = document["backlog"]["active-themes"][0]["epics"][0]
    epic["usage"].update(value=0, confidence=confidence)
    epic["confidence"] = confidence
    result = backlog.validate_repository(epic_repository(tmp_path, document))
    assert result.valid, result.findings


@pytest.mark.parametrize("kind", ["epic", "child"])
@pytest.mark.parametrize("path_type", ["missing", "directory", "absolute", "traversal", "escape-link"])
def test_v3_file_must_be_safe_existing_contained_regular(tmp_path, kind, path_type):
    document = v3_backlog()
    epic = document["backlog"]["active-themes"][0]["epics"][0]
    epic["stories"] = [v3_child()]
    item = epic if kind == "epic" else epic["stories"][0]
    if path_type == "missing":
        item["file"] = "absent.md"
    elif path_type == "directory":
        item["file"] = "stories"
    elif path_type == "absolute":
        item["file"] = (tmp_path / "outside.md").as_posix()
    elif path_type == "traversal":
        item["file"] = "../outside.md"
    else:
        item["file"] = "escape.md"
    root = epic_repository(tmp_path, document)
    if path_type == "escape-link":
        outside = tmp_path / "outside.md"
        outside.write_text("# Not in repository\n")
        (root / "escape.md").symlink_to(outside)

    result = backlog.validate_repository(root)

    assert not result.valid
    assert ".file:" in messages(result)


@pytest.mark.parametrize("status", ["todo", "in-progress", "blocked", "failed", "done"])
def test_done_epic_requires_every_child_done(tmp_path, status):
    document = v3_backlog()
    epic = document["backlog"]["active-themes"][0]["epics"][0]
    epic.update(status="done", stories=[v3_child(status="done"), v3_child(2, status=status)])
    result = backlog.validate_repository(epic_repository(tmp_path, document))
    assert result.valid is (status == "done"), result.findings
    if status != "done":
        assert "done epic requires every acceptance child to be done" in messages(result)


def test_child_governance_is_not_duplicated(tmp_path):
    document = v3_backlog()
    epic = document["backlog"]["active-themes"][0]["epics"][0]
    child = v3_child()
    child["risk"] = deepcopy(epic["risk"])
    epic["stories"] = [child]
    result = backlog.validate_repository(epic_repository(tmp_path, document))
    assert not result.valid
    assert "unknown key 'risk'" in messages(result)


def test_v3_optional_child_priority_and_contained_file_link_are_valid(tmp_path):
    document = v3_backlog()
    epic = document["backlog"]["active-themes"][0]["epics"][0]
    child = v3_child()
    child["priority"] = "low"
    epic["stories"] = [child]
    epic["file"] = "epic-link.md"
    root = epic_repository(tmp_path, document)
    (root / "epic-link.md").symlink_to(EPIC_PATH)
    result = backlog.validate_repository(root)
    assert result.valid, result.findings


@pytest.mark.parametrize(
    ("kind", "dependency"),
    [("theme", "TH3.E1"), ("epic", "TH2.E1.US1"), ("epic", "TH99.E1"),
     ("epic", "TH3.E1"), ("child", "TH2.E1"), ("child", "TH3.E1.US1")],
)
def test_dependencies_must_resolve_same_kind_and_not_self(tmp_path, kind, dependency):
    document = v3_backlog()
    theme = document["backlog"]["active-themes"][0]
    epic = theme["epics"][0]
    epic["stories"] = [v3_child()]
    item = {"theme": theme, "epic": epic, "child": epic["stories"][0]}[kind]
    item["depends-on"] = [dependency]
    result = backlog.validate_repository(epic_repository(tmp_path, document))
    assert not result.valid
    assert "depends-on" in messages(result)


@pytest.mark.parametrize("kind", ["epic", "child"])
def test_active_dependency_cycles_rejected(tmp_path, kind):
    document = v3_backlog()
    theme = document["backlog"]["active-themes"][0]
    if kind == "epic":
        first = theme["epics"][0]
        second = deepcopy(first)
        second["id"] = "TH3.E2"
        theme["epics"].append(second)
    else:
        first, second = v3_child(), v3_child(2)
        theme["epics"][0]["stories"] = [first, second]
    first["depends-on"] = [second["id"]]
    second["depends-on"] = [first["id"]]
    result = backlog.validate_repository(epic_repository(tmp_path, document))
    assert not result.valid
    assert "dependency cycle detected" in messages(result)


def test_child_order_dependencies_do_not_require_done_at_schema_level(tmp_path):
    document = v3_backlog()
    epic = document["backlog"]["active-themes"][0]["epics"][0]
    first, second = v3_child(), v3_child(2)
    second["depends-on"] = [first["id"], "TH2.E1.US1"]
    epic["stories"] = [first, second]
    result = backlog.validate_repository(epic_repository(tmp_path, document))
    assert result.valid, result.findings


@pytest.mark.parametrize("version", [1, 2, 3])
def test_epic_and_child_dependencies_resolve_indexed_archive_versions(tmp_path, version):
    document = v3_backlog()
    epic = document["backlog"]["active-themes"][0]["epics"][0]
    epic["depends-on"] = ["TH2.E1"]
    child = v3_child()
    child["depends-on"] = ["TH2.E1.US1"]
    epic["stories"] = [child]
    document["backlog"]["archived-themes"][1]["schema-version"] = version
    root = epic_repository(tmp_path, document)
    if version in (2, 3):
        theme = v2_archive_theme("TH2")
        if version == 3:
            theme["schema-version"] = 3
            archived_epic = v3_epic()
            archived_epic.update(
                id="TH2.E1", status="done", stories=theme["epics"][0]["stories"]
            )
            archived_epic["stories"] = [
                {key: value for key, value in item.items() if key in v3_child()}
                for item in archived_epic["stories"]
            ]
            theme["epics"] = [archived_epic]
        (root / "docs/plan/backlog-archive/TH2.yaml").write_text(
            yaml.safe_dump({"theme": theme})
        )

    result = backlog.validate_repository(root)

    assert result.valid, result.findings


@pytest.mark.parametrize(
    ("key", "value", "valid"),
    [("locked", True, True), ("locked", False, False),
     ("status", "done", True), ("status", "todo", False)],
)
def test_v3_archive_requires_completed_locked_snapshot(tmp_path, key, value, valid):
    document = v3_backlog()
    theme = document["backlog"]["active-themes"].pop()
    theme.update(status="done", locked=True)
    theme["epics"][0]["status"] = "done"
    theme[key] = value
    document["backlog"]["archived-themes"].append({
        "id": "TH3", "name": theme["name"], "schema-version": 3,
        "status": "done", "locked": True, "completed-at": "2026-09-09T09:00:00Z",
        "archive-ref": "docs/plan/backlog-archive/TH3.yaml",
        "stats": {"epics": 1, "stories": 0},
    })
    root = epic_repository(tmp_path, document)
    (root / "docs/plan/backlog-archive/TH3.yaml").write_text(
        yaml.safe_dump({"theme": theme})
    )
    result = backlog.validate_repository(root)
    assert result.valid is valid, result.findings


def test_v3_archive_index_cannot_claim_unfinished_theme(tmp_path):
    document = v3_backlog()
    summary = document["backlog"]["archived-themes"][0]
    summary.update({"schema-version": 3, "status": "todo"})
    result = backlog.validate_repository(epic_repository(tmp_path, document))
    assert not result.valid
    assert "version 3 archived theme must have status: done" in messages(result)


def test_v3_root_version_is_still_rejected(tmp_path):
    document = v3_backlog()
    document["backlog"]["schema-version"] = 3
    result = backlog.validate_repository(epic_repository(tmp_path, document))
    assert not result.valid
    assert "backlog.schema-version" in messages(result)


def test_v1_v2_and_v3_themes_coexist_without_migration(tmp_path):
    document = v3_backlog()
    legacy = v2_archive_theme("TH4")
    document["backlog"]["active-themes"].append(legacy)
    root = epic_repository(tmp_path, document)
    (root / "stories/TH4-US1.md").write_text("# Legacy story\n")
    result = backlog.validate_repository(root)
    assert result.valid, result.findings


def test_legacy_traceability_contract_is_exactly_preserved():
    text = (ROOT / ".github/skills/bdd-stories/SKILL.md").read_text()
    region = text.split("<!-- traceability-contract:start -->", 1)[1].split(
        "<!-- traceability-contract:end -->", 1
    )[0]
    assert region == """
```yaml
contract-version: 1
frontmatter-key: traceability
required-story-types: [standard, spike]
empty-allowed-story-types: [trivial]
keys:
  vision:
    prefixes: [VO]
  requirements:
    prefixes: [PR, QR]
  adrs:
    prefixes: [ADR]
  invariants:
    prefixes: [INV]
```
"""
