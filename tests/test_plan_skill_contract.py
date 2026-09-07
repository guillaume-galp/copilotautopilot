"""Contract and gate-integration tests for TH3.E3.US6 two-stage plan."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from methodlib import cli, exits, gates  # noqa: E402


PLAN = ROOT / ".github" / "skills" / "plan" / "SKILL.md"
ARCHITECT = ROOT / ".github" / "agents" / "architect.agent.md"
PRODUCT_OWNER = ROOT / ".github" / "agents" / "product-owner.agent.md"
FIXTURES = ROOT / "tests" / "fixtures" / "method_gates"
VP = "VP9"
SLUG = "VP9-fixture"


def section(text: str, heading: str) -> str:
    match = re.search(
        rf"^{re.escape(heading)}\n(?P<body>.*?)(?=^#{{1,6}} |\Z)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match, f"missing section {heading}"
    return match.group("body")


def normalized(text: str) -> str:
    return " ".join(text.split())


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def architecture_repository(root: Path, *, heading: str | None = "Approval") -> Path:
    target = root / "docs" / "architecture" / "README.md"
    target.parent.mkdir(parents=True)
    if heading is None:
        text = "# Architecture\n\n## Components\n\nNo accepted checkpoint.\n"
    else:
        text = fixture("architecture-accepted.md").replace(
            "## Approval", f"## {heading}", 1
        )
    target.write_text(text, encoding="utf-8")
    if heading is not None:
        revision = gates._architecture_revision(root, target)
        target.write_text(
            re.sub(
                r"(?m)^\| Source revision \| [^|]+ \|$",
                f"| Source revision | {revision} |",
                target.read_text(encoding="utf-8"),
                count=1,
            ),
            encoding="utf-8",
        )
    return root


def stage_one_repository(
    root: Path,
    *,
    prd: str | None = "prd-approved.md",
    prd_verdict: str = "Approved",
) -> Path:
    vision = root / "docs" / "vision_of_product" / SLUG / f"{VP}.md"
    vision.parent.mkdir(parents=True)
    vision.write_text(
        "# VP9 Fixture\n\n"
        "## Outcomes\n\n"
        "| ID | Outcome |\n"
        "|---|---|\n"
        "| VO-001 | Validate lifecycle entry safely. |\n",
        encoding="utf-8",
    )

    discovery = root / "docs" / "discovery" / SLUG / "README.md"
    discovery.parent.mkdir(parents=True)
    discovery.write_text(fixture("discovery-ready.md"), encoding="utf-8")
    discovery_revision = gates._discovery_revision(
        vision=vision,
        dossier=discovery.parent,
        root=root,
    )
    assert discovery_revision is not None
    discovery.write_text(
        re.sub(
            r"(?m)^\| Source revision \| [^|]+ \|$",
            f"| Source revision | {discovery_revision} |",
            discovery.read_text(encoding="utf-8"),
            count=1,
        ),
        encoding="utf-8",
    )

    if prd is not None:
        target = root / "docs" / "requirements" / SLUG / "PRD.md"
        target.parent.mkdir(parents=True)
        text = fixture(prd)
        text = re.sub(
            r"(?m)^\| Discovery source revision \| [^|]+ \|$",
            f"| Discovery source revision | {discovery_revision} |",
            text,
            count=1,
        )
        text = text.replace("| Verdict | Approved |", f"| Verdict | {prd_verdict} |")
        target.write_text(text, encoding="utf-8")
        revision = gates._prd_revision(target.read_text(encoding="utf-8"))
        target.write_text(
            re.sub(
                r"(?m)^\| Source revision \| [^|]+ \|$",
                f"| Source revision | {revision} |",
                target.read_text(encoding="utf-8"),
                count=1,
            ),
            encoding="utf-8",
        )
    return root


def test_ac1_and_ac9_dispatch_architect_only_after_both_exact_gates_open(
    tmp_path: Path,
):
    barrier = normalized(section(PLAN.read_text(), "## Stage 1 Entry Barrier"))
    result = cli.dispatch(
        [
            "validate",
            "gates",
            "--vp",
            VP,
            "--stage",
            "architecture",
        ],
        probe_directory=stage_one_repository(tmp_path),
    )

    assert result.exit_code == exits.SUCCESS
    assert result.payload["stage_entry"] == "open"
    assert [
        gate["name"] for gate in result.payload["upstream_gates"]
    ] == ["discovery-readiness", "prd-approval"]
    assert all(
        gate["status"] == "open"
        for gate in result.payload["upstream_gates"]
    )
    assert "do not dispatch `@architect`" in barrier
    assert "Validate both records independently even when one fails" in barrier
    assert (
        PLAN.read_text().index(
            "method validate gates --vp <vp> --stage architecture"
        )
        < PLAN.read_text().index(
            "After the barrier passes, dispatch `@architect`"
        )
    )


@pytest.mark.parametrize(
    ("prd", "verdict"),
    [(None, "Approved"), ("prd-approved.md", "Rejected")],
)
def test_ac1_and_error_case_missing_or_unaccepted_prd_exit_two_and_name_gate(
    tmp_path: Path,
    prd: str | None,
    verdict: str,
):
    result = cli.dispatch(
        [
            "validate",
            "gates",
            "--vp",
            VP,
            "--stage",
            "architecture",
        ],
        probe_directory=stage_one_repository(
            tmp_path, prd=prd, prd_verdict=verdict
        ),
    )

    assert result.exit_code == exits.VALIDATION_FAILURE == 2
    assert result.payload["stage_entry"] == "closed"
    assert any(
        finding["record"] == "prd-approval"
        for finding in result.payload["findings"]
    )


def test_ac2_stage_one_write_set_stops_at_human_checkpoint():
    boundary = normalized(
        section(PLAN.read_text(), "## Stage 1 Architecture Boundary")
    )

    assert "The complete stage 1 write set is" in boundary
    assert "`docs/architecture/`" in boundary
    assert "`docs/ADRs/`" in boundary
    for forbidden in (
        "theme",
        "epic",
        "story",
        "issue template",
        "planning-admission record",
        "`docs/plan/backlog.yaml` entry",
    ):
        assert forbidden in boundary
    assert "stop at the human architecture checkpoint" in boundary
    assert "Do not continue to stage 2 in the same uninterrupted run" in boundary


def test_resume_skips_accepted_stage_one_and_starts_with_planning_gate(
    tmp_path: Path,
):
    result = cli.dispatch(
        ["validate", "gates", "--vp", VP, "--stage", "planning"],
        probe_directory=architecture_repository(tmp_path),
    )
    resume = normalized(
        section(PLAN.read_text(), "## Scope Resolution and Invocation Mode")
    )

    assert result.exit_code == exits.SUCCESS
    assert result.payload["stage_entry"] == "open"
    assert result.payload["upstream_gates"][0]["name"] == (
        "architecture-acceptance"
    )
    assert "first run the exact planning-gate command" in resume
    assert "skip stage 1 and `@architect` completely" in resume
    assert "continue at stage 2" in resume


def test_ac3_missing_architecture_approval_exits_two_with_named_finding(
    tmp_path: Path,
):
    result = cli.dispatch(
        ["validate", "gates", "--vp", VP, "--stage", "planning"],
        probe_directory=architecture_repository(tmp_path, heading=None),
    )

    assert result.exit_code == exits.VALIDATION_FAILURE == 2
    assert result.payload["stage_entry"] == "closed"
    finding = next(
        item
        for item in result.payload["findings"]
        if item["record"] == "architecture-acceptance"
    )
    assert "## Approval gate record is missing" in finding["message"]


def test_ac3_and_ac8_prospective_acceptance_requires_approval_heading(
    tmp_path: Path,
):
    result = cli.dispatch(
        ["validate", "gates", "--vp", VP, "--stage", "planning"],
        probe_directory=architecture_repository(
            tmp_path, heading="Acceptance"
        ),
    )
    checkpoint = normalized(
        section(ARCHITECT.read_text(), "## Output and Human Checkpoint")
    )

    assert result.exit_code == exits.VALIDATION_FAILURE == 2
    assert any(
        item["record"] == "architecture-acceptance"
        and "Canonical ## Approval" in item["message"]
        for item in result.payload["findings"]
    )
    assert "exactly one canonical `## Approval` gate table" in checkpoint
    assert "only verdict `Accepted` opens planning" in checkpoint
    assert "Never infer, recommend as final, or self-issue acceptance" in checkpoint


def test_ac4_planning_gate_and_schema_both_precede_admission():
    text = PLAN.read_text()
    barrier = normalized(section(text, "## Stage 2 Entry Barrier"))
    admission = normalized(
        section(text, "## Stage 2 Numbering, Schema, and Admission")
    )

    planning_command = "method validate gates --vp <vp> --stage planning"
    schema_command = "method validate schema"
    admission_phrase = (
        "Only after that schema pass may `@product-owner` issue the canonical"
    )
    assert text.count(planning_command) == 1
    assert text.count(schema_command) == 1
    assert "Before reading backlog content for planning" in barrier
    assert "perform no planning work and do not delegate" in barrier
    assert text.index(planning_command) < text.index(schema_command)
    assert text.index(schema_command) < text.index(admission_phrase)
    assert "create no `Accepted` planning-admission record" in admission
    assert "exit with code `2`" in admission


def test_product_owner_independently_revalidates_planning_gate_and_fails_closed():
    process = normalized(section(PRODUCT_OWNER.read_text(), "## Process"))
    command = "method validate gates --vp <vp> --stage planning"

    assert "Verify the gate independently" in process
    assert command in process
    assert "never trust or reuse a `plan` report as proof" in process
    for field in (
        "`command: validate`",
        "`check: gates`",
        "`status: ok`",
        "`stage: planning`",
        "`stage_entry: open`",
        "`findings: []`",
        "exactly one open `architecture-acceptance` upstream gate",
    ):
        assert field in process
    assert "fail closed with exit code `2`" in process
    assert "perform no writes" in process


def test_ac5_theme_allocation_is_append_only_and_schema_v2():
    plan = normalized(
        section(PLAN.read_text(), "## Stage 2 Numbering, Schema, and Admission")
    )
    product_owner = normalized(PRODUCT_OWNER.read_text())

    assert "greatest numeric theme ID ever allocated" in plan
    assert "`TH<greatest+1>`" in plan
    for prohibited in (
        "derive it from the VP number",
        "fill a gap",
        "reuse an archived/deleted number",
        "repurpose an existing theme",
    ):
        assert prohibited in plan
    assert "Every new theme declares `schema-version: 2`" in plan
    assert "every unlocked theme touched by planning" in plan
    assert "declares `schema-version: 2`" in product_owner


def test_product_owner_uses_canonical_theme_directory_for_all_planning_paths():
    text = PRODUCT_OWNER.read_text()

    for path in (
        "docs/themes/TH<n>-<slug>/README.md",
        "docs/themes/TH<n>-<slug>/epics/E<m>-<slug>/README.md",
        (
            "docs/themes/TH<n>-<slug>/epics/E<m>-<slug>/stories/"
            "US<l>-<slug>.md"
        ),
        "docs/themes/TH<n>-<slug>/epics/E<m>-<slug>/stories/",
    ):
        assert path in text
    assert "docs/themes/TH<n>/" not in text
    assert "docs/themes/TH<n>-<name>" not in text


def test_product_owner_archives_completed_templates_before_any_new_theme_write():
    process = normalized(section(PRODUCT_OWNER.read_text(), "## Process"))

    allocate = process.index("Allocate the theme number")
    archive = process.index("Archive completed-theme templates first")
    create_theme = process.index("Create the theme")
    create_epics = process.index("Break into epics")
    create_stories = process.index("Write user stories")
    create_templates = process.index("Generate issue templates")

    assert allocate < archive
    assert archive < min(
        create_theme,
        create_epics,
        create_stories,
        create_templates,
    )
    assert (
        "before creating any new-theme directory, artefact, backlog entry, "
        "or issue template"
    ) in process


def test_ac6_architect_accepts_only_accepted_dossier_and_approved_prd():
    inputs = normalized(
        section(ARCHITECT.read_text(), "## Accepted Inputs and Fail-Closed Entry")
    )

    assert "Accept exactly one same-number, same-slug input pair" in inputs
    assert "human-accepted Discovery dossier" in inputs
    assert "human-approved effective PRD" in inputs
    assert "method validate gates --vp <vp> --stage architecture" in inputs
    assert "exactly two open upstream records" in inputs
    assert "`discovery-readiness`" in inputs
    assert "`prd-approval`" in inputs
    assert "refuse to start, perform no writes" in inputs
    assert "exit with code `2`" in inputs
    assert "A vision directory alone is not an accepted input" in inputs


def test_ac7_orphan_invariant_is_rejected_with_named_finding():
    barrier = normalized(
        section(ARCHITECT.read_text(), "## PRD-Backed Invariant Barrier")
    )

    assert (
        "Architecture formalizes accepted PRD requirements into named "
        "`INV-###` technical invariants recorded in `docs/architecture/`"
    ) in barrier
    assert "may not introduce" in barrier
    assert "absent from the effective approved PRD" in barrier
    assert "enumerate every proposed or changed architecture `INV-###`" in barrier
    assert "existing effective `PR-###` or `QR-###`" in barrier
    assert "not a substitute for a PRD requirement reference" in barrier
    assert "reject it as an introduced requirement" in barrier
    assert "`architecture-invariant` finding" in barrier
    assert "record names the `INV-###`" in barrier
    assert "`missing PRD requirement reference`" in barrier
    assert "do not prepare the checkpoint" in barrier
    assert "PRD-owned `VO-###` and Discovery-owned `DEF-###`" in barrier


def test_ac8_architect_output_is_architecture_and_adrs_only():
    output = normalized(
        section(ARCHITECT.read_text(), "## Output and Human Checkpoint")
    )

    for allowed in (
        "`docs/architecture/README.md`",
        "`docs/architecture/tech-stack.md`",
        "`docs/architecture/components.md`",
        "`docs/architecture/data-model.md`",
        "`docs/architecture/project-setup.md`",
        "`docs/ADRs/ADR-<NNN>-<slug>.md`",
    ):
        assert allowed in output
    assert "stop at the human architecture checkpoint" in output
    assert "return control to `plan`" in output
    assert "Never invoke `@product-owner`" in output
    for forbidden in (
        "theme",
        "epic",
        "story",
        "issue template",
        "planning-admission record",
        "backlog entry",
    ):
        assert forbidden in output
