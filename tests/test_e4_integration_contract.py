"""Cross-story integration contract for TH3.E4."""

from __future__ import annotations

import hashlib
import os
import shutil
import sys
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from methodlib import activation, cli, docs, exits, migrate, self_hosted  # noqa: E402


def _copy_repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    shutil.copytree(
        ROOT,
        root,
        ignore=shutil.ignore_patterns(
            ".git",
            ".pytest_cache",
            ".mypy_cache",
            "__pycache__",
            ".coverage",
            "*.pyc",
        ),
    )
    return root


def _backlog(root: Path) -> dict[str, object]:
    document = yaml.safe_load(
        (root / activation.BACKLOG_PATH).read_text(encoding="utf-8")
    )
    assert isinstance(document, dict)
    backlog = document["backlog"]
    assert isinstance(backlog, dict)
    return backlog


def _file_digests(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_real_e4_gate_connects_activation_docs_migration_and_all_checks():
    backlog = _backlog(ROOT)
    assert isinstance(backlog["revision"], int)
    assert backlog["revision"] >= 65
    assert backlog["revision"] == 68
    assert backlog["last-updated"] == "2026-09-07T09:22:22.527+01:00"
    assert backlog["active-themes"] == []
    summary = next(item for item in backlog["archived-themes"] if item["id"] == "TH3")
    assert summary["status"] == "done"
    assert summary["locked"] is True
    assert summary["schema-version"] == 2
    assert summary["stats"] == {"epics": 4, "stories": 22}
    theme = yaml.safe_load((ROOT / summary["archive-ref"]).read_text(encoding="utf-8"))["theme"]
    assert theme["status"] == "done"
    assert theme["locked"] is True
    epic = next(item for item in theme["epics"] if item["id"] == "TH3.E4")
    assert epic["status"] == "done"
    assert [story["status"] for story in epic["stories"]] == ["done"] * 6

    aggregate = cli.dispatch(
        ["validate", "all", "--json"],
        probe_directory=ROOT,
    )
    assert aggregate.exit_code == exits.SUCCESS
    assert aggregate.payload["findings"] == []
    assert [item["check"] for item in aggregate.payload["checks"]] == [
        "schema",
        "gates",
        "lock",
        "trace",
        "maturity",
        "docs",
    ]
    checked_files = set(aggregate.payload["checked_files"])
    assert {
        "README.md",
        ".github/copilot-instructions.md",
        ".github/skills/kickstart/SKILL.md",
        "tests/test_lifecycle_documentation_migration.py",
        "tests/test_method_docs.py",
        "tests/test_e4_integration_contract.py",
    } <= checked_files
    assert not set(docs.EXCLUDED_SCOPES) & checked_files

    maturity = activation.validate_repository(ROOT)
    assert maturity.valid
    states = {item["id"]: item["state"] for item in maturity.controls}
    assert {
        identifier: states[identifier]
        for identifier in ("CTL-001", "CTL-002", "CTL-003", "CTL-014")
    } == {
        "CTL-001": "ENFORCED",
        "CTL-002": "ENFORCED",
        "CTL-003": "ENFORCED",
        "CTL-014": "ENFORCED",
    }
    acceptance = maturity.payload["acceptance-report"]
    assert acceptance["theme-status"] == "done"
    assert acceptance["usage"]["value"] is None
    assert acceptance["usage"]["confidence"] == "unknown"
    assert acceptance["open-waivers"] == []
    assert [item["id"] for item in acceptance["consumed-waivers"]] == ["WVR-001"]

    assessment = (ROOT / migrate.DEFAULT_OUTPUT).read_text(encoding="utf-8")
    assert (
        f"| Assessed at | deterministic backlog revision {backlog['revision']} "
        "(no wall-clock timestamp) |"
    ) in assessment
    for control in maturity.controls:
        assert (
            f"| {control['id']} — {control['name']} | {control['state']} |"
            in assessment
        )


def test_migration_assessment_tracks_mutable_inputs_then_is_idempotent(
    tmp_path: Path,
):
    root = _copy_repository(tmp_path)
    backlog_path = root / activation.BACKLOG_PATH
    document = yaml.safe_load(backlog_path.read_text(encoding="utf-8"))
    document["backlog"]["revision"] += 1
    backlog_path.write_text(
        yaml.safe_dump(document, sort_keys=False),
        encoding="utf-8",
    )
    expected_revision = document["backlog"]["revision"]
    before = _file_digests(root)

    first = migrate.assess_repository(root)
    after_first = _file_digests(root)
    output = root / migrate.DEFAULT_OUTPUT
    first_bytes = output.read_bytes()
    first_mtime = output.stat().st_mtime_ns
    second = migrate.assess_repository(root)

    changed_paths = {
        path
        for path in before | after_first
        if before.get(path) != after_first.get(path)
    }
    assert first.changed is True
    assert changed_paths == {migrate.DEFAULT_OUTPUT}
    assert (
        f"deterministic backlog revision {expected_revision} "
        "(no wall-clock timestamp)"
    ) in first_bytes.decode("utf-8")
    assert second.changed is False
    assert output.read_bytes() == first_bytes
    assert output.stat().st_mtime_ns == first_mtime


def test_th3_acceptance_boundary_rejects_a_later_backlog_revision(
    tmp_path: Path,
):
    if os.environ.get("METHOD_EVIDENCE_BOOTSTRAP") == "1":
        pytest.skip("report consumer is bootstrapped before report generation")

    root = _copy_repository(tmp_path)
    assert self_hosted.validate_report(root).valid
    report = yaml.safe_load(
        (root / self_hosted.REPORT_PATH).read_text(encoding="utf-8")
    )
    snapshot_path = root / self_hosted.BACKLOG_SNAPSHOT_PATH
    retained_snapshot = snapshot_path.read_bytes()

    backlog_path = root / activation.BACKLOG_PATH
    document = yaml.safe_load(backlog_path.read_text(encoding="utf-8"))
    document["backlog"]["revision"] += 1
    document["backlog"]["last-updated"] = "2026-09-07T03:16:38+01:00"
    backlog_path.write_text(
        yaml.safe_dump(document, sort_keys=False),
        encoding="utf-8",
    )
    session_log = root / "docs/plan/session-log.md"
    session_log.write_text(
        session_log.read_text(encoding="utf-8")
        + "\nMutable orchestrator transition fixture.\n",
        encoding="utf-8",
    )

    assert backlog_path.read_bytes() != retained_snapshot
    assert snapshot_path.read_bytes() == retained_snapshot
    assert report["bounded-snapshots"]["backlog"]["semantics"] == (
        self_hosted.MUTABLE_SNAPSHOT_SEMANTICS
    )
    assert report["bounded-snapshots"]["session-log"] == {
        "semantics": self_hosted.SESSION_LOG_SEMANTICS
    }
    result = self_hosted.validate_report(root)
    assert not result.valid
    assert "current maturity validation rejects retained recovery evidence" in result.findings
