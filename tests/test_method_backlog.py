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

from methodlib import backlog, cli, exits, packet  # noqa: E402


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
            "gitflow": ["not-applicable: isolated fixture has no delivery remote"],
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


def story_document(
    identifier: str = "TH3.E1.US1",
    *,
    title: str = "Schema story",
    agents: tuple[str, ...] = ("developer",),
    story_type: str = "standard",
    priority: str | None = None,
    size: str | None = None,
    dependencies: tuple[str, ...] = (),
) -> str:
    optional = ""
    if priority is not None:
        optional += f"priority: {priority}\n"
    if size is not None:
        optional += f"size: {size}\n"
    return (
        "---\n"
        f"id: {identifier}\n"
        f'title: "{title}"\n'
        f"type: {story_type}\n"
        f"{optional}"
        f"agents: [{', '.join(agents)}]\n"
        "skills: [the-copilot-build-method]\n"
        "traceability:\n"
        "  vision: [VO-001]\n"
        "  requirements: [PR-001]\n"
        "  adrs: [ADR-004]\n"
        "  invariants: [INV-001]\n"
        "acceptance-criteria:\n"
        '  - AC1: "Packet contract is enforced"\n'
        f"depends-on: [{', '.join(dependencies)}]\n"
        "---\n\n"
        f"# {identifier}\n"
    )


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
    method_skill = root / ".github/skills/the-copilot-build-method/SKILL.md"
    method_skill.parent.mkdir(parents=True, exist_ok=True)
    method_skill.write_text(
        (ROOT / ".github/skills/the-copilot-build-method/SKILL.md").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    for name in ("bdd-stories", "code-quality"):
        target = root / f".github/skills/{name}/SKILL.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            (ROOT / f".github/skills/{name}/SKILL.md").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    for directory in (
        "docs/vision_of_product/VP3",
        "docs/discovery/VP3",
        "docs/architecture",
        "docs/ADRs",
    ):
        (root / directory).mkdir(parents=True, exist_ok=True)
    (root / "docs/vision_of_product/VP3/README.md").write_text("# Vision\n")
    (root / "docs/discovery/VP3/README.md").write_text("# Discovery\n")
    (root / "docs/requirements/VP3").mkdir(parents=True)
    (root / "docs/requirements/VP3/PRD.md").write_text("# Requirements\n")
    (root / "docs/architecture/README.md").write_text("# Architecture\n")
    (root / "docs/ADRs/ADR-004-fixture.md").write_text("# ADR-004\n")
    plan = root / "docs/plan"
    (plan / "backlog-archive").mkdir(parents=True)
    (root / "stories").mkdir()
    for name in ("US1.md", "TH1-US1.md", "TH2-US1.md"):
        (root / "stories" / name).write_text(
            story_document(),
            encoding="utf-8",
        )
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
        "v3": {
            "theme": ["todo", "in-progress", "done"],
            "epic": ["todo", "in-progress", "blocked", "failed", "done"],
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
    from test_epic_backlog import epic_repository, v3_backlog, v3_child

    prospective = v3_backlog()
    theme_v3 = prospective["backlog"]["active-themes"][0]
    epic_v3 = theme_v3["epics"][0]
    child_v3 = {**v3_child(), "priority": "medium"}
    epic_v3["stories"] = [child_v3]
    prospective_root = epic_repository(tmp_path / "v3", prospective)
    assert backlog.validate_repository(prospective_root).valid
    objects.update({
        "theme-v3": theme_v3, "epic-v3": epic_v3, "story-v3": child_v3,
    })
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


def test_packet_projection_uses_backlog_fifo_without_duplicate_queue_state(
    tmp_path: Path,
):
    document = valid_backlog()
    story = document["backlog"]["active-themes"][0]["epics"][0]["stories"][0]
    story["status"] = "done"
    second = copy.deepcopy(story)
    second.update(
        {
            "id": "TH3.E1.US2",
            "title": "Next eligible story",
            "status": "todo",
            "priority": "low",
            "file": "stories/US2.md",
            "depends-on": ["TH3.E1.US1"],
        }
    )
    third = copy.deepcopy(story)
    third.update(
        {
            "id": "TH3.E1.US3",
            "title": "Blocked by dependency",
            "status": "todo",
            "priority": "high",
            "file": "stories/US3.md",
            "depends-on": ["TH3.E1.US2"],
        }
    )
    stories = document["backlog"]["active-themes"][0]["epics"][0]["stories"]
    stories.extend([second, third])
    root = write_repository(tmp_path, document)
    (root / "stories/US2.md").write_text("# US2\n", encoding="utf-8")
    (root / "stories/US3.md").write_text("# US3\n", encoding="utf-8")

    result = packet.project_next(root)

    assert result.exit_code == exits.SUCCESS
    projection = result.payload["projection"]
    assert projection["source"]["path"] == "docs/plan/backlog.yaml"
    assert projection["story"]["id"] == "TH3.E1.US2"
    assert projection["dependencies"]["story"] == ["TH3.E1.US1"]


@pytest.mark.parametrize("status", ("blocked", "failed", "in-progress"))
def test_packet_projection_refuses_non_dispatchable_story_status(
    tmp_path: Path,
    status: str,
):
    document = valid_backlog()
    document["backlog"]["active-themes"][0]["epics"][0]["stories"][0][
        "status"
    ] = status
    root = write_repository(tmp_path, document)

    result = packet.project_next(root)

    assert result.exit_code == exits.VALIDATION_FAILURE
    assert result.payload["status"] == "projection-refused"
    assert any(status in finding["message"] for finding in result.payload["findings"])


def test_packet_build_preflight_verify_and_stale_backlog_detection(tmp_path: Path):
    root = write_repository(tmp_path)
    allowed = tmp_path / "implementation"
    implementation = allowed / "checkout"
    implementation.mkdir(parents=True)
    build = packet.build_packet(
        root,
        task="impl-1",
        story_id=None,
        mode="developer",
        implementation_root=implementation.as_posix(),
        allowed_implementation_root=allowed.as_posix(),
        planning_roots=[root.as_posix()],
    )
    packet_path = build.payload["packet"]

    assert build.exit_code == exits.SUCCESS
    preflight = packet.preflight_packet(
        root,
        packet_path=packet_path,
        allowed_implementation_root=allowed.as_posix(),
        expected_authorization_hash=str(build.payload["authorization_hash"]),
    )
    assert preflight.exit_code == exits.SUCCESS
    assert preflight.payload["findings"] == []

    backlog_path = root / "docs/plan/backlog.yaml"
    document = yaml.safe_load(backlog_path.read_text(encoding="utf-8"))
    document["backlog"]["revision"] = 8
    backlog_path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    verify = packet.verify_packet(
        root,
        packet_path=packet_path,
        allowed_implementation_root=allowed.as_posix(),
        expected_authorization_hash=str(build.payload["authorization_hash"]),
    )

    assert verify.exit_code == exits.VALIDATION_FAILURE
    assert verify.payload["status"] == "STALE"
    assert any(
        finding["record"] == "backlog.revision"
        for finding in verify.payload["findings"]
    )


def test_packet_build_refuses_missing_implementation_root(tmp_path: Path):
    root = write_repository(tmp_path)

    result = packet.build_packet(
        root,
        task="impl-1",
        story_id=None,
        mode="developer",
        implementation_root=(tmp_path / "missing").as_posix(),
        allowed_implementation_root=(tmp_path / "implementation").as_posix(),
        planning_roots=[root.as_posix()],
    )

    assert result.exit_code == exits.VALIDATION_FAILURE
    assert result.payload["status"] == "failed"
    assert any(
        finding["record"] == "implementation-root"
        for finding in result.payload["findings"]
    )


def test_planning_packet_cannot_authorize_mutations(tmp_path: Path):
    root = write_repository(tmp_path)
    (root / "stories/US1.md").write_text(
        story_document(agents=("product-owner",)),
        encoding="utf-8",
    )
    allowed = tmp_path / "implementation"
    implementation = allowed / "checkout"
    implementation.mkdir(parents=True)

    build = packet.build_packet(
        root,
        task="plan-1",
        story_id=None,
        mode="planning",
        implementation_root=implementation.as_posix(),
        allowed_implementation_root=allowed.as_posix(),
        planning_roots=[root.as_posix()],
    )
    packet_path = root / build.payload["packet"]
    document = yaml.safe_load(packet_path.read_text(encoding="utf-8"))

    assert build.exit_code == exits.SUCCESS
    assert document["workspace"]["mutation-scope"] == []
    assert document["workspace"]["implementation-root"] in document["workspace"][
        "denied-paths"
    ]
    assert "write-implementation" not in document["workspace"]["permitted-actions"]


def test_packet_build_rejects_later_eligible_story_until_fifo_projection_runs(
    tmp_path: Path,
):
    document = valid_backlog()
    first = document["backlog"]["active-themes"][0]["epics"][0]["stories"][0]
    second = copy.deepcopy(first)
    second.update(
        {
            "id": "TH3.E1.US2",
            "title": "Later story",
            "status": "todo",
            "file": "stories/US2.md",
            "depends-on": [],
        }
    )
    document["backlog"]["active-themes"][0]["epics"][0]["stories"].append(second)
    root = write_repository(tmp_path, document)
    (root / "stories/US2.md").write_text(
        story_document("TH3.E1.US2"),
        encoding="utf-8",
    )
    allowed = tmp_path / "implementation"
    implementation = allowed / "checkout"
    implementation.mkdir(parents=True)

    result = packet.build_packet(
        root,
        task="impl-2",
        story_id="TH3.E1.US2",
        mode="developer",
        implementation_root=implementation.as_posix(),
        allowed_implementation_root=allowed.as_posix(),
        planning_roots=[root.as_posix()],
    )

    assert result.exit_code == exits.VALIDATION_FAILURE
    assert "not the next FIFO projection" in result.payload["findings"][0]["message"]


def build_test_packet(
    root: Path,
    tmp_path: Path,
    *,
    mode: str = "developer",
    task: str = "impl-1",
) -> tuple[packet.PacketResult, Path]:
    (root / "stories/US1.md").write_text(
        story_document(
            agents=("developer",) if mode == "developer" else ("product-owner",)
        ),
        encoding="utf-8",
    )
    allowed = tmp_path / f"{task}-implementation"
    implementation = allowed / "checkout"
    implementation.mkdir(parents=True)
    result = packet.build_packet(
        root,
        task=task,
        story_id=None,
        mode=mode,
        implementation_root=implementation.as_posix(),
        allowed_implementation_root=allowed.as_posix(),
        planning_roots=[root.as_posix()],
    )
    assert result.exit_code == exits.SUCCESS
    return result, root / str(result.payload["packet"])


@pytest.mark.parametrize(
    ("field", "mutate"),
    (
        ("story", lambda value: value["story"].update({"title": "Tampered"})),
        ("workspace", lambda value: value["workspace"]["permitted-actions"].append("shell")),
        ("required-gates", lambda value: value["required-gates"].append("bypass")),
    ),
)
def test_packet_authorization_hash_rejects_tampered_authority(
    tmp_path: Path,
    field: str,
    mutate,
):
    root = write_repository(tmp_path)
    build, path = build_test_packet(root, tmp_path)
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    mutate(document)
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    result = packet.verify_packet(
        root,
        packet_path=path.relative_to(root).as_posix(),
        allowed_implementation_root=(
            tmp_path / "impl-1-implementation"
        ).as_posix(),
        expected_authorization_hash=str(build.payload["authorization_hash"]),
    )

    assert result.exit_code == exits.VALIDATION_FAILURE
    assert any(
        finding["record"] == "authorization-hash"
        for finding in result.payload["findings"]
    ), field


def test_packet_story_is_checked_against_authority_after_hash_is_recomputed(
    tmp_path: Path,
):
    root = write_repository(tmp_path)
    build, path = build_test_packet(root, tmp_path)
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    document["story"]["title"] = "Forged but self-consistent"
    document["authorization-hash"] = packet._authorization_hash(document)
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    result = packet.verify_packet(
        root,
        packet_path=path.relative_to(root).as_posix(),
        allowed_implementation_root=(
            tmp_path / "impl-1-implementation"
        ).as_posix(),
        expected_authorization_hash=str(build.payload["authorization_hash"]),
    )

    assert result.exit_code == exits.VALIDATION_FAILURE
    assert any(
        finding["record"] == "story"
        and "authoritative backlog" in finding["message"]
        for finding in result.payload["findings"]
    )


def test_planning_packet_cannot_be_tampered_into_developer_capabilities(
    tmp_path: Path,
):
    root = write_repository(tmp_path)
    build, path = build_test_packet(root, tmp_path, mode="planning", task="plan")
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    implementation = document["workspace"]["implementation-root"]
    document["mode"] = "developer"
    document["workspace"].update(
        {
            "permitted-actions": [
                "read",
                "write-implementation",
                "test",
                "review",
            ],
            "mutation-scope": [implementation],
            "denied-paths": [root.as_posix()],
        }
    )
    document["required-skills"].append("code-quality")
    document["required-gates"] = ["lint", "unit", "integration", "review"]
    document["authorization-hash"] = packet._authorization_hash(document)
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    result = packet.verify_packet(
        root,
        packet_path=path.relative_to(root).as_posix(),
        allowed_implementation_root=(tmp_path / "plan-implementation").as_posix(),
        expected_authorization_hash=str(build.payload["authorization_hash"]),
    )

    assert result.exit_code == exits.VALIDATION_FAILURE
    assert any(
        finding["record"] == "mode"
        and "authoritative backlog data" in finding["message"]
        for finding in result.payload["findings"]
    )


@pytest.mark.parametrize("case", ("broad", "outside", "overlap"))
def test_packet_rejects_broad_outside_or_overlapping_implementation_roots(
    tmp_path: Path,
    case: str,
):
    root = write_repository(tmp_path)
    dedicated = tmp_path / "implementation"
    implementation = dedicated / "checkout"
    implementation.mkdir(parents=True)
    allowed = dedicated
    if case == "broad":
        allowed = tmp_path
    elif case == "outside":
        allowed = tmp_path / "other"
        allowed.mkdir()
    elif case == "overlap":
        implementation = root

    result = packet.build_packet(
        root,
        task=f"invalid-{case}",
        story_id=None,
        mode="developer",
        implementation_root=implementation.as_posix(),
        allowed_implementation_root=allowed.as_posix(),
        planning_roots=[root.as_posix()],
    )

    assert result.exit_code == exits.VALIDATION_FAILURE
    assert any(
        finding["record"]
        in {"allowed-implementation-root", "implementation-root"}
        for finding in result.payload["findings"]
    )


def test_packet_requires_authoritative_repository_as_a_planning_root(tmp_path: Path):
    root = write_repository(tmp_path)
    (root / "stories/US1.md").write_text(
        story_document(agents=("product-owner",)),
        encoding="utf-8",
    )
    planning = tmp_path / "partial-planning"
    planning.mkdir()
    allowed = tmp_path / "implementation"
    implementation = allowed / "checkout"
    implementation.mkdir(parents=True)

    result = packet.build_packet(
        root,
        task="missing-authority",
        story_id=None,
        mode="planning",
        implementation_root=implementation.as_posix(),
        allowed_implementation_root=allowed.as_posix(),
        planning_roots=[planning.as_posix()],
    )

    assert result.exit_code == exits.VALIDATION_FAILURE
    assert any(
        finding["record"] == "planning-roots"
        and "authoritative repository" in finding["message"]
        for finding in result.payload["findings"]
    )


def test_packet_build_rejects_mode_not_authorized_by_story_agents(tmp_path: Path):
    root = write_repository(tmp_path)
    (root / "stories/US1.md").write_text(
        story_document(agents=("developer", "reviewer")),
        encoding="utf-8",
    )
    allowed = tmp_path / "implementation"
    implementation = allowed / "checkout"
    implementation.mkdir(parents=True)

    result = packet.build_packet(
        root,
        task="unauthorized-plan",
        story_id=None,
        mode="planning",
        implementation_root=implementation.as_posix(),
        allowed_implementation_root=allowed.as_posix(),
        planning_roots=[root.as_posix()],
    )

    assert result.exit_code == exits.VALIDATION_FAILURE
    assert result.payload["status"] == "packet-refused"
    assert "not requested planning mode" in result.payload["message"]


@pytest.mark.parametrize("action", ("verify", "preflight"))
def test_packet_rejects_recomputed_workspace_boundary_against_caller_assertion(
    tmp_path: Path,
    action: str,
):
    root = write_repository(tmp_path)
    build, path = build_test_packet(root, tmp_path)
    expected_allowed = tmp_path / "impl-1-implementation"
    forged_allowed = tmp_path / "forged-implementation"
    forged_checkout = forged_allowed / "checkout"
    forged_checkout.mkdir(parents=True)
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    document["workspace"].update(
        {
            "allowed-implementation-root": forged_allowed.as_posix(),
            "implementation-root": forged_checkout.as_posix(),
            "mutation-scope": [forged_checkout.as_posix()],
        }
    )
    document["authorization-hash"] = packet._authorization_hash(document)
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    result = cli.dispatch(
        [
            "packet",
            action,
            "--packet",
            path.relative_to(root).as_posix(),
            "--allowed-implementation-root",
            expected_allowed.as_posix(),
            "--expected-authorization-hash",
            str(build.payload["authorization_hash"]),
        ],
        probe_directory=root,
    )

    assert result.exit_code == exits.VALIDATION_FAILURE
    assert any(
        finding["record"] == "workspace.allowed-implementation-root"
        and "caller-authorized boundary" in finding["message"]
        for finding in result.payload["findings"]
    )


def test_packet_rejects_dotdot_workspace_alias_even_with_recomputed_hash(
    tmp_path: Path,
):
    root = write_repository(tmp_path)
    build, path = build_test_packet(root, tmp_path)
    allowed = tmp_path / "impl-1-implementation"
    (allowed / "alias").mkdir()
    alias = f"{allowed.as_posix()}/alias/../checkout"
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    document["workspace"]["implementation-root"] = alias
    document["workspace"]["mutation-scope"] = [alias]
    document["authorization-hash"] = packet._authorization_hash(document)
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    result = packet.verify_packet(
        root,
        packet_path=path.relative_to(root).as_posix(),
        allowed_implementation_root=allowed.as_posix(),
        expected_authorization_hash=str(build.payload["authorization_hash"]),
    )

    assert result.exit_code == exits.VALIDATION_FAILURE
    assert any(
        finding["record"] == "workspace.implementation-root"
        and "canonical resolved absolute" in finding["message"]
        for finding in result.payload["findings"]
    )


def test_packet_build_and_preflight_reject_extra_planning_root(tmp_path: Path):
    root = write_repository(tmp_path)
    allowed = tmp_path / "implementation"
    implementation = allowed / "checkout"
    implementation.mkdir(parents=True)

    build = packet.build_packet(
        root,
        task="extra-planning",
        story_id=None,
        mode="developer",
        implementation_root=implementation.as_posix(),
        allowed_implementation_root=allowed.as_posix(),
        planning_roots=[root.as_posix(), "/etc"],
    )

    assert build.exit_code == exits.VALIDATION_FAILURE
    assert any(
        finding["record"] == "planning-roots"
        and "exactly the authoritative repository root" in finding["message"]
        for finding in build.payload["findings"]
    )

    valid_build, path = build_test_packet(root, tmp_path)
    packet_allowed = tmp_path / "impl-1-implementation"
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    document["workspace"]["planning-roots"].append(
        {"path": "/etc", "access": "read-only"}
    )
    document["workspace"]["denied-paths"].append("/etc")
    document["authorization-hash"] = packet._authorization_hash(document)
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    preflight = packet.preflight_packet(
        root,
        packet_path=path.relative_to(root).as_posix(),
        allowed_implementation_root=packet_allowed.as_posix(),
        expected_authorization_hash=str(valid_build.payload["authorization_hash"]),
    )

    assert preflight.exit_code == exits.VALIDATION_FAILURE
    assert any(
        finding["record"] == "workspace.planning-roots"
        and "exactly the authoritative repository root" in finding["message"]
        for finding in preflight.payload["findings"]
    )


def test_cross_active_theme_story_dependency_is_eligible(tmp_path: Path):
    document = valid_backlog()
    completed = v2_archive_theme("TH4")
    completed["locked"] = False
    document["backlog"]["active-themes"].append(completed)
    story = document["backlog"]["active-themes"][0]["epics"][0]["stories"][0]
    story["depends-on"] = ["TH4.E1.US1"]
    root = write_repository(tmp_path, document)
    (root / "stories/TH4-US1.md").write_text(
        story_document("TH4.E1.US1"),
        encoding="utf-8",
    )

    result = packet.project_next(root)

    assert result.exit_code == exits.SUCCESS
    assert result.payload["projection"]["story"]["id"] == "TH3.E1.US1"


def test_archived_story_and_normalized_v1_epic_dependencies_are_eligible(
    tmp_path: Path,
):
    document = valid_backlog()
    theme = document["backlog"]["active-themes"][0]
    theme["epics"][0]["depends-on"] = ["TH2.E1"]
    theme["epics"][0]["stories"][0]["depends-on"] = ["TH2.E1.US1"]
    root = write_repository(tmp_path, document)

    result = packet.project_next(root)

    assert result.exit_code == exits.SUCCESS
    assert result.payload["projection"]["story"]["id"] == "TH3.E1.US1"


def test_acceptance_criteria_are_required_bound_and_authoritatively_compared(
    tmp_path: Path,
):
    root = write_repository(tmp_path)
    build, path = build_test_packet(root, tmp_path)
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert document["acceptance-criteria"] == [
        {"AC1": "Packet contract is enforced"}
    ]
    document["acceptance-criteria"][0]["AC1"] = "Tampered criterion"
    document["authorization-hash"] = packet._authorization_hash(document)
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    result = packet.verify_packet(
        root,
        packet_path=path.relative_to(root).as_posix(),
        allowed_implementation_root=(
            tmp_path / "impl-1-implementation"
        ).as_posix(),
        expected_authorization_hash=str(build.payload["authorization_hash"]),
    )

    assert result.exit_code == exits.VALIDATION_FAILURE
    assert any(
        finding["record"] == "acceptance-criteria"
        for finding in result.payload["findings"]
    )


@pytest.mark.parametrize(
    "story_text",
    (
        "---\nid: TH3.E1.US1\n---\n# Missing\n",
        "---\nid: TH3.E1.US1\nacceptance-criteria: []\n---\n# Empty\n",
        (
            "---\nid: TH3.E1.US1\nacceptance-criteria: [AC1]\n"
            "acceptance-criteria: [AC2]\n---\n# Duplicate\n"
        ),
    ),
)
def test_packet_build_rejects_missing_empty_or_duplicate_acceptance_criteria(
    tmp_path: Path,
    story_text: str,
):
    root = write_repository(tmp_path)
    (root / "stories/US1.md").write_text(story_text, encoding="utf-8")
    allowed = tmp_path / "implementation"
    implementation = allowed / "checkout"
    implementation.mkdir(parents=True)

    result = packet.build_packet(
        root,
        task="invalid-ac",
        story_id=None,
        mode="developer",
        implementation_root=implementation.as_posix(),
        allowed_implementation_root=allowed.as_posix(),
        planning_roots=[root.as_posix()],
    )

    assert result.exit_code == exits.VALIDATION_FAILURE
    assert "frontmatter" in result.payload["message"]


def test_verify_and_preflight_frame_disappearing_backlog_as_packet_results(
    tmp_path: Path,
):
    root = write_repository(tmp_path)
    build, _path = build_test_packet(root, tmp_path)
    (root / backlog.BACKLOG_PATH).unlink()

    results = [
        packet.verify_packet(
            root,
            packet_path=str(build.payload["packet"]),
            allowed_implementation_root=(
                tmp_path / "impl-1-implementation"
            ).as_posix(),
            expected_authorization_hash=str(build.payload["authorization_hash"]),
        ),
        packet.preflight_packet(
            root,
            packet_path=str(build.payload["packet"]),
            allowed_implementation_root=(
                tmp_path / "impl-1-implementation"
            ).as_posix(),
            expected_authorization_hash=str(build.payload["authorization_hash"]),
        ),
    ]

    for result in results:
        stdout = io.StringIO()
        stderr = io.StringIO()
        emitted = cli.emit(
            cli.CommandResult(result.exit_code, result.payload, result.diagnostics),
            stdout=stdout,
            stderr=stderr,
        )
        assert emitted == exits.VALIDATION_FAILURE
        assert len(stdout.getvalue().splitlines()) == 1
        assert json.loads(stdout.getvalue())["status"] in {
            "packet-invalid",
            "preflight-refused",
        }
        assert "Traceback" not in stderr.getvalue()


def test_project_frames_backlog_disappearance_after_validation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root = write_repository(tmp_path)
    backlog_path = root / backlog.BACKLOG_PATH
    original_hash = packet._sha256_file

    def disappear_before_hash(path: Path) -> str:
        if path == backlog_path:
            path.unlink()
        return original_hash(path)

    monkeypatch.setattr(packet, "_sha256_file", disappear_before_hash)

    result = packet.project_next(root)
    stdout = io.StringIO()
    stderr = io.StringIO()
    cli.emit(
        cli.CommandResult(result.exit_code, result.payload, result.diagnostics),
        stdout=stdout,
        stderr=stderr,
    )

    assert result.exit_code == exits.VALIDATION_FAILURE
    assert result.payload["action"] == "project"
    assert len(stdout.getvalue().splitlines()) == 1
    assert json.loads(stdout.getvalue())["status"] == "projection-refused"
    assert "Traceback" not in stderr.getvalue()


def test_projection_failure_frames_backlog_hash_enrichment_race(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    document = valid_backlog()
    document["backlog"]["active-themes"][0]["epics"][0]["stories"][0][
        "status"
    ] = "blocked"
    root = write_repository(tmp_path, document)

    def unreadable(_path: Path) -> str:
        raise PermissionError("simulated enrichment race")

    monkeypatch.setattr(packet, "_sha256_file", unreadable)

    result = packet.project_next(root)

    assert result.exit_code == exits.VALIDATION_FAILURE
    assert result.payload["status"] == "projection-refused"
    assert result.payload["backlog_sha256"] is None
    assert "simulated enrichment race" in result.payload["backlog_enrichment_error"]


@pytest.mark.parametrize("action", ("verify", "preflight"))
def test_verify_and_preflight_frame_unreadable_hash_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    action: str,
):
    root = write_repository(tmp_path)
    build, _path = build_test_packet(root, tmp_path)
    original_hash = packet._sha256_file

    def unreadable(path: Path) -> str:
        if path == root / backlog.BACKLOG_PATH:
            raise PermissionError("simulated unreadable backlog")
        return original_hash(path)

    monkeypatch.setattr(packet, "_sha256_file", unreadable)
    operation = (
        packet.verify_packet if action == "verify" else packet.preflight_packet
    )

    result = operation(
        root,
        packet_path=str(build.payload["packet"]),
        allowed_implementation_root=(
            tmp_path / "impl-1-implementation"
        ).as_posix(),
        expected_authorization_hash=str(build.payload["authorization_hash"]),
    )
    stdout = io.StringIO()
    stderr = io.StringIO()
    cli.emit(
        cli.CommandResult(result.exit_code, result.payload, result.diagnostics),
        stdout=stdout,
        stderr=stderr,
    )

    assert result.exit_code == exits.VALIDATION_FAILURE
    assert len(stdout.getvalue().splitlines()) == 1
    assert json.loads(stdout.getvalue())["status"] in {
        "packet-invalid",
        "preflight-refused",
    }
    assert "Traceback" not in stderr.getvalue()


def test_packet_binds_scope_traceability_and_complete_source_manifest(
    tmp_path: Path,
):
    root = write_repository(tmp_path)
    build, path = build_test_packet(root, tmp_path)
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    source_paths = {item["path"] for item in document["sources"]}
    source_trust = {item["path"]: item["trust"] for item in document["sources"]}

    assert document["scope"] == {
        "story-id": "TH3.E1.US1",
        "story-file": "stories/US1.md",
        "maximum-stories": 1,
        "mutation": "implementation-root-only",
    }
    assert document["traceability"]["adrs"] == ["ADR-004"]
    assert {
        ".github/skills/bdd-stories/SKILL.md",
        ".github/skills/the-copilot-build-method/SKILL.md",
        ".github/skills/backlog-management/SKILL.md",
        "docs/vision_of_product/VP3/README.md",
        "docs/discovery/VP3/README.md",
        "docs/requirements/VP3/PRD.md",
        "docs/architecture/README.md",
        "docs/ADRs/ADR-004-fixture.md",
    } <= source_paths
    assert source_trust["docs/plan/backlog.yaml"] == "untrusted"
    assert all(
        trust == (
            "trusted" if path.startswith(".github/skills/") else "untrusted"
        )
        for path, trust in source_trust.items()
    )
    assert build.payload["authorization_hash"] == document["authorization-hash"]


@pytest.mark.parametrize(
    "relative",
    ("docs/plan/backlog.yaml", "docs/ADRs/ADR-004-fixture.md"),
)
def test_packet_verify_rejects_trust_elevation_for_untrusted_sources(
    tmp_path: Path,
    relative: str,
):
    root = write_repository(tmp_path)
    build, path = build_test_packet(root, tmp_path)
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    source = next(item for item in document["sources"] if item["path"] == relative)
    source["trust"] = "trusted"
    document["authorization-hash"] = packet._authorization_hash(document)
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    result = packet.verify_packet(
        root,
        packet_path=path.relative_to(root).as_posix(),
        allowed_implementation_root=(
            tmp_path / "impl-1-implementation"
        ).as_posix(),
        expected_authorization_hash=str(document["authorization-hash"]),
    )

    assert result.exit_code == exits.VALIDATION_FAILURE
    assert any(
        finding["record"] == "sources"
        for finding in result.payload["findings"]
    )


@pytest.mark.parametrize(
    "relative",
    (
        ".github/skills/bdd-stories/SKILL.md",
        "docs/ADRs/ADR-004-fixture.md",
        "docs/vision_of_product/VP3/README.md",
    ),
)
def test_packet_detects_required_skill_adr_and_planning_source_staleness(
    tmp_path: Path,
    relative: str,
):
    root = write_repository(tmp_path)
    build, path = build_test_packet(root, tmp_path)
    source = root / relative
    source.write_text(source.read_text(encoding="utf-8") + "\nchanged\n")

    result = packet.verify_packet(
        root,
        packet_path=path.relative_to(root).as_posix(),
        allowed_implementation_root=(tmp_path / "impl-1-implementation").as_posix(),
        expected_authorization_hash=str(build.payload["authorization_hash"]),
    )

    assert result.exit_code == exits.VALIDATION_FAILURE
    assert result.payload["status"] == "STALE"
    assert any(relative in finding["message"] for finding in result.payload["findings"])


@pytest.mark.parametrize("field", ("task", "trace-id", "generated-at"))
def test_recomputed_hash_tamper_fails_external_authorization_anchor(
    tmp_path: Path,
    field: str,
):
    root = write_repository(tmp_path)
    build, path = build_test_packet(root, tmp_path)
    original_hash = str(build.payload["authorization_hash"])
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    document[field] = f"forged-{field}"
    if field == "generated-at":
        document[field] = "2026-09-07T12:00:00+00:00"
    document["authorization-hash"] = packet._authorization_hash(document)
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    result = packet.verify_packet(
        root,
        packet_path=path.relative_to(root).as_posix(),
        allowed_implementation_root=(tmp_path / "impl-1-implementation").as_posix(),
        expected_authorization_hash=original_hash,
    )

    assert result.exit_code == exits.VALIDATION_FAILURE
    assert any(
        "caller-provided anchor" in finding["message"]
        for finding in result.payload["findings"]
    )


def test_build_rejects_noncanonical_output_and_frames_hash_race(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root = write_repository(tmp_path)
    allowed = tmp_path / "implementation"
    implementation = allowed / "checkout"
    implementation.mkdir(parents=True)
    arguments = {
        "task": "impl-1",
        "story_id": None,
        "mode": "developer",
        "implementation_root": implementation.as_posix(),
        "allowed_implementation_root": allowed.as_posix(),
        "planning_roots": [root.as_posix()],
    }
    wrong = packet.build_packet(
        root,
        **arguments,
        output="docs/plan/runtime/packets/TH3.E1.US1/wrong.yaml",
    )
    assert wrong.exit_code == exits.VALIDATION_FAILURE

    def raced(_path: Path) -> str:
        raise FileNotFoundError("simulated build hash race")

    monkeypatch.setattr(packet, "_sha256_file", raced)
    result = packet.build_packet(root, **arguments)
    stdout = io.StringIO()
    cli.emit(
        cli.CommandResult(result.exit_code, result.payload, result.diagnostics),
        stdout=stdout,
        stderr=io.StringIO(),
    )
    assert result.exit_code == exits.VALIDATION_FAILURE
    assert len(stdout.getvalue().splitlines()) == 1
    assert "simulated build hash race" in result.payload["message"]


@pytest.mark.parametrize("action", ("verify", "preflight"))
def test_packet_validation_rejects_noncanonical_packet_location(
    tmp_path: Path,
    action: str,
):
    root = write_repository(tmp_path)
    build, path = build_test_packet(root, tmp_path)
    moved = root / "docs/plan/runtime/packets/TH3.E1.US1/copied.yaml"
    shutil.copyfile(path, moved)
    operation = (
        packet.verify_packet if action == "verify" else packet.preflight_packet
    )

    result = operation(
        root,
        packet_path=moved.relative_to(root).as_posix(),
        allowed_implementation_root=(tmp_path / "impl-1-implementation").as_posix(),
        expected_authorization_hash=str(build.payload["authorization_hash"]),
    )

    assert result.exit_code == exits.VALIDATION_FAILURE
    assert any(
        finding["record"] == "path" for finding in result.payload["findings"]
    )


def transition_fixture_backlog(
    root: Path,
    story_status: str,
    *,
    parent_status: str = "in-progress",
    completion_evidence: bool = True,
) -> None:
    path = root / backlog.BACKLOG_PATH
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    state = document["backlog"]
    state["revision"] += 1
    state["last-updated"] = (
        f"2026-09-07T12:{state['revision']:02d}:00+00:00"
    )
    theme = state["active-themes"][0]
    theme["status"] = parent_status
    theme["epics"][0]["status"] = parent_status
    story = theme["epics"][0]["stories"][0]
    story["status"] = story_status
    if story_status == "done" and completion_evidence:
        story["evidence"]["verification"].extend(
            ["lint passed", "integration passed"]
        )
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")


def reconcile_test_packet(
    root: Path,
    tmp_path: Path,
    build: packet.PacketResult,
) -> packet.PacketResult:
    return packet.reconcile_packet(
        root,
        packet_path=str(build.payload["packet"]),
        allowed_implementation_root=(
            tmp_path / "impl-1-implementation"
        ).as_posix(),
        expected_authorization_hash=str(build.payload["authorization_hash"]),
    )


def update_story_revision(root: Path, mutate) -> None:
    path = root / backlog.BACKLOG_PATH
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    state = document["backlog"]
    state["revision"] += 1
    state["last-updated"] = f"2026-09-07T13:{state['revision']:02d}:00+00:00"
    theme = state["active-themes"][0]
    mutate(theme, theme["epics"][0], theme["epics"][0]["stories"][0])
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")


def test_packet_reconcile_todo_start_then_verify_and_preflight(tmp_path: Path):
    document = valid_backlog()
    theme = document["backlog"]["active-themes"][0]
    theme["status"] = "todo"
    theme["epics"][0]["status"] = "todo"
    root = write_repository(tmp_path, document)
    build, path = build_test_packet(root, tmp_path)
    old_hash = str(build.payload["authorization_hash"])
    old_packet = yaml.safe_load(path.read_text(encoding="utf-8"))

    transition_fixture_backlog(root, "in-progress")
    unreconciled = packet.verify_packet(
        root,
        packet_path=str(build.payload["packet"]),
        allowed_implementation_root=(
            tmp_path / "impl-1-implementation"
        ).as_posix(),
        expected_authorization_hash=old_hash,
    )
    reconciled = reconcile_test_packet(root, tmp_path, build)

    assert unreconciled.exit_code == exits.VALIDATION_FAILURE
    assert unreconciled.payload["status"] == "STALE"
    assert reconciled.exit_code == exits.SUCCESS
    new_hash = str(reconciled.payload["authorization_hash"])
    assert new_hash != old_hash
    rewritten = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert rewritten["story"]["status"] == "in-progress"
    assert rewritten["theme"]["status"] == "in-progress"
    assert rewritten["epic"]["status"] == "in-progress"
    assert rewritten["backlog"]["revision"] == 8
    assert rewritten["sources"] != old_packet["sources"]
    assert rewritten["composite-hash"] != old_packet["composite-hash"]
    assert rewritten["reconciliations"] == [
        {
            "from-revision": 7,
            "to-revision": 8,
            "from-backlog-sha256": old_packet["backlog"]["sha256"],
            "to-backlog-sha256": rewritten["backlog"]["sha256"],
            "from-status": {
                "theme": "todo",
                "epic": "todo",
                "story": "todo",
            },
            "to-status": {
                "theme": "in-progress",
                "epic": "in-progress",
                "story": "in-progress",
            },
            "timestamp": rewritten["reconciliations"][0]["timestamp"],
            "reason": "status-transition",
        }
    ]
    for operation in (packet.verify_packet, packet.preflight_packet):
        result = operation(
            root,
            packet_path=str(build.payload["packet"]),
            allowed_implementation_root=(
                tmp_path / "impl-1-implementation"
            ).as_posix(),
            expected_authorization_hash=new_hash,
        )
        assert result.exit_code == exits.SUCCESS
        assert result.payload["findings"] == []


def test_packet_reconciles_evidence_before_review_then_parent_completion(
    tmp_path: Path,
):
    document = valid_backlog()
    evidence = document["backlog"]["active-themes"][0]["epics"][0]["stories"][0][
        "evidence"
    ]
    evidence["verification"] = []
    evidence["review"] = []
    evidence["gitflow"] = []
    root = write_repository(tmp_path, document)
    current, path = build_test_packet(root, tmp_path)

    transition_fixture_backlog(root, "in-progress")
    current = reconcile_test_packet(root, tmp_path, current)

    update_story_revision(
        root,
        lambda _theme, _epic, story: story["evidence"]["verification"].extend(
            ["UNIT: PASSED", "lint passed", "integration: passed"]
        ),
    )
    current = reconcile_test_packet(root, tmp_path, current)
    assert current.exit_code == exits.SUCCESS
    assert current.payload["reconciliation"]["reason"] == "evidence-update"
    before_review = packet.verify_packet(
        root,
        packet_path=str(current.payload["packet"]),
        allowed_implementation_root=(
            tmp_path / "impl-1-implementation"
        ).as_posix(),
        expected_authorization_hash=str(current.payload["authorization_hash"]),
    )
    assert before_review.exit_code == exits.SUCCESS

    def append_approval(_theme, _epic, story):
        story["evidence"]["review"].extend(
            ["security review complete", "APPROVED"]
        )
        story["evidence"]["gitflow"].append(
            "not-applicable: fixture has no delivery remote"
        )

    update_story_revision(root, append_approval)
    current = reconcile_test_packet(root, tmp_path, current)
    assert current.exit_code == exits.SUCCESS
    assert current.payload["reconciliation"]["reason"] == "evidence-update"

    update_story_revision(
        root,
        lambda _theme, _epic, story: story.update({"status": "done"}),
    )
    current = reconcile_test_packet(root, tmp_path, current)
    assert current.exit_code == exits.SUCCESS
    assert current.payload["reconciliation"]["reason"] == "status-transition"

    update_story_revision(
        root,
        lambda _theme, epic, _story: epic.update({"status": "done"}),
    )
    current = reconcile_test_packet(root, tmp_path, current)
    assert current.exit_code == exits.SUCCESS
    assert current.payload["reconciliation"]["reason"] == "parent-completion"

    update_story_revision(
        root,
        lambda theme, _epic, _story: theme.update({"status": "done"}),
    )
    current = reconcile_test_packet(root, tmp_path, current)
    assert current.exit_code == exits.SUCCESS
    assert current.payload["reconciliation"]["reason"] == "parent-completion"
    reasons = [
        item["reason"]
        for item in yaml.safe_load(path.read_text(encoding="utf-8"))[
            "reconciliations"
        ]
    ]
    assert reasons == [
        "status-transition",
        "evidence-update",
        "evidence-update",
        "status-transition",
        "parent-completion",
        "parent-completion",
    ]


def test_packet_reconcile_rejects_noop_newer_revision(tmp_path: Path):
    root = write_repository(tmp_path)
    current, _path = build_test_packet(root, tmp_path)
    transition_fixture_backlog(root, "in-progress")
    current = reconcile_test_packet(root, tmp_path, current)
    update_story_revision(root, lambda _theme, _epic, _story: None)

    result = reconcile_test_packet(root, tmp_path, current)

    assert result.exit_code == exits.VALIDATION_FAILURE
    assert any(
        finding["record"] == "reconciliation"
        and "no authorized lifecycle change" in finding["message"]
        for finding in result.payload["findings"]
    )


def test_packet_reconcile_supports_block_resume_and_completion(tmp_path: Path):
    root = write_repository(tmp_path)
    current, path = build_test_packet(root, tmp_path)
    hashes = [str(current.payload["authorization_hash"])]

    for story_status in (
        "in-progress",
        "blocked",
        "in-progress",
        "done",
    ):
        transition_fixture_backlog(
            root,
            story_status,
            parent_status="in-progress",
        )
        current = reconcile_test_packet(root, tmp_path, current)
        assert current.exit_code == exits.SUCCESS
        hashes.append(str(current.payload["authorization_hash"]))

    for mutate in (
        lambda _theme, epic, _story: epic.update({"status": "done"}),
        lambda theme, _epic, _story: theme.update({"status": "done"}),
    ):
        update_story_revision(root, mutate)
        current = reconcile_test_packet(root, tmp_path, current)
        assert current.exit_code == exits.SUCCESS
        hashes.append(str(current.payload["authorization_hash"]))

    assert len(set(hashes)) == len(hashes)
    rewritten = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert rewritten["story"]["status"] == "done"
    assert rewritten["evidence-snapshot"]["verification"] == ["unit passed"]
    assert rewritten["evidence-current"]["verification"] == [
        "unit passed",
        "lint passed",
        "integration passed",
    ]
    assert len(rewritten["reconciliations"]) == 6
    verified = packet.verify_packet(
        root,
        packet_path=str(current.payload["packet"]),
        allowed_implementation_root=(
            tmp_path / "impl-1-implementation"
        ).as_posix(),
        expected_authorization_hash=hashes[-1],
    )
    assert verified.exit_code == exits.SUCCESS


def test_packet_reconcile_blocks_done_without_complete_evidence(tmp_path: Path):
    document = valid_backlog()
    evidence = document["backlog"]["active-themes"][0]["epics"][0]["stories"][0][
        "evidence"
    ]
    evidence["verification"] = []
    evidence["review"] = []
    evidence["gitflow"] = []
    root = write_repository(tmp_path, document)
    build, path = build_test_packet(root, tmp_path)

    transition_fixture_backlog(
        root,
        "done",
        parent_status="done",
        completion_evidence=False,
    )
    result = reconcile_test_packet(root, tmp_path, build)

    assert result.exit_code == exits.VALIDATION_FAILURE
    records = {finding["record"] for finding in result.payload["findings"]}
    assert {
        "evidence.verification",
        "evidence.review",
        "evidence.gitflow",
    } <= records
    assert yaml.safe_load(path.read_text(encoding="utf-8"))["story"]["status"] == "todo"


def reconcile_completion_evidence(
    tmp_path: Path,
    *,
    verification: list[str],
    review: list[str],
    gitflow: list[str],
    waived_check: str | None = None,
) -> packet.PacketResult:
    document = valid_backlog()
    story = document["backlog"]["active-themes"][0]["epics"][0]["stories"][0]
    story["evidence"]["verification"] = []
    story["evidence"]["review"] = []
    story["evidence"]["gitflow"] = []
    if waived_check is not None:
        story["verification"]["waivers"].append(
            {
                "check": waived_check,
                "authority": "architect",
                "reviewer": "reviewer",
                "rationale": "Governed fixture waiver",
                "record": "TH3.E1.US1",
            }
        )
    root = write_repository(tmp_path, document)
    current, _path = build_test_packet(root, tmp_path)
    transition_fixture_backlog(root, "in-progress")
    current = reconcile_test_packet(root, tmp_path, current)

    def complete(_theme, _epic, current_story):
        current_story["status"] = "done"
        current_story["evidence"]["verification"] = verification
        current_story["evidence"]["review"] = review
        current_story["evidence"]["gitflow"] = gitflow

    update_story_revision(root, complete)
    return reconcile_test_packet(root, tmp_path, current)


@pytest.mark.parametrize(
    "gitflow",
    (
        ["committed"],
        ["MERGED"],
        ["squash-merged"],
        ["not-applicable: fixture has no delivery remote"],
    ),
)
def test_completion_accepts_closed_positive_success_evidence(
    tmp_path: Path,
    gitflow: list[str],
):
    result = reconcile_completion_evidence(
        tmp_path,
        verification=["UNIT: PASSED", "lint passed", "Integration: passed"],
        review=["bounded security review detail", "APPROVED"],
        gitflow=gitflow,
    )

    assert result.exit_code == exits.SUCCESS


@pytest.mark.parametrize(
    "entry",
    (
        "unit failed",
        "unit failure",
        "unit error",
        "unit skipped",
        "unit not passed",
        "unit tests passed",
        "unit:passed",
        "unit  passed",
    ),
)
def test_completion_rejects_failure_shaped_or_noncanonical_verification(
    tmp_path: Path,
    entry: str,
):
    result = reconcile_completion_evidence(
        tmp_path,
        verification=[entry, "lint passed", "integration passed"],
        review=["approved"],
        gitflow=["merged"],
    )

    assert result.exit_code == exits.VALIDATION_FAILURE
    assert any(
        finding["record"] == "evidence.verification"
        for finding in result.payload["findings"]
    )


def test_completion_accepts_failure_evidence_only_with_governed_check_waiver(
    tmp_path: Path,
):
    result = reconcile_completion_evidence(
        tmp_path,
        verification=["unit failed", "lint passed", "integration passed"],
        review=["approved"],
        gitflow=["merged"],
        waived_check="unit",
    )

    assert result.exit_code == exits.SUCCESS


@pytest.mark.parametrize("entry", ("APPROVE", "approved"))
def test_completion_accepts_canonical_and_legacy_review_approval(
    tmp_path: Path,
    entry: str,
):
    result = reconcile_completion_evidence(
        tmp_path,
        verification=["unit passed", "lint passed", "integration passed"],
        review=[entry],
        gitflow=["merged"],
    )

    assert result.exit_code == exits.SUCCESS


@pytest.mark.parametrize(
    "entry",
    (
        "REQUEST_CHANGES",
        "rejected",
        "review failed",
        "conditionally approved",
        "approved: not approved",
        "approved: bounded detail",
    ),
)
def test_completion_rejects_nonapproval_review_results(
    tmp_path: Path,
    entry: str,
):
    result = reconcile_completion_evidence(
        tmp_path,
        verification=["unit passed", "lint passed", "integration passed"],
        review=[entry],
        gitflow=["merged"],
    )

    assert result.exit_code == exits.VALIDATION_FAILURE
    assert any(
        finding["record"] == "evidence.review"
        for finding in result.payload["findings"]
    )


@pytest.mark.parametrize(
    "entry",
    (
        "not applicable",
        "not-applicable",
        "n/a",
        "CI failed",
        "not merged",
        "merge succeeded",
        "squash merge: succeeded",
        "committed successfully",
    ),
)
def test_completion_rejects_bare_not_applicable_or_failed_gitflow(
    tmp_path: Path,
    entry: str,
):
    result = reconcile_completion_evidence(
        tmp_path,
        verification=["unit passed", "lint passed", "integration passed"],
        review=["approved"],
        gitflow=[entry],
    )

    assert result.exit_code == exits.VALIDATION_FAILURE
    assert any(
        finding["record"] == "evidence.gitflow"
        for finding in result.payload["findings"]
    )


def test_packet_reconcile_rejects_evidence_removal_or_replacement(tmp_path: Path):
    root = write_repository(tmp_path)
    build, path = build_test_packet(root, tmp_path)
    backlog_path = root / backlog.BACKLOG_PATH
    document = yaml.safe_load(backlog_path.read_text(encoding="utf-8"))
    state = document["backlog"]
    state["revision"] += 1
    theme = state["active-themes"][0]
    theme["status"] = "in-progress"
    theme["epics"][0]["status"] = "in-progress"
    story = theme["epics"][0]["stories"][0]
    story["status"] = "in-progress"
    story["evidence"]["review"] = ["replacement approval"]
    backlog_path.write_text(
        yaml.safe_dump(document, sort_keys=False),
        encoding="utf-8",
    )

    result = reconcile_test_packet(root, tmp_path, build)

    assert result.exit_code == exits.VALIDATION_FAILURE
    assert any(
        finding["record"] == "evidence.review"
        and "removal, replacement, or reordering" in finding["message"]
        for finding in result.payload["findings"]
    )
    assert yaml.safe_load(path.read_text(encoding="utf-8"))["story"]["status"] == "todo"


@pytest.mark.parametrize("completed_parents", (("epic",), ("epic", "theme")))
def test_packet_reconcile_rejects_story_and_parent_completion_in_one_revision(
    tmp_path: Path,
    completed_parents: tuple[str, ...],
):
    root = write_repository(tmp_path)
    current, _path = build_test_packet(root, tmp_path)
    transition_fixture_backlog(root, "in-progress")
    current = reconcile_test_packet(root, tmp_path, current)

    def combine_completion(theme, epic, story):
        story["status"] = "done"
        story["evidence"]["verification"].extend(
            ["lint passed", "integration passed"]
        )
        if "epic" in completed_parents:
            epic["status"] = "done"
        if "theme" in completed_parents:
            theme["status"] = "done"

    update_story_revision(root, combine_completion)
    result = reconcile_test_packet(root, tmp_path, current)

    assert result.exit_code == exits.VALIDATION_FAILURE
    assert any(
        finding["record"] == "status-transition.completion"
        and "story and parent completion" in finding["message"]
        for finding in result.payload["findings"]
    )


def test_packet_reconcile_rejects_combined_epic_and_theme_completion(
    tmp_path: Path,
):
    root = write_repository(tmp_path)
    current, _path = build_test_packet(root, tmp_path)
    transition_fixture_backlog(root, "in-progress")
    current = reconcile_test_packet(root, tmp_path, current)
    update_story_revision(
        root,
        lambda _theme, _epic, story: (
            story.update({"status": "done"}),
            story["evidence"]["verification"].extend(
                ["lint passed", "integration passed"]
            ),
        ),
    )
    current = reconcile_test_packet(root, tmp_path, current)
    assert current.exit_code == exits.SUCCESS

    update_story_revision(
        root,
        lambda theme, epic, _story: (
            epic.update({"status": "done"}),
            theme.update({"status": "done"}),
        ),
    )
    result = reconcile_test_packet(root, tmp_path, current)

    assert result.exit_code == exits.VALIDATION_FAILURE
    assert any(
        finding["record"] == "status-transition.completion"
        and "epic and theme completion require distinct" in finding["message"]
        for finding in result.payload["findings"]
    )


def test_packet_reconcile_rejects_epic_done_with_unfinished_sibling_story(
    tmp_path: Path,
):
    document = valid_backlog()
    epic = document["backlog"]["active-themes"][0]["epics"][0]
    sibling = copy.deepcopy(epic["stories"][0])
    sibling.update(
        {
            "id": "TH3.E1.US2",
            "title": "Unfinished sibling",
            "status": "todo",
            "file": "stories/US2.md",
        }
    )
    epic["stories"].append(sibling)
    root = write_repository(tmp_path, document)
    (root / "stories/US2.md").write_text(
        story_document("TH3.E1.US2"),
        encoding="utf-8",
    )
    build, _path = build_test_packet(root, tmp_path)

    transition_fixture_backlog(root, "done", parent_status="done")
    result = reconcile_test_packet(root, tmp_path, build)

    assert result.exit_code == exits.VALIDATION_FAILURE
    assert any(
        finding["record"] == "definition-of-done.epic"
        and finding["details"]["unfinished"] == ["TH3.E1.US2"]
        for finding in result.payload["findings"]
    )


def test_packet_reconcile_rejects_theme_done_with_unfinished_sibling_epic(
    tmp_path: Path,
):
    document = valid_backlog()
    theme = document["backlog"]["active-themes"][0]
    sibling_epic = copy.deepcopy(theme["epics"][0])
    sibling_epic.update({"id": "TH3.E2", "name": "Unfinished epic"})
    sibling_story = sibling_epic["stories"][0]
    sibling_story.update(
        {
            "id": "TH3.E2.US1",
            "title": "Completed sibling story",
            "status": "done",
            "file": "stories/E2-US1.md",
        }
    )
    theme["epics"].append(sibling_epic)
    root = write_repository(tmp_path, document)
    (root / "stories/E2-US1.md").write_text(
        story_document("TH3.E2.US1"),
        encoding="utf-8",
    )
    build, _path = build_test_packet(root, tmp_path)

    transition_fixture_backlog(root, "done", parent_status="done")
    result = reconcile_test_packet(root, tmp_path, build)

    assert result.exit_code == exits.VALIDATION_FAILURE
    assert any(
        finding["record"] == "definition-of-done.theme"
        and finding["details"]["unfinished"] == ["TH3.E2"]
        for finding in result.payload["findings"]
    )


@pytest.mark.parametrize("mutation", ("invalid-transition", "immutable-title"))
def test_packet_reconcile_rejects_invalid_transition_or_immutable_change(
    tmp_path: Path,
    mutation: str,
):
    root = write_repository(tmp_path)
    build, path = build_test_packet(root, tmp_path)
    transition_fixture_backlog(
        root,
        "done" if mutation == "invalid-transition" else "in-progress",
        parent_status=(
            "done" if mutation == "invalid-transition" else "in-progress"
        ),
    )
    if mutation == "immutable-title":
        backlog_path = root / backlog.BACKLOG_PATH
        document = yaml.safe_load(backlog_path.read_text(encoding="utf-8"))
        document["backlog"]["active-themes"][0]["epics"][0]["stories"][0][
            "title"
        ] = "Changed after dispatch"
        backlog_path.write_text(
            yaml.safe_dump(document, sort_keys=False),
            encoding="utf-8",
        )

    result = reconcile_test_packet(root, tmp_path, build)

    assert result.exit_code == exits.VALIDATION_FAILURE
    assert result.payload["status"] == "reconciliation-refused"
    assert any(
        finding["record"]
        == ("status-transition.story" if mutation == "invalid-transition" else "story")
        for finding in result.payload["findings"]
    )
    assert yaml.safe_load(path.read_text(encoding="utf-8"))["story"]["status"] == "todo"


@pytest.mark.parametrize(
    ("replacement", "message"),
    (
        (
            "  invariants: [INV-001]\n",
            "",
        ),
        (
            "  vision: [VO-001]\n",
            "  vision: [PR-001]\n",
        ),
        (
            '  - AC1: "Packet contract is enforced"\n',
            '  - AC-1: "Malformed key"\n',
        ),
        (
            '  - AC1: "Packet contract is enforced"\n',
            '  - AC1: ""\n',
        ),
    ),
)
def test_packet_build_rejects_malformed_traceability_or_acceptance_criteria(
    tmp_path: Path,
    replacement: str,
    message: str,
):
    root = write_repository(tmp_path)
    source = story_document().replace(replacement, message)
    (root / "stories/US1.md").write_text(source, encoding="utf-8")
    allowed = tmp_path / "malformed-implementation"
    implementation = allowed / "checkout"
    implementation.mkdir(parents=True)

    result = packet.build_packet(
        root,
        task="malformed-authority",
        story_id=None,
        mode="developer",
        implementation_root=implementation.as_posix(),
        allowed_implementation_root=allowed.as_posix(),
        planning_roots=[root.as_posix()],
    )

    assert result.exit_code == exits.VALIDATION_FAILURE
    assert result.payload["status"] == "packet-refused"
    assert (
        "traceability" in result.payload["message"]
        or "acceptance criteria" in result.payload["message"]
    )


@pytest.mark.parametrize(
    ("mutation", "expected"),
    (
        (
            lambda text: text.replace(
                "type: standard\n",
                "type: standard\npriority: urgent\n",
            ),
            "priority must be high, medium, or low",
        ),
        (
            lambda text: text.replace(
                "type: standard\n",
                "type: standard\nsize: XXL\n",
            ),
            "size must be S, M, or L",
        ),
        (
            lambda text: text.replace(
                "type: standard\n",
                "type: standard\nunexpected: value\n",
            ),
            "unknown=['unexpected']",
        ),
        (
            lambda text: text.replace(
                'title: "Schema story"',
                'title: "Different title"',
            ),
            "title does not match",
        ),
        (
            lambda text: text.replace(
                "type: standard\n",
                "type: standard\npriority: low\n",
            ),
            "priority does not match",
        ),
        (
            lambda text: text.replace(
                "depends-on: []",
                "depends-on: [TH3.E1.US2]",
            ),
            "depends-on does not exactly match",
        ),
        (
            lambda text: text.replace(
                "agents: [developer]",
                "agents: [developer, developer]",
            ),
            "unique agents",
        ),
        (
            lambda text: text.replace(
                "skills: [the-copilot-build-method]",
                "skills: []",
            ),
            "unique skills",
        ),
    ),
)
def test_packet_build_rejects_strict_bdd_frontmatter_contract(
    tmp_path: Path,
    mutation,
    expected: str,
):
    root = write_repository(tmp_path)
    (root / "stories/US1.md").write_text(
        mutation(story_document()),
        encoding="utf-8",
    )
    allowed = tmp_path / "strict-frontmatter-implementation"
    implementation = allowed / "checkout"
    implementation.mkdir(parents=True)

    result = packet.build_packet(
        root,
        task="strict-frontmatter",
        story_id=None,
        mode="developer",
        implementation_root=implementation.as_posix(),
        allowed_implementation_root=allowed.as_posix(),
        planning_roots=[root.as_posix()],
    )

    assert result.exit_code == exits.VALIDATION_FAILURE
    assert expected in result.payload["message"]


def test_packet_build_accepts_optional_frontmatter_matching_backlog(tmp_path: Path):
    root = write_repository(tmp_path)
    (root / "stories/US1.md").write_text(
        story_document(priority="high", size="M"),
        encoding="utf-8",
    )
    allowed = tmp_path / "matching-frontmatter-implementation"
    implementation = allowed / "checkout"
    implementation.mkdir(parents=True)

    result = packet.build_packet(
        root,
        task="matching-frontmatter",
        story_id=None,
        mode="developer",
        implementation_root=implementation.as_posix(),
        allowed_implementation_root=allowed.as_posix(),
        planning_roots=[root.as_posix()],
    )

    assert result.exit_code == exits.SUCCESS


def test_packet_build_accepts_trivial_story_with_empty_exact_traceability(
    tmp_path: Path,
):
    root = write_repository(tmp_path)
    source = story_document(story_type="trivial")
    for populated in (
        "[VO-001]",
        "[PR-001]",
        "[ADR-004]",
        "[INV-001]",
    ):
        source = source.replace(populated, "[]")
    (root / "stories/US1.md").write_text(source, encoding="utf-8")
    allowed = tmp_path / "trivial-implementation"
    implementation = allowed / "checkout"
    implementation.mkdir(parents=True)

    result = packet.build_packet(
        root,
        task="trivial-authority",
        story_id=None,
        mode="developer",
        implementation_root=implementation.as_posix(),
        allowed_implementation_root=allowed.as_posix(),
        planning_roots=[root.as_posix()],
    )

    assert result.exit_code == exits.SUCCESS


def test_reconciliation_record_is_authorization_bound_and_schema_validated(
    tmp_path: Path,
):
    root = write_repository(tmp_path)
    build, path = build_test_packet(root, tmp_path)
    transition_fixture_backlog(root, "in-progress")
    reconciled = reconcile_test_packet(root, tmp_path, build)
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    document["reconciliations"][0]["reason"] = "manual"
    document["authorization-hash"] = packet._authorization_hash(document)
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    result = packet.verify_packet(
        root,
        packet_path=str(build.payload["packet"]),
        allowed_implementation_root=(
            tmp_path / "impl-1-implementation"
        ).as_posix(),
        expected_authorization_hash=str(reconciled.payload["authorization_hash"]),
    )

    assert result.exit_code == exits.VALIDATION_FAILURE
    records = {finding["record"] for finding in result.payload["findings"]}
    assert "authorization-hash" in records
    assert "reconciliations[0].reason" in records


@pytest.mark.parametrize(
    ("native_yaml", "type_name"),
    (
        ("yaml-native: 2026-09-07\n", "date"),
        ("yaml-native: !!set\n  ? forbidden\n", "set"),
    ),
)
@pytest.mark.parametrize("action", ("verify", "preflight", "reconcile"))
def test_packet_cli_rejects_yaml_native_values_as_one_json_result(
    tmp_path: Path,
    native_yaml: str,
    type_name: str,
    action: str,
):
    root = write_repository(tmp_path)
    build, path = build_test_packet(root, tmp_path)
    path.write_text(
        path.read_text(encoding="utf-8") + native_yaml,
        encoding="utf-8",
    )
    shutil.copytree(ROOT / "methodlib", root / "methodlib")
    (root / "bin").mkdir()
    shutil.copy2(ROOT / "bin/method", root / "bin/method")

    completed = subprocess.run(
        [
            str(root / "bin/method"),
            "packet",
            action,
            "--packet",
            str(build.payload["packet"]),
            "--allowed-implementation-root",
            (tmp_path / "impl-1-implementation").as_posix(),
            "--expected-authorization-hash",
            str(build.payload["authorization_hash"]),
        ],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert completed.returncode == exits.VALIDATION_FAILURE
    assert len(completed.stdout.splitlines()) == 1
    payload = json.loads(completed.stdout)
    assert payload["status"] in {
        "packet-invalid",
        "preflight-refused",
        "reconciliation-refused",
    }
    assert payload["findings"] == []
    assert type_name in payload["message"]
    assert "Traceback" not in completed.stderr


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
