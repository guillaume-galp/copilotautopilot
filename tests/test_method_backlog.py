import copy
import io
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from methodlib import backlog, cli, exits  # noqa: E402


SKILL = ROOT / ".github/skills/backlog-management/SKILL.md"


def independently_read_skill_contract(path: Path = SKILL) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    region = text.split(backlog.CONTRACT_START, 1)[1].split(
        backlog.CONTRACT_END, 1
    )[0]
    fenced = re.fullmatch(r"\s*```yaml\s*\n(.*)\n```\s*", region, re.DOTALL)
    assert fenced is not None
    contract = yaml.safe_load(fenced.group(1))
    assert isinstance(contract, dict)
    return contract


def v2_story(path: str = "stories/US1.md") -> dict[str, object]:
    return {
        "id": "TH3.E1.US1",
        "title": "Schema story",
        "status": "todo",
        "priority": "high",
        "file": path,
        "depends-on": [],
        "risk": {
            "tier": "R2",
            "triggers": ["persistence-compatibility"],
            "assigned-by": "product-owner",
            "validated-by": "architect",
            "overrides": [
                {
                    "from": "R1",
                    "to": "R2",
                    "authority": "architect",
                    "reviewer": "reviewer",
                    "rationale": "Persistence risk",
                    "record": "ADR-004",
                }
            ],
        },
        "model-route": {
            "default-class": "balanced",
            "allowed-classes": ["light", "balanced", "reasoning"],
            "escalations": [
                {
                    "task": "schema-design",
                    "class": "reasoning",
                    "question": "How should compatibility work?",
                    "scope": "backlog",
                    "stop": "Contract is complete",
                    "estimated-aic": 2,
                    "record": "ADR-004",
                }
            ],
        },
        "verification": {
            "profile": "targeted-plus-integration",
            "matrix": ["lint", "unit", "integration"],
            "suite-policy": {
                "story": "targeted",
                "epic": "required",
                "theme": "full",
            },
            "waivers": [
                {
                    "check": "browser",
                    "authority": "architect",
                    "reviewer": "reviewer",
                    "rationale": "No user interface",
                    "record": "TH3.E1.US1",
                }
            ],
        },
        "review-profile": "adversarial",
        "budgets": {"target": 2, "warning": 3, "pause": 4, "unit": "AIC"},
        "usage": {
            "value": 1.5,
            "confidence": "measured",
            "source": "local-session",
            "sampled-at": "2026-09-06T18:00:00+01:00",
        },
        "evidence": {
            "packets": ["docs/plan/runtime/packets/TH3.E1.US1/"],
            "verification": ["unit passed"],
            "review": ["approved"],
            "gitflow": ["not applicable"],
            "usage": ["sample-1"],
        },
        "confidence": "measured",
    }


def v2_theme() -> dict[str, object]:
    return {
        "id": "TH3",
        "name": "Current theme",
        "schema-version": 2,
        "status": "in-progress",
        "locked": False,
        "vision-ref": "docs/vision_of_product/VP3/",
        "discovery-ref": "docs/discovery/VP3/",
        "requirements-ref": "docs/requirements/VP3/PRD.md",
        "depends-on": ["TH2"],
        "budgets": {"target": None, "warning": None, "pause": None, "unit": "AIC"},
        "usage": {
            "value": None,
            "confidence": "unknown",
            "source": "none",
            "sampled-at": None,
        },
        "epics": [
            {
                "id": "TH3.E1",
                "name": "Schema",
                "status": "in-progress",
                "depends-on": [],
                "budgets": {
                    "target": None,
                    "warning": None,
                    "pause": None,
                    "unit": "AIC",
                },
                "usage": {
                    "value": None,
                    "confidence": "unknown",
                    "source": "none",
                    "sampled-at": None,
                },
                "stories": [v2_story()],
            }
        ],
    }


def v1_theme(identifier: str) -> dict[str, object]:
    return {
        "id": identifier,
        "name": f"Historical {identifier}",
        "status": "done",
        "locked": True,
        "vision-ref": f"docs/vision_of_product/VP{identifier[2:]}/",
        "depends-on": [],
        "epics": [
            {
                "id": "E1",
                "name": "Historical epic",
                "status": "done",
                "depends-on": [],
                "stories": [
                    {
                        "id": f"{identifier}.E1.US1",
                        "title": "Historical story",
                        "status": "done",
                        "priority": "medium",
                        "file": f"stories/{identifier}-US1.md",
                        "depends-on": [],
                    }
                ],
            }
        ],
    }


def v2_archive_theme(identifier: str) -> dict[str, object]:
    theme = v2_theme()
    theme.update(
        {
            "id": identifier,
            "status": "done",
            "locked": True,
            "depends-on": [],
        }
    )
    epic = theme["epics"][0]
    epic.update({"id": f"{identifier}.E1", "status": "done"})
    story = epic["stories"][0]
    story.update(
        {
            "id": f"{identifier}.E1.US1",
            "status": "done",
            "file": f"stories/{identifier}-US1.md",
            "confidence": "measured",
        }
    )
    return theme


def valid_backlog() -> dict[str, object]:
    return {
        "backlog": {
            "schema-version": 2,
            "revision": 7,
            "project": "fixture",
            "last-updated": "2026-09-06T18:00:00+01:00",
            "policy": {"model-policy": None, "budget-policy": None},
            "active-themes": [v2_theme()],
            "archived-themes": [
                {
                    "id": identifier,
                    "name": f"Historical {identifier}",
                    "status": "done",
                    "locked": True,
                    "completed-at": "2026-01-01T00:00:00Z",
                    "archive-ref": f"docs/plan/backlog-archive/{identifier}.yaml",
                    "stats": {"epics": 1, "stories": 1},
                }
                for identifier in ("TH1", "TH2")
            ],
        }
    }


def write_repository(
    tmp_path: Path,
    document: object | None = None,
    *,
    backlog_text: str | None = None,
) -> Path:
    root = tmp_path / "repository"
    skill = root / backlog.SKILL_PATH
    skill.parent.mkdir(parents=True)
    skill.write_text(SKILL.read_text(encoding="utf-8"), encoding="utf-8")
    plan = root / "docs/plan"
    (plan / "backlog-archive").mkdir(parents=True)
    (root / "stories").mkdir()
    for name in ("US1.md", "TH1-US1.md", "TH2-US1.md"):
        (root / "stories" / name).write_text(f"# {name}\n", encoding="utf-8")
    source = backlog_text
    if source is None:
        source = yaml.safe_dump(
            valid_backlog() if document is None else document,
            sort_keys=False,
        )
    (plan / "backlog.yaml").write_text(source, encoding="utf-8")
    for identifier in ("TH1", "TH2"):
        snapshot = {"theme": v1_theme(identifier)}
        (plan / "backlog-archive" / f"{identifier}.yaml").write_text(
            yaml.safe_dump(snapshot, sort_keys=False),
            encoding="utf-8",
        )
    return root


def validate(tmp_path: Path, document: object | None = None) -> backlog.ValidationResult:
    return backlog.validate_repository(write_repository(tmp_path, document))


def finding_paths(result: backlog.ValidationResult) -> set[str]:
    return {str(finding["record"]) for finding in result.findings}


def test_real_backlog_and_unmodified_v1_snapshots_validate():
    result = backlog.validate_repository(ROOT)

    assert result.valid
    assert result.findings == ()


def test_schema_recovery_rejects_corruption_then_accepts_restored_fixture(
    tmp_path: Path,
):
    root = write_repository(tmp_path)
    path = root / backlog.BACKLOG_PATH
    original = path.read_text(encoding="utf-8")
    path.write_text("backlog:\n  active-themes: [\n", encoding="utf-8")

    bypass_attempt = backlog.validate_repository(root)
    bypass_cli = cli.dispatch(
        ["validate", "schema", "--json"], probe_directory=root
    )
    path.write_text(original, encoding="utf-8")
    restore_and_pass = backlog.validate_repository(root)
    restore_cli = cli.dispatch(
        ["validate", "schema", "--json"], probe_directory=root
    )

    assert not bypass_attempt.valid
    assert bypass_cli.exit_code == exits.VALIDATION_FAILURE
    assert restore_and_pass.valid
    assert restore_cli.exit_code == exits.SUCCESS


def test_bdd_mixed_v2_and_absent_version_th1_th2_snapshots_validate(tmp_path: Path):
    root = write_repository(tmp_path)

    result = backlog.validate_repository(root)

    assert result.valid
    assert all(
        "migration" not in str(finding["remediation"]).lower()
        for finding in result.findings
    )


def test_bdd_v1_snapshots_do_not_require_v2_blocks(tmp_path: Path):
    root = write_repository(tmp_path)
    snapshot = yaml.safe_load(
        (root / "docs/plan/backlog-archive/TH1.yaml").read_text()
    )["theme"]

    assert "risk" not in snapshot["epics"][0]["stories"][0]
    assert "model-route" not in snapshot["epics"][0]["stories"][0]
    assert "budgets" not in snapshot
    assert backlog.validate_repository(root).valid


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("locked", False, "locked: true"),
        ("status", "in-progress", "status: done"),
    ),
)
def test_v2_archive_snapshot_requires_locked_and_done(
    tmp_path: Path,
    field: str,
    value: object,
    message: str,
):
    document = valid_backlog()
    document["backlog"]["archived-themes"][0]["schema-version"] = 2
    root = write_repository(tmp_path, document)
    archive = root / "docs/plan/backlog-archive/TH1.yaml"
    snapshot = {"theme": v2_archive_theme("TH1")}
    snapshot["theme"][field] = value
    archive.write_text(yaml.safe_dump(snapshot, sort_keys=False))

    result = backlog.validate_repository(root)

    finding = next(
        item for item in result.findings if item["record"] == f"theme.{field}"
    )
    assert finding["file"] == "docs/plan/backlog-archive/TH1.yaml"
    assert message in finding["message"]


def test_v2_archive_index_entry_requires_done_status(tmp_path: Path):
    document = valid_backlog()
    summary = document["backlog"]["archived-themes"][0]
    summary.update({"schema-version": 2, "status": "in-progress"})
    root = write_repository(tmp_path, document)
    archive = root / "docs/plan/backlog-archive/TH1.yaml"
    archive.write_text(
        yaml.safe_dump({"theme": v2_archive_theme("TH1")}, sort_keys=False)
    )

    result = backlog.validate_repository(root)

    finding = next(
        item
        for item in result.findings
        if item["record"] == "backlog.archived-themes[0].status"
    )
    assert "status: done" in finding["message"]


def test_v2_archive_index_entry_requires_locked_true(tmp_path: Path):
    document = valid_backlog()
    summary = document["backlog"]["archived-themes"][0]
    summary.update({"schema-version": 2, "locked": False})
    root = write_repository(tmp_path, document)
    archive = root / "docs/plan/backlog-archive/TH1.yaml"
    archive.write_text(
        yaml.safe_dump({"theme": v2_archive_theme("TH1")}, sort_keys=False)
    )

    result = backlog.validate_repository(root)

    finding = next(
        item
        for item in result.findings
        if item["record"] == "backlog.archived-themes[0].locked"
    )
    assert "true" in str(finding["message"]).lower()


def test_locked_active_theme_without_version_uses_v1_contract(tmp_path: Path):
    document = valid_backlog()
    historical = v1_theme("TH4")
    historical["depends-on"] = ["TH2"]
    document["backlog"]["active-themes"].append(historical)
    root = write_repository(tmp_path, document)
    (root / "stories/TH4-US1.md").write_text("# historical\n")

    assert backlog.validate_repository(root).valid


def test_bdd_blocked_is_accepted_for_v2_story(tmp_path: Path):
    document = valid_backlog()
    document["backlog"]["active-themes"][0]["epics"][0]["stories"][0][
        "status"
    ] = "blocked"

    assert validate(tmp_path, document).valid


def test_bdd_unlocked_v1_theme_fails_closed_with_path_and_remediation(
    tmp_path: Path,
):
    document = valid_backlog()
    theme = document["backlog"]["active-themes"][0]
    del theme["schema-version"]

    result = validate(tmp_path, document)

    assert not result.valid
    finding = next(
        item
        for item in result.findings
        if item["record"] == "backlog.active-themes[0].schema-version"
    )
    assert "schema-version: 2" in finding["message"]
    assert "schema-version" in finding["remediation"]
    assert "2" in finding["remediation"]


def test_bdd_unknown_story_status_uses_exact_skill_vocabulary(tmp_path: Path):
    contract = independently_read_skill_contract()
    expected = contract["status-vocabulary"]["v2"]["story"]
    document = valid_backlog()
    document["backlog"]["active-themes"][0]["epics"][0]["stories"][0][
        "status"
    ] = "paused"

    result = validate(tmp_path, document)

    finding = next(item for item in result.findings if item["record"].endswith(".status"))
    assert result.valid is False
    assert "paused" in finding["message"]
    assert ", ".join(expected) in finding["message"]


def test_blocked_remains_invalid_in_v1_snapshot(tmp_path: Path):
    root = write_repository(tmp_path)
    archive = root / "docs/plan/backlog-archive/TH1.yaml"
    snapshot = yaml.safe_load(archive.read_text())
    snapshot["theme"]["epics"][0]["stories"][0]["status"] = "blocked"
    archive.write_text(yaml.safe_dump(snapshot, sort_keys=False))

    result = backlog.validate_repository(root)

    finding = next(item for item in result.findings if item["record"].endswith(".status"))
    assert finding["file"] == "docs/plan/backlog-archive/TH1.yaml"
    assert finding["record"] == "theme.epics[0].stories[0].status"
    assert "todo, in-progress, done, failed" in finding["message"]


def test_skill_status_vocabulary_is_independently_pinned_to_validator(
    tmp_path: Path,
):
    contract = independently_read_skill_contract()
    assert contract["status-vocabulary"] == {
        "v1": {
            "theme": ["todo", "in-progress", "done"],
            "epic": ["todo", "in-progress", "done"],
            "story": ["todo", "in-progress", "done", "failed"],
        },
        "v2": {
            "theme": ["todo", "in-progress", "done"],
            "epic": ["todo", "in-progress", "done"],
            "story": ["todo", "in-progress", "blocked", "failed", "done"],
        },
    }

    for level, location in (
        ("theme", (0,)),
        ("epic", (0, "epics", 0)),
        ("story", (0, "epics", 0, "stories", 0)),
    ):
        for status in contract["status-vocabulary"]["v2"][level]:
            document = valid_backlog()
            item = document["backlog"]["active-themes"]
            for part in location:
                item = item[part]
            item["status"] = status
            assert validate(tmp_path / f"v2-{level}-{status}", document).valid

    for level, location in (
        ("theme", ()),
        ("epic", ("epics", 0)),
        ("story", ("epics", 0, "stories", 0)),
    ):
        for status in contract["status-vocabulary"]["v1"][level]:
            root = write_repository(tmp_path / f"v1-{level}-{status}")
            archive = root / "docs/plan/backlog-archive/TH1.yaml"
            snapshot = yaml.safe_load(archive.read_text())
            item = snapshot["theme"]
            for part in location:
                item = item[part]
            item["status"] = status
            archive.write_text(yaml.safe_dump(snapshot, sort_keys=False))
            assert backlog.validate_repository(root).valid


def test_skill_documents_blocked_transition_pause_and_v1_compatibility():
    text = SKILL.read_text(encoding="utf-8")

    assert "`in-progress -> blocked -> in-progress`" in text
    assert "pause dispositions" in text
    assert "Discovery-escape" in text
    assert "Version 1 keeps its historical status" in text
    assert "absent `schema-version` means version 1" in text


def test_every_documented_key_is_exercised_by_an_accepted_fixture(tmp_path: Path):
    contract = independently_read_skill_contract()
    document = valid_backlog()
    document["backlog"]["archived-themes"][0]["schema-version"] = 1
    root = write_repository(tmp_path, document)
    snapshot_path = root / "docs/plan/backlog-archive/TH1.yaml"
    snapshot = yaml.safe_load(snapshot_path.read_text())
    snapshot["theme"]["schema-version"] = 1
    snapshot_path.write_text(yaml.safe_dump(snapshot, sort_keys=False))
    objects = {
        "backlog-v2": document["backlog"],
        "policy": document["backlog"]["policy"],
        "theme-v2": document["backlog"]["active-themes"][0],
        "epic-v2": document["backlog"]["active-themes"][0]["epics"][0],
        "story-v2": document["backlog"]["active-themes"][0]["epics"][0]["stories"][0],
        "risk": document["backlog"]["active-themes"][0]["epics"][0]["stories"][0]["risk"],
        "risk-override": document["backlog"]["active-themes"][0]["epics"][0]["stories"][0]["risk"]["overrides"][0],
        "model-route": document["backlog"]["active-themes"][0]["epics"][0]["stories"][0]["model-route"],
        "escalation": document["backlog"]["active-themes"][0]["epics"][0]["stories"][0]["model-route"]["escalations"][0],
        "verification": document["backlog"]["active-themes"][0]["epics"][0]["stories"][0]["verification"],
        "suite-policy": document["backlog"]["active-themes"][0]["epics"][0]["stories"][0]["verification"]["suite-policy"],
        "verification-waiver": document["backlog"]["active-themes"][0]["epics"][0]["stories"][0]["verification"]["waivers"][0],
        "budgets": document["backlog"]["active-themes"][0]["budgets"],
        "usage": document["backlog"]["active-themes"][0]["usage"],
        "evidence": document["backlog"]["active-themes"][0]["epics"][0]["stories"][0]["evidence"],
        "archived-theme": document["backlog"]["archived-themes"][0],
        "archive-stats": document["backlog"]["archived-themes"][0]["stats"],
        "theme-v1": snapshot["theme"],
        "epic-v1": snapshot["theme"]["epics"][0],
        "story-v1": snapshot["theme"]["epics"][0]["stories"][0],
    }

    assert backlog.validate_repository(root).valid
    assert set(objects) == set(contract["schemas"])
    for name, value in objects.items():
        documented = set(contract["schemas"][name]["properties"])
        assert documented <= set(value), f"{name} fixture omits {documented - set(value)}"


@pytest.mark.parametrize(
    ("mutate", "path"),
    (
        (
            lambda doc: doc["backlog"].update({"revision": "seven"}),
            "backlog.revision",
        ),
        (
            lambda doc: doc["backlog"]["active-themes"][0].update({"locked": "no"}),
            "backlog.active-themes[0].locked",
        ),
        (
            lambda doc: doc["backlog"]["active-themes"][0]["epics"][0][
                "stories"
            ][0]["risk"].update({"triggers": "risk"}),
            "backlog.active-themes[0].epics[0].stories[0].risk.triggers",
        ),
        (
            lambda doc: doc["backlog"]["active-themes"][0]["epics"][0][
                "stories"
            ][0]["budgets"].update({"target": True}),
            "backlog.active-themes[0].epics[0].stories[0].budgets.target",
        ),
    ),
)
def test_wrong_types_fail_at_the_exact_yaml_path(tmp_path: Path, mutate, path: str):
    document = valid_backlog()
    mutate(document)

    result = validate(tmp_path, document)

    assert path in finding_paths(result)
    assert all(set(item) == {
        "check", "severity", "file", "record", "message", "remediation"
    } for item in result.findings)


@pytest.mark.parametrize(
    ("mutate", "path"),
    (
        (
            lambda doc: doc["backlog"].update({"surprise": True}),
            "backlog.surprise",
        ),
        (
            lambda doc: doc["backlog"]["active-themes"][0]["epics"][0][
                "stories"
            ][0]["risk"].update({"score": 2}),
            "backlog.active-themes[0].epics[0].stories[0].risk.score",
        ),
        (
            lambda doc: doc["backlog"]["active-themes"][0]["epics"][0][
                "stories"
            ][0]["verification"]["suite-policy"].update({"release": "full"}),
            "backlog.active-themes[0].epics[0].stories[0].verification.suite-policy.release",
        ),
    ),
)
def test_unknown_keys_fail_closed(tmp_path: Path, mutate, path: str):
    document = valid_backlog()
    mutate(document)

    result = validate(tmp_path, document)

    finding = next(item for item in result.findings if item["record"] == path)
    assert "unknown key" in finding["message"]
    assert finding["remediation"]


def test_malformed_yaml_and_duplicate_keys_each_produce_one_finding(tmp_path: Path):
    malformed_root = write_repository(
        tmp_path / "malformed",
        backlog_text="backlog:\n  active-themes: [\n",
    )
    duplicate_root = write_repository(
        tmp_path / "duplicate",
        backlog_text="backlog:\n  revision: 1\n  revision: 2\n",
    )

    for root in (malformed_root, duplicate_root):
        result = backlog.validate_repository(root)
        assert len(result.findings) == 1
        assert result.findings[0]["record"] == "backlog"
        assert "YAML" in result.findings[0]["message"]


def test_recursive_sequence_alias_is_rejected_by_real_cli_as_one_json(
    tmp_path: Path,
):
    recursive = """\
backlog:
  schema-version: 2
  revision: 1
  project: fixture
  last-updated: 2026-09-06T18:00:00+01:00
  policy: {model-policy: null, budget-policy: null}
  active-themes: &themes
    - *themes
  archived-themes: []
"""
    root = write_repository(tmp_path, backlog_text=recursive)
    shutil.copytree(ROOT / "methodlib", root / "methodlib")
    (root / "bin").mkdir()
    shutil.copy2(ROOT / "bin/method", root / "bin/method")

    completed = subprocess.run(
        [str(root / "bin/method"), "validate", "schema", "--json"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert completed.returncode == exits.VALIDATION_FAILURE
    assert len(completed.stdout.splitlines()) == 1
    payload = json.loads(completed.stdout)
    assert payload["status"] == "failed"
    assert len(payload["findings"]) == 1
    finding = payload["findings"][0]
    assert finding["record"] == "backlog.active-themes[0]"
    assert "recursive YAML aliases" in finding["message"]
    assert "Traceback" not in completed.stderr


def test_recursive_contract_alias_is_framed_as_validation_failure(
    tmp_path: Path,
):
    root = write_repository(tmp_path)
    skill = root / backlog.SKILL_PATH
    text = skill.read_text()
    text = text.replace(
        "contract-version: 1",
        "contract-version: &recursive [*recursive]",
        1,
    )
    skill.write_text(text)

    result = cli.dispatch(["validate", "schema", "--json"], probe_directory=root)
    stdout = io.StringIO()
    stderr = io.StringIO()
    code = cli.emit(result, stdout=stdout, stderr=stderr)

    assert code == exits.VALIDATION_FAILURE
    assert len(stdout.getvalue().splitlines()) == 1
    payload = json.loads(stdout.getvalue())
    assert payload["findings"][0]["record"] == "schema-contract"
    assert "recursive YAML alias" in payload["findings"][0]["message"]
    assert "Traceback" not in stderr.getvalue()


@pytest.mark.parametrize(
    ("mutate", "expected_path", "message"),
    (
        (
            lambda doc: doc["backlog"]["active-themes"][0].update(
                {"depends-on": ["TH99"]}
            ),
            "backlog.active-themes[0].depends-on[0]",
            "does not resolve",
        ),
        (
            lambda doc: doc["backlog"]["active-themes"][0]["epics"][0][
                "stories"
            ][0].update({"depends-on": ["TH3.E1.US1"]}),
            "backlog.active-themes[0].epics[0].stories[0].depends-on[0]",
            "itself",
        ),
        (
            lambda doc: doc["backlog"]["active-themes"][0]["epics"][0].update(
                {"id": "TH4.E1"}
            ),
            "backlog.active-themes[0].epics[0].id",
            "does not belong",
        ),
        (
            lambda doc: doc["backlog"]["active-themes"][0]["epics"][0][
                "stories"
            ][0].update({"id": "TH3.E1.US0"}),
            "backlog.active-themes[0].epics[0].stories[0].id",
            "valid story-id",
        ),
    ),
)
def test_dependency_and_id_violations_are_precise(
    tmp_path: Path,
    mutate,
    expected_path: str,
    message: str,
):
    document = valid_backlog()
    mutate(document)

    result = validate(tmp_path, document)

    assert any(
        item["record"] == expected_path and message in item["message"]
        for item in result.findings
    )


def test_dependency_cycles_are_rejected_deterministically(tmp_path: Path):
    document = valid_backlog()
    first = document["backlog"]["active-themes"][0]["epics"][0]["stories"][0]
    second = copy.deepcopy(first)
    first["depends-on"] = ["TH3.E1.US2"]
    second["id"] = "TH3.E1.US2"
    second["file"] = "stories/US2.md"
    second["depends-on"] = ["TH3.E1.US1"]
    root = write_repository(tmp_path, document)
    (root / "stories/US2.md").write_text("# US2\n")
    document["backlog"]["active-themes"][0]["epics"][0]["stories"].append(second)
    (root / "docs/plan/backlog.yaml").write_text(
        yaml.safe_dump(document, sort_keys=False)
    )

    first_run = backlog.validate_repository(root)
    second_run = backlog.validate_repository(root)

    assert first_run == second_run
    assert any("dependency cycle" in item["message"] for item in first_run.findings)


def test_archived_epic_and_story_dependencies_use_repository_wide_index(
    tmp_path: Path,
):
    root = write_repository(tmp_path)
    backlog_path = root / "docs/plan/backlog.yaml"
    document = yaml.safe_load(backlog_path.read_text())
    active_epic = document["backlog"]["active-themes"][0]["epics"][0]
    active_epic["depends-on"] = ["TH1.E1"]
    active_epic["stories"][0]["depends-on"] = ["TH1.E1.US1"]
    backlog_path.write_text(yaml.safe_dump(document, sort_keys=False))
    archive = root / "docs/plan/backlog-archive/TH2.yaml"
    snapshot = yaml.safe_load(archive.read_text())
    epic = snapshot["theme"]["epics"][0]
    epic["depends-on"] = ["TH1.E1"]
    epic["stories"][0]["depends-on"] = ["TH1.E1.US1"]
    archive.write_text(yaml.safe_dump(snapshot, sort_keys=False))

    assert backlog.validate_repository(root).valid


@pytest.mark.parametrize(
    ("kind", "dependency", "expected_path"),
    (
        ("epic", "TH99.E1", "theme.epics[0].depends-on[0]"),
        ("story", "TH99.E1.US1", "theme.epics[0].stories[0].depends-on[0]"),
    ),
)
def test_archived_dependencies_still_reject_dangling_targets(
    tmp_path: Path,
    kind: str,
    dependency: str,
    expected_path: str,
):
    root = write_repository(tmp_path)
    archive = root / "docs/plan/backlog-archive/TH2.yaml"
    snapshot = yaml.safe_load(archive.read_text())
    epic = snapshot["theme"]["epics"][0]
    target = epic if kind == "epic" else epic["stories"][0]
    target["depends-on"] = [dependency]
    archive.write_text(yaml.safe_dump(snapshot, sort_keys=False))

    result = backlog.validate_repository(root)

    finding = next(item for item in result.findings if item["record"] == expected_path)
    assert finding["file"] == "docs/plan/backlog-archive/TH2.yaml"
    assert "does not resolve" in finding["message"]


def test_archived_dependency_cycles_are_not_executable_graph_cycles(tmp_path: Path):
    root = write_repository(tmp_path)
    archive = root / "docs/plan/backlog-archive/TH2.yaml"
    snapshot = yaml.safe_load(archive.read_text())
    first = snapshot["theme"]["epics"][0]["stories"][0]
    second = copy.deepcopy(first)
    first["depends-on"] = ["TH2.E1.US2"]
    second["id"] = "TH2.E1.US2"
    second["file"] = "stories/TH2-US2.md"
    second["depends-on"] = ["TH2.E1.US1"]
    snapshot["theme"]["epics"][0]["stories"].append(second)
    (root / "stories/TH2-US2.md").write_text("# historical\n")
    archive.write_text(yaml.safe_dump(snapshot, sort_keys=False))

    assert backlog.validate_repository(root).valid


def test_archive_ref_outside_canonical_root_cannot_supply_v1_or_dependencies(
    tmp_path: Path,
):
    document = valid_backlog()
    summary = document["backlog"]["archived-themes"][0]
    summary["archive-ref"] = "docs/plan/indexed/TH1.yaml"
    active_story = document["backlog"]["active-themes"][0]["epics"][0]["stories"][0]
    active_story["depends-on"] = ["TH1.E1.US1"]
    root = write_repository(tmp_path, document)
    outside = root / "docs/plan/indexed/TH1.yaml"
    outside.parent.mkdir()
    outside.write_text(
        yaml.safe_dump({"theme": v1_theme("TH1")}, sort_keys=False),
        encoding="utf-8",
    )

    result = backlog.validate_repository(root)

    assert any(
        item["record"] == "backlog.archived-themes[0].archive-ref"
        and "docs/plan/backlog-archive/" in item["message"]
        for item in result.findings
    )
    assert any(
        item["record"].endswith(".depends-on[0]")
        and "TH1.E1.US1" in item["message"]
        and "does not resolve" in item["message"]
        for item in result.findings
    )


def test_mismatched_archive_identity_cannot_supply_dependency_targets(
    tmp_path: Path,
):
    document = valid_backlog()
    active_story = document["backlog"]["active-themes"][0]["epics"][0]["stories"][0]
    active_story["depends-on"] = ["TH9.E1.US1"]
    root = write_repository(tmp_path, document)
    archive = root / "docs/plan/backlog-archive/TH1.yaml"
    archive.write_text(
        yaml.safe_dump({"theme": v1_theme("TH9")}, sort_keys=False),
        encoding="utf-8",
    )
    (root / "stories/TH9-US1.md").write_text("# historical\n", encoding="utf-8")

    result = backlog.validate_repository(root)

    assert any(
        item["file"] == "docs/plan/backlog-archive/TH1.yaml"
        and item["record"] == "theme.id"
        and "does not match archive index ID" in item["message"]
        for item in result.findings
    )
    assert any(
        item["record"].endswith(".depends-on[0]")
        and "TH9.E1.US1" in item["message"]
        and "does not resolve" in item["message"]
        for item in result.findings
    )


def test_malformed_story_id_and_dangling_file_both_report_deterministically(
    tmp_path: Path,
):
    document = valid_backlog()
    story = document["backlog"]["active-themes"][0]["epics"][0]["stories"][0]
    story["id"] = None
    story["file"] = "stories/missing.md"
    root = write_repository(tmp_path, document)

    first = backlog.validate_repository(root)
    second = backlog.validate_repository(root)

    assert first == second
    paths = [finding["record"] for finding in first.findings]
    assert "backlog.active-themes[0].epics[0].stories[0].id" in paths
    assert "backlog.active-themes[0].epics[0].stories[0].file" in paths


def test_dangling_and_escaping_story_paths_fail_closed(tmp_path: Path):
    for name, value in (
        ("missing", "stories/missing.md"),
        ("absolute", "/tmp/story.md"),
        ("traversal", "../story.md"),
    ):
        document = valid_backlog()
        document["backlog"]["active-themes"][0]["epics"][0]["stories"][0][
            "file"
        ] = value
        result = validate(tmp_path / name, document)
        path = "backlog.active-themes[0].epics[0].stories[0].file"
        assert path in finding_paths(result)


def test_story_symlink_cannot_escape_repository(tmp_path: Path):
    root = write_repository(tmp_path)
    outside = tmp_path / "outside.md"
    outside.write_text("# outside\n")
    link = root / "stories/escape.md"
    link.symlink_to(outside)
    document = yaml.safe_load((root / backlog.BACKLOG_PATH).read_text())
    document["backlog"]["active-themes"][0]["epics"][0]["stories"][0][
        "file"
    ] = "stories/escape.md"
    (root / backlog.BACKLOG_PATH).write_text(yaml.safe_dump(document, sort_keys=False))

    result = backlog.validate_repository(root)

    assert (
        "backlog.active-themes[0].epics[0].stories[0].file"
        in finding_paths(result)
    )


def test_failure_cli_contract_is_exit_two_and_exactly_one_json_object(
    tmp_path: Path,
):
    document = valid_backlog()
    document["backlog"]["active-themes"][0]["epics"][0]["stories"][0][
        "status"
    ] = "paused"
    root = write_repository(tmp_path, document)

    result = cli.dispatch(["validate", "schema", "--json"], probe_directory=root)
    stdout = io.StringIO()
    stderr = io.StringIO()
    code = cli.emit(result, stdout=stdout, stderr=stderr)

    assert code == exits.VALIDATION_FAILURE
    assert len(stdout.getvalue().splitlines()) == 1
    payload = json.loads(stdout.getvalue())
    assert payload["status"] == "failed"
    assert payload["findings"]
    assert all(
        set(finding)
        == {"check", "severity", "file", "record", "message", "remediation"}
        for finding in payload["findings"]
    )
    assert stderr.getvalue()


def test_missing_required_v2_block_fails_at_its_yaml_path(tmp_path: Path):
    document = valid_backlog()
    story = document["backlog"]["active-themes"][0]["epics"][0]["stories"][0]

    for key in (
        "risk",
        "model-route",
        "verification",
        "review-profile",
        "budgets",
        "usage",
        "evidence",
        "confidence",
    ):
        candidate = copy.deepcopy(document)
        del candidate["backlog"]["active-themes"][0]["epics"][0]["stories"][0][
            key
        ]
        result = validate(tmp_path / key, candidate)
        assert (
            f"backlog.active-themes[0].epics[0].stories[0].{key}"
            in finding_paths(result)
        )

    assert set(story) >= {
        "risk",
        "model-route",
        "verification",
        "review-profile",
        "budgets",
        "usage",
        "evidence",
        "confidence",
    }


@pytest.mark.parametrize("confidence", ("measured", "estimated"))
def test_zero_usage_is_valid_only_as_an_actual_known_sample(
    tmp_path: Path,
    confidence: str,
):
    document = valid_backlog()
    for usage in (
        document["backlog"]["active-themes"][0]["usage"],
        document["backlog"]["active-themes"][0]["epics"][0]["usage"],
    ):
        usage.update(
            {
                "value": 0,
                "confidence": confidence,
                "source": "local-session",
                "sampled-at": "2026-09-06T18:00:00+01:00",
            }
        )

    assert validate(tmp_path, document).valid


@pytest.mark.parametrize(
    ("updates", "field"),
    (
        ({"value": 0}, "value"),
        ({"source": "local-session"}, "source"),
        ({"sampled-at": "2026-09-06T18:00:00+01:00"}, "sampled-at"),
    ),
)
def test_unknown_usage_requires_null_value_none_source_and_null_timestamp(
    tmp_path: Path,
    updates: dict[str, object],
    field: str,
):
    document = valid_backlog()
    usage = document["backlog"]["active-themes"][0]["usage"]
    usage.update(updates)

    result = validate(tmp_path, document)

    expected = f"backlog.active-themes[0].usage.{field}"
    assert any(
        finding["record"] == expected and "unknown usage requires" in finding["message"]
        for finding in result.findings
    )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("value", None),
        ("value", -1),
        ("source", "none"),
        ("source", ""),
        ("sampled-at", None),
        ("sampled-at", "2026-09-06T18:00:00"),
    ),
)
def test_known_usage_requires_a_coherent_actual_sample(
    tmp_path: Path,
    field: str,
    value: object,
):
    document = valid_backlog()
    usage = document["backlog"]["active-themes"][0]["usage"]
    usage.update(
        {
            "value": 1,
            "confidence": "estimated",
            "source": "token-proxy",
            "sampled-at": "2026-09-06T18:00:00+01:00",
            field: value,
        }
    )

    result = validate(tmp_path, document)

    assert f"backlog.active-themes[0].usage.{field}" in finding_paths(result)


def test_story_confidence_uses_architecture_vocabulary_with_bounded_legacy(
    tmp_path: Path,
):
    contract = independently_read_skill_contract()
    confidence_schema = contract["schemas"]["story-v2"]["properties"]["confidence"]
    expected_migration = {
        "TH3.E1.US1": (
            "high",
            "APPROVED after developer rework iteration 1",
        ),
        "TH3.E1.US2": (
            "high",
            "APPROVED by final closed-checklist review: AC1-AC6, all BDD "
            "scenarios, and all adjudicated actions passed",
        ),
        "TH3.E1.US3": (
            "high",
            "APPROVED by final closed-checklist review: AC1-AC5, all BDD "
            "scenarios, and all adjudicated evidence actions passed",
        ),
        "TH3.E1.US4": ("high", "APPROVED by standard reviewer"),
        "TH3.E2.US1": (
            "high",
            "APPROVED after rework iteration 1",
        ),
        "TH3.E2.US2": (
            "high",
            "APPROVED after rework iteration 1",
        ),
    }
    code_migration = {
        identifier: (confidence, evidence)
        for identifier, confidence, evidence in backlog.LEGACY_CONFIDENCE_MIGRATION
    }
    real_document = yaml.safe_load((ROOT / backlog.BACKLOG_PATH).read_text())
    completed_legacy = {}
    archived_th3 = next(
        item
        for item in real_document["backlog"]["archived-themes"]
        if item["id"] == "TH3"
    )
    archived_document = yaml.safe_load(
        (ROOT / archived_th3["archive-ref"]).read_text(encoding="utf-8")
    )
    for theme in [archived_document["theme"]]:
        for epic in theme["epics"]:
            for story in epic["stories"]:
                if story.get("confidence") in confidence_schema["legacy-enum"]:
                    completed_legacy[story["id"]] = (
                        story["confidence"],
                        story["status"],
                        story["evidence"]["review"],
                    )

    assert confidence_schema["enum"] == ["measured", "estimated", "unknown"]
    assert confidence_schema["legacy-enum"] == ["high", "medium", "low"]
    assert set(confidence_schema["legacy-records"]) == set(expected_migration)
    assert code_migration == expected_migration
    assert set(completed_legacy) == set(expected_migration)
    for identifier, (confidence, acceptance) in expected_migration.items():
        actual_confidence, status, reviews = completed_legacy[identifier]
        assert (actual_confidence, status) == (confidence, "done")
        assert acceptance in reviews
    for confidence in confidence_schema["enum"]:
        document = valid_backlog()
        document["backlog"]["active-themes"][0]["epics"][0]["stories"][0][
            "confidence"
        ] = confidence
        assert validate(tmp_path / confidence, document).valid

    for identifier, (confidence, acceptance) in expected_migration.items():
        legacy_completed = valid_backlog()
        epic = legacy_completed["backlog"]["active-themes"][0]["epics"][0]
        epic["id"] = ".".join(identifier.split(".")[:2])
        legacy_story = epic["stories"][0]
        legacy_story.update(
            {
                "id": identifier,
                "status": "done",
                "confidence": confidence,
            }
        )
        legacy_story["evidence"]["review"] = [acceptance]
        assert validate(tmp_path / identifier, legacy_completed).valid

    legacy_unfinished = valid_backlog()
    legacy_unfinished["backlog"]["active-themes"][0]["epics"][0]["stories"][0][
        "confidence"
    ] = "high"
    result = validate(tmp_path / "legacy-unfinished", legacy_unfinished)
    assert any(
        finding["record"].endswith(".confidence")
        and "pinned acceptance evidence" in finding["message"]
        for finding in result.findings
    )


@pytest.mark.parametrize(
    ("confidence", "reviews"),
    (
        ("medium", ["APPROVED after developer rework iteration 1"]),
        ("high", ["different approval"]),
        ("high", []),
    ),
)
def test_legacy_confidence_requires_exact_value_and_acceptance_evidence(
    tmp_path: Path,
    confidence: str,
    reviews: list[str],
):
    document = valid_backlog()
    story = document["backlog"]["active-themes"][0]["epics"][0]["stories"][0]
    story.update({"status": "done", "confidence": confidence})
    story["evidence"]["review"] = reviews

    result = validate(tmp_path, document)

    assert any(
        finding["record"].endswith(".confidence")
        and "pinned acceptance evidence" in finding["message"]
        for finding in result.findings
    )


@pytest.mark.parametrize("mutation", ("extend", "replace"))
def test_skill_legacy_allowlist_drift_fails_closed(
    tmp_path: Path,
    mutation: str,
):
    root = write_repository(tmp_path)
    skill = root / backlog.SKILL_PATH
    text = skill.read_text(encoding="utf-8")
    if mutation == "extend":
        text = text.replace(
            "          - TH3.E2.US2\n",
            "          - TH3.E2.US2\n          - TH3.E2.US3\n",
            1,
        )
    else:
        text = text.replace("          - TH3.E2.US2\n", "          - TH3.E2.US9\n", 1)
    skill.write_text(text, encoding="utf-8")

    result = backlog.validate_repository(root)

    assert len(result.findings) == 1
    assert result.findings[0]["record"] == "schema-contract"
    assert "immutable migration cohort" in result.findings[0]["message"]


@pytest.mark.parametrize(
    ("mutation", "expected_message"),
    (
        (
            "remove",
            "schema contract story-v2.cross-field must be exactly story-confidence",
        ),
        (
            "replace",
            "schema contract story-v2.cross-field must be exactly story-confidence",
        ),
        ("duplicate", "schema contract contains malformed YAML"),
    ),
)
def test_story_cross_field_contract_drift_fails_closed_via_real_cli(
    tmp_path: Path,
    mutation: str,
    expected_message: str,
):
    root = write_repository(tmp_path)
    skill = root / backlog.SKILL_PATH
    text = skill.read_text(encoding="utf-8")
    rule = "    cross-field: story-confidence\n"
    if mutation == "remove":
        text = text.replace(rule, "", 1)
    elif mutation == "replace":
        text = text.replace(rule, "    cross-field: usage-sample\n", 1)
    else:
        text = text.replace(rule, f"{rule}    cross-field: usage-sample\n", 1)
    skill.write_text(text, encoding="utf-8")
    shutil.copytree(ROOT / "methodlib", root / "methodlib")
    (root / "bin").mkdir()
    shutil.copy2(ROOT / "bin/method", root / "bin/method")

    completed = subprocess.run(
        [str(root / "bin/method"), "validate", "schema", "--json"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert completed.returncode == exits.VALIDATION_FAILURE
    assert len(completed.stdout.splitlines()) == 1
    payload = json.loads(completed.stdout)
    assert payload["status"] == "failed"
    assert len(payload["findings"]) == 1
    assert payload["findings"][0] == {
        "check": "schema",
        "severity": "error",
        "file": ".github/skills/backlog-management/SKILL.md",
        "record": "schema-contract",
        "message": f"schema-contract: {expected_message}",
        "remediation": (
            "Restore the machine-readable contract in backlog-management."
        ),
    }
    assert "Traceback" not in completed.stderr


def test_skill_encodes_usage_semantics_and_canonical_confidence():
    contract = independently_read_skill_contract()
    text = SKILL.read_text(encoding="utf-8")

    assert contract["schemas"]["usage"]["cross-field"] == "usage-sample"
    assert contract["schemas"]["story-v2"]["cross-field"] == "story-confidence"
    assert "`measured|estimated|unknown`" in text
    assert "accepted only on the completed pre-v2 story IDs" in text
