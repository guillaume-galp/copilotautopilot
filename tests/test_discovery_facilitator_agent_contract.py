"""Contract tests for the thin TH3.E3.US2 Discovery facilitator agent."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / ".github" / "agents" / "discovery-facilitator.agent.md"
DOSSIER = ROOT / ".github" / "skills" / "discovery-dossier" / "SKILL.md"
METHOD = ROOT / ".github" / "skills" / "the-copilot-build-method" / "SKILL.md"


def section(text: str, heading: str) -> str:
    match = re.search(
        rf"^{re.escape(heading)}\n(?P<body>.*?)(?=^#{{1,6}} |\Z)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match, f"missing section {heading}"
    return " ".join(match.group("body").split())


def agent_body(text: str) -> str:
    parts = text.split("---", 2)
    assert len(parts) == 3, "agent must have one YAML frontmatter block"
    return parts[2].removeprefix("\n")


def normalized(text: str) -> str:
    return " ".join(text.split())


def test_agent_is_thin_and_declares_the_four_bounded_responsibilities():
    text = AGENT.read_text()
    body = agent_body(text)
    responsibilities = section(body, "## Responsibilities")

    assert len(body.splitlines()) <= 50
    assert "Discovery Facilitator Agent" in body
    for responsibility in (
        "Sequence the smallest bounded investigations",
        "evidence taxonomy owned by `discovery-dossier`",
        "Maintain coherent dossier references",
        "readiness recommendation, never an approval",
    ):
        assert responsibility in responsibilities


def test_schema_and_procedure_stay_in_the_canonical_contracts():
    body = agent_body(AGENT.read_text())
    contracts = section(body, "## Canonical Contracts")

    assert "<!-- Skills: the-copilot-build-method, discovery-dossier -->" in body
    assert "`discovery-dossier`, the sole owner of Discovery schema" in contracts
    assert "`the-copilot-build-method`" in contracts
    assert "Never copy, summarize, extend, or redefine that contract here" in (
        contracts
    )

    # A thin agent names contracts and outcomes, not their schemas or forms.
    for duplicated_schema in (
        "| ID | Schema version |",
        "| Field | Value |",
        "docs/discovery/VP<n>-<slug>/",
        "Acceptance actor",
        "Acceptance timestamp",
        "`FULL`, `LIGHTWEIGHT`, and `WAIVED`",
    ):
        assert duplicated_schema not in body
    assert "```" not in body


def test_happy_path_delegates_acceptance_details_and_records_the_decision():
    body = agent_body(AGENT.read_text())
    boundaries = section(body, "## Behavioral Boundaries")
    dossier = DOSSIER.read_text()

    assert "only after `discovery-dossier` validates" in boundaries
    assert "complete attributable human acceptance" in boundaries
    assert "Otherwise leave it proposed" in boundaries
    assert "canonical `DEC` acceptance/write contract" in boundaries
    assert "then update the canonical working state" in boundaries

    # The owning skill, rather than the agent, carries every AC3 detail.
    for kind in (
        "assumption",
        "preference",
        "decision",
        "deferral",
        "override",
        "risk acceptance",
    ):
        assert kind in dossier
    for field in (
        "`Actor`",
        "`Timestamp`",
        "`Scope`",
        "`Verdict`",
        "`Rationale`",
        "`Source revision`",
    ):
        assert field in dossier
    assert "An accepted decision or deferral without one complete suffix" in (
        dossier
    )


def test_checkpoint_and_resume_behavior_delegates_to_the_method_contract():
    body = agent_body(AGENT.read_text())
    boundaries = section(body, "## Behavioral Boundaries")
    method = normalized(METHOD.read_text())

    assert "At session start, apply the canonical resume contract" in boundaries
    assert "continue unresolved work and never re-elicit accepted records" in (
        boundaries
    )
    assert "After every checkpoint, persist the canonical `## Working state`" in (
        boundaries
    )

    # The canonical owner defines the mechanism that makes the edge case true.
    assert "continues the single `Next action`" in method
    assert "does not re-elicit IDs in `Accepted so far`" in method
    for field in ("`Status`", "`Open items`", "`Accepted so far`", "`Next action`"):
        assert field in method


def test_error_case_refuses_approval_without_copying_checkpoint_procedure():
    body = agent_body(AGENT.read_text())
    boundaries = section(body, "## Behavioral Boundaries")
    method = normalized(METHOD.read_text())

    assert "Never approve or accept a consequential proposal" in boundaries
    assert "Refuse any agent or orchestrator approval request" in boundaries
    assert "return it to `discover` for a grouped human checkpoint" in boundaries
    assert (
        "only the human authority identified by `the-copilot-build-method` "
        "can accept it"
    ) in normalized(DOSSIER.read_text())
    assert "| Authority |" in method


def test_prd_authorship_and_record_ownership_remain_out_of_scope():
    body = agent_body(AGENT.read_text())
    boundaries = section(body, "## Behavioral Boundaries")

    assert "Never author, edit, or complete a PRD" in boundaries
    assert "preserve canonical `VO` and `DEF` ownership" in boundaries
    assert "return recommendations to `discover`" in boundaries
