from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_current_skills_reference_gitflow_operator():
    required = [
        ROOT / ".github/skills/the-copilot-build-method/SKILL.md",
        ROOT / ".github/skills/autopilot/SKILL.md",
        ROOT / ".github/agents/orchestrator.agent.md",
        ROOT / ".github/agents/developer.agent.md",
    ]
    for path in required:
        assert "gitflow-operator" in path.read_text(), path


def test_autopilot_docs_do_not_claim_cockpit_queue_clearance():
    docs = [
        ROOT / ".github/skills/the-copilot-build-method/SKILL.md",
        ROOT / ".github/skills/autopilot/SKILL.md",
        ROOT / "docs/vision_of_product/VP2-gitflow-operator/VP2.md",
        ROOT / "docs/ADRs/ADR-001-gitflow-operator.md",
    ]
    banned = ["e2e-operator", "queue clearance", "FIFO execution"]
    for path in docs:
        text = path.read_text()
        for term in banned:
            assert term not in text, f"{term} found in {path}"
