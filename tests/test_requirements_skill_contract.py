"""Contract tests for the TH3.E3.US4 interactive requirements skill."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".github" / "skills" / "requirements" / "SKILL.md"
LIFECYCLE = (
    ROOT / ".github" / "skills" / "the-copilot-build-method" / "SKILL.md"
)


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


def test_ac1_interactively_translates_discovery_to_measurable_pr_and_qr():
    text = SKILL.read_text()
    flow = normalized(section(text, "## Interactive Translation Flow"))

    assert "name: requirements" in text
    assert "`the-copilot-build-method`" in text
    assert "`product-requirements`" in text
    assert "`discovery-dossier`" in text
    assert "accepted Discovery source revision" in flow
    assert "`PR-###` records for observable product behavior" in flow
    assert "`QR-###` records for measurable quality properties" in flow
    assert "objective measure" in flow
    assert "valid upstream traceability" in flow
    assert "The human may accept, amend, reject, or defer" in flow
    assert "Do not infer a choice from silence" in flow


def test_ac2_exact_gate_validation_runs_before_any_requirements_work():
    text = SKILL.read_text()
    barrier = normalized(section(text, "## Fail-Closed Entry Barrier"))
    command = "method validate gates --vp <vp> --stage requirements"

    assert text.count(command) == 1
    assert "one and only one canonical VP" in barrier
    assert "same VP number and slug" in barrier
    for invalid_scope in (
        "Zero matches",
        "more than one match",
        "mixed-VP input set",
        "VP number or slug disagreement",
    ):
        assert invalid_scope in barrier
    assert "Never run once per candidate or merge evidence from multiple VPs" in (
        barrier
    )
    assert "Before reading an in-progress PRD" in barrier
    assert "asking a requirements question" in barrier
    assert "creating or changing a PRD" in barrier
    assert "delegating any drafting" in barrier
    assert "run exactly" in barrier
    for expected in (
        "exits `0`",
        "`command: validate`",
        "`check: gates`",
        "`status: ok`",
        "`stage: requirements`",
        "`stage_entry: open`",
        "`findings: []`",
        "`vp: <vp>`",
        "exactly one `discovery-readiness` gate",
        "same VP's canonical dossier `## Acceptance` record",
        "explicitly attributable human `Actor`",
        "human-accepted verdict `READY` or `READY_WITH_DEFERRALS`",
    ):
        assert expected in barrier


def test_ac2_rejects_agent_recommendations_and_statuses_as_gate_evidence():
    barrier = normalized(section(SKILL.read_text(), "## Fail-Closed Entry Barrier"))

    assert (
        "`status: ok`, `stage_entry: open`, and gate `status: open` are "
        "validation result state, not independent gate evidence"
    ) in barrier
    for inadmissible in (
        "dossier or PRD identity `Status`",
        "Working state `Status`",
        "PRD `Discovery verdict` field",
        "agent-authored status",
        "agent or facilitator recommendation",
        "proposed verdict",
        "agent-authored acceptance",
    ):
        assert inadmissible in barrier
    assert "canonical attributable human acceptance record" in barrier


def test_ac2_gate_failure_is_fail_closed_with_actionable_diagnostics():
    barrier = normalized(
        section(SKILL.read_text(), "## Fail-Closed Entry Barrier")
    )

    for failure in (
        "cannot run",
        "exits non-zero",
        "malformed or missing output",
        "omits or duplicates the VP result or readiness gate",
        "names another VP or stage",
        "reports any finding",
        "missing, incomplete, stale, unaccepted, unknown, `BLOCKED`, "
        "agent-attributed",
    ):
        assert failure in barrier
    assert "Perform no requirements work" in barrier
    for finding_field in ("check", "file", "record", "message", "remediation"):
        assert finding_field in barrier
    assert "exit with code `2`" in barrier
    assert "Never fill or accept the Discovery gate on the human's behalf" in barrier
    assert "run the exact command again before doing work" in barrier


def test_ac3_and_error_scenario_refuse_unmeasurable_or_untraced_approval():
    barrier = normalized(
        section(
            SKILL.read_text(),
            "## Measurability and Traceability Approval Barrier",
        )
    )

    assert "independently enumerate both review inventories" in barrier
    assert (
        "every proposed `PR-###` and `QR-###` in the submitted draft or "
        "proposed PCR content, whether or not it is yet effective"
    ) in barrier
    assert (
        "every effective `PR-###` and `QR-###` in the baseline plus the "
        "canonically folded, currently applicable approved PCR state"
    ) in barrier
    assert "Review every row in both inventories for both" in barrier
    for bypass in ("supersession", "rejection", "draft status", "prior review"):
        assert bypass in barrier
    assert "Approval must be refused" in barrier
    assert "any measurability or traceability failure" in barrier
    assert "identify every failing inventory, ID, and cell" in barrier
    assert "“the system shall be fast,”" in barrier
    assert "`fast` has no independently observable acceptance result" in barrier
    assert "concrete threshold or an observable condition" in barrier
    assert "how it will be observed" in barrier
    assert "name the requirement and unresolved reference" in barrier
    assert "valid, resolving upstream link allowed by `product-requirements`" in barrier
    assert "do not invent a record" in barrier


def test_ac3_requires_complete_zero_failure_rereview_after_every_remediation():
    barrier = normalized(
        section(
            SKILL.read_text(),
            "## Measurability and Traceability Approval Barrier",
        )
    )

    assert (
        "Every remediation or other proposed/effective content change "
        "invalidates the prior review"
    ) in barrier
    assert "perform a new complete re-review" in barrier
    assert "re-enumerate both inventories" in barrier
    assert (
        "re-check both measurability and traceability for every row against "
        "the exact submitted revision"
    ) in barrier
    assert "incremental check of only the previously failing IDs is insufficient" in (
        barrier
    )
    assert "zero measurability failures and zero traceability failures" in barrier
    assert "Any later amendment requires another complete zero-failure re-review" in (
        barrier
    )


def test_ac4_enforces_the_strict_architecture_boundary_everywhere():
    boundary = normalized(
        section(SKILL.read_text(), "## Product and Architecture Boundary")
    )

    assert "complete PRD implementation-neutral" in boundary
    assert "every normative section and field" in boundary
    for prohibited in (
        "components or internal ownership units",
        "technologies or implementation mechanisms",
        "detailed interfaces or technical contracts",
    ):
        assert prohibited in boundary
    assert "refuse it and identify the affected ID or section" in boundary
    assert "observable product need" in boundary
    assert "explicitly defer the design choice to the Architecture stage" in boundary
    assert "moving it into a measure, rationale, scenario, constraint" in boundary
    assert "return it to Discovery" in boundary


def test_ac5_resumes_canonical_working_state_without_reelicitation():
    raw_resume = section(SKILL.read_text(), "## Resume Before Elicitation")
    resume = normalized(raw_resume)
    lifecycle_forms = normalized(
        section(
            LIFECYCLE.read_text(),
            "### Canonical Gate and Working-State Templates",
        )
    )

    assert "`## Working state`" in resume
    assert "The reusable lifecycle forms are owned here" in lifecycle_forms
    assert (
        "`the-copilot-build-method` remains the sole owner of the Working "
        "state schema and field order"
    ) in resume
    assert "`product-requirements` owns where that block appears in a PRD" in resume
    assert "This skill defines neither schema" in resume
    fields = ("Status", "Open items", "Accepted so far", "Next action")
    canonical_order = (
        "`Status`, `Open items`, `Accepted so far`, and `Next action`"
    )
    assert f"canonical working-state field order is {canonical_order}" in (
        lifecycle_forms
    )
    field_positions = [raw_resume.index(f"`{field}`") for field in fields]
    assert field_positions == sorted(field_positions)
    assert (
        f"{canonical_order}, in that exact order"
    ) in resume
    assert "no renamed, reordered, duplicated, or additional field" in resume
    assert "owned open draft requirement IDs or human questions" in resume
    assert "one concrete action" in resume
    assert "Resume that single `Next action`" in resume
    assert "do not re-ask, redraft, or re-approve content" in resume
    assert "`Accepted so far`" in resume
    assert "another session can continue without replaying accepted content" in resume
    assert "remove the block or set its status to `accepted`" in resume
    assert "not by re-eliciting or rewriting its baseline" in resume


def test_edge_case_reconciles_exact_deferral_sets_without_changing_owner():
    text = SKILL.read_text()
    ownership = normalized(section(text, "## Authority and Ownership Boundaries"))
    deferrals = normalized(section(text, "## Deferral Reconciliation"))

    assert "Discovery dossier remains the sole owner of `DEF-###` records" in ownership
    assert "PRD deferral rows are references" in ownership
    assert "set `D`" in deferrals
    assert "every dossier-owned `DEF-###` that is both accepted and currently applicable" in (
        deferrals
    )
    assert "Do not infer acceptance or applicability from the readiness verdict alone" in (
        deferrals
    )
    assert "set `P` only from canonical reference-only rows" in deferrals
    assert "`## Constraints and deferrals`" in deferrals
    assert "product effect and required downstream disposition" in deferrals
    assert "require `D == P`" in deferrals
    for mismatch in (
        "missing or extra ID",
        "duplicate reference row",
        "redefinition",
        "Discovery-schema copy",
    ):
        assert mismatch in deferrals
    assert "never silently drop a deferral" in deferrals
    assert "transfer its ownership to the PRD" in deferrals


def test_edge_case_applies_exact_deferral_set_comparison_to_both_verdicts():
    deferrals = section(SKILL.read_text(), "## Deferral Reconciliation")
    expected = {
        "READY": (
            "Reconcile every accepted, applicable Discovery deferral and "
            "require exact set equality."
        ),
        "READY_WITH_DEFERRALS": (
            "Reconcile every accepted, applicable Discovery deferral and "
            "require exact set equality."
        ),
    }

    for verdict, handling in expected.items():
        row = f"| `{verdict}` | {handling} |"
        assert row in deferrals
    assert (
        "require `D == P` for both `READY` and `READY_WITH_DEFERRALS`"
        in normalized(deferrals)
    )
    assert (
        "`READY` with no accepted, applicable deferrals requires an empty "
        "PRD reference set"
    ) in normalized(deferrals)
    assert "a non-empty `D` must be carried for either verdict" in normalized(
        deferrals
    )


def test_happy_path_uses_canonical_prd_path_and_complete_human_approval():
    text = SKILL.read_text()
    approval = normalized(section(text, "## Final Human Approval"))

    assert "docs/requirements/VP<n>-<slug>/PRD.md" in approval
    assert "complete PRD and its exact source revision" in approval
    assert "canonical `## Approval` table from `product-requirements`" in approval
    for field in (
        "Actor",
        "Timestamp",
        "Scope",
        "Verdict",
        "Rationale",
        "Source revision",
    ):
        assert field in approval
    assert "human explicitly to approve, reject, or amend that exact revision" in approval
    assert "Only an attributable human `Approved` verdict" in approval
    assert "do not generate the human's values" in approval


def test_skill_delegates_schema_details_instead_of_defining_a_competing_schema():
    text = SKILL.read_text()
    flow = normalized(section(text, "## Interactive Translation Flow"))

    assert "sole authority for the PRD path and schema" in normalized(text)
    assert "does not restate or extend those contracts" in normalized(text)
    assert (
        "All PRD structure, field order, record allocation, impact classification, "
        "trace-resolution rules, and change-control details come directly from "
        "`product-requirements`"
    ) in flow
    assert "| ID | Schema version | Requirement |" not in text
    assert "| Field | Value |" not in text


def test_required_report_preserves_decisions_and_open_work():
    report = normalized(section(SKILL.read_text(), "## Required Session Report"))

    for expected in (
        "resolved single VP and PRD path",
        "Discovery verdict, human acceptance actor, and source revision",
        "entry validation command, status, and findings",
        "resumed Working state and next action",
        "proposed and effective `PR-###` and `QR-###` inventories",
        "final zero-failure re-review result and submitted source revision",
        "open IDs with owners",
        "architecture-boundary findings",
        "Discovery set `D`, PRD reference set `P`, their exact-equality result",
        "`DEF-###` downstream dispositions",
        "human approval response",
        "persisted next action",
    ):
        assert expected in report
