import re
import shutil
from pathlib import Path

import test_artefact_templates_contract as template_contract
import test_discovery_dossier_contract as discovery_contract
import test_lifecycle_contract as lifecycle_contract
import test_product_requirements_contract as requirements_contract


ROOT = Path(__file__).resolve().parents[1]
LIFECYCLE = (
    ROOT / ".github" / "skills" / "the-copilot-build-method" / "SKILL.md"
)
DISCOVERY = ROOT / ".github" / "skills" / "discovery-dossier" / "SKILL.md"
REQUIREMENTS = (
    ROOT / ".github" / "skills" / "product-requirements" / "SKILL.md"
)
PLAN = ROOT / ".github" / "skills" / "plan" / "SKILL.md"
DATA_MODEL = ROOT / "docs" / "architecture" / "data-model.md"
ARCHITECTURE_OVERVIEW = ROOT / "docs" / "architecture" / "README.md"
ADR_002 = ROOT / "docs" / "ADRs" / "ADR-002-six-stage-gated-lifecycle.md"
ADR_003 = (
    ROOT / "docs" / "ADRs" / "ADR-003-markdown-records-and-local-validator.md"
)
LEGACY_DISCOVERY = (
    ROOT
    / "docs"
    / "discovery"
    / "VP3-discovery-led-cost-aware-methodology"
    / "README.md"
)
LEGACY_PRD = (
    ROOT
    / "docs"
    / "requirements"
    / "VP3-discovery-led-cost-aware-methodology"
    / "PRD.md"
)


def normalized(text: str) -> str:
    return " ".join(text.split())


def fields_after(text: str, marker: str) -> list[str]:
    return [
        row[0]
        for row in template_contract.table_after(text, marker)[1:]
    ]


def verdicts(text: str) -> set[str]:
    return set(
        re.findall(
            r"`(READY|READY_WITH_DEFERRALS|BLOCKED|Approved|Rejected|Accepted)`",
            text,
        )
    )


def test_all_owned_template_headers_and_fields_match_their_canonical_schemas():
    lifecycle = LIFECYCLE.read_text()
    discovery = DISCOVERY.read_text()
    requirements = REQUIREMENTS.read_text()

    gate_fields = fields_after(lifecycle, "### Gate Record Contract")
    for filename, heading in (
        ("approval.md", "## Approval"),
        ("acceptance.md", "## Acceptance"),
    ):
        template = (
            template_contract.LIFECYCLE_TEMPLATES / filename
        ).read_text()
        assert list(template_contract.field_table(template, heading)) == gate_fields
    waiver = (
        template_contract.LIFECYCLE_TEMPLATES / "waiver.md"
    ).read_text()
    assert list(
        template_contract.field_table(waiver, "## Acceptance")
    ) == [*gate_fields, "Expiry", "Invalidation"]

    discovery_schemas = template_contract.canonical_discovery_schemas(
        discovery
    )
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
            for table in template_contract.parsed_tables(
                (template_contract.DOSSIER_TEMPLATE / owner).read_text()
            )
        ]
        assert headers.count(discovery_schemas[prefix]) == 1
    for prefix in ("EXP", "DR"):
        template = (
            template_contract.DISCOVERY_SKILL
            / "templates"
            / f"{prefix}.md"
        ).read_text()
        assert list(template_contract.field_table(template)) == (
            template_contract.canonical_metadata_fields(discovery, prefix)
        )

    assert discovery_contract.DR_FIELDS == [
        "Schema version",
        "Classification",
        "Reason",
        "Requestor",
        "Affected records",
        "Downstream impact set",
        "Invalidated gates",
        "Actor",
        "Timestamp",
        "Scope",
        "Verdict",
        "Rationale",
        "Source revision",
        "Provenance",
        "Confidence / limitations",
        "Owner",
        "Disposition",
    ]

    prd = template_contract.PRD_TEMPLATE.read_text()
    pcr = (
        template_contract.REQUIREMENTS_SKILL / "templates" / "PCR.md"
    ).read_text()
    requirement_fields = template_contract.table_after(
        requirements, "## Requirement Record Grammar"
    )[0]
    for heading in ("## Functional requirements", "## Quality requirements"):
        assert template_contract.parsed_tables(
            template_contract.section(prd, heading)
        )[0][0] == requirement_fields
    assert list(template_contract.field_table(pcr)) == fields_after(
        requirements, "### Location, title, and metadata"
    )
    assert [
        table[0]
        for table in template_contract.parsed_tables(pcr)
        if table[0] == requirement_fields
    ] == [requirement_fields, requirement_fields]


def test_gate_fields_verdicts_and_architecture_entry_semantics_align():
    lifecycle = LIFECYCLE.read_text()
    discovery = DISCOVERY.read_text()
    requirements = REQUIREMENTS.read_text()
    data_model = DATA_MODEL.read_text()
    adr_002 = ADR_002.read_text()
    adr_003 = ADR_003.read_text()
    plan = PLAN.read_text()

    canonical_fields = fields_after(lifecycle, "### Gate Record Contract")
    assert canonical_fields == requirements_contract.APPROVAL_FIELDS
    assert fields_after(data_model, "## 2. Gate records") == canonical_fields
    for field in canonical_fields:
        assert field.lower() in normalized(adr_002).lower()

    canonical_verdicts = verdicts(
        lifecycle_contract.section(lifecycle, "### Gate Record Contract")
    )
    assert canonical_verdicts == {
        "READY",
        "READY_WITH_DEFERRALS",
        "BLOCKED",
        "Approved",
        "Rejected",
        "Accepted",
    }
    assert verdicts(
        lifecycle_contract.section(data_model, "## 2. Gate records")
    ) == canonical_verdicts

    discovery_gate = normalized(
        discovery_contract.section(
            discovery, "### Canonical README acceptance gate"
        )
    )
    prd_gate = normalized(
        requirements_contract.section(requirements, "## Approval Gate")
    )
    plan_gate = normalized(
        lifecycle_contract.section(plan, "## Stage Entry Gates")
    )
    assert "`READY` or `READY_WITH_DEFERRALS`" in discovery_gate
    assert "`BLOCKED` never opens it" in discovery_gate
    assert "Only exact verdict `Approved` opens this gate" in prd_gate
    assert "both independent upstream gates" in prd_gate
    assert "Discovery readiness record" in plan_gate
    assert "approved PRD record" in plan_gate
    assert "neither record implies or replaces the other" in plan_gate
    assert "missing, incomplete, unaccepted, `BLOCKED`" in plan_gate
    assert "exit with code `2`" in plan_gate
    assert "refuses to proceed when it is missing, unaccepted, or `BLOCKED`" in (
        normalized(adr_002)
    )
    assert "fail-closed with exit code 2" in normalized(adr_002)
    assert "validation failure" in adr_003 and "`2`" in adr_003


def test_accepted_discovery_and_approved_prd_open_architecture_happy_path(
    tmp_path: Path,
):
    fixture = tmp_path / "approved"
    shutil.copytree(requirements_contract.FIXTURE, fixture)

    assert requirements_contract.architecture_admissible(
        fixture / "PRD.md", repo_root=fixture
    )

    discovery_gate = requirements_contract.field_values(
        requirements_contract.section(
            (
                fixture
                / "docs"
                / "discovery"
                / "VP99-fixture"
                / "README.md"
            ).read_text(),
            "## Acceptance",
        ),
        requirements_contract.APPROVAL_FIELDS,
    )
    prd_gate = requirements_contract.field_values(
        requirements_contract.section(
            (fixture / "PRD.md").read_text(), "## Approval"
        ),
        requirements_contract.APPROVAL_FIELDS,
    )
    assert discovery_gate["Verdict"] == "READY"
    assert prd_gate["Verdict"] == "Approved"
    assert (
        requirements_contract.prd_identity(fixture / "PRD.md")[
            "Discovery source revision"
        ]
        == discovery_gate["Source revision"]
    )

    architecture_row = lifecycle_contract.markdown_rows(
        lifecycle_contract.section(
            LIFECYCLE.read_text(), "## Canonical Lifecycle Contract"
        )
    )["Architecture"]
    assert architecture_row[0] == "`plan` stage 1"
    assert architecture_row[2] == (
        "Human-accepted Discovery readiness verdict and human-approved PRD"
    )
    assert architecture_row[4] == "human"


def test_schema_v1_adoption_is_prospective_for_both_accepted_record_sets():
    discovery_versioning = normalized(
        discovery_contract.section(
            DISCOVERY.read_text(),
            "## Schema Version and Prospective Applicability",
        )
    )
    requirements_versioning = normalized(
        requirements_contract.section(
            REQUIREMENTS.read_text(),
            "## Schema Version and Prospective Applicability",
        )
    )
    for text in (discovery_versioning, requirements_versioning):
        assert "schema version is `1`" in text
        assert "VP3" in text
        assert "legacy record set" in text
        assert "no rewrite" in text
        assert "prospective" in text

    assert "| Schema version |" not in LEGACY_DISCOVERY.read_text()
    legacy_prd_prefix = LEGACY_PRD.read_text().split("\n## ", 1)[0]
    assert "| Schema version |" not in legacy_prd_prefix

    dossier_template = (
        template_contract.DOSSIER_TEMPLATE / "README.md"
    ).read_text()
    prd_template = template_contract.PRD_TEMPLATE.read_text()
    assert "| Schema version | 1 |" in dossier_template
    assert "| Schema version | 1 |" in prd_template
    assert "accepted legacy records remain valid" in normalized(
        discovery_contract.section(
            DISCOVERY.read_text(),
            "## Schema Version and Prospective Applicability",
        )
    )
    assert "Version 1 (TH1, TH2, archives) stays valid" in DATA_MODEL.read_text()


def test_discovery_and_product_changes_append_without_rewriting_history(
    tmp_path: Path,
):
    discovery_before = discovery_contract.create_dossier(
        tmp_path / "discovery-before", "FULL"
    )
    discovery_after = tmp_path / "discovery-after"
    shutil.copytree(discovery_before, discovery_after)
    (discovery_after / "revisions" / "DR-001-correction.md").write_text(
        discovery_contract.metadata_document(
            "DR-001",
            "Correct DEC-001",
            discovery_contract.DR_FIELDS,
        )
    )
    discovery_contract.validate_dossier(discovery_after)
    discovery_contract.validate_append_only(
        discovery_before, discovery_after
    )
    assert (
        discovery_before / "decisions.md"
    ).read_bytes() == (discovery_after / "decisions.md").read_bytes()

    requirements_before = tmp_path / "requirements-before"
    shutil.copytree(requirements_contract.FIXTURE, requirements_before)
    requirements_after = tmp_path / "requirements-after"
    shutil.copytree(requirements_before, requirements_after)
    requirements_contract.append_non_requirement_pcr(
        requirements_after, supersedes="PCR-001"
    )
    requirements_contract.validate_append_only(
        requirements_before, requirements_after
    )
    assert (
        requirements_before / "PRD.md"
    ).read_bytes() == (requirements_after / "PRD.md").read_bytes()

    encoding = normalized(
        discovery_contract.section(
            DATA_MODEL.read_text(), "## 1. Record encoding"
        )
    )
    assert "Records are never physically deleted." in encoding
    assert "appending a `DR-###` or `PCR-###`" in encoding
    adr_002 = normalized(ADR_002.read_text())
    assert "Accepted Discovery changes append `DR-###` records" in adr_002
    assert "approved PRD changes append `PCR-###` records" in adr_002


def test_accepted_dr_attribution_and_source_revision_fail_closed_across_contracts(
    tmp_path: Path,
):
    discovery = DISCOVERY.read_text()
    data_model = normalized(DATA_MODEL.read_text())
    grammar = discovery_contract.section(discovery, "### File-per-record form")
    template = (
        template_contract.DISCOVERY_SKILL / "templates" / "DR.md"
    ).read_text()

    assert template_contract.canonical_metadata_fields(
        discovery, "DR"
    ) == discovery_contract.DR_FIELDS
    assert list(template_contract.field_table(template)) == (
        discovery_contract.DR_FIELDS
    )
    for field in discovery_contract.DR_ACCEPTANCE_FIELDS:
        assert field in data_model
    assert "Requestor remains separate from the human acceptance actor." in (
        data_model
    )
    assert "mutable source labels" in normalized(grammar)
    assert "shared angle-bracket placeholder rule" in normalized(grammar)
    assert "finding names `Actor`" in normalized(grammar)

    valid = discovery_contract.create_dossier(tmp_path / "valid-dr", "FULL")
    revision = valid / "revisions" / "DR-001-correction.md"
    revision.write_text(
        discovery_contract.metadata_document(
            "DR-001", "Correction", discovery_contract.DR_FIELDS
        )
    )
    assert discovery_contract.validate_dossier(valid)

    invalid_cases = {
        "nonhuman": {"Actor": "automation agent"},
        "actor-placeholder": {
            "Actor": "Human: <name-or-accountable-role>"
        },
        "missing-rationale": {"Rationale": ""},
        "malformed-timestamp": {"Timestamp": "2026-09-05"},
        "mutable-source": {"Source revision": "main"},
    }
    for name, override in invalid_cases.items():
        invalid = tmp_path / name
        shutil.copytree(valid, invalid)
        target = invalid / "revisions" / "DR-001-correction.md"
        target.write_text(
            discovery_contract.metadata_document(
                "DR-001",
                "Correction",
                discovery_contract.DR_FIELDS,
                overrides=override,
            )
        )
        try:
            discovery_contract.validate_dossier(invalid)
        except AssertionError as failure:
            if name == "actor-placeholder":
                evidence = str(failure)
                assert "Actor" in evidence
                assert "Replace Actor" in evidence
        else:
            raise AssertionError(f"{name} DR attribution must fail closed")


def test_each_e1_contract_and_record_family_has_one_authoritative_owner():
    skills = sorted((ROOT / ".github" / "skills").glob("*/SKILL.md"))
    ownership_phrases = {
        "lifecycle": "single authoritative owner of the lifecycle stage list",
        "discovery": "single owner of the Discovery dossier schema",
        "requirements": (
            "single owner of the Product Requirements Document (PRD) schema"
        ),
    }
    expected = {
        "lifecycle": LIFECYCLE,
        "discovery": DISCOVERY,
        "requirements": REQUIREMENTS,
    }
    for topic, phrase in ownership_phrases.items():
        owners = [
            path for path in skills if phrase in normalized(path.read_text())
        ]
        assert owners == [expected[topic]]

    assert lifecycle_contract.active_instruction_files()
    lifecycle_owners = [
        path
        for path in lifecycle_contract.active_instruction_files()
        if all(
            stage.lower() in path.read_text().lower()
            for stage in (
                "Vision sketch",
                "Discovery",
                "PRD finalization",
                "Architecture",
                "Planning",
                "Autopilot",
            )
        )
    ]
    assert lifecycle_owners == [LIFECYCLE]

    discovery_owners = discovery_contract.ownership_map(DISCOVERY.read_text())
    assert discovery_owners == discovery_contract.ownership_map(
        DATA_MODEL.read_text(), "## 3. Discovery dossier"
    )
    assert "it does not own `PR-###` records" in discovery_owners[
        "`prd-recommendations.md`"
    ]
    assert "not duplicate decisions" in discovery_owners["`mechanisms.md`"]

    adr_ownership = normalized(ADR_002.read_text())
    for statement in (
        "canonical `VO-###` vision outcomes and requirements are in the PRD",
        "Discovery records (including `DEF-###`) are in the dossier",
        "technical contracts are in `docs/architecture/` and `docs/ADRs/`",
        "story definitions are in `docs/themes/`",
        "runtime state is in `docs/plan/backlog.yaml`",
    ):
        assert statement in adr_ownership

    architecture_ownership = template_contract.table_after(
        ARCHITECTURE_OVERVIEW.read_text(), "## Authority and ownership"
    )
    owners = {row[0]: row[1] for row in architecture_ownership[1:]}
    assert owners["Vision outcome (`VO-`)"] == (
        "Canonical PRD `## Vision outcomes` table "
        "(`docs/requirements/VP<n>-<slug>/PRD.md`)"
    )
    assert owners["Product requirements (`PR/QR/PCR`)"] == "PRD"
    assert "PRD" in owners["Vision outcome (`VO-`)"]
    requirements_sections = normalized(
        requirements_contract.section(
            REQUIREMENTS.read_text(), "## PRD Location and Required Sections"
        )
    )
    assert "`## Vision outcomes` is the canonical same-VP Vision-outcome" in (
        requirements_sections
    )


def test_architecture_gate_requires_canonical_prd_vision_content(
    tmp_path: Path,
):
    mutations = (
        (
            "| ID | Outcome |",
            "| Vision outcome | Product contribution |",
        ),
        (
            (
                "| ID | Outcome |\n"
                "|---|---|\n"
                "| VO-001 | Users receive the bounded result. |"
            ),
            (
                "| ID | Outcome |\n"
                "|---|---|\n"
                "| VO-001 | Users receive the bounded result. |\n"
                "| VO-001 | Duplicate outcome. |"
            ),
        ),
        (
            "| VO-001 | Users receive the bounded result. |",
            (
                "| VO-001 | Users receive the bounded result. |\n\n"
                "This prose is not a record."
            ),
        ),
        (
            "| VO-001 | Users receive the bounded result. |",
            (
                "| VO-001 | Users receive the bounded result. |\n\n"
                "| Outcome reference | Contribution summary |\n"
                "|---|---|\n"
                "| VO-001 | Completion reporting. |"
            ),
        ),
        (
            "| VO-001 | Users receive the bounded result. |",
            (
                "| VO-001 | Users receive the bounded result. |\n\n"
                "| Note | Value |\n"
                "|---|---|\n"
                "| Status | Reviewed |"
            ),
        ),
    )
    for index, (old, new) in enumerate(mutations):
        fixture = tmp_path / f"invalid-vision-owner-{index}"
        shutil.copytree(requirements_contract.FIXTURE, fixture)
        prd = fixture / "PRD.md"
        requirements_contract.replace_once(prd, old, new)
        requirements_contract.refresh_prd_source_revision(prd)

        try:
            requirements_contract.architecture_admissible(
                prd, repo_root=fixture
            )
        except AssertionError:
            pass
        else:
            raise AssertionError(
                "noncanonical PRD Vision content must keep Architecture closed"
            )
