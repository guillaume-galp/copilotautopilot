import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from methodlib import cli, exits, gates  # noqa: E402


METHOD = ROOT / "bin" / "method"
FIXTURES = ROOT / "tests/fixtures/method_gates"
VP = "VP9"
SLUG = "VP9-fixture"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def repository(
    root: Path,
    *,
    discovery: str | None = "discovery-ready.md",
    prd: str | None = None,
    architecture: bool = False,
    vision: bool = True,
) -> Path:
    if vision:
        vision_file = root / "docs/vision_of_product" / SLUG / f"{VP}.md"
        vision_file.parent.mkdir(parents=True)
        vision_file.write_text(
            "# VP9 Fixture\n\n"
            "## Outcomes\n\n"
            "| ID | Outcome |\n"
            "|---|---|\n"
            "| VO-001 | Validate lifecycle entry safely. |\n",
            encoding="utf-8",
        )
    if discovery is not None:
        readme = root / "docs/discovery" / SLUG / "README.md"
        readme.parent.mkdir(parents=True)
        readme.write_text(fixture(discovery), encoding="utf-8")
        revision = gates._discovery_revision(
            vision=root / "docs/vision_of_product" / SLUG / f"{VP}.md",
            dossier=readme.parent,
            root=root,
        )
        if revision is not None and "| Source revision |" in readme.read_text():
            readme.write_text(
                re.sub(
                    r"(?m)^\| Source revision \| [^|]+ \|$",
                    f"| Source revision | {revision} |",
                    readme.read_text(),
                    count=1,
                ),
                encoding="utf-8",
            )
    if prd is not None:
        target = root / "docs/requirements" / SLUG / "PRD.md"
        target.parent.mkdir(parents=True)
        text = fixture(prd)
        discovery_readme = root / "docs/discovery" / SLUG / "README.md"
        if discovery_readme.is_file():
            accepted = re.search(
                r"(?m)^\| Source revision \| ([^|]+) \|$",
                discovery_readme.read_text(),
            )
            assert accepted
            text = re.sub(
                r"(?m)^\| Discovery source revision \| [^|]+ \|$",
                f"| Discovery source revision | {accepted.group(1)} |",
                text,
            )
        target.write_text(text, encoding="utf-8")
        revision = gates._prd_revision(target.read_text())
        target.write_text(
            re.sub(
                r"(?m)^\| Source revision \| [^|]+ \|$",
                f"| Source revision | {revision} |",
                target.read_text(),
                count=1,
            ),
            encoding="utf-8",
        )
    if architecture:
        target = root / "docs/architecture/README.md"
        target.parent.mkdir(parents=True)
        target.write_text(
            fixture("architecture-accepted.md"), encoding="utf-8"
        )
        revision = gates._architecture_revision(root, target)
        target.write_text(
            re.sub(
                r"(?m)^\| Source revision \| [^|]+ \|$",
                f"| Source revision | {revision} |",
                target.read_text(),
                count=1,
            ),
            encoding="utf-8",
        )
    return root


def validate(
    root: Path,
    stage: str,
    **kwargs,
) -> gates.ValidationResult:
    return gates.validate_repository(root, vp=VP, stage=stage, **kwargs)


def assert_finding_shape(finding: gates.Finding) -> None:
    assert set(finding) == {
        "check",
        "severity",
        "file",
        "record",
        "message",
        "remediation",
    }
    assert finding["check"] == "gates"
    assert finding["severity"] == "error"
    assert finding["file"]
    assert finding["message"]
    assert finding["remediation"]


def test_real_vp3_ready_with_deferrals_opens_requirements_and_emits_one_json():
    result = subprocess.run(
        [
            str(METHOD),
            "validate",
            "gates",
            "--vp",
            "VP3",
            "--stage",
            "requirements",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == exits.SUCCESS
    assert len(result.stdout.splitlines()) == 1
    report = json.loads(result.stdout)
    assert report["status"] == "ok"
    assert report["stage_entry"] == "open"
    assert report["gate"] == {
        "name": "discovery-readiness",
        "file": (
            "docs/discovery/VP3-discovery-led-cost-aware-methodology/"
            "README.md"
        ),
        "section": "Acceptance",
        "status": "open",
        "actor": "Human product owner",
        "timestamp": "2026-09-05T16:08:02+01:00",
        "scope": "VP3 Discovery dossier and bounded architecture deferrals",
        "verdict": "READY_WITH_DEFERRALS",
        "source_revision": (
            "Discovery dossier state at 2026-09-05T16:08:02+01:00"
        ),
    }
    assert report["findings"] == []
    assert result.stderr == ""


def test_stage_resolution_distinguishes_root_and_each_formal_upstream_gate(
    tmp_path: Path,
):
    discovery_root = repository(
        tmp_path / "discovery", discovery="discovery-working.md"
    )
    requirements_root = repository(tmp_path / "requirements")
    architecture_root = repository(
        tmp_path / "architecture", prd="prd-approved.md"
    )
    planning_root = repository(
        tmp_path / "planning",
        discovery=None,
        vision=False,
        architecture=True,
    )

    discovery = validate(discovery_root, "discovery")
    requirements = validate(requirements_root, "requirements")
    architecture = validate(architecture_root, "architecture")
    planning = validate(planning_root, "planning")

    assert discovery.valid
    assert [gate["name"] for gate in discovery.payload["upstream_gates"]] == [
        "vision-sketch"
    ]
    assert requirements.valid
    assert [gate["name"] for gate in requirements.payload["upstream_gates"]] == [
        "discovery-readiness"
    ]
    assert architecture.valid
    assert [gate["name"] for gate in architecture.payload["upstream_gates"]] == [
        "discovery-readiness",
        "prd-approval",
    ]
    assert planning.valid
    assert [gate["name"] for gate in planning.payload["upstream_gates"]] == [
        "architecture-acceptance"
    ]


def test_planning_scope_rejects_vp_token_with_alphanumeric_suffix(
    tmp_path: Path,
):
    root = repository(
        tmp_path,
        discovery=None,
        vision=False,
        architecture=True,
    )
    architecture = root / "docs/architecture/README.md"
    architecture.write_text(
        architecture.read_text().replace(
            "| Scope | VP9 architecture |",
            "| Scope | VP9foo architecture |",
        ),
        encoding="utf-8",
    )

    result = validate(root, "planning")

    assert not result.valid
    assert result.payload["stage_entry"] == "closed"
    assert any(
        finding["record"] == "architecture-acceptance"
        and "Scope does not cover VP9" in finding["message"]
        for finding in result.findings
    )


def test_discovery_requires_the_root_vision_but_not_a_formal_gate(tmp_path: Path):
    missing = validate(repository(tmp_path / "missing", vision=False), "discovery")
    present = validate(repository(tmp_path / "present", discovery=None), "discovery")

    assert not missing.valid
    assert missing.payload["stage_entry"] == "closed"
    assert any(
        finding["record"] == "vision-sketch"
        for finding in missing.findings
    )
    assert present.valid
    assert present.payload["upstream_gates"][0]["formal_gate"] is False


def test_paused_discovery_reports_open_items_without_opening_requirements(
    tmp_path: Path,
):
    root = repository(tmp_path, discovery="discovery-working.md")

    result = validate(root, "discovery")

    assert result.valid
    assert result.payload["stage_entry"] == "open"
    assert result.payload["working_state"] == {
        "status": "awaiting-human",
        "open_items": [
            "DQ-001 (owner: designer)",
            "DQ-002 (owner: product owner)",
        ],
        "accepted_so_far": ["DEC-001"],
        "next_action": (
            "Actor: Human; Action: answer the grouped scope checkpoint; "
            "Intended result: resolve DQ-001 and DQ-002"
        ),
    }
    assert result.payload["downstream_gate"]["status"] == "closed"
    assert result.findings == ()


@pytest.mark.parametrize(
    "discovery",
    [None, "discovery-blocked.md"],
)
def test_missing_and_blocked_discovery_fail_closed(
    tmp_path: Path, discovery: str | None
):
    root = repository(tmp_path, discovery=discovery, prd="prd-approved.md")

    result = validate(root, "architecture")

    assert not result.valid
    assert result.payload["stage_entry"] == "closed"
    assert all(finding["remediation"] for finding in result.findings)
    assert all(
        set(finding)
        == {
            "check",
            "severity",
            "file",
            "record",
            "message",
            "remediation",
        }
        for finding in result.findings
    )
    if discovery is not None:
        assert any(
            "Architecture cannot begin before an accepted readiness verdict"
            in finding["message"]
            for finding in result.findings
        )


@pytest.mark.parametrize("verdict", ["Rejected", "Accepted", "ready", "UNKNOWN"])
def test_unaccepted_discovery_verdicts_fail_closed(
    tmp_path: Path, verdict: str
):
    root = repository(tmp_path)
    readme = root / "docs/discovery" / SLUG / "README.md"
    readme.write_text(
        readme.read_text().replace("| Verdict | READY |", f"| Verdict | {verdict} |"),
        encoding="utf-8",
    )

    result = validate(root, "requirements")

    assert not result.valid
    assert any(
        "verdict" in finding["message"].casefold()
        for finding in result.findings
    )


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    [
        ("Actor", "", "Actor"),
        ("Timestamp", "2026-09-05", "Timestamp"),
        ("Scope", "", "Scope"),
        ("Verdict", "", "Verdict"),
        ("Rationale", "<rationale>", "Rationale"),
        ("Source revision", "", "Source revision"),
    ],
)
def test_each_required_gate_field_is_completely_validated(
    tmp_path: Path,
    field: str,
    replacement: str,
    message: str,
):
    root = repository(tmp_path)
    readme = root / "docs/discovery" / SLUG / "README.md"
    lines = readme.read_text().splitlines()
    lines = [
        f"| {field} | {replacement} |"
        if line.startswith(f"| {field} |")
        else line
        for line in lines
    ]
    readme.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = validate(root, "requirements")

    assert not result.valid
    assert any(message in finding["message"] for finding in result.findings)
    for finding in result.findings:
        assert_finding_shape(finding)


def test_agent_actor_and_malformed_timestamp_are_not_human_acceptance(
    tmp_path: Path,
):
    root = repository(tmp_path)
    readme = root / "docs/discovery" / SLUG / "README.md"
    text = readme.read_text()
    text = text.replace("Human: product owner", "discovery-facilitator agent")
    text = text.replace(
        "2026-09-05T12:00:00+01:00", "2026-02-30T12:00:00+01:00"
    )
    readme.write_text(text, encoding="utf-8")

    result = validate(root, "requirements")

    assert not result.valid
    assert any("human authority" in finding["message"] for finding in result.findings)
    assert any("ISO-8601" in finding["message"] for finding in result.findings)


@pytest.mark.parametrize("verdict", ["READY", "READY_WITH_DEFERRALS"])
def test_both_human_accepted_readiness_verdicts_open_requirements(
    tmp_path: Path, verdict: str
):
    source = (
        "discovery-ready.md"
        if verdict == "READY"
        else "discovery-ready-with-deferrals.md"
    )

    result = validate(repository(tmp_path, discovery=source), "requirements")

    assert result.valid
    assert result.payload["stage_entry"] == "open"
    assert result.payload["gate"]["verdict"] == verdict


def test_working_state_never_substitutes_for_requirements_gate(tmp_path: Path):
    root = repository(tmp_path, discovery="discovery-working.md")

    result = validate(root, "requirements")

    assert not result.valid
    assert result.payload["stage_entry"] == "closed"
    assert result.payload["working_state"]["status"] == "awaiting-human"
    assert any(
        finding["record"] == "discovery-readiness"
        for finding in result.findings
    )


def test_valid_waiver_obeys_date_timestamp_and_lifecycle_expiry(
    tmp_path: Path,
):
    root = repository(tmp_path, discovery="discovery-waived.md")
    readme = root / "docs/discovery" / SLUG / "README.md"
    before = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
    after = datetime(2026, 10, 2, 0, tzinfo=timezone.utc)

    assert validate(root, "requirements", as_of=before).valid
    expired = validate(root, "requirements", as_of=after)
    assert not expired.valid
    assert any("expired" in finding["message"] for finding in expired.findings)

    text = readme.read_text().replace(
        "| Expiry | 2026-10-01 |",
        "| Expiry | 2026-10-01T08:00:00+01:00 |",
    )
    readme.write_text(text, encoding="utf-8")
    instant_expired = validate(
        root,
        "requirements",
        as_of=datetime(2026, 10, 1, 12, tzinfo=timezone.utc),
    )
    assert not instant_expired.valid

    readme.write_text(
        text.replace(
            "| Expiry | 2026-10-01T08:00:00+01:00 |",
            "| Expiry | until TH9 acceptance |",
        ),
        encoding="utf-8",
    )
    assert validate(root, "requirements", as_of=before).valid
    occurred = validate(
        root,
        "requirements",
        as_of=before,
        occurred_lifecycle_events=frozenset({"until TH9 acceptance"}),
    )
    assert not occurred.valid
    assert any("TH9 acceptance occurred" in item["message"] for item in occurred.findings)


@pytest.mark.parametrize(
    ("old", "new", "expected"),
    [
        ("| Actor | Human: product owner |\n", "", "Actor"),
        ("| Expiry | 2026-10-01 |\n", "", "Expiry"),
        (
            "| Invalidation | Material scope expansion, new integration, or authority-boundary change |",
            "| Invalidation | Optional review |",
            "material scope expansion",
        ),
    ],
)
def test_waiver_requires_human_approval_expiry_and_invalidation(
    tmp_path: Path, old: str, new: str, expected: str
):
    root = repository(tmp_path, discovery="discovery-waived.md")
    readme = root / "docs/discovery" / SLUG / "README.md"
    readme.write_text(readme.read_text().replace(old, new), encoding="utf-8")

    result = validate(
        root,
        "requirements",
        as_of=datetime(2026, 9, 6, tzinfo=timezone.utc),
    )

    assert not result.valid
    assert any(expected in finding["message"] for finding in result.findings)


def test_material_scope_expansion_invalidates_an_otherwise_active_waiver(
    tmp_path: Path,
):
    root = repository(tmp_path, discovery="discovery-waived.md")

    result = validate(
        root,
        "requirements",
        as_of=datetime(2026, 9, 6, tzinfo=timezone.utc),
        material_scope_expanded=True,
    )

    assert not result.valid
    assert any(
        "invalidated by material scope expansion" in finding["message"]
        for finding in result.findings
    )


def test_current_discovery_digest_detects_stale_upstream_source(tmp_path: Path):
    root = repository(tmp_path)
    dossier = root / "docs/discovery" / SLUG
    readme = dossier / "README.md"
    for name in set(gates.DISCOVERY_OWNERS.values()):
        (dossier / name).write_text(f"# {name}\n", encoding="utf-8")
    text = fixture("discovery-ready.md")
    text = text.replace(
        "| Source revision | sha256:"
        + ("a" * 64)
        + " |",
        "| Source revision | sha256:" + ("a" * 64) + " |",
    )
    readme.write_text(text, encoding="utf-8")

    stale = validate(root, "requirements")
    stale_cli = cli.dispatch(
        ["validate", "gates", "--vp", VP, "--stage", "requirements"],
        probe_directory=root,
    )
    revision = gates._discovery_revision(
        vision=root / "docs/vision_of_product" / SLUG / f"{VP}.md",
        dossier=dossier,
        root=root,
    )
    readme.write_text(
        readme.read_text().replace("sha256:" + ("a" * 64), str(revision)),
        encoding="utf-8",
    )
    fresh = validate(root, "requirements")
    fresh_cli = cli.dispatch(
        ["validate", "gates", "--vp", VP, "--stage", "requirements"],
        probe_directory=root,
    )

    assert not stale.valid
    assert stale_cli.exit_code == exits.VALIDATION_FAILURE
    assert any("Source revision is stale" in item["message"] for item in stale.findings)
    assert fresh.valid
    assert fresh_cli.exit_code == exits.SUCCESS


def test_current_prd_digest_detects_stale_submitted_content(tmp_path: Path):
    root = repository(tmp_path, prd="prd-approved.md")
    prd = root / "docs/requirements" / SLUG / "PRD.md"
    text = prd.read_text()
    text = text.replace(
        re.search(
            r"(?m)^\| Source revision \| sha256:[0-9a-f]{64} \|$",
            text,
        ).group(0),
        "| Source revision | sha256:" + ("b" * 64) + " |",
        1,
    )
    prd.write_text(text, encoding="utf-8")

    stale = validate(root, "architecture")
    revision = gates._prd_revision(prd.read_text())
    prd.write_text(
        prd.read_text().replace("sha256:" + ("b" * 64), revision),
        encoding="utf-8",
    )
    fresh = validate(root, "architecture")

    assert not stale.valid
    assert any("Source revision is stale" in item["message"] for item in stale.findings)
    assert fresh.valid


def test_gate_sources_cannot_escape_repository_through_symlinks(tmp_path: Path):
    root = repository(tmp_path / "repo", discovery=None)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "README.md").write_text(
        fixture("discovery-ready.md"), encoding="utf-8"
    )
    link = root / "docs/discovery" / SLUG
    link.parent.mkdir(parents=True)
    link.symlink_to(outside, target_is_directory=True)

    result = validate(root, "requirements")

    assert not result.valid
    assert any("outside the repository" in item["message"] for item in result.findings)
    assert all(
        not str(item["file"]).startswith(str(outside))
        for item in result.findings
    )


def test_cli_dispatch_returns_exit_two_and_six_field_findings(tmp_path: Path):
    root = repository(tmp_path, discovery="discovery-blocked.md")

    result = cli.dispatch(
        ["validate", "gates", "--vp", VP, "--stage", "requirements"],
        probe_directory=root,
    )

    assert result.exit_code == exits.VALIDATION_FAILURE
    assert result.payload["status"] == "failed"
    for finding in result.payload["findings"]:
        assert_finding_shape(finding)


def test_adversarial_1_discovery_entry_ignores_its_invalid_completion_gate(
    tmp_path: Path,
):
    root = repository(tmp_path)
    readme = root / "docs/discovery" / SLUG / "README.md"
    readme.write_text(
        readme.read_text().replace(
            "Human: product owner", "Human: discovery-facilitator"
        ),
        encoding="utf-8",
    )

    result = validate(root, "discovery")

    assert result.valid
    assert result.payload["stage_entry"] == "open"
    assert result.payload["findings"] == []
    assert result.payload["downstream_gate"]["status"] == "closed"
    assert any(
        "Actor" in item["message"]
        for item in result.payload["completion_findings"]
    )


@pytest.mark.parametrize(
    "spoof",
    [
        "Human: discovery-facilitator",
        "Human: agent",
        "Humanized product owner",
        "Human: product owner agent",
    ],
)
def test_adversarial_2_only_exact_accountable_human_authorities_open_gates(
    tmp_path: Path,
    spoof: str,
):
    root = repository(tmp_path)
    readme = root / "docs/discovery" / SLUG / "README.md"
    readme.write_text(
        readme.read_text().replace("Human: product owner", spoof),
        encoding="utf-8",
    )

    result = validate(root, "requirements")

    assert not result.valid
    assert result.payload["stage_entry"] == "closed"
    assert any(
        "human authority" in item["message"] for item in result.findings
    )


@pytest.mark.parametrize(
    "commented_gate",
    [
        "<!--\n{gate}\n-->",
        "<!-- outer\n<!-- nested -->\n{gate}\n-->",
        "<!-- unclosed\n{gate}",
    ],
)
def test_adversarial_3_html_commented_gates_never_open(
    tmp_path: Path,
    commented_gate: str,
):
    root = repository(tmp_path, discovery=None)
    readme = root / "docs/discovery" / SLUG / "README.md"
    readme.parent.mkdir(parents=True)
    gate = fixture("discovery-ready.md").split("## Acceptance", 1)[1]
    readme.write_text(
        "# VP9 Discovery Dossier\n\n"
        + commented_gate.format(gate="## Acceptance" + gate)
        + "\n",
        encoding="utf-8",
    )

    result = validate(root, "requirements")

    assert not result.valid
    assert result.payload["stage_entry"] == "closed"
    assert any("missing" in item["message"] for item in result.findings)


def _git_commit(root: Path, message: str) -> str:
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(
        ["git", "-C", str(root), "config", "user.email", "gate@example.test"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(root), "config", "user.name", "Gate Test"],
        check=True,
    )
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(root), "commit", "-q", "-m", message], check=True
    )
    return subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()


def _replace_gate_revision(path: Path, revision: str) -> None:
    path.write_text(
        re.sub(
            r"(?m)^\| Source revision \| [^|]+ \|$",
            f"| Source revision | {revision} |",
            path.read_text(),
            count=1,
        ),
        encoding="utf-8",
    )


def _write_add_pcr(
    root: Path,
    *,
    requirement_id: str = "PR-002",
    affected_requirement_id: str | None = None,
    pcr_number: int = 1,
    verdict: str = "Approved",
    impact: str = "consequential",
    traces: str = "VO-001",
    all_impacts_none: bool = False,
) -> Path:
    record_id = f"PCR-{pcr_number:03d}"
    prd = root / "docs/requirements" / SLUG / "PRD.md"
    baseline = re.search(
        r"(?m)^\| Source revision \| (sha256:[0-9a-f]{64}) \|$",
        prd.read_text(),
    ).group(1)
    impact_value = "None" if all_impacts_none else "No Discovery impact."
    metadata = {
        "Schema version": "1",
        "Requirement operation": "add",
        "Change": f"Add {requirement_id} behavior.",
        "Reason": "The approved scope requires the behavior.",
        "Requestor": "Human product owner",
        "Affected PR": affected_requirement_id or requirement_id,
        "Affected QR": "None",
        "Affected decisions": "None",
        "Affected assumptions": "None",
        "Affected risks": "None",
        "Affected themes": "None",
        "Discovery impact": impact_value,
        "Architecture impact": impact_value,
        "Migration impact": impact_value,
        "Replanning impact": impact_value,
        "Supersedes": "None",
        "Human actor": "Human: product owner",
        "Human timestamp": "2026-09-06T10:00:00+01:00",
        "Human scope": (
            f"VP9 {record_id} proposed content against PRD baseline {baseline}"
        ),
        "Human verdict": verdict,
        "Human rationale": "Approve the exact proposed behavior.",
        "Baseline revision": baseline,
        "Source revision": "sha256:" + ("0" * 64),
    }
    row = {
        "ID": requirement_id,
        "Schema version": "1",
        "Requirement": "The product shall expose the added behavior.",
        "Measure": "An acceptance scenario observes the added behavior.",
        "Impact": impact,
        "Impact rationale": "The behavior changes observable product scope.",
        "Traces": traces,
    }
    source_revision = gates._pcr_revision(record_id, metadata, [row])
    metadata["Source revision"] = source_revision
    path = prd.parent / f"changes/{record_id}-add-behavior.md"
    path.parent.mkdir(exist_ok=True)
    path.write_text(
        f"# {record_id}: Add behavior\n\n"
        "| Field | Value |\n"
        "|---|---|\n"
        + "\n".join(
            f"| {field} | {metadata[field]} |" for field in gates.PCR_FIELDS
        )
        + "\n\n"
        + "| "
        + " | ".join(gates.REQUIREMENT_FIELDS)
        + " |\n|"
        + "|".join("---" for _ in gates.REQUIREMENT_FIELDS)
        + "|\n| "
        + " | ".join(row[field] for field in gates.REQUIREMENT_FIELDS)
        + " |\n",
        encoding="utf-8",
    )
    return path


def _write_metadata_only_pcr(
    root: Path,
    *,
    pcr_number: int,
    operation: str = "non-requirement",
    affected_pr: str = "None",
    affected_qr: str = "None",
    supersedes: str = "None",
    verdict: str = "Approved",
) -> Path:
    record_id = f"PCR-{pcr_number:03d}"
    prd = root / "docs/requirements" / SLUG / "PRD.md"
    baseline = re.search(
        r"(?m)^\| Source revision \| (sha256:[0-9a-f]{64}) \|$",
        prd.read_text(),
    ).group(1)
    metadata = {
        "Schema version": "1",
        "Requirement operation": operation,
        "Change": "Change the normative product scope without adding a requirement.",
        "Reason": "The approved scope needs an explicit product rule.",
        "Requestor": "Human product owner",
        "Affected PR": affected_pr,
        "Affected QR": affected_qr,
        "Affected decisions": "None",
        "Affected assumptions": "None",
        "Affected risks": "None",
        "Affected themes": "None",
        "Discovery impact": "None",
        "Architecture impact": "None",
        "Migration impact": "None",
        "Replanning impact": "None",
        "Supersedes": supersedes,
        "Human actor": "Human: product owner",
        "Human timestamp": "2026-09-06T10:00:00+01:00",
        "Human scope": (
            f"VP9 {record_id} proposed content against PRD baseline {baseline}"
        ),
        "Human verdict": verdict,
        "Human rationale": "Approve the exact normative scope change.",
        "Baseline revision": baseline,
        "Source revision": "sha256:" + ("0" * 64),
    }
    metadata["Source revision"] = gates._pcr_revision(
        record_id, metadata, []
    )
    path = prd.parent / f"changes/{record_id}-scope-rule.md"
    path.parent.mkdir(exist_ok=True)
    path.write_text(
        f"# {record_id}: Scope rule\n\n"
        "| Field | Value |\n"
        "|---|---|\n"
        + "\n".join(
            f"| {field} | {metadata[field]} |" for field in gates.PCR_FIELDS
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _replace_prd_and_pcr_baseline(
    prd: Path, pcr: Path, baseline: str
) -> None:
    _replace_gate_revision(prd, baseline)
    pcr.write_text(
        re.sub(
            r"(?m)^\| Human scope \| [^|]+ \|$",
            (
                "| Human scope | VP9 PCR-001 proposed content against PRD "
                f"baseline {baseline} |"
            ),
            re.sub(
                r"(?m)^\| Baseline revision \| [^|]+ \|$",
                f"| Baseline revision | {baseline} |",
                pcr.read_text(),
                count=1,
            ),
            count=1,
        ),
        encoding="utf-8",
    )


def test_adversarial_4_sha_and_git_revisions_are_fresh_for_all_three_gates(
    tmp_path: Path,
):
    discovery_root = repository(tmp_path / "discovery")
    discovery_readme = (
        discovery_root / "docs/discovery" / SLUG / "README.md"
    )
    discovery_commit = _git_commit(discovery_root, "discovery baseline")
    _replace_gate_revision(discovery_readme, f"git:{discovery_commit}")
    assert validate(discovery_root, "requirements").valid
    vision = (
        discovery_root / "docs/vision_of_product" / SLUG / f"{VP}.md"
    )
    vision.write_text(vision.read_text() + "\nChanged outcome state.\n")
    assert any(
        "stale or unverifiable" in item["message"]
        for item in validate(discovery_root, "requirements").findings
    )

    prd_root = repository(tmp_path / "prd", prd="prd-approved.md")
    prd = prd_root / "docs/requirements" / SLUG / "PRD.md"
    prd_commit = _git_commit(prd_root, "prd baseline")
    _replace_gate_revision(prd, f"git:{prd_commit}")
    assert validate(prd_root, "architecture").valid
    prd.write_text(
        prd.read_text().replace(
            "The fixture promises deterministic validation.",
            "The fixture promises changed validation.",
        )
    )
    assert any(
        "stale or unverifiable" in item["message"]
        for item in validate(prd_root, "architecture").findings
    )

    architecture_root = repository(
        tmp_path / "architecture-git",
        discovery=None,
        vision=False,
        architecture=True,
    )
    architecture = architecture_root / "docs/architecture/README.md"
    architecture_commit = _git_commit(
        architecture_root, "architecture baseline"
    )
    _replace_gate_revision(architecture, f"git:{architecture_commit}")
    assert validate(architecture_root, "planning").valid
    architecture.write_text(
        architecture.read_text().replace(
            "one bounded architecture component",
            "two changed architecture components",
        )
    )
    assert any(
        "deterministic architecture" in item["message"]
        for item in validate(architecture_root, "planning").findings
    )

    arbitrary = repository(tmp_path / "arbitrary")
    arbitrary_readme = arbitrary / "docs/discovery" / SLUG / "README.md"
    _replace_gate_revision(
        arbitrary_readme, "release-label dated 2026-09-05"
    )
    assert not validate(arbitrary, "requirements").valid


def test_adversarial_5_waiver_checks_all_material_and_named_invalidations(
    tmp_path: Path,
):
    for category in (
        "users",
        "outcomes",
        "integrations",
        "data sensitivity",
        "authority",
        "risk",
        "delivery",
    ):
        root = repository(
            tmp_path / category.replace(" ", "-"),
            discovery="discovery-waived.md",
        )
        result = validate(
            root,
            "requirements",
            as_of=datetime(2026, 9, 6, tzinfo=timezone.utc),
            occurred_invalidation_conditions=frozenset({category}),
        )
        assert not result.valid, category
        assert any(
            "material expansion" in item["message"]
            for item in result.findings
        )

    named = repository(
        tmp_path / "named", discovery="discovery-waived.md"
    )
    readme = named / "docs/discovery" / SLUG / "README.md"
    readme.write_text(
        readme.read_text().replace(
            "new integration, or authority-boundary change",
            "new integration, authority-boundary change, or contract termination",
        )
    )
    result = validate(
        named,
        "requirements",
        as_of=datetime(2026, 9, 6, tzinfo=timezone.utc),
        occurred_invalidation_conditions=frozenset({"contract termination"}),
    )
    assert not result.valid
    assert any(
        "contract termination" in item["message"] for item in result.findings
    )

    cli_root = repository(
        tmp_path / "cli-material", discovery="discovery-waived.md"
    )
    cli_result = cli.dispatch(
        [
            "validate",
            "gates",
            "--vp",
            VP,
            "--stage",
            "requirements",
            "--material-scope-expanded",
        ],
        probe_directory=cli_root,
    )
    assert cli_result.exit_code == exits.VALIDATION_FAILURE
    assert any(
        "material scope expansion" in item["message"]
        for item in cli_result.payload["findings"]
    )


def test_adversarial_6_architecture_rejects_incomplete_prd_and_stale_pcr(
    tmp_path: Path,
):
    malformed_root = repository(
        tmp_path / "malformed", prd="prd-approved.md"
    )
    malformed = (
        malformed_root / "docs/requirements" / SLUG / "PRD.md"
    )
    malformed.write_text(
        malformed.read_text().replace("## Success measures", "## Results")
    )
    _replace_gate_revision(
        malformed, gates._prd_revision(malformed.read_text())
    )
    result = validate(malformed_root, "architecture")
    assert not result.valid
    assert any("required sections" in item["message"] for item in result.findings)

    pcr_root = repository(tmp_path / "pcr", prd="prd-approved.md")
    prd = pcr_root / "docs/requirements" / SLUG / "PRD.md"
    baseline = re.search(
        r"(?m)^\| Source revision \| (sha256:[0-9a-f]{64}) \|$",
        prd.read_text(),
    ).group(1)
    pcr = prd.parent / "changes/PCR-001-change.md"
    pcr.parent.mkdir()
    values = {
        "Schema version": "1",
        "Requirement operation": "non-requirement",
        "Change": "Clarify reporting.",
        "Reason": "Clarity.",
        "Requestor": "Human product owner",
        "Affected PR": "None",
        "Affected QR": "None",
        "Affected decisions": "None",
        "Affected assumptions": "None",
        "Affected risks": "None",
        "Affected themes": "None",
        "Discovery impact": "None",
        "Architecture impact": "None",
        "Migration impact": "None",
        "Replanning impact": "None",
        "Supersedes": "None",
        "Human actor": "Human: product owner",
        "Human timestamp": "2026-09-06T10:00:00+01:00",
        "Human scope": (
            f"VP9 PCR-001 proposed content against PRD baseline {baseline}"
        ),
        "Human verdict": "Approved",
        "Human rationale": "Accepted.",
        "Baseline revision": baseline,
        "Source revision": "sha256:" + ("c" * 64),
    }
    pcr.write_text(
        "# PCR-001: Change\n\n| Field | Value |\n|---|---|\n"
        + "\n".join(f"| {field} | {values[field]} |" for field in gates.PCR_FIELDS)
        + "\n"
    )
    stale = validate(pcr_root, "architecture")
    assert not stale.valid
    assert any(
        item["record"] == "PCR-001" and "stale" in item["message"]
        for item in stale.findings
    )


@pytest.mark.parametrize(
    ("open_items", "next_action"),
    [
        ("None", "None"),
        ("<open-items>", "<next-action>"),
        ("", ""),
    ],
)
def test_adversarial_7_paused_state_requires_items_and_action(
    tmp_path: Path,
    open_items: str,
    next_action: str,
):
    root = repository(tmp_path, discovery="discovery-working.md")
    readme = root / "docs/discovery" / SLUG / "README.md"
    text = re.sub(
        r"(?m)^\| Open items \|.*$",
        f"| Open items | {open_items} |",
        readme.read_text(),
    )
    text = re.sub(
        r"(?m)^\| Next action \|.*$",
        f"| Next action | {next_action} |",
        text,
    )
    readme.write_text(text)

    discovery = validate(root, "discovery")
    requirements = validate(root, "requirements")

    assert discovery.valid
    assert discovery.payload["stage_entry"] == "open"
    assert discovery.payload["downstream_gate"]["status"] == "closed"
    assert discovery.payload["completion_findings"]
    assert not requirements.valid
    assert requirements.payload["stage_entry"] == "closed"
    assert any(
        item["record"] == "working-state" for item in requirements.findings
    )


def test_exact_authority_rejects_parenthetical_spoof_and_keeps_registered_roles(
    tmp_path: Path,
):
    for actor in ("Human: product owner", "Human: designer"):
        root = repository(tmp_path / actor.rsplit(" ", 1)[-1])
        readme = root / "docs/discovery" / SLUG / "README.md"
        readme.write_text(
            readme.read_text().replace("Human: product owner", actor)
        )
        revision = gates._discovery_revision(
            vision=root / "docs/vision_of_product" / SLUG / f"{VP}.md",
            dossier=readme.parent,
            root=root,
        )
        _replace_gate_revision(readme, str(revision))
        assert validate(root, "requirements").valid

    spoofed = repository(tmp_path / "spoofed")
    readme = spoofed / "docs/discovery" / SLUG / "README.md"
    readme.write_text(
        readme.read_text().replace(
            "Human: product owner",
            "Human: product owner (discovery-facilitator)",
        )
    )
    result = validate(spoofed, "requirements")
    assert not result.valid
    assert any("Qualifiers" in item["remediation"] for item in result.findings)


def _copy_vp3_gate_sources(root: Path) -> None:
    for relative in (
        "docs/vision_of_product/VP3-discovery-led-cost-aware-methodology",
        "docs/discovery/VP3-discovery-led-cost-aware-methodology",
        "docs/requirements/VP3-discovery-led-cost-aware-methodology",
        "docs/architecture",
        "docs/ADRs",
    ):
        source = ROOT / relative
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target)


@pytest.mark.parametrize(
    ("stage", "relative", "mutation", "current_valid"),
    [
        (
            "requirements",
            "docs/discovery/VP3-discovery-led-cost-aware-methodology/"
            "architecture-handoff.md",
            "\nMutated accepted content.\n",
            True,
        ),
        (
            "architecture",
            "docs/requirements/VP3-discovery-led-cost-aware-methodology/PRD.md",
            "rename-section",
            True,
        ),
        (
            "planning",
            "docs/architecture/components.md",
            "\n## Appended architecture\n\nChanged.\n",
            True,
        ),
    ],
)
def test_pinned_vp3_legacy_allowlist_rejects_every_artifact_drift(
    tmp_path: Path,
    stage: str,
    relative: str,
    mutation: str,
    current_valid: bool,
):
    _copy_vp3_gate_sources(tmp_path)
    current = gates.validate_repository(tmp_path, vp="VP3", stage=stage)
    assert current.valid is current_valid
    if not current_valid:
        assert any(
            "Architecture Source revision is stale" in item["message"]
            for item in current.findings
        )
    target = tmp_path / relative
    if mutation == "rename-section":
        target.write_text(
            target.read_text().replace(
                "## 11. Success measures",
                "## 11. Renamed success measures",
            )
        )
    else:
        target.write_text(target.read_text() + mutation)

    drifted = gates.validate_repository(tmp_path, vp="VP3", stage=stage)

    assert not drifted.valid
    assert any(
        "revision" in item["message"].casefold()
        or "schema" in item["message"].casefold()
        for item in drifted.findings
    )


def test_pinned_vp3_prd_allowlist_rejects_appended_pcr(tmp_path: Path):
    _copy_vp3_gate_sources(tmp_path)
    changes = (
        tmp_path
        / "docs/requirements/VP3-discovery-led-cost-aware-methodology/changes"
    )
    changes.mkdir()
    (changes / "PCR-001-change.md").write_text(
        "# PCR-001: Unapproved mutation\n"
    )

    result = gates.validate_repository(
        tmp_path, vp="VP3", stage="architecture"
    )

    assert not result.valid
    assert any(item["record"] == "PCR-001" for item in result.findings)


def test_waiver_behavior_occurrence_and_no_impact_pcr_both_invalidate(
    tmp_path: Path,
):
    occurred_root = repository(
        tmp_path / "occurred", discovery="discovery-waived.md"
    )
    occurred = validate(
        occurred_root,
        "requirements",
        as_of=datetime(2026, 9, 6, tzinfo=timezone.utc),
        occurred_invalidation_conditions=frozenset({"behavior"}),
    )
    assert not occurred.valid
    assert any("behavior" in item["message"] for item in occurred.findings)

    pcr_root = repository(
        tmp_path / "pcr",
        discovery="discovery-waived.md",
        prd="prd-approved.md",
    )
    _write_add_pcr(pcr_root, all_impacts_none=True)
    invalidated = validate(
        pcr_root,
        "requirements",
        as_of=datetime(2026, 9, 6, tzinfo=timezone.utc),
    )
    assert not invalidated.valid
    assert any(
        "PCR behavior/scope change" in item["message"]
        and "None impact" in item["remediation"]
        for item in invalidated.findings
    )

    dossier = pcr_root / "docs/discovery" / SLUG
    waiver_revision = gates._discovery_revision(
        vision=pcr_root / "docs/vision_of_product" / SLUG / f"{VP}.md",
        dossier=dossier,
        requirements=pcr_root / "docs/requirements" / SLUG,
        root=pcr_root,
    )
    _replace_gate_revision(dossier / "README.md", str(waiver_revision))
    assert validate(
        pcr_root,
        "requirements",
        as_of=datetime(2026, 9, 6, tzinfo=timezone.utc),
    ).valid


def test_waiver_covers_exact_effective_non_requirement_pcr_state(
    tmp_path: Path,
):
    root = repository(
        tmp_path,
        discovery="discovery-waived.md",
        prd="prd-approved.md",
    )
    first = _write_metadata_only_pcr(
        root, pcr_number=1, affected_pr="PR-001"
    )

    stale = validate(
        root,
        "requirements",
        as_of=datetime(2026, 9, 6, tzinfo=timezone.utc),
    )

    assert not stale.valid
    assert any(
        "PCR behavior/scope change" in item["message"]
        and "PCR-001" in item["message"]
        for item in stale.findings
    )

    second = _write_metadata_only_pcr(
        root,
        pcr_number=2,
        affected_pr="PR-001",
        supersedes="PCR-001",
    )
    assert gates._approved_behavior_pcr_paths(
        root / "docs/requirements" / SLUG, root
    ) == [second]
    assert first not in gates._approved_behavior_pcr_paths(
        root / "docs/requirements" / SLUG, root
    )

    dossier = root / "docs/discovery" / SLUG
    refreshed = gates._discovery_revision(
        vision=root / "docs/vision_of_product" / SLUG / f"{VP}.md",
        dossier=dossier,
        requirements=root / "docs/requirements" / SLUG,
        root=root,
    )
    _replace_gate_revision(dossier / "README.md", str(refreshed))

    assert validate(
        root,
        "requirements",
        as_of=datetime(2026, 9, 6, tzinfo=timezone.utc),
    ).valid


def test_rejected_non_requirement_pcr_does_not_invalidate_waiver(
    tmp_path: Path,
):
    root = repository(
        tmp_path,
        discovery="discovery-waived.md",
        prd="prd-approved.md",
    )
    _write_metadata_only_pcr(
        root,
        pcr_number=1,
        affected_pr="PR-001",
        verdict="Rejected",
    )

    assert gates._approved_behavior_pcr_paths(
        root / "docs/requirements" / SLUG, root
    ) == []
    assert validate(
        root,
        "requirements",
        as_of=datetime(2026, 9, 6, tzinfo=timezone.utc),
    ).valid


@pytest.mark.parametrize(
    "invalidity",
    ["stale-source", "invalid-authority", "invalid-row"],
)
def test_invalid_approved_pcr_does_not_affect_waiver_applicability(
    tmp_path: Path,
    invalidity: str,
):
    root = repository(
        tmp_path,
        discovery="discovery-waived.md",
        prd="prd-approved.md",
    )
    pcr = _write_add_pcr(
        root,
        traces="None" if invalidity == "invalid-row" else "VO-001",
    )
    if invalidity == "stale-source":
        pcr.write_text(
            re.sub(
                r"(?m)^\| Source revision \| sha256:[0-9a-f]{64} \|$",
                f"| Source revision | sha256:{'0' * 64} |",
                pcr.read_text(),
            )
        )
    elif invalidity == "invalid-authority":
        pcr.write_text(
            pcr.read_text().replace(
                "| Human actor | Human: product owner |",
                "| Human actor | requirements-facilitator |",
            )
        )

    assert gates._approved_behavior_pcr_paths(
        root / "docs/requirements" / SLUG, root
    ) == []
    assert validate(
        root,
        "requirements",
        as_of=datetime(2026, 9, 6, tzinfo=timezone.utc),
    ).valid


def test_valid_applicable_approved_pcr_invalidates_stale_waiver(
    tmp_path: Path,
):
    root = repository(
        tmp_path,
        discovery="discovery-waived.md",
        prd="prd-approved.md",
    )
    pcr = _write_add_pcr(root)

    assert gates._approved_behavior_pcr_paths(
        root / "docs/requirements" / SLUG, root
    ) == [pcr]
    result = validate(
        root,
        "requirements",
        as_of=datetime(2026, 9, 6, tzinfo=timezone.utc),
    )
    assert not result.valid
    assert any(
        item["record"] == "discovery-readiness"
        and "PCR behavior/scope change" in item["message"]
        and "PCR-001" in item["message"]
        for item in result.findings
    )


@pytest.mark.parametrize(
    ("baseline_state", "expected_gate_message"),
    [
        ("malformed", "not an immutable accepted revision"),
        ("unapproved", "does not approve architecture entry"),
        ("stale", "stale or unverifiable"),
    ],
)
def test_pcr_is_not_applicable_when_its_prd_baseline_gate_is_invalid(
    tmp_path: Path,
    baseline_state: str,
    expected_gate_message: str,
):
    root = repository(
        tmp_path,
        discovery="discovery-waived.md",
        prd="prd-approved.md",
    )
    prd = root / "docs/requirements" / SLUG / "PRD.md"
    pcr = _write_add_pcr(root)

    if baseline_state == "unapproved":
        prd.write_text(
            prd.read_text().replace(
                "| Verdict | Approved |", "| Verdict | Rejected |"
            ),
            encoding="utf-8",
        )
    else:
        invalid_baseline = (
            "mutable-main"
            if baseline_state == "malformed"
            else "sha256:" + ("0" * 64)
        )
        _replace_prd_and_pcr_baseline(prd, pcr, invalid_baseline)

    assert gates._approved_behavior_pcr_paths(
        root / "docs/requirements" / SLUG, root
    ) == []
    assert validate(
        root,
        "requirements",
        as_of=datetime(2026, 9, 6, tzinfo=timezone.utc),
    ).valid

    architecture = validate(root, "architecture")
    assert not architecture.valid
    assert any(
        item["record"] == "prd-approval"
        and expected_gate_message in item["message"]
        for item in architecture.findings
    )


def test_pcr_is_applicable_when_its_prd_baseline_gate_is_fully_valid(
    tmp_path: Path,
):
    root = repository(
        tmp_path,
        discovery="discovery-waived.md",
        prd="prd-approved.md",
    )
    pcr = _write_add_pcr(root)

    assert gates._approved_behavior_pcr_paths(
        root / "docs/requirements" / SLUG, root
    ) == [pcr]


def test_non_requirement_pcr_accepts_existing_effective_pr_and_qr(
    tmp_path: Path,
):
    root = repository(tmp_path, prd="prd-approved.md")
    _write_metadata_only_pcr(
        root,
        pcr_number=1,
        affected_pr="PR-001",
        affected_qr="QR-001",
    )

    assert validate(root, "architecture").valid


@pytest.mark.parametrize(
    ("affected_pr", "affected_qr", "expected"),
    [
        ("PR-999", "None", "PR-999"),
        ("PR-001", "QR-999", "QR-999"),
    ],
)
def test_non_requirement_pcr_rejects_dangling_affected_requirement(
    tmp_path: Path,
    affected_pr: str,
    affected_qr: str,
    expected: str,
):
    root = repository(tmp_path, prd="prd-approved.md")
    _write_metadata_only_pcr(
        root,
        pcr_number=1,
        affected_pr=affected_pr,
        affected_qr=affected_qr,
    )

    result = validate(root, "architecture")

    assert not result.valid
    assert any(
        item["record"] == "PCR-001"
        and "immediately prior effective requirement state" in item["message"]
        and expected in item["message"]
        for item in result.findings
    )


def test_non_requirement_pcr_rejects_removed_affected_requirement(
    tmp_path: Path,
):
    root = repository(tmp_path, prd="prd-approved.md")
    _write_metadata_only_pcr(
        root,
        pcr_number=1,
        operation="remove",
        affected_pr="PR-001",
        supersedes="PR-001",
    )
    _write_metadata_only_pcr(
        root, pcr_number=2, affected_pr="PR-001"
    )

    result = validate(root, "architecture")

    assert not result.valid
    assert any(
        item["record"] == "PCR-002"
        and "immediately prior effective requirement state" in item["message"]
        and "PR-001" in item["message"]
        for item in result.findings
    )


def test_non_requirement_pcr_rejects_rejected_only_affected_requirement(
    tmp_path: Path,
):
    root = repository(tmp_path, prd="prd-approved.md")
    _write_add_pcr(
        root,
        pcr_number=1,
        requirement_id="PR-002",
        verdict="Rejected",
    )
    _write_metadata_only_pcr(
        root, pcr_number=2, affected_pr="PR-002"
    )

    result = validate(root, "architecture")

    assert not result.valid
    assert any(
        item["record"] == "PCR-002"
        and "immediately prior effective requirement state" in item["message"]
        and "PR-002" in item["message"]
        for item in result.findings
    )


def test_non_requirement_pcr_rejects_merely_proposed_affected_requirement(
    tmp_path: Path,
):
    root = repository(tmp_path, prd="prd-approved.md")
    _write_add_pcr(
        root,
        pcr_number=1,
        requirement_id="PR-002",
        affected_requirement_id="PR-001",
    )
    _write_metadata_only_pcr(
        root, pcr_number=2, affected_pr="PR-002"
    )

    result = validate(root, "architecture")

    assert not result.valid
    assert any(
        item["record"] == "PCR-002"
        and "immediately prior effective requirement state" in item["message"]
        and "PR-002" in item["message"]
        for item in result.findings
    )


def test_non_requirement_pcr_rejects_stale_source_approved_add_id(
    tmp_path: Path,
):
    root = repository(tmp_path, prd="prd-approved.md")
    stale = _write_add_pcr(
        root,
        pcr_number=1,
        requirement_id="PR-002",
    )
    stale.write_text(
        re.sub(
            r"(?m)^\| Source revision \| sha256:[0-9a-f]{64} \|$",
            f"| Source revision | sha256:{'0' * 64} |",
            stale.read_text(),
        )
    )
    _write_add_pcr(
        root,
        pcr_number=2,
        requirement_id="PR-003",
    )
    _write_metadata_only_pcr(
        root,
        pcr_number=3,
        affected_pr="PR-002",
    )

    result = validate(root, "architecture")

    assert not result.valid
    assert any(
        item["record"] == "PCR-001"
        and "Source revision is stale" in item["message"]
        for item in result.findings
    )
    assert not any(
        item["record"] == "PR-003"
        and "deterministic next ID" in item["message"]
        for item in result.findings
    )
    assert any(
        item["record"] == "PCR-003"
        and "immediately prior effective requirement state" in item["message"]
        and "PR-002" in item["message"]
        for item in result.findings
    )


def test_non_requirement_pcr_rejects_invalid_authority_approved_add_id(
    tmp_path: Path,
):
    root = repository(tmp_path, prd="prd-approved.md")
    invalid = _write_add_pcr(
        root,
        pcr_number=1,
        requirement_id="PR-002",
    )
    invalid.write_text(
        invalid.read_text().replace(
            "| Human actor | Human: product owner |",
            "| Human actor | requirements-facilitator |",
        )
    )
    _write_metadata_only_pcr(
        root,
        pcr_number=2,
        affected_pr="PR-002",
    )

    result = validate(root, "architecture")

    assert not result.valid
    assert any(
        item["record"] == "PCR-001"
        and "not an allowed accountable human authority" in item["message"]
        for item in result.findings
    )
    assert any(
        item["record"] == "PCR-002"
        and "immediately prior effective requirement state" in item["message"]
        and "PR-002" in item["message"]
        for item in result.findings
    )


def test_non_requirement_pcr_rejects_invalid_row_approved_add_id(
    tmp_path: Path,
):
    root = repository(tmp_path, prd="prd-approved.md")
    _write_add_pcr(
        root,
        pcr_number=1,
        requirement_id="PR-002",
        traces="None",
    )
    _write_metadata_only_pcr(
        root,
        pcr_number=2,
        affected_pr="PR-002",
    )

    result = validate(root, "architecture")

    assert not result.valid
    assert any(
        item["record"] == "PR-002"
        and "None, malformed, dangling" in item["message"]
        for item in result.findings
    )
    assert any(
        item["record"] == "PCR-002"
        and "immediately prior effective requirement state" in item["message"]
        and "PR-002" in item["message"]
        for item in result.findings
    )


def test_pcr_proposed_row_rejects_gapped_id_banana_impact_and_none_trace(
    tmp_path: Path,
):
    root = repository(tmp_path, prd="prd-approved.md")
    _write_add_pcr(
        root,
        requirement_id="PR-003",
        impact="banana",
        traces="None",
    )

    result = validate(root, "architecture")

    assert not result.valid
    messages = [item["message"] for item in result.findings]
    assert any("deterministic next ID PR-002" in message for message in messages)
    assert any("invalid Impact 'banana'" in message for message in messages)
    assert any("None, malformed, dangling" in message for message in messages)


def test_active_prd_working_state_blocks_architecture_after_digest_refresh(
    tmp_path: Path,
):
    root = repository(tmp_path, prd="prd-approved.md")
    prd = root / "docs/requirements" / SLUG / "PRD.md"
    prd.write_text(
        prd.read_text()
        + "\n## Working state\n\n"
        "| Field | Value |\n"
        "|---|---|\n"
        "| Status | awaiting-human |\n"
        "| Open items | PR-002 (owner: product owner) |\n"
        "| Accepted so far | PR-001, QR-001 |\n"
        "| Next action | Actor: product owner; Action: decide PR-002 wording; "
        "Intended result: approve measurable requirement text |\n"
    )
    _replace_gate_revision(prd, gates._prd_revision(prd.read_text()))

    result = validate(root, "architecture")

    assert not result.valid
    assert result.payload["working_states"]["prd"] == {
        "status": "awaiting-human",
        "open_items": ["PR-002 (owner: product owner)"],
        "accepted_so_far": ["PR-001", "QR-001"],
        "next_action": (
            "Actor: product owner; Action: decide PR-002 wording; "
            "Intended result: approve measurable requirement text"
        ),
    }
    assert any(
        item["record"] == "prd-working-state"
        and "PR-002 (owner: product owner)" in item["message"]
        and "Next action:" in item["message"]
        for item in result.findings
    )


@pytest.mark.parametrize(
    ("open_items", "next_action"),
    [
        (
            "draft requirement (owner: product owner)",
            "Actor: product owner; Action: define the requirement; "
            "Intended result: produce measurable text",
        ),
        (
            "PR-002 (owner: TBD)",
            "Actor: product owner; Action: define the requirement; "
            "Intended result: produce measurable text",
        ),
        (
            "PR-002 (owner: product owner)",
            "review",
        ),
    ],
)
def test_prd_working_state_rejects_unstable_unowned_or_vague_progress(
    tmp_path: Path,
    open_items: str,
    next_action: str,
):
    root = repository(tmp_path, prd="prd-approved.md")
    prd = root / "docs/requirements" / SLUG / "PRD.md"
    prd.write_text(
        prd.read_text()
        + "\n## Working state\n\n"
        "| Field | Value |\n"
        "|---|---|\n"
        "| Status | in-progress |\n"
        f"| Open items | {open_items} |\n"
        "| Accepted so far | PR-001 |\n"
        f"| Next action | {next_action} |\n"
    )
    _replace_gate_revision(prd, gates._prd_revision(prd.read_text()))

    result = validate(root, "architecture")

    assert not result.valid
    assert any(
        item["record"] == "working-state" for item in result.findings
    )
