"""Contract tests for the TH3.E3.US1 interactive discover skill."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".github" / "skills" / "discover" / "SKILL.md"


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


def test_ac1_interactive_flow_runs_from_disposition_to_bounded_verdict():
    text = SKILL.read_text()

    assert "name: discover" in text
    assert "`the-copilot-build-method`" in text
    assert "`discovery-dossier`" in text
    headings = (
        "## Disposition Classification",
        "## Question Framing and Investigation",
        "## Grouped Human Checkpoint",
        "## Readiness Validation Barrier",
    )
    positions = [text.index(heading) for heading in headings]
    assert positions == sorted(positions)
    report = normalized(section(text, "## Required Session Report"))
    for outcome in (
        "confirmed disposition",
        "DQ IDs",
        "investigation outcomes",
        "proposed verdict",
        "persisted next action",
    ):
        assert outcome in report


def test_happy_path_lightweight_has_one_grouped_checkpoint_and_30_minute_cap():
    text = SKILL.read_text()
    checkpoint = normalized(section(text, "## Grouped Human Checkpoint"))

    assert "at most one grouped human checkpoint for the entire run" in checkpoint
    assert "30 cumulative minutes of human interaction" in checkpoint
    assert "disposition confirmation" in checkpoint
    assert "verdict acceptance" in checkpoint
    assert "stop asking questions" in checkpoint
    assert "persist the next action and report `BLOCKED`" in checkpoint
    assert "never disguise a second checkpoint" in checkpoint


def test_edge_case_material_expansion_invalidates_waiver_before_work_continues():
    text = SKILL.read_text()
    waiver = normalized(section(text, "### WAIVED re-evaluation"))

    for dimension in (
        "users",
        "outcomes",
        "behavior",
        "integrations",
        "data sensitivity",
        "authority boundaries",
        "risk",
        "delivery impact",
    ):
        assert dimension in normalized(
            section(text, "## Disposition Classification")
        )
    assert "material scope expansion as an invalidation condition" in waiver
    assert "Any material expansion invalidates the waiver automatically" in waiver
    assert "omitted by the recorded invalidation text" in waiver
    assert "Stop work under the waiver" in waiver
    assert "as `LIGHTWEIGHT` or `FULL`" in waiver
    assert "before any investigation or other work continues" in waiver


def test_error_case_accepts_canonical_split_result_before_recommendation():
    text = SKILL.read_text()
    barrier = normalized(section(text, "## Readiness Validation Barrier"))
    command = "method validate gates --vp <vp> --stage discovery"

    assert text.count(command) == 1
    assert "run exactly" in barrier
    assert "after the last dossier write" in barrier
    assert "before every readiness recommendation" in barrier
    assert (
        "top-level `findings` decide entry to Discovery, while "
        "`completion_findings` describe the downstream requirements gate"
    ) in barrier
    for entry_field in (
        "`command: validate`",
        "`check: gates`",
        "`status: ok`",
        "`stage: discovery`",
        "`stage_entry: open`",
        "`findings: []`",
    ):
        assert entry_field in barrier
    for downstream_field in (
        "`stage: requirements`",
        "`name: discovery-readiness`",
        "`Acceptance` section",
        "`status: closed`",
    ):
        assert downstream_field in barrier
    for placeholder in (
        "`Actor: <actor>`",
        "`Timestamp: <timestamp-with-UTC-offset>`",
        "`Scope: <exact-scope>`",
        "`Disposition: <FULL-or-LIGHTWEIGHT>`",
        "`Verdict: <readiness-verdict-not-accepted>`",
        "`Rationale: <rationale>`",
        "`Source revision: <source-revision>`",
    ):
        assert placeholder in barrier
    assert (
        "`completion_findings` must equal `downstream_gate.findings`"
        in barrier
    )
    assert (
        "consist exactly of the validator's eleven derivative "
        "`discovery-readiness` diagnostics"
    ) in barrier
    assert "the seven required-field findings" in barrier
    for derivative in ("Scope", "Disposition", "Verdict", "Source revision"):
        assert derivative in barrier
    assert (
        "No working-state, dossier-record, deferral, or other completion "
        "finding is allowed"
    ) in barrier
    assert (
        "expected `completion_findings` in either accepted state do not reject "
        "the pre-recommendation result"
    ) in barrier
    assert "neither state opens the requirements gate" in barrier


def test_waived_pre_recommendation_shape_is_validated_but_never_opens():
    text = SKILL.read_text()
    barrier = normalized(section(text, "## Readiness Validation Barrier"))

    assert "sole additional completion state is a prospective `WAIVED` acceptance" in (
        barrier
    )
    assert "current human explicitly approved the waiver" in barrier
    assert "Do not infer that approval from repository content or an agent proposal" in (
        barrier
    )
    assert (
        "exactly these fields in this order: `Actor`, `Timestamp`, `Scope`, "
        "`Disposition`, `Verdict`, `Rationale`, `Source revision`, `Expiry`, "
        "and `Invalidation`"
    ) in barrier
    for requirement in (
        "exact registered human authority",
        "ISO-8601 timestamp with an explicit UTC offset",
        "exact current scope and covers the requested VP",
        "`Disposition` is exactly `WAIVED`",
        "`Verdict` is exactly `BLOCKED`",
        "fresh immutable revision",
        "`Expiry` is present, bounded",
        "has not expired or occurred",
        "`Invalidation` is present, specific",
        "names `material scope expansion`",
    ):
        assert requirement in barrier
    assert (
        "`Discovery verdict is BLOCKED and does not open a downstream gate.`"
        in barrier
    )
    assert "closed downstream status are mandatory" in barrier
    assert "permits presenting a recommendation only and never opens requirements" in (
        barrier
    )


def test_waived_final_acceptance_is_human_only_and_revalidated():
    text = SKILL.read_text()
    barrier = normalized(section(text, "## Readiness Validation Barrier"))

    assert "final acceptance must remain attributable to the human" in barrier
    assert "preserve the exact scope, `Disposition: WAIVED`" in barrier
    assert "active bounded `Expiry`" in barrier
    assert "material-expansion `Invalidation`" in barrier
    assert "replace `BLOCKED` with the human's explicit `READY` or " in barrier
    assert "`READY_WITH_DEFERRALS` verdict" in barrier
    assert "run the exact validation command again" in barrier
    assert "no top-level or completion findings" in barrier
    assert "gate as `open`" in barrier
    assert "never converted to a positive verdict by an agent" in barrier


def test_error_case_incomplete_attempted_acceptance_fails_closed():
    text = SKILL.read_text()
    barrier = normalized(section(text, "## Readiness Validation Barrier"))

    assert (
        "Any change to one or more of those seven scaffold values is an "
        "attempted acceptance"
    ) in barrier
    assert "not the untouched-scaffold exception" in barrier
    assert "is incomplete or invalid and is not the exact prospective `WAIVED` shape" in (
        barrier
    )
    assert (
        "the command still exits `0` with `status: ok`, `stage_entry: open`, "
        "and errors only in `completion_findings`"
    ) in barrier
    for failure in (
        "cannot run",
        "non-zero status",
        "malformed or missing results",
        "top-level finding",
        "different VP",
        "non-exempt completion finding",
    ):
        assert failure in barrier
    assert "fails closed" in barrier
    assert "Do not present `READY` or `READY_WITH_DEFERRALS`" in barrier
    assert "do not proceed to requirements" in barrier
    for finding_field in ("check", "file", "record", "message", "remediation"):
        assert finding_field in barrier
    assert "incomplete acceptance record" in barrier
    assert "the skill must not complete it itself" in barrier
    assert "run the exact command again" in barrier
    for waiver_failure in (
        "expired or occurred `Expiry`",
        "malformed or unbounded expiry",
        "missing `material scope expansion` invalidation",
        "material expansion",
        "non-human actor",
    ):
        assert waiver_failure in barrier


def test_ac4_every_dq_is_bounded_and_unknowns_have_owner_and_disposition():
    text = SKILL.read_text()
    framing = normalized(
        section(text, "## Question Framing and Investigation")
    )
    barrier = normalized(section(text, "## Readiness Validation Barrier"))

    assert "Before any question is delegated" in framing
    assert "explicit budget" in framing
    assert "objective stop condition" in framing
    assert "one accountable owner" in framing
    assert "a current disposition" in framing
    assert (
        "Missing budget or stop condition means the question is not dispatchable"
        in framing
    )
    assert "Missing owner or disposition means the unknown is a readiness blocker" in (
        framing
    )
    assert "unresolved `unknown` blocks `READY` and `READY_WITH_DEFERRALS`" in (
        framing
    )
    assert "re-check every DQ budget and stop condition" in barrier
    assert "owner and disposition of every item classified `unknown`" in barrier


def test_ac5_all_writes_are_delegated_and_human_keeps_authority_and_ownership():
    text = SKILL.read_text()
    boundaries = normalized(section(text, "## Authority and Ownership Boundaries"))

    assert "The human is the authority" in boundaries
    assert "`discover` and every delegated agent are proposers" in boundaries
    assert "They never approve" in boundaries
    delegated_writes = (
        "Delegate every dossier create, update, acceptance, applicability, "
        "and working-state write to `@discovery-facilitator`"
    )
    assert delegated_writes in boundaries
    assert "`discover` never writes the dossier directly" in boundaries
    assert "only `discover` presents it to the human after the validation barrier" in (
        boundaries
    )
    assert "PRD is the sole owner of canonical `VO-###` records" in boundaries
    assert "Discovery dossier is the sole owner of `DEF-###` records" in boundaries
    assert "only the human's complete acceptance opens the gate" in normalized(
        text
    )
