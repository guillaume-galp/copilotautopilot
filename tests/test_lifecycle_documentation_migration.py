"""Contract tests for the TH3.E4.US3 documentation-only migration."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
INSTRUCTIONS = ROOT / ".github" / "copilot-instructions.md"
CANONICAL = (
    ROOT / ".github" / "skills" / "the-copilot-build-method" / "SKILL.md"
)
KICKSTART = ROOT / ".github" / "skills" / "kickstart" / "SKILL.md"
INVENTORY = (
    ROOT / "docs" / "plan" / "TH3.E4.US3-lifecycle-migration-inventory.md"
)

EXPECTED_ACTIVE_FILES = {
    "README.md": "migrated",
    ".github/copilot-instructions.md": "migrated",
    ".github/skills/architecture-decisions/SKILL.md": "already-consistent",
    ".github/skills/autopilot/SKILL.md": "already-consistent",
    ".github/skills/backlog-management/SKILL.md": "already-consistent",
    ".github/skills/bdd-stories/SKILL.md": "already-consistent",
    ".github/skills/code-quality/SKILL.md": "already-consistent",
    ".github/skills/discover/SKILL.md": "already-consistent",
    ".github/skills/discovery-dossier/SKILL.md": "already-consistent",
    ".github/skills/gitflow-operator/SKILL.md": "already-consistent",
    ".github/skills/kickstart/SKILL.md": "migrated",
    ".github/skills/plan/SKILL.md": "already-consistent",
    ".github/skills/product-requirements/SKILL.md": "already-consistent",
    ".github/skills/requirements/SKILL.md": "already-consistent",
    ".github/skills/the-copilot-build-method/SKILL.md": "already-consistent",
    ".github/agents/README.md": "already-consistent",
    ".github/agents/architect.agent.md": "already-consistent",
    ".github/agents/developer.agent.md": "already-consistent",
    ".github/agents/discovery-facilitator.agent.md": "already-consistent",
    ".github/agents/investigator.agent.md": "already-consistent",
    ".github/agents/orchestrator.agent.md": "already-consistent",
    ".github/agents/product-owner.agent.md": "already-consistent",
    ".github/agents/requirements-facilitator.agent.md": "already-consistent",
    ".github/agents/reviewer.agent.md": "already-consistent",
    ".github/agents/troubleshooter.agent.md": "already-consistent",
}


def active_instruction_files() -> list[Path]:
    """Return every non-archived skill and top-level agent instruction file."""

    return sorted((ROOT / ".github" / "skills").glob("*/SKILL.md")) + sorted(
        (ROOT / ".github" / "agents").glob("*.md")
    )


def marked_section(text: str, name: str) -> str:
    match = re.search(
        rf"<!-- {re.escape(name)}:start -->"
        rf"(?P<body>.*?)"
        rf"<!-- {re.escape(name)}:end -->",
        text,
        flags=re.DOTALL,
    )
    assert match, f"missing marked section {name}"
    return match.group("body")


def table_rows(text: str) -> list[list[str]]:
    rows = []
    for line in text.splitlines():
        if not line.startswith("|") or re.fullmatch(r"[|: -]+", line):
            continue
        rows.append([cell.strip() for cell in line.strip("|").split("|")])
    return rows


def aggregate_digest(paths: list[Path]) -> str:
    """Hash sorted path/file-hash pairs without depending on Git."""

    digest = hashlib.sha256()
    for path in sorted(set(paths), key=lambda item: item.as_posix()):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT).as_posix()
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).hexdigest().encode())
        digest.update(b"\n")
    return digest.hexdigest()


def test_readme_and_workspace_instructions_describe_six_stages_five_entrypoints():
    readme = README.read_text(encoding="utf-8")
    summary = table_rows(marked_section(readme, "lifecycle-summary"))
    assert summary[0] == ["Stage", "Entrypoint", "Outcome"]

    stages_and_entrypoints = [row[:2] for row in summary[1:]]
    assert stages_and_entrypoints == [
        ["Vision sketch", "`kickstart`"],
        ["Discovery", "`discover`"],
        ["PRD finalization", "`requirements`"],
        ["Architecture", "`plan` stage 1"],
        ["Planning", "`plan` stage 2"],
        ["Autopilot", "`autopilot`"],
    ]
    assert {
        entrypoint.split()[0] for _, entrypoint in stages_and_entrypoints
    } == {"`kickstart`", "`discover`", "`requirements`", "`plan`", "`autopilot`"}

    instructions = INSTRUCTIONS.read_text(encoding="utf-8")
    assert "six\nstages exposed through five entrypoints" in instructions
    assert "`the-copilot-build-method`" in instructions
    for text in (readme, instructions):
        assert not re.search(r"\bfour[- ]stage\b", text, flags=re.IGNORECASE)
        assert not re.search(r"\bPhase\s+[1-4]\b", text, flags=re.IGNORECASE)


def test_active_skills_and_agents_defer_without_competing_stage_map():
    canonical_stages = (
        "vision sketch",
        "discovery",
        "prd finalization",
        "architecture",
        "planning",
        "autopilot",
    )
    complete_stage_maps = []

    for path in active_instruction_files():
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        assert "the-copilot-build-method" in text, path
        assert not re.search(
            r"\bfour[- ]stage lifecycle\b", text, flags=re.IGNORECASE
        ), path
        if all(stage in lowered for stage in canonical_stages):
            complete_stage_maps.append(path)

    assert complete_stage_maps == [CANONICAL]


def test_kickstart_hands_off_through_the_accepted_discovery_gate():
    kickstart = " ".join(KICKSTART.read_text(encoding="utf-8").split())

    assert "hand off to `discover`" in kickstart
    assert "never hand off directly to `plan`" in kickstart
    assert "human must accept the Discovery readiness gate" in kickstart
    assert "`READY` or `READY_WITH_DEFERRALS`" in kickstart
    assert "before `plan` stage 1 can run" in kickstart


def test_inventory_covers_every_active_file_once_with_a_closed_verdict():
    text = INVENTORY.read_text(encoding="utf-8")
    section = text.split("## Active file inventory", 1)[1].split(
        "## Explicit exclusions", 1
    )[0]
    inventory = {}
    for row in table_rows(section)[1:]:
        path = row[0].strip("`")
        assert path not in inventory
        inventory[path] = row[1]

    discovered = {
        path.relative_to(ROOT).as_posix() for path in active_instruction_files()
    }
    discovered.update({"README.md", ".github/copilot-instructions.md"})
    assert discovered == set(EXPECTED_ACTIVE_FILES)
    assert inventory == EXPECTED_ACTIVE_FILES
    assert set(inventory.values()) == {"migrated", "already-consistent"}
    assert sum(value == "migrated" for value in inventory.values()) == 3
    assert sum(value == "already-consistent" for value in inventory.values()) == 22


def test_exclusions_and_no_pr_provenance_are_explicit():
    inventory = INVENTORY.read_text(encoding="utf-8")
    expected_exclusions = (
        "docs/themes/TH1-methodology-improvements/**",
        "docs/themes/TH2-gitflow-operator/**",
        "docs/architecture/history/**",
        ".github/agents/archive/**",
        ".github/ISSUE_TEMPLATE/archive/**",
        "docs/vision_of_product/VP3-discovery-led-cost-aware-methodology/**",
        "docs/discovery/VP3-discovery-led-cost-aware-methodology/**",
        "docs/requirements/VP3-discovery-led-cost-aware-methodology/**",
        "docs/ADRs/ADR-001-gitflow-operator.md",
        "docs/plan/backlog.yaml",
        "docs/plan/session-log.md",
    )
    for exclusion in expected_exclusions:
        assert exclusion in inventory
    assert "Gitflow was blocked" in inventory
    assert "no pull request could exist" in inventory
    assert "retains the inventory for inclusion in a later pull request" in inventory


def test_locked_th2_history_remains_at_its_byte_identical_baseline():
    paths = list((ROOT / "docs" / "themes").glob("TH2-*/**/*"))
    paths.append(ROOT / "docs" / "plan" / "backlog-archive" / "TH2.yaml")

    assert sum(path.is_file() for path in paths) == 6
    assert aggregate_digest(paths) == (
        "46a4a68beb1c64de1fa4b823104af3b27661afbc6145128baa290ee939518f94"
    )
