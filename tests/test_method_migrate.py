import io
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from methodlib import cli, exits, migrate  # noqa: E402


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _story(theme: str, status: str, *, verification: list[str]) -> dict[str, object]:
    return {
        "id": f"{theme}.E1.US1",
        "status": status,
        "file": f"docs/themes/{theme}-scope/epics/E1/stories/US1.md",
        "evidence": {"verification": verification, "usage": []},
    }


def repository_fixture(tmp_path: Path, *, include_discovery: bool = True) -> Path:
    root = tmp_path / "repository"
    backlog = {
        "backlog": {
            "schema-version": 2,
            "revision": 9,
            "project": "migration-fixture",
            "active-themes": [
                {
                    "id": "TH3",
                    "schema-version": 2,
                    "status": "in-progress",
                    "locked": False,
                    "vision-ref": "docs/vision_of_product/VP3-current/",
                    "epics": [
                        {
                            "id": "TH3.E1",
                            "stories": [
                                _story(
                                    "TH3",
                                    "in-progress",
                                    verification=["targeted checks passed"],
                                )
                            ],
                        }
                    ],
                    "usage": {
                        "value": None,
                        "confidence": "unknown",
                        "source": "none",
                    },
                }
            ],
            "archived-themes": [
                {
                    "id": "TH1",
                    "status": "done",
                    "locked": True,
                    "archive-ref": "docs/plan/backlog-archive/TH1.yaml",
                },
                {
                    "id": "TH2",
                    "status": "done",
                    "locked": True,
                    "archive-ref": "docs/plan/backlog-archive/TH2.yaml",
                },
            ],
        }
    }
    _write(
        root / migrate.BACKLOG_PATH,
        yaml.safe_dump(backlog, sort_keys=False),
    )
    for number in (1, 2):
        theme = f"TH{number}"
        vp = f"VP{number}"
        archive = {
            "theme": {
                "id": theme,
                "status": "done",
                "locked": True,
                "vision-ref": f"docs/vision_of_product/{vp}-legacy/",
                "epics": [
                    {
                        "id": f"{theme}.E1",
                        "stories": [_story(theme, "done", verification=[])],
                    }
                ],
            }
        }
        _write(
            root / f"docs/plan/backlog-archive/{theme}.yaml",
            yaml.safe_dump(archive, sort_keys=False),
        )
        _write(
            root / f"docs/vision_of_product/{vp}-legacy/{vp}.md",
            f"# {vp} legacy vision\n",
        )
        _write(
            root / f"docs/themes/{theme}-scope/epics/E1/stories/US1.md",
            f"# {theme}.E1.US1\n",
        )
    _write(root / "docs/vision_of_product/VP3-current/VP3.md", "# VP3\n")
    _write(
        root / "docs/themes/TH3-scope/epics/E1/stories/US1.md",
        "# TH3.E1.US1\n",
    )
    if include_discovery:
        _write(
            root / "docs/discovery/VP3-current/README.md",
            """# VP3 Discovery

## Acceptance

| Field | Value |
|---|---|
| Actor | Human: designer |
| Timestamp | 2026-09-05T10:00:00+01:00 |
| Scope | VP3 Discovery |
| Verdict | READY |
| Rationale | Accepted evidence. |
| Source revision | sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa |
""",
        )
    _write(
        root / "docs/requirements/VP3-current/PRD.md",
        """# VP3 PRD

## Approval

| Field | Value |
|---|---|
| Actor | Human: product owner |
| Timestamp | 2026-09-05T11:00:00+01:00 |
| Scope | VP3 requirements |
| Verdict | Approved |
| Rationale | Approved scope. |
| Source revision | sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb |
""",
    )
    _write(
        root / "docs/architecture/README.md",
        """# Architecture for VP3

## Acceptance

| Field | Value |
|---|---|
| Actor | Human: product owner |
| Timestamp | 2026-09-05T12:00:00+01:00 |
| Scope | VP3 architecture |
| Verdict | Accepted |
| Rationale | Accepted architecture. |
| Source revision | sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc |
""",
    )
    ledger = {
        "ledger-version": 1,
        "controls": [
            {
                "id": "CTL-001",
                "name": "Gate enforcement",
                "state": "ENFORCED",
                "effective-point": "method validate gates",
                "limitations": ["Interactive operation remains manual."],
            }
        ],
    }
    _write(
        root / migrate.LEDGER_PATH,
        yaml.safe_dump(ledger, sort_keys=False),
    )
    _write(root / "docs/ADRs/ADR-001-gitflow-operator.md", "# ADR-001\n")
    return root


def _emit(result: cli.CommandResult) -> tuple[int, dict[str, object], str]:
    stdout, stderr = io.StringIO(), io.StringIO()
    status = cli.emit(result, stdout=stdout, stderr=stderr)
    return status, json.loads(stdout.getvalue()), stderr.getvalue()


def test_assess_reports_legacy_coverage_gaps_maturity_and_vp3_adoption(
    tmp_path: Path,
):
    root = repository_fixture(tmp_path)

    result = cli.dispatch(["migrate", "assess"], probe_directory=root)
    status, payload, stderr = _emit(result)
    assessment = (root / migrate.DEFAULT_OUTPUT).read_text(encoding="utf-8")

    assert status == exits.SUCCESS
    assert payload == {
        "command": "migrate",
        "action": "assess",
        "status": "ok",
        "output": migrate.DEFAULT_OUTPUT,
        "changed": True,
        "findings": [],
    }
    assert stderr == ""
    assert "| VP1 / TH1 | present | unknown | unknown | unknown | present | present |" in assessment
    assert "| VP3 / TH3 | present | present | present | present | present | present |" in assessment
    assert (
        "Discovery readiness acceptance | no | Not recorded; expected for a "
        "locked legacy scope"
    ) in assessment
    assert "CTL-001 — Gate enforcement | ENFORCED | method validate gates" in assessment
    assert "| Adoption point | VP3 / TH3 |" in assessment
    assert "| VP1 / TH1 | unknown | unknown | unknown |" in assessment
    assert "| VP3 / TH3 | present | present | unknown |" in assessment
    assert "Retroactive evidence generated | none, by contract" in assessment


def test_no_discovery_history_stays_unknown_and_next_new_scope_is_adoption_point(
    tmp_path: Path,
):
    root = repository_fixture(tmp_path, include_discovery=False)
    backlog = yaml.safe_load((root / migrate.BACKLOG_PATH).read_text())
    backlog["backlog"]["active-themes"] = []
    (root / migrate.BACKLOG_PATH).write_text(
        yaml.safe_dump(backlog, sort_keys=False),
        encoding="utf-8",
    )
    shutil.rmtree(root / "docs/discovery", ignore_errors=True)

    result = cli.dispatch(["migrate", "assess"], probe_directory=root)
    status, payload, _stderr = _emit(result)
    assessment = (root / migrate.DEFAULT_OUTPUT).read_text(encoding="utf-8")

    assert status == exits.SUCCESS
    assert payload["status"] == "ok"
    assert "| VP1 / TH1 | present | unknown | unknown |" in assessment
    assert "| VP2 / TH2 | present | unknown | unknown |" in assessment
    assert "| Adoption point | VP3 / TH3 (next new scope) |" in assessment
    assert "Historical evidence remains unknown" in assessment


@pytest.mark.parametrize(
    ("usage_evidence", "expected"),
    (
        (
            ["WVR-001 records missing TH3 usage evidence as unknown."],
            "unknown",
        ),
        (["Measured local adapter sample: 12.5 AIC."], "present"),
    ),
)
def test_usage_waiver_is_not_usage_evidence_without_measured_or_estimated_sample(
    tmp_path: Path,
    usage_evidence: list[str],
    expected: str,
):
    root = repository_fixture(tmp_path)
    backlog_path = root / migrate.BACKLOG_PATH
    backlog = yaml.safe_load(backlog_path.read_text(encoding="utf-8"))
    story = backlog["backlog"]["active-themes"][0]["epics"][0]["stories"][0]
    story["evidence"]["usage"] = usage_evidence
    backlog_path.write_text(yaml.safe_dump(backlog, sort_keys=False), encoding="utf-8")

    result = migrate.assess_repository(root)
    assessment = (root / migrate.DEFAULT_OUTPUT).read_text(encoding="utf-8")

    assert result.changed is True
    assert f"| VP3 / TH3 | present | present | {expected} |" in assessment


def test_unchanged_assessment_is_byte_identical_and_does_not_rewrite_output(
    tmp_path: Path,
):
    root = repository_fixture(tmp_path)

    first = migrate.assess_repository(root)
    output = root / migrate.DEFAULT_OUTPUT
    first_bytes = output.read_bytes()
    first_stat = output.stat()
    files_after_first = sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    )
    second = migrate.assess_repository(root)
    files_after_second = sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    )

    assert first.changed is True
    assert second.changed is False
    assert output.read_bytes() == first_bytes
    assert output.stat().st_mtime_ns == first_stat.st_mtime_ns
    assert files_after_second == files_after_first


def test_output_inside_locked_theme_exits_two_with_finding(tmp_path: Path):
    root = repository_fixture(tmp_path)
    output = "docs/themes/TH1-scope/migration-assessment.md"

    result = cli.dispatch(
        ["migrate", "assess", "--output", output],
        probe_directory=root,
    )
    status, payload, stderr = _emit(result)

    assert status == exits.VALIDATION_FAILURE
    assert payload["status"] == "failed"
    assert payload["changed"] is False
    assert len(payload["findings"]) == 1
    assert payload["findings"][0]["record"] == "TH1"
    assert "locked artefacts cannot receive generated content" in (
        payload["findings"][0]["message"]
    )
    assert "locked artefacts cannot receive generated content" in stderr
    assert not (root / output).exists()


@pytest.mark.parametrize(
    ("output", "record"),
    (
        ("docs/ADRs/ADR-001-gitflow-operator.md", "ADR-001"),
        ("docs/vision_of_product/VP1-legacy/VP1.md", "VP1"),
        ("docs/discovery/VP1-legacy/README.md", "VP1"),
        ("docs/requirements/VP1-legacy/PRD.md", "VP1"),
    ),
)
def test_custom_output_rejects_canonical_locked_adr_and_shared_vp_scopes(
    tmp_path: Path,
    output: str,
    record: str,
):
    root = repository_fixture(tmp_path)
    archive_path = root / "docs/plan/backlog-archive/TH1.yaml"
    archive = yaml.safe_load(archive_path.read_text(encoding="utf-8"))
    archive["theme"].update(
        {
            "discovery-ref": "docs/discovery/VP1-legacy/",
            "requirements-ref": "docs/requirements/VP1-legacy/PRD.md",
        }
    )
    archive_path.write_text(
        yaml.safe_dump(archive, sort_keys=False),
        encoding="utf-8",
    )
    _write(root / "docs/discovery/VP1-legacy/README.md", "# Legacy Discovery\n")
    _write(root / "docs/requirements/VP1-legacy/PRD.md", "# Legacy PRD\n")
    original = (root / output).read_bytes()

    result = cli.dispatch(
        ["migrate", "assess", "--output", output],
        probe_directory=root,
    )

    assert result.exit_code == exits.VALIDATION_FAILURE
    assert result.payload["findings"][0]["record"] == record
    assert "locked artefacts cannot receive generated content" in (
        result.payload["findings"][0]["message"]
    )
    assert (root / output).read_bytes() == original


def test_locked_theme_uses_actual_story_path_instead_of_directory_name(
    tmp_path: Path,
):
    root = repository_fixture(tmp_path)
    archive_path = root / "docs/plan/backlog-archive/TH1.yaml"
    archive = yaml.safe_load(archive_path.read_text(encoding="utf-8"))
    archive["theme"]["epics"][0]["stories"][0]["file"] = (
        "docs/themes/historical-delivery/epics/E1/stories/US1.md"
    )
    archive_path.write_text(
        yaml.safe_dump(archive, sort_keys=False),
        encoding="utf-8",
    )
    _write(
        root / "docs/themes/historical-delivery/epics/E1/stories/US1.md",
        "# Historical story\n",
    )
    output = "docs/themes/historical-delivery/migration-assessment.md"

    result = cli.dispatch(
        ["migrate", "assess", "--output", output],
        probe_directory=root,
    )

    assert result.exit_code == exits.VALIDATION_FAILURE
    assert result.payload["findings"][0]["record"] == "TH1"
    assert not (root / output).exists()


def test_architecture_requires_exact_vp_tokens_for_coverage_and_gate_scope(
    tmp_path: Path,
):
    root = repository_fixture(tmp_path)
    (root / "docs/architecture/README.md").write_text(
        """# Architecture for VP30

## Acceptance

| Field | Value |
|---|---|
| Actor | Human: product owner |
| Timestamp | 2026-09-05T12:00:00+01:00 |
| Scope | VP30 architecture |
| Verdict | Accepted |
| Rationale | Accepted architecture. |
| Source revision | sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc |
""",
        encoding="utf-8",
    )

    result = migrate.assess_repository(root)
    assessment = (root / migrate.DEFAULT_OUTPUT).read_text(encoding="utf-8")

    assert result.changed is True
    assert (
        "| VP3 / TH3 | present | present | present | unknown | present | present |"
        in assessment
    )
    assert (
        "| VP3 / TH3 | Planning | Architecture acceptance | no |"
        in assessment
    )


@pytest.mark.parametrize(
    ("limit_name", "limit_value", "fixture_path", "expected"),
    (
        (
            "MAX_RECURSIVE_FILES",
            0,
            None,
            "file limit of 0",
        ),
        (
            "MAX_RECURSIVE_BYTES",
            1,
            None,
            "aggregate byte limit of 1",
        ),
        (
            "MAX_RECURSIVE_DEPTH",
            0,
            "docs/architecture/nested/too-deep.md",
            "maximum depth of 0",
        ),
    ),
)
def test_recursive_architecture_limits_fail_closed_deterministically(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    limit_name: str,
    limit_value: int,
    fixture_path: str | None,
    expected: str,
):
    root = repository_fixture(tmp_path)
    if fixture_path is not None:
        _write(root / fixture_path, "# VP3 nested architecture\n")
    monkeypatch.setattr(migrate, limit_name, limit_value)

    first = cli.dispatch(["migrate", "assess"], probe_directory=root)
    second = cli.dispatch(["migrate", "assess"], probe_directory=root)

    assert first.exit_code == exits.VALIDATION_FAILURE
    assert second.exit_code == exits.VALIDATION_FAILURE
    assert first.payload == second.payload
    assert first.payload["changed"] is False
    assert expected in first.payload["findings"][0]["message"]
    assert not (root / migrate.DEFAULT_OUTPUT).exists()


@pytest.mark.parametrize("failure", ("mkstemp", "write"))
def test_filesystem_failures_are_exit_two_and_one_json_object(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    failure: str,
):
    root = repository_fixture(tmp_path)

    def fail(*_args, **_kwargs):
        raise OSError(f"simulated {failure} failure")

    if failure == "mkstemp":
        monkeypatch.setattr(migrate.tempfile, "mkstemp", fail)
    else:
        monkeypatch.setattr(migrate.os, "fsync", fail)

    result = cli.dispatch(["migrate", "assess"], probe_directory=root)
    status, payload, stderr = _emit(result)

    assert status == exits.VALIDATION_FAILURE
    assert payload["status"] == "failed"
    assert payload["changed"] is False
    assert len(payload["findings"]) == 1
    assert "could not be written atomically" in payload["findings"][0]["message"]
    assert "could not be written atomically" in stderr
    assert not (root / migrate.DEFAULT_OUTPUT).exists()
    assert list((root / "docs/plan").glob(".migration-assessment.md.*.tmp")) == []


def test_mkstemp_failure_preserves_subprocess_json_framing(tmp_path: Path):
    root = repository_fixture(tmp_path)
    shutil.copytree(ROOT / "methodlib", root / "methodlib")
    (root / "bin").mkdir()
    shutil.copy2(ROOT / "bin/method", root / "bin/method")
    # The target basename fits NAME_MAX, while mkstemp's prefix and random
    # suffix exceed it deterministically on the supported local filesystem.
    output = "docs/plan/" + ("x" * 245) + ".md"

    completed = subprocess.run(
        [str(root / "bin/method"), "migrate", "assess", "--output", output],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    decoder = json.JSONDecoder()
    payload, end = decoder.raw_decode(completed.stdout)

    assert completed.returncode == exits.VALIDATION_FAILURE
    assert completed.stdout[end:].strip() == ""
    assert len(completed.stdout.splitlines()) == 1
    assert payload["status"] == "failed"
    assert payload["changed"] is False
    assert "could not be written atomically" in payload["findings"][0]["message"]
    assert "Traceback" not in completed.stderr
    assert not (root / output).exists()


def test_path_traversal_and_symlink_outputs_exit_two_without_writes(tmp_path: Path):
    root = repository_fixture(tmp_path)
    outside = tmp_path / "outside.md"
    symlink = root / "docs/plan/linked.md"
    symlink.symlink_to(outside)

    traversal = cli.dispatch(
        ["migrate", "assess", "--output", "../outside.md"],
        probe_directory=root,
    )
    linked = cli.dispatch(
        ["migrate", "assess", "--output", "docs/plan/linked.md"],
        probe_directory=root,
    )

    assert traversal.exit_code == exits.VALIDATION_FAILURE
    assert "traverses the repository" in traversal.payload["findings"][0]["message"]
    assert linked.exit_code == exits.VALIDATION_FAILURE
    assert "symlinks are not allowed" in linked.payload["findings"][0]["message"]
    assert not outside.exists()


def test_output_with_symlink_ancestor_is_rejected(tmp_path: Path):
    root = repository_fixture(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "reports").symlink_to(outside, target_is_directory=True)

    result = cli.dispatch(
        ["migrate", "assess", "--output", "reports/migration.md"],
        probe_directory=root,
    )

    assert result.exit_code == exits.VALIDATION_FAILURE
    assert "symlinks are not allowed" in result.payload["findings"][0]["message"]
    assert not (outside / "migration.md").exists()
