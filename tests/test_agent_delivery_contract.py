"""Prospective epic-first agent contracts, without rewriting legacy artefacts."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def text(relative: str) -> str:
    return " ".join((ROOT / relative).read_text(encoding="utf-8").split())


def test_canonical_unit_is_bounded_epic_and_children_are_optional():
    method = text(".github/skills/the-copilot-build-method/SKILL.md")
    assert "A bounded epic is the default unit" in method
    assert "no synthetic story is required" in method
    assert "Stories do not require individual agent handoffs" in method
    assert "Existing version 1/2 backlogs and story-scoped packets" in method
    assert "Do not rewrite accepted history" in method


def test_owner_keeps_implementation_testing_and_repair_in_one_epic():
    developer = text(".github/agents/developer.agent.md")
    assert "exactly ONE bounded epic per assignment" in developer
    assert "Integration is part of the epic assignment" in developer
    assert "targeted and integration checks" in developer
    assert "legacy story packet authorizes only its story" in developer
    assert "NEVER implement more than one story" not in developer
    assert "ALWAYS run the full test suite" not in developer


def test_review_is_integrated_and_risk_based_not_per_story():
    method = text(".github/skills/the-copilot-build-method/SKILL.md")
    reviewer = text(".github/agents/reviewer.agent.md")
    assert "R0/R1 with `standard` review profile" in method
    assert "R2/R3 or `adversarial`/`critical` profiles require explicit independent approval" in method
    assert "A capability being available is not evidence it ran" in method
    assert "Native independent review may fulfil the same role" in reviewer
    assert "Review the integrated change once" in reviewer


def test_orchestrator_dispatches_epic_and_escalates_only_after_local_repair():
    orchestrator = text(".github/agents/orchestrator.agent.md")
    assert "`--epic`" in orchestrator
    assert "delegate once to **@developer**" in orchestrator
    assert "after the canonical local-repair bound" in orchestrator
    assert "Complete optional children and their epic in one authorized revision" in orchestrator
    assert "Never combine epic and theme completion" in orchestrator
    assert "durable worker" in orchestrator


def test_active_entrypoints_no_longer_mandate_story_sized_assignments():
    paths = [
        ".github/copilot-instructions.md",
        ".github/agents/developer.agent.md",
        ".github/agents/orchestrator.agent.md",
        ".github/agents/product-owner.agent.md",
        ".github/skills/the-copilot-build-method/SKILL.md",
        ".github/skills/autopilot/SKILL.md",
        "README.md",
    ]
    obsolete = (
        "1 story per developer session",
        "One developer session = one story",
        "exactly ONE user story per session",
        "implement → test → review per story",
        "NEVER implement more than one story",
    )
    for path in paths:
        content = text(path)
        for phrase in obsolete:
            assert phrase not in content, (path, phrase)
