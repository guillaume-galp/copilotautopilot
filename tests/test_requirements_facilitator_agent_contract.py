"""Contract tests for the thin TH3.E3.US5 requirements facilitator."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / ".github" / "agents" / "requirements-facilitator.agent.md"
PRODUCT_REQUIREMENTS = (
    ROOT / ".github" / "skills" / "product-requirements" / "SKILL.md"
)
DISCOVERY_DOSSIER = (
    ROOT / ".github" / "skills" / "discovery-dossier" / "SKILL.md"
)


def agent_parts() -> tuple[str, str]:
    parts = AGENT.read_text().split("---", 2)
    assert len(parts) == 3, "agent must have one YAML frontmatter block"
    return parts[1], parts[2].removeprefix("\n")


def section(text: str, heading: str) -> str:
    match = re.search(
        rf"^{re.escape(heading)}\n(?P<body>.*?)(?=^#{{1,6}} |\Z)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match, f"missing section {heading}"
    return " ".join(match.group("body").split())


def normalized(text: str) -> str:
    return " ".join(text.split())


def test_agent_is_thin_internal_and_drafts_only_from_accepted_discovery():
    frontmatter, body = agent_parts()
    responsibilities = section(body, "## Responsibilities")

    assert len(body.splitlines()) <= 50
    assert "user-invocable: false" in frontmatter
    assert "Requirements Facilitator Agent" in body
    assert "only from the exact human-accepted Discovery source revision" in (
        responsibilities
    )
    assert "exclude unresolved or unaccepted material" in responsibilities
    assert "measurable requirement proposals" in responsibilities


def test_every_draft_resolves_an_allowed_trace_and_happy_path_uses_vo_and_dec():
    _, body = agent_parts()
    responsibilities = section(body, "## Responsibilities")
    canonical = normalized(PRODUCT_REQUIREMENTS.read_text())

    assert "every draft a `Traces` cell" in responsibilities
    assert (
        "at least one accepted same-VP Discovery record or PRD-owned Vision "
        "outcome"
    ) in responsibilities
    assert "accepted `DEC`-backed recommendation" in responsibilities
    assert "objective measure" in responsibilities
    assert (
        "make `Traces` resolve both its relevant PRD-owned `VO` and accepted "
        "`DEC`"
    ) in responsibilities
    assert "Every declared ID must resolve" in canonical
    assert "at least one must resolve" in canonical


def test_product_requirements_owns_schema_without_agent_restatement():
    _, body = agent_parts()
    contracts = section(body, "## Canonical Contracts")

    assert (
        "<!-- Skills: the-copilot-build-method, product-requirements, "
        "discovery-dossier -->"
    ) in body
    assert "`product-requirements` as the sole owner" in contracts
    assert "Never restate, copy, extend, or redefine those schemas here" in (
        contracts
    )
    for duplicated_schema in (
        "| ID | Schema version | Requirement |",
        "| Field | Value |",
        "docs/requirements/VP<n>-<slug>/PRD.md",
        "Affected PR",
        "Human timestamp",
    ):
        assert duplicated_schema not in body
    assert "```" not in body


def test_unsupported_recommendation_returns_open_question_without_a_draft():
    _, body = agent_parts()
    boundaries = section(body, "## Behavioral Boundaries")

    assert "lacks an accepted supporting record" in boundaries
    assert "return an open question to `requirements`" in boundaries
    assert "draft no requirement from it" in boundaries


def test_post_approval_change_is_only_a_pcr_proposal():
    _, body = agent_parts()
    boundaries = section(body, "## Behavioral Boundaries")
    canonical = normalized(PRODUCT_REQUIREMENTS.read_text())

    assert "After PRD approval" in boundaries
    assert "propose a canonical `PCR` for any consequential change" in boundaries
    assert "never rewrite approved content or approve a PCR" in boundaries
    assert "Only an attributable human `Approved` verdict" in canonical
    assert "never edits the accepted baseline in place" in canonical


def test_agent_has_no_prd_approval_or_architecture_authority():
    _, body = agent_parts()
    boundaries = section(body, "## Behavioral Boundaries")

    assert "Never approve or reject a PRD" in boundaries
    assert "infer approval" in boundaries
    assert "supply human gate values" in boundaries
    for forbidden_choice in (
        "components",
        "technologies",
        "storage engines",
        "implementation mechanisms",
        "interfaces",
        "technical contracts",
    ):
        assert forbidden_choice in boundaries
    assert "Refuse such a request" in boundaries
    assert "architecture-deferral note for the architect" in boundaries
    assert "return it to Discovery for human validation" in boundaries


def test_vo_and_def_ownership_is_preserved_by_reference():
    _, body = agent_parts()
    contracts = section(body, "## Canonical Contracts")
    product = normalized(PRODUCT_REQUIREMENTS.read_text())
    discovery = normalized(DISCOVERY_DOSSIER.read_text())

    assert "canonical `VO` records PRD-owned" in contracts
    assert "`DEF` definitions Discovery-owned" in contracts
    assert "without duplication, redefinition, or ownership transfer" in contracts
    assert (
        "`## Vision outcomes` is the canonical same-VP Vision-outcome record store"
        in product
    )
    assert "dossier remains the sole owner of `DEF-###` definitions" in product
    assert "`README.md` | Dossier identity" in discovery
    assert "`DEF-###` records" in discovery
