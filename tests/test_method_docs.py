"""Contract tests for TH3.E4.US6 lifecycle documentation validation."""

from __future__ import annotations

import io
import json
import shutil
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from methodlib import cli, docs, exits  # noqa: E402


FIXTURES = ROOT / "tests/fixtures/method_docs"


def fixture_text(relative: str) -> str:
    text = (FIXTURES / relative).read_text(encoding="utf-8")
    assert text.startswith(docs.FIXTURE_MARKER)
    return text.removeprefix(docs.FIXTURE_MARKER).lstrip("\n")


def write(root: Path, relative: str, text: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    stage_map = fixture_text("passing/stage-list.md")
    handoff = fixture_text("passing/handoff.md")
    write(root, "README.md", stage_map)
    write(root, ".github/copilot-instructions.md", handoff)
    write(root, docs.CANONICAL_SKILL.as_posix(), stage_map)
    write(
        root,
        ".github/agents/README.md",
        "Lifecycle authority: `the-copilot-build-method`.\n",
    )
    write(root, "tests/test_contract.py", '"""Current lifecycle contract."""\n')
    return root


def finding(result: docs.ValidationResult, record: str) -> dict[str, object]:
    return next(item for item in result.findings if item["record"] == record)


def test_passing_fixtures_scan_every_active_scope_and_emit_one_json_object(
    tmp_path: Path,
):
    root = repository(tmp_path)
    result = docs.validate_repository(root)

    assert result.valid
    assert result.findings == ()
    assert set(result.checked_files) == {
        ".github/agents/README.md",
        ".github/copilot-instructions.md",
        ".github/skills/the-copilot-build-method/SKILL.md",
        "README.md",
        "tests/test_contract.py",
    }

    command = cli.dispatch(
        ["validate", "docs", "--json"],
        probe_directory=root,
    )
    stdout = io.StringIO()
    stderr = io.StringIO()
    assert cli.emit(command, stdout=stdout, stderr=stderr) == exits.SUCCESS
    report = json.loads(stdout.getvalue())
    assert len(stdout.getvalue().splitlines()) == 1
    assert report["checked_files"] == list(result.checked_files)
    assert report["findings"] == []
    assert stderr.getvalue() == ""


def test_stale_stage_list_fixture_fails_closed_with_line_and_owned_map(
    tmp_path: Path,
):
    root = repository(tmp_path)
    write(
        root,
        ".github/skills/legacy/SKILL.md",
        fixture_text("failing/stale-stage-list.md"),
    )

    command = cli.dispatch(["validate", "docs"], probe_directory=root)
    result = docs.validate_repository(root)
    stale = finding(result, "stale-stage-list")

    assert command.exit_code == exits.VALIDATION_FAILURE
    assert stale["file"] == ".github/skills/legacy/SKILL.md"
    assert stale["line"] == 3
    assert stale["required_stage_map"] == [
        {"stage": stage, "entrypoint": entrypoint}
        for stage, entrypoint in docs.REQUIRED_STAGE_MAP
    ]
    assert "six-stage map" in stale["remediation"]


def test_multiline_stage_finding_reports_the_physical_matching_line(
    tmp_path: Path,
):
    root = repository(tmp_path)
    write(
        root,
        ".github/skills/legacy/SKILL.md",
        fixture_text("failing/stale-stage-list-multiline.md"),
    )

    result = docs.validate_repository(root)
    stale = finding(result, "stale-stage-list")

    assert not result.valid
    assert stale["line"] == 4


def test_stale_handoff_fixture_fails_closed_and_requires_discover(
    tmp_path: Path,
):
    root = repository(tmp_path)
    write(
        root,
        ".github/skills/legacy/SKILL.md",
        fixture_text("failing/stale-handoff.md"),
    )

    command = cli.dispatch(["validate", "docs"], probe_directory=root)
    result = docs.validate_repository(root)
    stale = finding(result, "stale-entrypoint-handoff")

    assert command.exit_code == exits.VALIDATION_FAILURE
    assert stale["file"] == ".github/skills/legacy/SKILL.md"
    assert stale["line"] == 3
    assert "kickstart to discover" in stale["remediation"]
    assert stale["required_stage_map"]


def test_reversed_multiline_handoff_reports_the_physical_matching_line(
    tmp_path: Path,
):
    root = repository(tmp_path)
    write(
        root,
        ".github/skills/legacy/SKILL.md",
        fixture_text("failing/stale-handoff-semantic.md"),
    )

    result = docs.validate_repository(root)
    stale = finding(result, "stale-entrypoint-handoff")

    assert not result.valid
    assert stale["line"] == 4


def test_direct_handoff_variants_are_detected_in_both_orders(
    tmp_path: Path,
):
    root = repository(tmp_path)
    write(
        root,
        ".github/skills/legacy/SKILL.md",
        fixture_text("failing/stale-handoff-variants.md"),
    )

    result = docs.validate_repository(root)
    lines = {
        item["line"]
        for item in result.findings
        if item["record"] == "stale-entrypoint-handoff"
    }

    assert not result.valid
    assert lines == {3, 4, 5}


def test_canonical_handoff_variants_do_not_raise_false_findings(
    tmp_path: Path,
):
    root = repository(tmp_path)
    write(
        root,
        ".github/skills/current/SKILL.md",
        fixture_text("passing/canonical-handoff-variants.md"),
    )

    result = docs.validate_repository(root)

    assert result.valid
    assert result.findings == ()


def test_canonical_discovery_noun_blocks_direct_handoff_false_positive(
    tmp_path: Path,
):
    root = repository(tmp_path)
    write(
        root,
        ".github/skills/current/SKILL.md",
        fixture_text("passing/canonical-discovery-noun.md"),
    )

    result = docs.validate_repository(root)

    assert result.valid
    assert result.findings == ()


@pytest.mark.parametrize(
    "relative",
    (".github/skills", ".github/agents", "tests"),
)
@pytest.mark.parametrize("failure_mode", ("symlink", "unreadable"))
def test_each_unsafe_active_root_fails_closed_with_named_finding(
    tmp_path: Path,
    relative: str,
    failure_mode: str,
):
    root = repository(tmp_path)
    active_root = root / relative
    if failure_mode == "symlink":
        outside = tmp_path / f"outside-{active_root.name}"
        outside.mkdir()
        shutil.rmtree(active_root)
        active_root.symlink_to(outside, target_is_directory=True)
    else:
        active_root.chmod(0)

    try:
        result = docs.validate_repository(root)
        command = cli.dispatch(
            ["validate", "docs", "--json"],
            probe_directory=root,
        )
    finally:
        if failure_mode == "unreadable":
            active_root.chmod(0o700)

    unsafe = finding(result, "unreadable-active-root")
    assert not result.valid
    assert command.exit_code == exits.VALIDATION_FAILURE
    assert unsafe["file"] == relative
    assert unsafe["line"] == 1
    assert relative not in result.checked_files


def test_locked_and_archived_paths_are_not_scanned_or_reported(
    tmp_path: Path,
):
    root = repository(tmp_path)
    stale = fixture_text("excluded/archive-stale.md")
    excluded = (
        ".github/agents/archive/retired.agent.md",
        ".github/ISSUE_TEMPLATE/archive/retired.md",
        "docs/architecture/history/retired.md",
        "docs/themes/TH1-methodology-improvements/retired.md",
        "docs/themes/TH2-gitflow-operator/retired.md",
        "docs/plan/backlog-archive/TH1.yaml",
        "docs/plan/backlog-archive/TH2.yaml",
    )
    for relative in excluded:
        write(root, relative, stale)

    result = docs.validate_repository(root)

    assert result.valid
    assert not (set(excluded) & set(result.checked_files))
    assert result.payload["excluded_scopes"] == list(docs.EXCLUDED_SCOPES)


def test_new_active_skill_is_discovered_dynamically_and_evaluated(
    tmp_path: Path,
):
    root = repository(tmp_path)
    relative = ".github/skills/new-after-migration/SKILL.md"
    new_skill = write(
        root,
        relative,
        "Lifecycle authority: `the-copilot-build-method`.\n",
    )

    passing = docs.validate_repository(root)
    assert passing.valid
    assert relative in passing.checked_files

    new_skill.write_text(
        fixture_text("failing/stale-handoff.md"),
        encoding="utf-8",
    )
    failing = docs.validate_repository(root)
    assert not failing.valid
    assert finding(failing, "stale-entrypoint-handoff")["file"] == relative


def test_explicit_test_fixture_marker_prevents_self_trigger_but_is_checked(
    tmp_path: Path,
):
    root = repository(tmp_path)
    relative = "tests/fixtures/example/legacy.md"
    source = FIXTURES / "failing/stale-stage-list.md"
    target = root / relative
    target.parent.mkdir(parents=True)
    shutil.copy2(source, target)

    result = docs.validate_repository(root)

    assert result.valid
    assert relative in result.checked_files
    assert result.fixture_exclusions == (relative,)


def test_executable_stage_map_matches_the_canonical_owner():
    text = (ROOT / docs.CANONICAL_SKILL).read_text(encoding="utf-8")
    rows = []
    for line in text.splitlines():
        if not line.startswith("|") or set(line) <= {"|", "-", ":", " "}:
            continue
        cells = [
            cell.strip().replace("`", "")
            for cell in line.strip("|").split("|")
        ]
        if cells[:2] == ["Stage", "Entrypoint"]:
            continue
        if len(cells) >= 2 and cells[0] in {
            stage for stage, _entrypoint in docs.REQUIRED_STAGE_MAP
        }:
            rows.append(tuple(cells[:2]))

    assert tuple(rows) == docs.REQUIRED_STAGE_MAP


def test_repository_migration_inventory_is_green_and_fully_listed():
    result = docs.validate_repository(ROOT)

    assert result.valid
    assert result.findings == ()
    assert "README.md" in result.checked_files
    assert ".github/copilot-instructions.md" in result.checked_files
    assert "tests/test_lifecycle_documentation_migration.py" in result.checked_files
    assert "tests/test_method_docs.py" in result.checked_files
    assert (
        ".github/agents/archive/documenter.agent.md"
        not in result.checked_files
    )
    assert (
        ".github/skills/discovery-dossier/templates/DR.md"
        not in result.checked_files
    )
