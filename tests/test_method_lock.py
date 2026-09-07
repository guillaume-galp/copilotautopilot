import io
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Sequence

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from methodlib import cli, exits, gates, lock  # noqa: E402


REV1 = "1" * 40
REV2 = "2" * 40
REV3 = "3" * 40


class SnapshotReader:
    """In-memory immutable baseline used by isolated repository fixtures."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.entries: list[lock.BaselineEntry] = []
        for path in sorted(root.rglob("*")):
            if path.is_symlink():
                mode = "120000"
                content = os.fsencode(os.readlink(path))
            elif path.is_file():
                mode = "100755" if path.stat().st_mode & 0o111 else "100644"
                content = path.read_bytes()
            else:
                continue
            self.entries.append(
                lock.BaselineEntry(
                    path=path.relative_to(root).as_posix(),
                    mode=mode,
                    content=content,
                )
            )
        self.committed_entries = list(self.entries)

    def read(
        self, revision: str, paths: Sequence[str]
    ) -> tuple[lock.BaselineEntry, ...]:
        if revision not in {REV1, REV2, REV3}:
            raise lock.BaselineError("unknown fixture revision")
        return tuple(
            entry
            for entry in self.entries
            if any(
                entry.path == scope or entry.path.startswith(scope + "/")
                for scope in paths
            )
        )

    def read_committed(
        self, paths: Sequence[str], since_revision: str
    ) -> tuple[str, tuple[lock.BaselineEntry, ...]]:
        return REV3, tuple(
            entry
            for entry in self.committed_entries
            if any(
                entry.path == scope or entry.path.startswith(scope + "/")
                for scope in paths
            )
        )

    def capture_committed(self) -> None:
        snapshot = SnapshotReader(self.root)
        self.committed_entries = snapshot.entries


def write(path: Path, content: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")


def replacement_adr(
    replacement_id: str = "ADR-009",
    *,
    status: str = "Accepted",
    replaces: str = "ADR-001",
    context: str = "The earlier decision needs a canonical replacement.",
) -> str:
    return (
        f"# {replacement_id}: Replacement\n\n"
        f"## Status\n\n{status}\n\n"
        "## Replacement\n\n"
        "| Field | Value |\n"
        "|---|---|\n"
        f"| Replaces | {replaces} |\n\n"
        f"## Context\n\n{context}\n\n"
        "## Decision\n\nUse the replacement decision.\n\n"
        "## Consequences\n\nThe prior decision remains historical.\n\n"
        "## Alternatives Considered\n\nRetain the prior decision.\n"
    )


def valid_dr() -> str:
    values = {
        "Schema version": "1",
        "Classification": "decision",
        "Reason": "A shared constraint changed.",
        "Requestor": "Product owner",
        "Affected records": "DEC-001",
        "Downstream impact set": "PR-001, TH3.E1.US1",
        "Invalidated gates": "requirements",
        "Actor": "Human: product owner",
        "Timestamp": "2026-09-06T20:00:00+01:00",
        "Scope": "VP3 DR-001",
        "Verdict": "Accepted",
        "Rationale": "The revision is required.",
        "Source revision": f"git:{REV3}",
        "Provenance": "Human decision on 2026-09-06.",
        "Confidence / limitations": "High confidence.",
        "Owner": "Product owner",
        "Disposition": "accepted",
    }
    rows = "\n".join(f"| {field} | {values[field]} |" for field in lock.DR_FIELDS)
    return f"# DR-001: Shared update\n\n| Field | Value |\n|---|---|\n{rows}\n"


def approved_prd() -> str:
    text = """# VP3 Product Requirements Document

| Field | Value |
|---|---|
| Schema version | 1 |
| Product | Fixture |
| Vision | VP3: Fixture; docs/vision_of_product/VP3-method/VP3.md |
| Status | Approved |
| Version | 1.0 |
| Date | 2026-09-06 |
| Discovery verdict | READY |
| Discovery source revision | sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa |
| Delivery mapping | TH3, TH4, TH5 |

## Approval

| Field | Value |
|---|---|
| Actor | Human: product owner |
| Timestamp | 2026-09-06T20:00:00+01:00 |
| Scope | VP3 PRD version 1.0 |
| Verdict | Approved |
| Rationale | Approve the fixture baseline. |
| Source revision | SOURCE |

## Functional requirements

| ID | Schema version | Requirement | Measure | Impact | Impact rationale | Traces |
|---|---|---|---|---|---|---|
| PR-001 | 1 | The product shall preserve accepted history. | A lock probe detects mutation. | consequential | This is observable product behavior. | DEC-001 |

## Quality requirements

| ID | Schema version | Requirement | Measure | Impact | Impact rationale | Traces |
|---|---|---|---|---|---|---|
| QR-001 | 1 | Validation remains deterministic. | Two runs return equal findings. | consequential | Determinism is observable. | DEC-001 |
"""
    return text.replace("SOURCE", gates._prd_revision(text))


def valid_pcr(
    baseline: str,
    *,
    operation: str = "non-requirement",
    affected_pr: str = "None",
    requirement_id: str | None = None,
    change: str = "Map a delivery-only clarification.",
) -> str:
    record_id = "PCR-001"
    values = {
        "Schema version": "1",
        "Requirement operation": operation,
        "Change": change,
        "Reason": "Planning needs the clarification.",
        "Requestor": "Product owner",
        "Affected PR": affected_pr,
        "Affected QR": "None",
        "Affected decisions": "None",
        "Affected assumptions": "None",
        "Affected risks": "None",
        "Affected themes": "TH4",
        "Discovery impact": "None; no discovery conclusion changes.",
        "Architecture impact": "None; no contract changes.",
        "Migration impact": "None; no existing user impact.",
        "Replanning impact": "TH4 mapping is clarified.",
        "Supersedes": "None",
        "Human actor": "Human: product owner",
        "Human timestamp": "2026-09-06T20:00:00+01:00",
        "Human scope": (
            f"VP3 {record_id} proposed content against PRD baseline {baseline}"
        ),
        "Human verdict": "Approved",
        "Human rationale": "The clarification is accepted.",
        "Baseline revision": baseline,
        "Source revision": "",
    }
    requirement_rows = []
    if requirement_id is not None:
        requirement_rows.append(
            {
                "ID": requirement_id,
                "Schema version": "1",
                "Requirement": "The product shall expose a visible status.",
                "Measure": "An acceptance check observes the status.",
                "Impact": "consequential",
                "Impact rationale": "The status changes product behavior.",
                "Traces": "DEC-001",
            }
        )
    values["Source revision"] = gates._pcr_revision(
        record_id, values, requirement_rows
    )
    rows = "\n".join(f"| {field} | {values[field]} |" for field in lock.PCR_FIELDS)
    requirement_table = ""
    if requirement_rows:
        row = requirement_rows[0]
        requirement_table = (
            "\n| "
            + " | ".join(gates.REQUIREMENT_FIELDS)
            + " |\n|"
            + "|".join("---" for _ in gates.REQUIREMENT_FIELDS)
            + "|\n| "
            + " | ".join(row[field] for field in gates.REQUIREMENT_FIELDS)
            + " |\n"
        )
    return (
        f"# {record_id}: Mapping clarification\n\n"
        f"| Field | Value |\n|---|---|\n{rows}\n{requirement_table}"
    )


def theme_snapshot(
    theme_id: str,
    *,
    vision: str,
    story_path: str,
) -> dict[str, object]:
    return {
        "theme": {
            "id": theme_id,
            "name": f"Fixture {theme_id}",
            "status": "done",
            "locked": True,
            "vision-ref": vision,
            "depends-on": [],
            "epics": [
                {
                    "id": f"{theme_id}.E1",
                    "name": "Fixture epic",
                    "status": "done",
                    "depends-on": [],
                    "stories": [
                        {
                            "id": f"{theme_id}.E1.US1",
                            "title": "Fixture story",
                            "status": "done",
                            "file": story_path,
                            "depends-on": [],
                        }
                    ],
                }
            ],
        }
    }


def create_repository(
    root: Path,
    *,
    vp3_locked: bool = False,
) -> tuple[lock.Baselines, SnapshotReader]:
    theme_paths = {
        "TH1": "docs/themes/TH1-methodology-improvements",
        "TH2": "docs/themes/TH2-gitflow-operator",
        "TH3": "docs/themes/TH3-foundation",
        "TH4": "docs/themes/TH4-delivery",
        "TH5": "docs/themes/TH5-economics",
    }
    vision_paths = {
        "TH1": "docs/vision_of_product/VP1-mvp/",
        "TH2": "docs/vision_of_product/VP2-gitflow/",
        "TH3": "docs/vision_of_product/VP3-method/",
        "TH4": "docs/vision_of_product/VP3-method/",
        "TH5": "docs/vision_of_product/VP3-method/",
    }
    archived_ids = ["TH1", "TH2"]
    active: list[dict[str, object]] = []
    if vp3_locked:
        archived_ids.extend(["TH3", "TH4", "TH5"])
    else:
        active.append(
            {
                "id": "TH3",
                "name": "Open foundation",
                "schema-version": 2,
                "status": "in-progress",
                "locked": False,
                "vision-ref": vision_paths["TH3"],
                "discovery-ref": "docs/discovery/VP3-method/",
                "requirements-ref": "docs/requirements/VP3-method/PRD.md",
                "depends-on": [],
                "epics": [
                    {
                        "id": "TH3.E1",
                        "name": "Open epic",
                        "status": "in-progress",
                        "depends-on": [],
                        "stories": [
                            {
                                "id": "TH3.E1.US1",
                                "title": "Open story",
                                "status": "todo",
                                "file": (
                                    "docs/themes/TH3-foundation/"
                                    "epics/E1/stories/US1.md"
                                ),
                                "depends-on": [],
                            }
                        ],
                    }
                ],
            }
        )

    summaries = []
    theme_baselines: dict[str, lock.ThemeBaseline] = {}
    for index, theme_id in enumerate(archived_ids, start=1):
        theme_path = theme_paths[theme_id]
        story = f"{theme_path}/epics/E1/stories/US1.md"
        archive = f"docs/plan/backlog-archive/{theme_id}.yaml"
        summaries.append(
            {
                "id": theme_id,
                "name": f"Fixture {theme_id}",
                "status": "done",
                "locked": True,
                "archive-ref": archive,
            }
        )
        write(root / archive, yaml.safe_dump(theme_snapshot(
            theme_id, vision=vision_paths[theme_id], story_path=story
        ), sort_keys=False))
        adr_ref = "ADR-001" if theme_id == "TH2" else (
            "ADR-002" if theme_id == "TH3" else ""
        )
        write(
            root / story,
            "\n".join(
                (
                    "---",
                    f"id: {theme_id}.E1.US1",
                    "traceability:",
                    f"  adrs: [{adr_ref}]" if adr_ref else "  adrs: []",
                    "---",
                    f"# {theme_id} story",
                    "",
                )
            ),
        )
        write(
            root / theme_path / "README.md",
            f"# {theme_id}\n\n| Input | Path |\n|---|---|\n"
            + (f"| ADRs | {adr_ref} |\n" if adr_ref else ""),
        )
        revision = REV1 if index == 1 else REV2
        if theme_id in {"TH3", "TH4", "TH5"}:
            revision = REV3
        theme_baselines[theme_id] = lock.ThemeBaseline(
            revision=revision,
            theme_path=theme_path,
            archive_path=archive,
        )

    backlog = {
        "backlog": {
            "schema-version": 2,
            "revision": 1,
            "project": "lock-fixture",
            "last-updated": "2026-09-06T20:00:00+01:00",
            "policy": {"model-policy": None, "budget-policy": None},
            "active-themes": active,
            "archived-themes": summaries,
        }
    }
    write(root / "docs/plan/backlog.yaml", yaml.safe_dump(backlog, sort_keys=False))

    if not vp3_locked:
        write(
            root / "docs/themes/TH3-foundation/epics/E1/stories/US1.md",
            "---\nid: TH3.E1.US1\ntraceability:\n  adrs: [ADR-002]\n---\n",
        )
        write(
            root / "docs/themes/TH3-foundation/README.md",
            "# TH3\n\n| Input | Path |\n|---|---|\n| ADRs | ADR-002 |\n",
        )

    write(root / "docs/vision_of_product/VP1-mvp/README.md", "# VP1\n")
    write(root / "docs/vision_of_product/VP2-gitflow/VP2.md", "# VP2\n")
    write(
        root / "docs/vision_of_product/VP3-method/VP3.md",
        "# VP3\n\n| Field | Value |\n|---|---|\n"
        "| Intended themes | TH3, TH4, TH5 |\n",
    )
    write(root / "docs/discovery/VP3-method/README.md", "# Discovery\n")
    write(root / "docs/requirements/VP3-method/PRD.md", approved_prd())
    write(
        root / "docs/discovery/VP3-method/decisions.md",
        "| ID | Decision |\n|---|---|\n| DEC-001 | Preserve history. |\n",
    )
    write(
        root / "docs/ADRs/README.md",
        "| ADR | Title | Status | Scope |\n"
        "|---|---|---|---|\n"
        "| ADR-001 | Legacy | Accepted | TH2 (locked) |\n"
        "| ADR-002 | Foundation | Accepted | TH3 |\n",
    )
    write(
        root / "docs/ADRs/ADR-001-legacy.md",
        "# ADR-001: Legacy\n\n## Status\n\nAccepted\n\n## Decision\n\nStable.\n",
    )
    write(
        root / "docs/ADRs/ADR-002-foundation.md",
        "# ADR-002: Foundation\n\n## Status\n\nAccepted\n\n## Decision\n\nStable.\n",
    )

    adrs = {
        "ADR-001": lock.ArtefactBaseline(REV2, "docs/ADRs/ADR-001-legacy.md")
    }
    vps = {
        "VP1": lock.VpBaseline(
            REV1, ("docs/vision_of_product/VP1-mvp",)
        ),
        "VP2": lock.VpBaseline(
            REV2, ("docs/vision_of_product/VP2-gitflow",)
        ),
    }
    if vp3_locked:
        adrs["ADR-002"] = lock.ArtefactBaseline(
            REV3, "docs/ADRs/ADR-002-foundation.md"
        )
        vps["VP3"] = lock.VpBaseline(
            REV3,
            (
                "docs/vision_of_product/VP3-method",
                "docs/discovery/VP3-method",
                "docs/requirements/VP3-method",
            ),
        )
    baselines = lock.Baselines(themes=theme_baselines, adrs=adrs, vps=vps)
    return baselines, SnapshotReader(root)


def create_partial_repository(
    root: Path,
) -> tuple[lock.Baselines, SnapshotReader]:
    baselines, _reader = create_repository(root)
    backlog_path = root / "docs/plan/backlog.yaml"
    document = yaml.safe_load(backlog_path.read_text(encoding="utf-8"))
    th3 = document["backlog"]["active-themes"].pop()
    th3["status"] = "done"
    th3["locked"] = True
    archive = "docs/plan/backlog-archive/TH3.yaml"
    th3_summary = {
        "id": "TH3",
        "name": th3["name"],
        "status": "done",
        "locked": True,
        "archive-ref": archive,
    }
    document["backlog"]["archived-themes"].append(th3_summary)
    write(
        root / archive,
        yaml.safe_dump(
            theme_snapshot(
                "TH3",
                vision="docs/vision_of_product/VP3-method/",
                story_path=(
                    "docs/themes/TH3-foundation/epics/E1/stories/US1.md"
                ),
            ),
            sort_keys=False,
        ),
    )
    backlog_path.write_text(
        yaml.safe_dump(document, sort_keys=False), encoding="utf-8"
    )
    themes = dict(baselines.themes)
    themes["TH3"] = lock.ThemeBaseline(
        REV3,
        "docs/themes/TH3-foundation",
        archive,
    )
    vps = dict(baselines.vps)
    vps["VP3"] = lock.VpBaseline(
        REV3,
        (
            "docs/vision_of_product/VP3-method",
            "docs/discovery/VP3-method",
            "docs/requirements/VP3-method",
        ),
        ("TH3", "TH4", "TH5"),
    )
    adrs = dict(baselines.adrs)
    adrs["ADR-002"] = lock.ArtefactBaseline(
        REV3, "docs/ADRs/ADR-002-foundation.md"
    )
    result = lock.Baselines(themes=themes, adrs=adrs, vps=vps)
    return result, SnapshotReader(root)


def test_th3_partial_vp_digest_pins_executable_modes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    root = tmp_path / "repository"
    shutil.copytree(
        ROOT,
        root,
        ignore=shutil.ignore_patterns(
            ".git", ".mypy_cache", ".pytest_cache", ".ruff_cache", "__pycache__", "*.pyc"
        ),
    )
    baseline = SnapshotReader(root)
    target = root / (
        "docs/vision_of_product/VP3-discovery-led-cost-aware-methodology/VP3.md"
    )
    target.chmod(target.stat().st_mode | 0o111)
    monkeypatch.setattr(lock, "GitBaselineReader", lambda _root: baseline)

    result = lock.validate_repository(root)

    assert not result.valid
    assert any(
        finding["record"] == "VP3"
        and "rewrites content preserved at partial acceptance" in str(finding["message"])
        for finding in result.findings
    )


@pytest.fixture
def repository(tmp_path: Path) -> tuple[Path, lock.Baselines, SnapshotReader]:
    baselines, reader = create_repository(tmp_path)
    return tmp_path, baselines, reader


def validate(
    fixture: tuple[Path, lock.Baselines, SnapshotReader],
) -> lock.ValidationResult:
    root, baselines, reader = fixture
    return lock.validate_repository(
        root, baselines=baselines, baseline_reader=reader
    )


def finding_files(result: lock.ValidationResult) -> list[str]:
    return [str(finding["file"]) for finding in result.findings]


def test_real_repository_legacy_locks_validate_without_migration():
    result = lock.validate_repository(ROOT)

    assert result.valid
    themes = {item["id"]: item for item in result.manifest["themes"]}
    assert set(themes) == {"TH1", "TH2", "TH3"}
    assert themes["TH1"]["archive_path"] == "docs/plan/backlog-archive/TH1.yaml"
    assert themes["TH2"]["archive_path"] == "docs/plan/backlog-archive/TH2.yaml"
    assert all(item["artefacts"] for item in themes.values())
    assert themes["TH3"]["baseline_revision"].startswith("sha256:")
    assert [item["id"] for item in result.manifest["adrs"]] == [
        f"ADR-{number:03d}" for number in range(1, 9)
    ]
    vp3 = next(item for item in result.manifest["vps"] if item["id"] == "VP3")
    assert vp3["status"] == "unlocked"
    assert vp3["accepted_themes"] == ["TH3"]
    assert vp3["reason"] == "unaccepted mapped themes: TH4, TH5"


def test_lock_recovery_rejects_mutation_then_accepts_restored_fixture(
    monkeypatch: pytest.MonkeyPatch,
    repository: tuple[Path, lock.Baselines, SnapshotReader],
):
    root, _, _ = repository
    story = (
        root
        / "docs/themes/TH2-gitflow-operator/epics/E1/stories/US1.md"
    )
    original = story.read_text(encoding="utf-8")
    story.write_text(original + "\nunauthorized mutation\n", encoding="utf-8")

    bypass_attempt = validate(repository)
    story.write_text(original, encoding="utf-8")
    restore_and_pass = validate(repository)

    monkeypatch.setattr(
        lock, "validate_repository", lambda _root: bypass_attempt
    )
    bypass_cli = cli.dispatch(
        ["validate", "lock", "--json"], probe_directory=root
    )
    monkeypatch.setattr(
        lock, "validate_repository", lambda _root: restore_and_pass
    )
    restore_cli = cli.dispatch(
        ["validate", "lock", "--json"], probe_directory=root
    )

    assert not bypass_attempt.valid
    assert bypass_cli.exit_code == exits.VALIDATION_FAILURE
    assert restore_and_pass.valid
    assert restore_cli.exit_code == exits.SUCCESS


def test_open_th3_changes_are_allowed_and_vp3_names_every_unaccepted_theme(
    repository: tuple[Path, lock.Baselines, SnapshotReader],
):
    root, _, _ = repository
    write(
        root / "docs/discovery/VP3-method/revisions/DR-001-update.md",
        "# DR-001: Update\n",
    )

    result = validate(repository)

    assert result.valid
    vp3 = next(item for item in result.manifest["vps"] if item["id"] == "VP3")
    assert vp3["status"] == "unlocked"
    assert vp3["reason"] == "unaccepted mapped themes: TH3, TH4, TH5"
    assert not any(path.startswith("docs/themes/TH3-") for path in finding_files(result))


def test_locked_story_and_archive_changes_fail_with_specific_remediation(
    repository: tuple[Path, lock.Baselines, SnapshotReader],
):
    root, _, _ = repository
    story = (
        root
        / "docs/themes/TH2-gitflow-operator/epics/E1/stories/US1.md"
    )
    story.write_text(story.read_text() + "\nchanged\n", encoding="utf-8")
    archive = root / "docs/plan/backlog-archive/TH2.yaml"
    archive.write_text(archive.read_text() + "\n# changed\n", encoding="utf-8")

    result = validate(repository)

    assert not result.valid
    by_file = {finding["file"]: finding for finding in result.findings}
    assert story.relative_to(root).as_posix() in by_file
    assert "new theme and Discovery dossier" in by_file[
        story.relative_to(root).as_posix()
    ]["remediation"]
    assert archive.relative_to(root).as_posix() in by_file
    assert "immutable locked-theme snapshot" in by_file[
        archive.relative_to(root).as_posix()
    ]["message"]


@pytest.mark.parametrize(
    "mutation",
    ("rename", "delete", "untracked", "symlink", "binary"),
)
def test_locked_tree_detects_rename_delete_untracked_symlink_and_binary(
    repository: tuple[Path, lock.Baselines, SnapshotReader],
    mutation: str,
):
    root, _, reader = repository
    story = (
        root
        / "docs/themes/TH2-gitflow-operator/epics/E1/stories/US1.md"
    )
    if mutation == "rename":
        story.rename(story.with_name("US1-renamed.md"))
    elif mutation == "delete":
        story.unlink()
    elif mutation == "untracked":
        write(story.with_name("extra.md"), "new locked content\n")
    elif mutation == "symlink":
        story.unlink()
        story.symlink_to(root / "outside.md")
    else:
        binary = story.with_name("evidence.bin")
        write(binary, b"\x00accepted\xff")
        reader.entries.append(
            lock.BaselineEntry(
                binary.relative_to(root).as_posix(),
                "100644",
                binary.read_bytes(),
            )
        )
        write(binary, b"\x00changed\xfe")

    result = validate(repository)

    assert not result.valid
    files = finding_files(result)
    if mutation == "rename":
        assert story.relative_to(root).as_posix() in files
        assert story.with_name("US1-renamed.md").relative_to(root).as_posix() in files
    elif mutation == "untracked":
        assert story.with_name("extra.md").relative_to(root).as_posix() in files
    elif mutation == "binary":
        assert story.with_name("evidence.bin").relative_to(root).as_posix() in files
    else:
        assert story.relative_to(root).as_posix() in files


def test_exact_adr_status_supersession_is_the_only_body_exception(
    repository: tuple[Path, lock.Baselines, SnapshotReader],
):
    root, _, _ = repository
    adr = root / "docs/ADRs/ADR-001-legacy.md"
    write(
        root / "docs/ADRs/ADR-009-replacement.md",
        replacement_adr(),
    )
    adr.write_text(
        adr.read_text().replace("## Status\n\nAccepted", (
            "## Status\n\nSuperseded by ADR-009"
        )),
        encoding="utf-8",
    )

    result = validate(repository)

    assert result.valid


@pytest.mark.parametrize(
    ("status", "body_suffix"),
    (
        ("Superseded by ADR-009", "\nRewritten body.\n"),
        ("superseded by ADR-009", ""),
        ("Superseded by ADR-9", ""),
        ("Draft", ""),
        ("Accepted", "\nRewritten body.\n"),
    ),
)
def test_adr_body_or_non_exact_status_change_fails(
    repository: tuple[Path, lock.Baselines, SnapshotReader],
    status: str,
    body_suffix: str,
):
    root, _, _ = repository
    adr = root / "docs/ADRs/ADR-001-legacy.md"
    write(
        root / "docs/ADRs/ADR-009-replacement.md",
        replacement_adr(),
    )
    changed = adr.read_text().replace("## Status\n\nAccepted", f"## Status\n\n{status}")
    adr.write_text(changed + body_suffix, encoding="utf-8")

    result = validate(repository)

    assert not result.valid
    finding = next(item for item in result.findings if item["record"] == "ADR-001")
    assert finding["file"] == "docs/ADRs/ADR-001-legacy.md"
    assert "Only an exact Status change" in finding["remediation"]


@pytest.mark.parametrize(
    "replacement",
    (
        replacement_adr(status="Proposed"),
        "# ADR-009: Replacement\n\n## Status\n\nAccepted\n",
        replacement_adr(
            replaces="ADR-008",
            context="This ADR does not supersede ADR-001.",
        ),
        replacement_adr(
            replaces="ADR-008",
            context="This ADR might supersede ADR-001 in a future release.",
        ),
        replacement_adr().replace(
            "# ADR-009: Replacement", "# ADR-008: Wrong identity"
        ),
    ),
)
def test_adr_supersession_rejects_stub_or_unrelated_replacement(
    repository: tuple[Path, lock.Baselines, SnapshotReader],
    replacement: str,
):
    root, _, _ = repository
    adr = root / "docs/ADRs/ADR-001-legacy.md"
    write(root / "docs/ADRs/ADR-009-replacement.md", replacement)
    adr.write_text(
        adr.read_text().replace(
            "## Status\n\nAccepted", "## Status\n\nSuperseded by ADR-009"
        ),
        encoding="utf-8",
    )

    result = validate(repository)

    assert not result.valid
    assert any(item["record"] == "ADR-001" for item in result.findings)


@pytest.mark.parametrize(
    "relative",
    (
        "docs/vision_of_product/VP3-method/VP3.md",
        "docs/discovery/VP3-method/README.md",
        "docs/requirements/VP3-method/PRD.md",
    ),
)
def test_partial_acceptance_rejects_wholesale_shared_content_rewrite(
    tmp_path: Path,
    relative: str,
):
    baselines, reader = create_partial_repository(tmp_path)
    target = tmp_path / relative
    target.write_text("# Rewritten accepted basis\n", encoding="utf-8")

    result = lock.validate_repository(
        tmp_path, baselines=baselines, baseline_reader=reader
    )

    assert not result.valid
    assert relative in finding_files(result)
    vp3 = next(item for item in result.manifest["vps"] if item["id"] == "VP3")
    assert vp3["status"] == "unlocked"
    assert vp3["accepted_themes"] == ["TH3"]
    assert vp3["baseline_revision"] == REV3
    assert vp3["reason"] == "unaccepted mapped themes: TH4, TH5"


def test_partial_acceptance_allows_complete_append_only_dr_and_pcr(
    tmp_path: Path,
):
    baselines, reader = create_partial_repository(tmp_path)
    write(
        tmp_path / "docs/discovery/VP3-method/revisions/DR-001-update.md",
        valid_dr(),
    )
    write(
        tmp_path / "docs/requirements/VP3-method/changes/PCR-001-update.md",
        valid_pcr(
            re.search(
                r"(?m)^\| Source revision \| (sha256:[0-9a-f]{64}) \|$",
                (
                    tmp_path
                    / "docs/requirements/VP3-method/PRD.md"
                ).read_text(encoding="utf-8"),
            ).group(1)
        ),
    )

    result = lock.validate_repository(
        tmp_path, baselines=baselines, baseline_reader=reader
    )

    assert result.valid
    vp3 = next(item for item in result.manifest["vps"] if item["id"] == "VP3")
    assert vp3["status"] == "unlocked"
    assert vp3["accepted_themes"] == ["TH3"]
    assert vp3["baseline_revision"] == REV3
    assert "unaccepted mapped themes: TH4, TH5" == vp3["reason"]


@pytest.mark.parametrize("kind", ("DR", "PCR"))
@pytest.mark.parametrize("mutation", ("delete", "rewrite"))
def test_committed_append_after_partial_baseline_is_immutable(
    tmp_path: Path,
    kind: str,
    mutation: str,
):
    baselines, reader = create_partial_repository(tmp_path)
    if kind == "DR":
        relative = "docs/discovery/VP3-method/revisions/DR-001-update.md"
        content = valid_dr()
    else:
        relative = "docs/requirements/VP3-method/changes/PCR-001-update.md"
        prd = (
            tmp_path / "docs/requirements/VP3-method/PRD.md"
        ).read_text(encoding="utf-8")
        baseline = re.search(
            r"(?m)^\| Source revision \| (sha256:[0-9a-f]{64}) \|$", prd
        ).group(1)
        content = valid_pcr(baseline)
    target = tmp_path / relative
    write(target, content)
    reader.capture_committed()

    if mutation == "delete":
        target.unlink()
    else:
        target.write_text(
            target.read_text(encoding="utf-8").replace(
                "The revision is required.",
                "The accepted evidence was rewritten.",
            )
            if kind == "DR"
            else target.read_text(encoding="utf-8").replace(
                "The clarification is accepted.",
                "The accepted evidence was rewritten.",
            ),
            encoding="utf-8",
        )

    result = lock.validate_repository(
        tmp_path, baselines=baselines, baseline_reader=reader
    )

    assert not result.valid
    finding = next(item for item in result.findings if item["file"] == relative)
    assert (
        "deleted or renamed" in finding["message"]
        if mutation == "delete"
        else "rewrites content preserved" in finding["message"]
    )


@pytest.mark.parametrize(
    ("kind", "verdict"),
    (("DR", "Accepted"), ("PCR", "Approved"), ("PCR", "Rejected")),
)
@pytest.mark.parametrize("mutation", ("delete", "rewrite"))
def test_git_history_allows_draft_evolution_then_locks_first_adjudication(
    tmp_path: Path,
    kind: str,
    verdict: str,
    mutation: str,
):
    root = tmp_path / "repo"
    baselines, _reader = create_partial_repository(root)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(
        [
            "git", "-C", str(root), "-c", "user.name=Test",
            "-c", "user.email=test@example.invalid", "commit", "-qm", "baseline",
        ],
        check=True,
    )
    baseline_revision = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    baselines = lock.Baselines(
        themes={
            key: replace(
                value,
                revision=baseline_revision,
                archive_revision=baseline_revision,
            )
            for key, value in baselines.themes.items()
        },
        adrs={
            key: replace(value, revision=baseline_revision)
            for key, value in baselines.adrs.items()
        },
        vps={
            key: replace(value, revision=baseline_revision)
            for key, value in baselines.vps.items()
        },
    )
    if kind == "DR":
        relative = "docs/discovery/VP3-method/revisions/DR-001-update.md"
        adjudicated = valid_dr().replace(
            f"git:{REV3}", "sha256:" + ("d" * 64)
        )
    else:
        relative = "docs/requirements/VP3-method/changes/PCR-001-update.md"
        prd = (
            root / "docs/requirements/VP3-method/PRD.md"
        ).read_text(encoding="utf-8")
        prd_baseline = re.search(
            r"(?m)^\| Source revision \| (sha256:[0-9a-f]{64}) \|$",
            prd,
        ).group(1)
        adjudicated = valid_pcr(prd_baseline)
        if verdict == "Rejected":
            adjudicated = adjudicated.replace(
                "| Human verdict | Approved |",
                "| Human verdict | Rejected |",
            )
    target = root / relative
    write(target, f"# {kind}-001: Draft\n")
    subprocess.run(["git", "-C", str(root), "add", relative], check=True)
    subprocess.run(
        [
            "git", "-C", str(root), "-c", "user.name=Test",
            "-c", "user.email=test@example.invalid", "commit", "-qm", "draft",
        ],
        check=True,
    )
    write(target, adjudicated)
    subprocess.run(["git", "-C", str(root), "add", relative], check=True)
    subprocess.run(
        [
            "git", "-C", str(root), "-c", "user.name=Test",
            "-c", "user.email=test@example.invalid", "commit", "-qm", "adjudicated",
        ],
        check=True,
    )

    adjudicated_result = lock.validate_repository(root, baselines=baselines)
    assert adjudicated_result.valid
    vp3 = next(
        item
        for item in adjudicated_result.manifest["vps"]
        if item["id"] == "VP3"
    )
    assert vp3["status"] == "unlocked"
    assert vp3["accepted_themes"] == ["TH3"]
    assert vp3["baseline_revision"] == baseline_revision
    assert vp3["reason"] == "unaccepted mapped themes: TH4, TH5"

    if mutation == "delete":
        target.unlink()
        subprocess.run(["git", "-C", str(root), "add", "-u"], check=True)
    else:
        target.write_text(
            target.read_text(encoding="utf-8").replace(
                "The revision is required.",
                "The accepted evidence was rewritten.",
            )
            if kind == "DR"
            else target.read_text(encoding="utf-8").replace(
                "The clarification is accepted.",
                "The accepted evidence was rewritten.",
            ),
            encoding="utf-8",
        )
        subprocess.run(["git", "-C", str(root), "add", relative], check=True)
    subprocess.run(
        [
            "git", "-C", str(root), "-c", "user.name=Test",
            "-c", "user.email=test@example.invalid", "commit", "-qm",
            f"{mutation} adjudicated {kind}",
        ],
        check=True,
    )

    result = lock.validate_repository(root, baselines=baselines)

    assert not result.valid
    finding = next(item for item in result.findings if item["file"] == relative)
    assert (
        "deleted or renamed" in finding["message"]
        if mutation == "delete"
        else "rewrites content preserved" in finding["message"]
    )
    changed_vp3 = next(
        item for item in result.manifest["vps"] if item["id"] == "VP3"
    )
    assert changed_vp3["status"] == "unlocked"
    assert changed_vp3["accepted_themes"] == ["TH3"]
    assert changed_vp3["baseline_revision"] == baseline_revision
    assert changed_vp3["reason"] == "unaccepted mapped themes: TH4, TH5"


@pytest.mark.parametrize(
    ("relative", "content"),
    (
        (
            "docs/discovery/VP3-method/revisions/DR-001-stub.md",
            "# DR-001: Stub\n",
        ),
        (
            "docs/requirements/VP3-method/changes/PCR-001-stub.md",
            "# PCR-001: Stub\n",
        ),
        ("docs/discovery/VP3-method/new-basis.md", "# Direct addition\n"),
    ),
)
def test_partial_acceptance_rejects_invalid_or_non_record_additions(
    tmp_path: Path,
    relative: str,
    content: str,
):
    baselines, reader = create_partial_repository(tmp_path)
    write(tmp_path / relative, content)

    result = lock.validate_repository(
        tmp_path, baselines=baselines, baseline_reader=reader
    )

    assert not result.valid
    assert relative in finding_files(result)


def test_partial_acceptance_rejects_malformed_dr_semantics(tmp_path: Path):
    baselines, reader = create_partial_repository(tmp_path)
    malformed = valid_dr().replace(
        "| Invalidated gates | requirements |",
        "| Invalidated gates | deployment |",
    )
    relative = "docs/discovery/VP3-method/revisions/DR-001-malformed.md"
    write(tmp_path / relative, malformed)

    result = lock.validate_repository(
        tmp_path, baselines=baselines, baseline_reader=reader
    )

    assert not result.valid
    assert relative in finding_files(result)
    assert any(
        item["record"] == "DR-001" and "gate vocabulary" in item["message"]
        for item in result.findings
    )


def test_uncommitted_accepted_dr_requires_resolving_immutable_evidence(
    tmp_path: Path,
):
    baselines, reader = create_partial_repository(tmp_path)
    relative = "docs/discovery/VP3-method/revisions/DR-001-update.md"
    write(
        tmp_path / relative,
        valid_dr().replace(f"git:{REV3}", "git:" + ("9" * 40)),
    )

    result = lock.validate_repository(
        tmp_path, baselines=baselines, baseline_reader=reader
    )

    assert not result.valid
    assert any(
        item["file"] == relative
        and "no immutable repository evidence" in item["message"]
        for item in result.findings
    )


@pytest.mark.parametrize(
    ("operation", "affected_pr", "requirement_id"),
    (
        ("add", "PR-999", "PR-999"),
        ("rename", "None", None),
    ),
)
def test_partial_acceptance_reuses_canonical_pcr_semantics(
    tmp_path: Path,
    operation: str,
    affected_pr: str,
    requirement_id: str | None,
):
    baselines, reader = create_partial_repository(tmp_path)
    prd = (
        tmp_path / "docs/requirements/VP3-method/PRD.md"
    ).read_text(encoding="utf-8")
    baseline = re.search(
        r"(?m)^\| Source revision \| (sha256:[0-9a-f]{64}) \|$", prd
    ).group(1)
    relative = "docs/requirements/VP3-method/changes/PCR-001-invalid.md"
    write(
        tmp_path / relative,
        valid_pcr(
            baseline,
            operation=operation,
            affected_pr=affected_pr,
            requirement_id=requirement_id,
        ),
    )

    result = lock.validate_repository(
        tmp_path, baselines=baselines, baseline_reader=reader
    )

    assert not result.valid
    assert relative in finding_files(result)
    assert any(
        item["record"] in {"PCR-001", "PR-999"}
        and (
            "deterministic next ID" in item["message"]
            or "Requirement operation" in item["message"]
        )
        for item in result.findings
    )


def test_partial_acceptance_rejects_pcr_architecture_selection(tmp_path: Path):
    baselines, reader = create_partial_repository(tmp_path)
    prd = (
        tmp_path / "docs/requirements/VP3-method/PRD.md"
    ).read_text(encoding="utf-8")
    baseline = re.search(
        r"(?m)^\| Source revision \| (sha256:[0-9a-f]{64}) \|$", prd
    ).group(1)
    relative = "docs/requirements/VP3-method/changes/PCR-001-design.md"
    write(
        tmp_path / relative,
        valid_pcr(
            baseline,
            change="Use PostgreSQL as the product persistence database.",
        ),
    )

    result = lock.validate_repository(
        tmp_path, baselines=baselines, baseline_reader=reader
    )

    assert not result.valid
    assert any(
        item["record"] == "PCR-001"
        and "outside the product boundary" in item["message"]
        for item in result.findings
    )


def test_shared_vp_locks_only_after_all_mapped_themes_accept(tmp_path: Path):
    baselines, reader = create_repository(tmp_path, vp3_locked=True)

    initial = lock.validate_repository(
        tmp_path, baselines=baselines, baseline_reader=reader
    )
    assert initial.valid
    vp3 = next(item for item in initial.manifest["vps"] if item["id"] == "VP3")
    assert vp3["status"] == "locked"

    vp = tmp_path / "docs/vision_of_product/VP3-method/VP3.md"
    vp.write_text(vp.read_text() + "\nrewritten\n", encoding="utf-8")
    changed = lock.validate_repository(
        tmp_path, baselines=baselines, baseline_reader=reader
    )

    assert not changed.valid
    assert "docs/vision_of_product/VP3-method/VP3.md" in finding_files(changed)
    adr2 = next(item for item in changed.manifest["adrs"] if item["id"] == "ADR-002")
    assert adr2["dependent_accepted_themes"] == ["TH3"]


def test_fully_locked_vp_mapping_expansion_fails_without_reopening(
    tmp_path: Path,
):
    baselines, reader = create_repository(tmp_path, vp3_locked=True)
    vp = tmp_path / "docs/vision_of_product/VP3-method/VP3.md"
    vp.write_text(
        vp.read_text(encoding="utf-8").replace(
            "TH3, TH4, TH5", "TH3, TH4, TH5, TH6"
        ),
        encoding="utf-8",
    )

    result = lock.validate_repository(
        tmp_path, baselines=baselines, baseline_reader=reader
    )

    assert not result.valid
    vp3 = next(item for item in result.manifest["vps"] if item["id"] == "VP3")
    assert vp3["status"] == "unlocked"
    assert vp3["accepted_themes"] == ["TH3", "TH4", "TH5"]
    assert vp3["baseline_revision"] == REV3
    assert vp3["reason"] == "unaccepted mapped themes: TH6"
    assert any(
        finding["record"] == "VP3"
        and "mapping change cannot reopen" in finding["message"]
        and "new VP" in finding["remediation"]
        and "PCR" in finding["remediation"]
        for finding in result.findings
    )
    assert "docs/vision_of_product/VP3-method/VP3.md" in finding_files(result)


def test_missing_immutable_evidence_fails_closed(
    repository: tuple[Path, lock.Baselines, SnapshotReader],
):
    class MissingReader:
        def read(self, revision: str, paths: Sequence[str]):
            raise lock.BaselineError("fixture object missing")

    root, baselines, _ = repository
    result = lock.validate_repository(
        root, baselines=baselines, baseline_reader=MissingReader()
    )

    assert not result.valid
    assert any(
        "Immutable baseline evidence is unavailable" in finding["message"]
        for finding in result.findings
    )


def test_cli_lock_failure_is_exit_2_and_exactly_one_json_object(
    monkeypatch: pytest.MonkeyPatch,
    repository: tuple[Path, lock.Baselines, SnapshotReader],
):
    root, _, _ = repository
    story = (
        root
        / "docs/themes/TH2-gitflow-operator/epics/E1/stories/US1.md"
    )
    story.unlink()
    failed = validate(repository)
    monkeypatch.setattr(lock, "validate_repository", lambda _root: failed)

    command = cli.dispatch(["validate", "lock", "--json"], probe_directory=root)
    stdout = io.StringIO()
    stderr = io.StringIO()
    exit_code = cli.emit(command, stdout=stdout, stderr=stderr)

    assert exit_code == exits.VALIDATION_FAILURE
    assert len(stdout.getvalue().splitlines()) == 1
    payload = json.loads(stdout.getvalue())
    assert payload["check"] == "lock"
    assert payload["status"] == "failed"
    assert payload["findings"]
    assert "method validate lock:" in stderr.getvalue()


def test_git_reader_uses_no_shell_and_only_read_only_plumbing():
    source = (ROOT / "methodlib/lock.py").read_text(encoding="utf-8")

    assert "shell=True" not in source
    assert '"status"' not in source[source.index("class GitBaselineReader"):source.index(
        "def _read_control"
    )]
    assert '"commit"' not in source[source.index("class GitBaselineReader"):source.index(
        "def _read_control"
    )]
    assert '"branch"' not in source[source.index("class GitBaselineReader"):source.index(
        "def _read_control"
    )]


def test_git_reader_resolves_absolute_non_repository_binary_and_sanitizes_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    repository = tmp_path / "repo"
    fake_bin = repository / "bin"
    fake_git = fake_bin / "git"
    write(fake_git, "#!/bin/sh\nexit 99\n")
    fake_git.chmod(0o755)
    monkeypatch.setenv(
        "PATH",
        os.pathsep.join((str(fake_bin), "relative-bin", "/usr/bin", "/bin")),
    )
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    calls: list[tuple[list[str], dict[str, str]]] = []

    class Completed:
        returncode = 0
        stdout = b""
        stderr = b""

    def intercept(argv, **kwargs):
        calls.append((list(argv), dict(kwargs["env"])))
        return Completed()

    monkeypatch.setattr(subprocess, "run", intercept)
    reader = lock.GitBaselineReader(repository)
    reader._run(("cat-file", "-e", f"{REV1}^{{commit}}"))

    assert calls
    argv, environment = calls[0]
    assert Path(argv[0]).is_absolute()
    assert Path(argv[0]) != fake_git
    assert not Path(argv[0]).is_relative_to(repository)
    assert environment["PATH"] == str(Path(argv[0]).parent)
    assert "GIT_CONFIG_COUNT" not in environment
    assert environment["GIT_CONFIG_GLOBAL"] == os.devnull


def test_git_reader_rejects_repository_and_relative_path_substitution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    repository = tmp_path / "repo"
    fake_git = repository / "bin/git"
    write(fake_git, "#!/bin/sh\nexit 0\n")
    fake_git.chmod(0o755)
    monkeypatch.setenv("PATH", f"{fake_git.parent}{os.pathsep}relative-bin")

    reader = lock.GitBaselineReader(repository)

    assert reader.git_executable is None
    with pytest.raises(lock.BaselineError, match="trusted Git executable"):
        reader.read(REV1, ("docs",))


def test_legacy_provenance_uses_peeled_commit_ids():
    expected = {
        "TH1": subprocess.run(
            ["git", "rev-parse", "v0.7.0^{}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip(),
        "TH2": subprocess.run(
            ["git", "rev-parse", "v0.8.0^{}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip(),
    }

    assert lock.LEGACY_BASELINES.themes["TH1"].revision == expected["TH1"]
    assert lock.LEGACY_BASELINES.themes["TH2"].revision == expected["TH2"]
    assert lock.LEGACY_BASELINES.adrs["ADR-001"].revision == expected["TH2"]
    for revision in expected.values():
        kind = subprocess.run(
            ["git", "cat-file", "-t", revision],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        assert kind == "commit"


def test_git_reader_rejects_annotated_tag_object_as_unpeeled_provenance():
    tag_object = subprocess.run(
        ["git", "rev-parse", "v0.8.0^{tag}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    reader = lock.GitBaselineReader(ROOT)

    with pytest.raises(lock.BaselineError, match="peeled commit ID"):
        reader.read(tag_object, ("docs/themes/TH2-gitflow-operator",))


def test_locked_tree_detects_executable_mode_change(
    repository: tuple[Path, lock.Baselines, SnapshotReader],
):
    root, _, _ = repository
    story = root / "docs/themes/TH2-gitflow-operator/epics/E1/stories/US1.md"
    story.chmod(0o755)

    result = validate(repository)

    assert not result.valid
    finding = next(item for item in result.findings if item["file"] == str(
        story.relative_to(root)
    ))
    assert "executable mode" in finding["message"]


def test_control_and_artefact_reads_reject_symlinked_ancestor(tmp_path: Path):
    root = tmp_path / "repo"
    baselines, reader = create_repository(root)
    external_docs = tmp_path / "external-docs"
    (root / "docs").rename(external_docs)
    (root / "docs").symlink_to(external_docs, target_is_directory=True)

    result = lock.validate_repository(
        root, baselines=baselines, baseline_reader=reader
    )

    assert not result.valid
    assert any(
        item["file"] == lock.BACKLOG_PATH
        and "Cannot build the lock manifest" in item["message"]
        for item in result.findings
    )
    assert any("ancestor docs is a symlink" in item["message"] for item in result.findings)
