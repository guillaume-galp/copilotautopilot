import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LIFECYCLE_SKILL = (
    ROOT / ".github" / "skills" / "the-copilot-build-method"
)
DISCOVERY_SKILL = ROOT / ".github" / "skills" / "discovery-dossier"
REQUIREMENTS_SKILL = ROOT / ".github" / "skills" / "product-requirements"
DATA_MODEL = ROOT / "docs" / "architecture" / "data-model.md"

LIFECYCLE_TEMPLATES = LIFECYCLE_SKILL / "templates"
DOSSIER_TEMPLATE = DISCOVERY_SKILL / "templates" / "dossier"
PRD_TEMPLATE = REQUIREMENTS_SKILL / "templates" / "PRD.md"

PLACEHOLDER = re.compile(r"<[^<>\n]+>")


def section(text: str, heading: str) -> str:
    level = len(heading) - len(heading.lstrip("#"))
    lines = text.splitlines()
    start = lines.index(heading) + 1
    body: list[str] = []
    fenced = False
    for line in lines[start:]:
        if line.startswith("```"):
            fenced = not fenced
        if not fenced and re.match(rf"^#{{1,{level}}} ", line):
            break
        body.append(line)
    return "\n".join(body)


def table_blocks(text: str) -> list[list[list[str]]]:
    blocks: list[list[list[str]]] = []
    current: list[list[str]] = []
    for line in [*text.splitlines(), ""]:
        if line.startswith("|") and line.endswith("|"):
            current.append(
                [cell.strip() for cell in line.strip("|").split("|")]
            )
        elif current:
            blocks.append(current)
            current = []
    return blocks


def parsed_tables(text: str) -> list[list[list[str]]]:
    result = []
    for table in table_blocks(text):
        assert len(table) >= 2
        assert table[1] == ["---"] * len(table[0])
        assert all(len(row) == len(table[0]) for row in table)
        result.append([table[0], *table[2:]])
    return result


def table_after(text: str, marker: str) -> list[list[str]]:
    assert marker in text
    for table in table_blocks(text.split(marker, 1)[1]):
        if (
            len(table) >= 2
            and table[1] == ["---"] * len(table[0])
            and all(len(row) == len(table[0]) for row in table)
        ):
            return [table[0], *table[2:]]
    raise AssertionError(f"no parseable table after {marker}")


def field_table(text: str, heading: str | None = None) -> dict[str, str]:
    source = section(text, heading) if heading else text
    matches = [
        table
        for table in parsed_tables(source)
        if table[0] == ["Field", "Value"]
    ]
    assert len(matches) == 1
    rows = matches[0][1:]
    assert len({row[0] for row in rows}) == len(rows)
    return dict(rows)


def canonical_discovery_schemas(text: str) -> dict[str, list[str]]:
    table = table_after(text, "### Required table columns")
    return {
        row[0].strip("`"): [
            field.strip().strip("`") for field in row[2].split(",")
        ]
        for row in table[1:]
    }


def canonical_metadata_fields(text: str, prefix: str) -> list[str]:
    article = "An" if prefix == "EXP" else "A"
    start = (
        f"{article} `{prefix}-###` metadata table requires exactly these "
        "fields in this order:"
    )
    tail = text.split(start, 1)[1]
    fields = tail.split("and `Disposition`.", 1)[0] + "`Disposition`"
    return re.findall(r"`([^`]+)`", fields)


def template_files() -> list[Path]:
    roots = [
        LIFECYCLE_TEMPLATES,
        DISCOVERY_SKILL / "templates",
        REQUIREMENTS_SKILL / "templates",
    ]
    return sorted(path for root in roots for path in root.rglob("*.md"))


def gate_findings(text: str) -> list[dict[str, str]]:
    """Test-only contract oracle; TH3.E2 owns production validation."""
    values = field_table(text)
    findings = []
    for field, value in values.items():
        if PLACEHOLDER.search(value):
            findings.append(
                {
                    "field": field,
                    "remediation": (
                        f"Replace the {value} placeholder in {field} "
                        "with an attributable value."
                    ),
                }
            )
    return findings


def test_ac1_templates_are_under_their_owning_skills_and_cover_all_artefacts():
    discovery_contract = (DISCOVERY_SKILL / "SKILL.md").read_text()
    ownership = table_after(
        discovery_contract, "## Dossier Location and Ownership"
    )
    required_files = {
        row[0].strip("`")
        for row in ownership[1:]
        if "/" not in row[0]
    }

    assert {path.name for path in DOSSIER_TEMPLATE.glob("*.md")} == required_files
    assert (DOSSIER_TEMPLATE / "experiments" / ".gitkeep").is_file()
    assert (DOSSIER_TEMPLATE / "revisions" / ".gitkeep").is_file()
    assert (DISCOVERY_SKILL / "templates" / "EXP.md").is_file()
    assert (DISCOVERY_SKILL / "templates" / "DR.md").is_file()
    assert PRD_TEMPLATE.is_file()
    assert (REQUIREMENTS_SKILL / "templates" / "PCR.md").is_file()

    assert not (LIFECYCLE_TEMPLATES / "PRD.md").exists()
    assert not (REQUIREMENTS_SKILL / "templates" / "EXP.md").exists()


def test_ac1_dossier_headers_and_file_metadata_reuse_canonical_schemas():
    contract = (DISCOVERY_SKILL / "SKILL.md").read_text()
    schemas = canonical_discovery_schemas(contract)
    owners = {
        "DQ": "discovery-questions.md",
        "EV": "evidence-index.md",
        "ASM": "assumptions.md",
        "DEC": "decisions.md",
        "INV": "risks-and-failure-modes.md",
        "RSK": "risks-and-failure-modes.md",
        "DEF": "README.md",
    }

    for prefix, owner in owners.items():
        headers = [
            table[0]
            for table in parsed_tables((DOSSIER_TEMPLATE / owner).read_text())
        ]
        assert schemas[prefix] in headers

    for prefix in ("EXP", "DR"):
        template = DISCOVERY_SKILL / "templates" / f"{prefix}.md"
        assert list(field_table(template.read_text())) == (
            canonical_metadata_fields(contract, prefix)
        )


def test_ac1_prd_and_pcr_reuse_required_sections_and_exact_record_grammars():
    contract = (REQUIREMENTS_SKILL / "SKILL.md").read_text()
    prd = PRD_TEMPLATE.read_text()
    pcr = (REQUIREMENTS_SKILL / "templates" / "PCR.md").read_text()

    section_table = table_after(
        contract,
        "After the identity table, the following level-two sections are required",
    )
    required_sections = [row[1].strip("`") for row in section_table[1:]]
    template_sections = re.findall(r"^## .+$", prd, flags=re.MULTILINE)
    assert template_sections[:-1] == required_sections
    assert template_sections[-1] == "## Working state"

    canonical_identity = table_after(
        contract, "## PRD Location and Required Sections"
    )
    assert list(field_table(prd.split("## Approval", 1)[0])) == [
        row[0] for row in canonical_identity[1:]
    ]

    requirement_header = table_after(
        contract, "## Requirement Record Grammar"
    )[0]
    for heading in ("## Functional requirements", "## Quality requirements"):
        assert parsed_tables(section(prd, heading))[0][0] == requirement_header

    canonical_pcr = table_after(contract, "### Location, title, and metadata")
    assert list(field_table(pcr)) == [row[0] for row in canonical_pcr[1:]]
    requirement_tables = [
        table for table in parsed_tables(pcr) if table[0] == requirement_header
    ]
    assert len(requirement_tables) == 2


def test_ac2_gate_and_waiver_templates_have_canonical_order_and_extensions():
    lifecycle = (LIFECYCLE_SKILL / "SKILL.md").read_text()
    canonical_gate = table_after(lifecycle, "### Gate Record Contract")
    gate_fields = [row[0] for row in canonical_gate[1:]]

    for name, heading in (
        ("approval.md", "## Approval"),
        ("acceptance.md", "## Acceptance"),
    ):
        text = (LIFECYCLE_TEMPLATES / name).read_text()
        assert text.startswith(heading + "\n")
        assert list(field_table(text, heading)) == gate_fields

    waiver = (LIFECYCLE_TEMPLATES / "waiver.md").read_text()
    assert list(field_table(waiver, "## Acceptance")) == [
        *gate_fields,
        "Expiry",
        "Invalidation",
    ]

    discovery_fields = list(
        field_table(
            (DOSSIER_TEMPLATE / "README.md").read_text(), "## Acceptance"
        )
    )
    assert discovery_fields == [
        "Actor",
        "Timestamp",
        "Scope",
        "Disposition",
        "Verdict",
        "Rationale",
        "Source revision",
    ]
    assert list(field_table(PRD_TEMPLATE.read_text(), "## Approval")) == gate_fields


def test_ac3_working_state_is_canonical_not_started_and_gate_finalized():
    data_model = DATA_MODEL.read_text()
    canonical_working = table_after(data_model, "## 2b. Working state (resumability)")
    fields = [row[0] for row in canonical_working[1:]]
    sources = [
        (LIFECYCLE_TEMPLATES / "working-state.md").read_text(),
        (DOSSIER_TEMPLATE / "README.md").read_text(),
        PRD_TEMPLATE.read_text(),
    ]

    for text in sources:
        values = field_table(text, "## Working state")
        assert list(values) == fields
        assert values["Status"] == "not-started"
        assert len(values["Next action"]) > 0

    lifecycle = (LIFECYCLE_SKILL / "SKILL.md").read_text()
    template_contract = section(
        lifecycle, "### Canonical Gate and Working-State Templates"
    )
    assert "removed or `Status` is changed to\n`accepted`" in template_contract


def test_bdd_happy_path_scaffold_has_every_file_header_and_not_started_state(
    tmp_path: Path,
):
    scaffold = tmp_path / "VP99-example"
    shutil.copytree(DOSSIER_TEMPLATE, scaffold)
    contract = (DISCOVERY_SKILL / "SKILL.md").read_text()
    schemas = canonical_discovery_schemas(contract)

    for relative in (
        "README.md",
        "discovery-questions.md",
        "system-map.md",
        "domain-ontology.md",
        "mechanisms.md",
        "evidence-index.md",
        "assumptions.md",
        "decisions.md",
        "risks-and-failure-modes.md",
        "prd-recommendations.md",
        "architecture-handoff.md",
    ):
        assert (scaffold / relative).is_file()

    all_headers = [
        table[0]
        for path in scaffold.glob("*.md")
        for table in parsed_tables(path.read_text())
    ]
    assert all(header in all_headers for header in schemas.values())
    working = field_table((scaffold / "README.md").read_text(), "## Working state")
    assert working["Status"] == "not-started"


def test_bdd_paused_discovery_resumes_from_one_action_without_reelicitation():
    state = field_table(
        (LIFECYCLE_TEMPLATES / "working-state.md").read_text(),
        "## Working state",
    )
    state.update(
        {
            "Status": "awaiting-human",
            "Open items": "DQ-004 (product owner), DQ-009 (designer)",
            "Accepted so far": "DEC-002, ASM-003",
            "Next action": "Ask the product owner to resolve DQ-004.",
        }
    )

    assert state["Status"] == "awaiting-human"
    assert state["Open items"].count("DQ-") == 2
    assert state["Next action"] == "Ask the product owner to resolve DQ-004."
    accepted = set(state["Accepted so far"].split(", "))
    questions_to_elicit = {
        item.split(" ", 1)[0] for item in state["Open items"].split(", ")
    }
    assert accepted.isdisjoint(questions_to_elicit)
    assert accepted == {"DEC-002", "ASM-003"}


def test_bdd_unfilled_actor_is_not_accepted_and_remediation_names_actor():
    approval = (LIFECYCLE_TEMPLATES / "approval.md").read_text()
    values = field_table(approval, "## Approval")
    assert values["Actor"] == "<actor>"

    findings = gate_findings(approval)
    assert findings
    actor_finding = next(item for item in findings if item["field"] == "Actor")
    assert "Actor" in actor_finding["remediation"]
    assert "<actor>" in actor_finding["remediation"]


def test_dr_actor_template_preserves_human_prefix_but_remains_incomplete():
    dr = (DISCOVERY_SKILL / "templates" / "DR.md").read_text()
    actor = field_table(dr)["Actor"]

    assert actor == "Human: <name-or-accountable-role>"
    assert re.fullmatch(r"Human: \S(?:.*\S)?", "Human: product owner")
    assert not re.fullmatch(r"Human: \S(?:.*\S)?", "product owner")
    assert not re.fullmatch(r"Human: \S(?:.*\S)?", "automation agent")
    actor_finding = next(
        item for item in gate_findings(dr) if item["field"] == "Actor"
    )
    assert "<name-or-accountable-role>" in actor_finding["remediation"]


def test_ac4_every_template_is_ascii_and_every_table_is_structurally_parseable():
    paths = template_files()
    assert paths
    for path in paths:
        raw = path.read_bytes()
        raw.decode("ascii")
        text = raw.decode("ascii")
        assert parsed_tables(text), f"{path} must contain an ASCII pipe table"
        for table in parsed_tables(text):
            assert all(all(cell for cell in row) for row in table)


def test_ac4_placeholders_are_explicit_and_cannot_be_accepted_values():
    accepted_verdicts = {
        "READY",
        "READY_WITH_DEFERRALS",
        "Approved",
        "Accepted",
    }
    for path in template_files():
        text = path.read_text()
        for match in PLACEHOLDER.finditer(text):
            assert match.group(0).startswith("<")
            assert match.group(0).endswith(">")

    gate_paths = [
        LIFECYCLE_TEMPLATES / "approval.md",
        LIFECYCLE_TEMPLATES / "acceptance.md",
        LIFECYCLE_TEMPLATES / "waiver.md",
        DOSSIER_TEMPLATE / "README.md",
        PRD_TEMPLATE,
    ]
    for path in gate_paths:
        heading = "## Approval" if path.name in {"approval.md", "PRD.md"} else "## Acceptance"
        values = field_table(path.read_text(), heading)
        assert PLACEHOLDER.fullmatch(values["Actor"])
        assert PLACEHOLDER.fullmatch(values["Verdict"])
        assert values["Verdict"] not in accepted_verdicts

    lifecycle = (LIFECYCLE_SKILL / "SKILL.md").read_text()
    placeholder_contract = section(
        lifecycle, "### Canonical Gate and Working-State Templates"
    )
    assert "Every value enclosed in angle brackets is an unfilled placeholder" in (
        placeholder_contract
    )
    assert "`<actor>` is a missing `Actor`" in placeholder_contract
