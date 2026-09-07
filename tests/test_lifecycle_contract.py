import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = (
    ROOT / ".github" / "skills" / "the-copilot-build-method" / "SKILL.md"
)
ARCHITECTURE_OVERVIEW = ROOT / "docs" / "architecture" / "README.md"
ADR_002 = ROOT / "docs" / "ADRs" / "ADR-002-six-stage-gated-lifecycle.md"
CONTRADICTORY_MAPPING = re.compile(
    r"\beach\s+VP(?:<n>)?\s+maps\s+to\s+TH(?:<n>)?(?=\W|$)",
    flags=re.IGNORECASE,
)
LOCKED_TECHNICAL_MUTATION = re.compile(
    r"\b(?:may|can|permitted|allowed|restricted to)\b.{0,120}"
    r"(?:technical references?|broken file paths?)",
    flags=re.IGNORECASE,
)


def section(text: str, heading: str) -> str:
    """Return a markdown section, stopping at the next heading."""
    match = re.search(
        rf"^{re.escape(heading)}\n(?P<body>.*?)(?=^#{{1,6}} |\Z)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match, f"missing section {heading}"
    return match.group("body")


def markdown_rows(text: str) -> dict[str, list[str]]:
    rows: dict[str, list[str]] = {}
    for line in text.splitlines():
        if not line.startswith("|") or re.fullmatch(r"[|: -]+", line):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        rows[cells[0]] = cells[1:]
    return rows


def active_instruction_files() -> list[Path]:
    files = list((ROOT / ".github" / "skills").glob("*/SKILL.md"))
    files.extend((ROOT / ".github" / "agents").glob("*.md"))
    files.append(ROOT / ".github" / "copilot-instructions.md")
    return sorted(path for path in files if "archive" not in path.parts)


def test_six_stage_map_defines_entrypoint_artefact_gates_and_authority():
    lifecycle = section(CONTRACT.read_text(), "## Canonical Lifecycle Contract")
    rows = markdown_rows(lifecycle)

    expected_rows = {
        "Stage": [
            "Entrypoint",
            "Owning artefact(s)",
            "Upstream entry gate",
            "Completion gate",
            "Authority",
        ],
        "Vision sketch": [
            "`kickstart`",
            "`docs/vision_of_product/VP<n>-<slug>/` VP document",
            "None; this is the lifecycle root",
            "Vision sketch recorded; no formal gate record",
            "human",
        ],
        "Discovery": [
            "`discover`",
            "`docs/discovery/VP<n>-<slug>/` Discovery dossier",
            "Vision sketch exists",
            "`READY` or `READY_WITH_DEFERRALS` readiness verdict accepted",
            "human",
        ],
        "PRD finalization": [
            "`requirements`",
            "`docs/requirements/VP<n>-<slug>/PRD.md`",
            "Human-accepted Discovery readiness verdict",
            "PRD `Approved`",
            "human",
        ],
        "Architecture": [
            "`plan` stage 1",
            "`docs/architecture/` and `docs/ADRs/`",
            (
                "Human-accepted Discovery readiness verdict and "
                "human-approved PRD"
            ),
            "Architecture `Accepted`",
            "human",
        ],
        "Planning": [
            "`plan` stage 2",
            (
                "`docs/themes/TH<n>-<slug>/`, its story files, issue "
                "templates, "
                "`docs/themes/TH<n>-<slug>/planning-admission.md`, and the "
                "theme state in `docs/plan/backlog.yaml`"
            ),
            "Human-accepted architecture",
            (
                "`Accepted` planning-admission record issued by the product "
                "owner at "
                "`docs/themes/TH<n>-<slug>/planning-admission.md`, with its "
                "exact source revision passing the validator"
            ),
            "product owner plus validator",
        ],
        "Autopilot": [
            "`autopilot`",
            (
                "Product changes and their verification, review, Gitflow, "
                "and runtime evidence; runtime status in "
                "`docs/plan/backlog.yaml`"
            ),
            (
                "The planning-admission record is `Accepted` and its exact "
                "source revision passes the validator"
            ),
            "Applicable story, epic, and theme Definition of Done",
            (
                "orchestrator and reviewer for delivery evidence; human for "
                "theme acceptance"
            ),
        ],
    }
    assert rows == expected_rows


def test_planning_admission_uses_a_formal_record_and_closed_verdict():
    contract_text = CONTRACT.read_text()
    admission = section(
        contract_text, "### Planning-to-Autopilot Admission Gate"
    )

    assert "`docs/themes/TH<n>-<slug>/planning-admission.md`" in admission
    assert "`## Acceptance`" in admission
    assert (
        "product owner issues the record with verdict `Accepted`"
        in admission
    )
    assert "validator passes the exact source revision" in admission
    assert "`Backlog admitted` is not a verdict" in admission
    assert "does not invent or issue a second gate verdict" in admission


def test_architecture_summaries_do_not_drift_from_planning_admission_verdict():
    canonical = (
        "`Accepted` planning-admission record at exact validated source revision"
    )
    for path in (ARCHITECTURE_OVERVIEW, ADR_002):
        text = path.read_text()
        planning_rows = [
            line
            for line in text.splitlines()
            if line.startswith("|") and "Planning |" in line
        ]
        assert len(planning_rows) == 1, path
        assert canonical in planning_rows[0], path
        assert "backlog admitted" not in planning_rows[0].lower(), path


def test_gate_record_fields_and_closed_verdict_vocabulary_are_defined():
    gate_contract = section(CONTRACT.read_text(), "### Gate Record Contract")
    rows = markdown_rows(gate_contract)

    assert set(rows) == {
        "Field",
        "Actor",
        "Timestamp",
        "Scope",
        "Verdict",
        "Rationale",
        "Source revision",
    }
    verdicts = set(
        re.findall(
            r"`(READY|READY_WITH_DEFERRALS|BLOCKED|Approved|Rejected|Accepted)`",
            gate_contract,
        )
    )
    assert verdicts == {
        "READY",
        "READY_WITH_DEFERRALS",
        "BLOCKED",
        "Approved",
        "Rejected",
        "Accepted",
    }
    assert "closed verdict vocabulary" in gate_contract


def test_stage_entry_is_fail_closed_with_exit_code_two():
    stage_entry = section(CONTRACT.read_text(), "### Fail-Closed Stage Entry")

    for condition in ("missing", "incomplete", "unaccepted", "`BLOCKED`"):
        assert condition in stage_entry
    assert "fail-closed" in stage_entry
    assert "exits with code `2`" in stage_entry
    assert "performs no stage work" in stage_entry


def test_active_entrypoints_validate_their_gates_before_actions():
    plan = (
        ROOT / ".github" / "skills" / "plan" / "SKILL.md"
    ).read_text()
    plan_gates = section(plan, "## Stage Entry Gates")

    assert "Before architecture work" in plan_gates
    assert "independently validate" in plan_gates
    assert "Discovery readiness record" in plan_gates
    assert "approved PRD record" in plan_gates
    assert "neither record implies or replaces the other" in plan_gates
    assert "Before planning work or delegation" in plan_gates
    assert "human-accepted architecture record" in plan_gates
    assert "perform no work for that stage" in plan_gates
    assert "exit with code `2`" in plan_gates

    orchestrator = (
        ROOT / ".github" / "agents" / "orchestrator.agent.md"
    ).read_text()
    admission = section(orchestrator, "## Autopilot Admission Gate")
    normalized_admission = " ".join(admission.split())
    assert (
        "Before any backlog state transition or delegation"
        in normalized_admission
    )
    assert "planning-to-autopilot admission gate" in normalized_admission
    assert "product owner's `Accepted` verdict" in normalized_admission
    assert "validator to pass the exact source revision" in normalized_admission
    assert "perform no state transition" in normalized_admission
    assert "perform no delegation" in normalized_admission
    assert "exit with code `2`" in normalized_admission


def test_multi_theme_lock_scope_keeps_shared_vp_artefacts_revisable():
    lock_contract = section(
        CONTRACT.read_text(), "## Split Lock / Immutability Rules"
    )

    for locked_at_theme_acceptance in (
        "theme directory",
        "story files",
        "theme backlog snapshot",
    ):
        assert locked_at_theme_acceptance in lock_contract
    assert "The first accepted theme that depends on that ADR" in lock_contract
    assert "All themes currently mapped to that VP are accepted" in lock_contract

    for shared_artefact in ("VP3", "Discovery", "PRD"):
        assert shared_artefact in lock_contract
    assert "`DR-###`" in lock_contract
    assert "`PCR-###`" in lock_contract
    assert "TH3, TH4, and TH5 are all accepted" in lock_contract


def test_only_canonical_skill_owns_the_stage_list():
    active_files = active_instruction_files()
    contract_text = CONTRACT.read_text()
    canonical_stages = (
        "Vision sketch",
        "Discovery",
        "PRD finalization",
        "Architecture",
        "Planning",
        "Autopilot",
    )

    assert all(stage in contract_text for stage in canonical_stages)
    lifecycle_owners = []
    for path in active_files:
        text = path.read_text()
        if path != CONTRACT:
            assert "the-copilot-build-method" in text, (
                f"{path} does not reference the canonical lifecycle owner"
            )
        if all(stage.lower() in text.lower() for stage in canonical_stages):
            lifecycle_owners.append(path)
        if path == CONTRACT:
            continue
        numbered_stage_lines = re.findall(
            r"^\s*\d+\.\s+.*\b(?:Vision|Discovery|PRD|Architecture|Planning|"
            r"Autopilot)\b",
            text,
            flags=re.MULTILINE,
        )
        assert len(numbered_stage_lines) < 2, (
            f"{path} restates an ordered lifecycle: {numbered_stage_lines}"
        )
        assert not re.search(r"\bPhases?\s+[1-6]\b", text), (
            f"{path} retains a numbered legacy phase statement"
        )
        if "lifecycle" in text.lower():
            assert "the-copilot-build-method" in text, (
                f"{path} discusses lifecycle without referencing its owner"
            )

    assert lifecycle_owners == [CONTRACT]

    former_owners = (
        ROOT / ".github" / "agents" / "README.md",
        ROOT / ".github" / "copilot-instructions.md",
    )
    for path in former_owners:
        assert "`the-copilot-build-method`" in path.read_text()


def test_active_instructions_do_not_contradict_mapping_or_lock_contracts():
    assert CONTRADICTORY_MAPPING.search("each VP<n> maps to TH<n>")
    assert LOCKED_TECHNICAL_MUTATION.search(
        "locked theme edits are restricted to technical references"
    )

    active_files = active_instruction_files()
    for path in active_files:
        text = path.read_text()
        normalized = " ".join(text.split())
        assert not CONTRADICTORY_MAPPING.search(normalized), (
            f"{path} imposes a contradictory VP-to-theme 1:1 mapping"
        )
        assert not LOCKED_TECHNICAL_MUTATION.search(normalized), (
            f"{path} allows technical-reference mutation of a locked theme"
        )

    product_owner = (
        ROOT / ".github" / "agents" / "product-owner.agent.md"
    ).read_text()
    normalized_product_owner = " ".join(product_owner.split())
    assert "VP-to-theme 1:N mapping" in normalized_product_owner
    assert "independently of the VP number" in normalized_product_owner
    assert (
        "NEVER derive a theme number from a VP number"
        in normalized_product_owner
    )

    backlog = (
        ROOT / ".github" / "skills" / "backlog-management" / "SKILL.md"
    ).read_text()
    normalized_backlog = " ".join(backlog.split())
    assert "MUST NOT be mutated" in normalized_backlog
    assert (
        "including to repair a technical reference or broken file path"
        in normalized_backlog
    )
    assert "sole mutation exception" in normalized_backlog
    assert "ADR status changing to superseded" in normalized_backlog
    assert (
        "never permits a locked theme or backlog mutation"
        in normalized_backlog
    )
