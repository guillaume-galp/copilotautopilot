import copy
import io
import json
import shutil
import sys
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from methodlib import activation, cli, exits, recovery  # noqa: E402


LEDGER = ROOT / activation.LEDGER_PATH
PROMOTION = {
    "actor": "Human: designer",
    "timestamp": "2026-09-07T03:06:55+01:00",
    "record": "docs/plan/control-promotions/TH3.E4.US5.md",
}


def ledger_document() -> dict[str, object]:
    document = yaml.safe_load(LEDGER.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def control(document: dict[str, object], identifier: str) -> dict[str, object]:
    controls = document["controls"]
    assert isinstance(controls, list)
    return next(item for item in controls if item["id"] == identifier)


def copy_file(root: Path, relative: str) -> None:
    source = ROOT / relative
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def write_repository(
    tmp_path: Path,
    document: dict[str, object] | None = None,
) -> Path:
    root = tmp_path / "repository"
    document = copy.deepcopy(document or ledger_document())
    ledger = root / activation.LEDGER_PATH
    ledger.parent.mkdir(parents=True)
    ledger.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    referenced: set[str] = {
        ".github/skills/backlog-management/SKILL.md",
        activation.BACKLOG_PATH.as_posix(),
        "bin/method",
        "bin/run-th3-e4-us5-evidence",
        "docs/plan/backlog-archive/TH1.yaml",
        "docs/plan/backlog-archive/TH2.yaml",
        "docs/plan/control-promotions/TH3.E4.US1.md",
        "docs/plan/control-promotions/TH3.E4.US5.md",
        activation.TH3_USAGE_WAIVER_PATH.as_posix(),
        "docs/requirements/VP3-discovery-led-cost-aware-methodology/PRD.md",
        "methodlib/activation.py",
        "methodlib/backlog.py",
        "methodlib/cli.py",
        "methodlib/docs.py",
        "methodlib/gates.py",
        "methodlib/lock.py",
        "methodlib/records.py",
        "methodlib/recovery.py",
        "methodlib/trace.py",
        "tests/fixtures/method_recovery/cases.yaml",
        "tests/test_method_activation.py",
        "tests/test_method_backlog.py",
        "tests/test_method_docs.py",
        "tests/test_e4_self_hosted_validation.py",
        "tests/test_method_gates.py",
        "tests/test_method_lock.py",
        "tests/test_method_trace.py",
    }
    referenced.update(recovery.command_dependency_files(ROOT))
    backlog_document = yaml.safe_load(
        (ROOT / activation.BACKLOG_PATH).read_text(encoding="utf-8")
    )
    pending: list[object] = [backlog_document]
    while pending:
        value = pending.pop()
        if isinstance(value, dict):
            story_file = value.get("file")
            if isinstance(story_file, str) and (ROOT / story_file).is_file():
                referenced.add(story_file)
            archive_ref = value.get("archive-ref")
            if isinstance(archive_ref, str) and (ROOT / archive_ref).is_file():
                referenced.add(archive_ref)
                pending.append(
                    yaml.safe_load(
                        (ROOT / archive_ref).read_text(encoding="utf-8")
                    )
                )
            pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)
    controls = document["controls"]
    assert isinstance(controls, list)
    for item in controls:
        if not isinstance(item, dict):
            continue
        promoter = item.get("promoted-by")
        if isinstance(promoter, dict):
            promotion_record = promoter.get("record")
            if (
                isinstance(promotion_record, str)
                and (ROOT / promotion_record).is_file()
            ):
                referenced.add(promotion_record)
        evidence = item.get("evidence", [])
        if isinstance(evidence, list):
            for evidence_path in evidence:
                if (
                    not isinstance(evidence_path, str)
                    or not (ROOT / evidence_path).is_file()
                ):
                    continue
                referenced.add(evidence_path)
                if Path(evidence_path).suffix not in {".yaml", ".yml"}:
                    continue
                evidence_record = yaml.safe_load(
                    (ROOT / evidence_path).read_text(encoding="utf-8")
                )
                if (
                    isinstance(evidence_record, dict)
                    and isinstance(evidence_record.get("run-output"), str)
                    and (ROOT / evidence_record["run-output"]).is_file()
                ):
                    referenced.add(evidence_record["run-output"])
    for relative in sorted(referenced):
        copy_file(root, relative)
    # Most focused waiver tests exercise the pre-acceptance path.  The real
    # repository is now archived, so reconstruct that isolated active fixture
    # without changing the authoritative acceptance boundary.
    fixture_backlog = yaml.safe_load(
        (root / activation.BACKLOG_PATH).read_text(encoding="utf-8")
    )
    summaries = fixture_backlog["backlog"]["archived-themes"]
    th3_summary = next(item for item in summaries if item["id"] == "TH3")
    archived_theme = yaml.safe_load(
        (root / th3_summary["archive-ref"]).read_text(encoding="utf-8")
    )["theme"]
    archived_theme["locked"] = False
    fixture_backlog["backlog"]["active-themes"] = [archived_theme]
    fixture_backlog["backlog"]["archived-themes"] = [
        item for item in summaries if item["id"] != "TH3"
    ]
    (root / activation.BACKLOG_PATH).write_text(
        yaml.safe_dump(fixture_backlog, sort_keys=False), encoding="utf-8"
    )
    waiver = root / activation.TH3_USAGE_WAIVER_PATH
    waiver.write_text(
        waiver.read_text(encoding="utf-8")
        .replace("| Status | Consumed |", "| Status | Open |")
        .partition("\n## Closure\n")[0]
        + "\n",
        encoding="utf-8",
    )
    return root


def write_recovery_evidence(
    root: Path,
    relative: str,
    *,
    control_id: str,
    kind: str,
    check: str,
    recovery_case: str = "fixture-recovery",
    fixture: str = "generated repository fixture",
    test_reference: str = (
        "tests/test_method_activation.py::"
        "test_each_enforced_target_missing_recovery_fails_closed_"
        "and_names_control"
    ),
) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            {
                "evidence-version": 1,
                "control-id": control_id,
                "evidence-kind": kind,
                "validator-check": check,
                "recovery-case": recovery_case,
                "fixture": fixture,
                "test-reference": test_reference,
                "observed-exit": 2 if kind == "bypass-attempt" else 0,
                "observed-at": "2026-09-06T23:19:56+01:00",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def set_promotion_decision(root: Path, decision: str) -> None:
    path = root / PROMOTION["record"]
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace(
            "| Decision | Promote CTL-001, CTL-002, CTL-003, and CTL-014 "
            "to ENFORCED. |",
            f"| Decision | {decision} |",
        ),
        encoding="utf-8",
    )


def test_real_ledger_has_complete_honest_control_inventory_and_validates():
    result = activation.validate_repository(ROOT)

    assert result.valid
    assert result.findings == ()
    assert tuple(item["id"] for item in result.controls) == (
        activation.REQUIRED_CONTROL_IDS
    )
    states = {item["id"]: item["state"] for item in result.controls}
    assert states == {
        "CTL-001": "ENFORCED",
        "CTL-002": "ENFORCED",
        "CTL-003": "ENFORCED",
        "CTL-004": "MANUAL",
        **{f"CTL-{number:03d}": "SPECIFIED" for number in range(5, 14)},
        "CTL-014": "ENFORCED",
    }


def test_cli_maturity_emits_one_json_object_and_exits_zero():
    result = cli.dispatch(["validate", "maturity", "--json"], probe_directory=ROOT)
    stdout, stderr = io.StringIO(), io.StringIO()

    status = cli.emit(result, stdout=stdout, stderr=stderr)
    payload = json.loads(stdout.getvalue())

    assert status == exits.SUCCESS
    assert len(stdout.getvalue().splitlines()) == 1
    assert payload["check"] == "maturity"
    assert payload["status"] == "ok"
    assert payload["states"] == list(activation.STATES)
    assert payload["findings"] == []
    assert stderr.getvalue() == ""


def test_th3_acceptance_report_is_honest_complete_and_closes_waiver():
    result = activation.validate_repository(ROOT)
    report = result.payload["acceptance-report"]

    assert result.valid
    assert isinstance(report, dict)
    assert report["theme"] == "TH3"
    assert report["theme-status"] == "done"
    assert report["usage"] == {
        "value": None,
        "confidence": "unknown",
        "source": "none",
        "sampled-at": None,
    }
    assert report["control-maturity"] == [
        {"id": item["id"], "state": item["state"]}
        for item in result.controls
    ]
    assert len(report["control-maturity"]) == len(activation.REQUIRED_CONTROL_IDS)
    assert report["open-waivers"] == []
    assert report["consumed-waivers"] == [
        {
            "id": "WVR-001",
            "control": "CTL-010",
            "path": activation.TH3_USAGE_WAIVER_PATH.as_posix(),
            "expiry": (
                "TH3 acceptance, or earlier if CTL-010 reaches `INSTRUMENTED`"
            ),
        }
    ]
    assert result.waivers[0]["status"] == "consumed"


def test_existing_human_delegated_usage_waiver_has_complete_attribution_and_scope():
    text = (ROOT / activation.TH3_USAGE_WAIVER_PATH).read_text(encoding="utf-8")
    document = ledger_document()

    assert all(f"| {field} |" in text for field in activation.WAIVER_IDENTITY_FIELDS)
    assert all(f"| {field} |" in text for field in activation.WAIVER_APPROVAL_FIELDS)
    assert activation.TH3_USAGE_WAIVER_PATH.as_posix() in control(
        document, "CTL-010"
    )["evidence"]
    for obligation in (
        "acceptance",
        "quality",
        "verification",
        "review",
        "Gitflow",
    ):
        assert obligation in text
    for field in activation.WAIVER_CLOSURE_FIELDS:
        assert f"| {field} |" in text
    assert f"| Timestamp | {activation.TH3_ACCEPTANCE_TIMESTAMP} |" in text
    assert f"| Source revision | {activation.TH3_ACCEPTANCE_SOURCE} |" in text


def test_acceptance_report_lists_every_open_waiver_with_expiry(tmp_path: Path):
    document = ledger_document()
    second_path = "docs/plan/waivers/TH3-budget-evidence.md"
    control(document, "CTL-011")["evidence"].append(second_path)
    root = write_repository(tmp_path, document)
    second = root / second_path
    second.parent.mkdir(parents=True, exist_ok=True)
    second.write_text(
        "\n".join(
            (
                "# TH3 Budget Evidence Waiver",
                "",
                "| Field | Value |",
                "|---|---|",
                "| Waiver ID | WVR-002 |",
                "| Control | CTL-011 Budget thresholds |",
                "| Theme | TH3 Discovery and requirements foundation |",
                "| Requirement waived | QR-013 budget evidence |",
                "| Status | Open |",
                "",
                "## Approval",
                "",
                "| Field | Value |",
                "|---|---|",
                "| Actor | Human: designer |",
                "| Timestamp | 2026-09-06T23:19:56+01:00 |",
                "| Scope | Missing TH3 budget evidence |",
                "| Verdict | Approved |",
                "| Rationale | Test fixture |",
                "| Source revision | fixture |",
                "| Expiry | TH3 acceptance |",
                "| Invalidation | Budget evidence becomes available |",
                "",
            )
        ),
        encoding="utf-8",
    )

    result = activation.validate_repository(root)
    report = result.payload["acceptance-report"]

    assert result.valid
    assert [item["id"] for item in report["open-waivers"]] == [
        "WVR-002",
        "WVR-001",
    ]
    assert all(item["expiry"] for item in report["open-waivers"])


@pytest.mark.parametrize(
    ("mutation", "expected"),
    (
        ("unreferenced", "unreferenced"),
        ("undated", "undated"),
        ("no-expiry", "expiry"),
    ),
)
def test_incomplete_or_unreferenced_usage_waiver_fails_closed(
    tmp_path: Path,
    mutation: str,
    expected: str,
):
    document = ledger_document()
    if mutation == "unreferenced":
        usage_control = control(document, "CTL-010")
        usage_control["evidence"] = [
            item
            for item in usage_control["evidence"]
            if item != activation.TH3_USAGE_WAIVER_PATH.as_posix()
        ]
    root = write_repository(tmp_path, document)
    waiver = root / activation.TH3_USAGE_WAIVER_PATH
    if mutation == "unreferenced":
        copy_file(root, activation.TH3_USAGE_WAIVER_PATH.as_posix())
    if mutation == "undated":
        waiver.write_text(
            waiver.read_text(encoding="utf-8").replace(
                "| Timestamp | 2026-09-05T17:02:11+01:00 |",
                "| Timestamp | 2026-09-05 |",
            ),
            encoding="utf-8",
        )
    elif mutation == "no-expiry":
        waiver.write_text(
            "\n".join(
                line
                for line in waiver.read_text(encoding="utf-8").splitlines()
                if not line.startswith("| Expiry |")
            )
            + "\n",
            encoding="utf-8",
        )

    result = activation.validate_repository(root)

    assert not result.valid
    assert any(
        finding["record"] == "WVR-001"
        and expected.lower() in str(finding["message"]).lower()
        for finding in result.findings
    )


def test_th4_cannot_reuse_th3_waiver_and_gets_own_waiver_remediation(
    tmp_path: Path,
):
    root = write_repository(tmp_path, ledger_document())
    backlog_path = root / activation.BACKLOG_PATH
    backlog = yaml.safe_load(backlog_path.read_text(encoding="utf-8"))
    th4 = copy.deepcopy(backlog["backlog"]["active-themes"][0])
    th4["id"] = "TH4"
    th4["name"] = "Context and verification controls"
    th4["epics"][0]["stories"][0]["evidence"]["usage"] = ["WVR-001"]
    backlog["backlog"]["active-themes"].append(th4)
    backlog_path.write_text(yaml.safe_dump(backlog, sort_keys=False), encoding="utf-8")

    result = activation.validate_repository(root)

    assert not result.valid
    finding = next(
        item
        for item in result.findings
        if item["record"] == "TH4" and "cannot reuse WVR-001" in item["message"]
    )
    assert "TH4-specific usage-evidence waiver" in finding["remediation"]
    assert "approve" in finding["remediation"]


def test_instrumentation_invalidates_waiver_and_requires_available_usage(
    tmp_path: Path,
):
    document = ledger_document()
    usage_control = control(document, "CTL-010")
    usage_control["state"] = "INSTRUMENTED"
    usage_control["promoted-by"] = dict(PROMOTION)
    root = write_repository(tmp_path, document)

    result = activation.validate_repository(root)

    assert not result.valid
    assert result.waivers[0]["status"] == "invalidated"
    assert result.payload["acceptance-report"]["open-waivers"] == []
    assert result.payload["acceptance-report"]["invalidated-waivers"][0][
        "id"
    ] == "WVR-001"
    assert any(
        finding["record"] == "WVR-001"
        and "invalidated early" in str(finding["message"])
        and "usage evidence is missing or unknown" in str(finding["message"])
        and "measured or estimated usage evidence"
        in str(finding["remediation"])
        for finding in result.findings
    )


@pytest.mark.parametrize(
    "replacement",
    (
        (
            "TH3 acceptance does not expire this waiver, or earlier if "
            "CTL-010 reaches `INSTRUMENTED`"
        ),
        (
            "TH3 acceptance may expire this waiver, or earlier if CTL-010 "
            "reaches `INSTRUMENTED`"
        ),
        (
            "TH3 acceptance, but not earlier if CTL-010 reaches "
            "`INSTRUMENTED`"
        ),
    ),
)
def test_usage_waiver_rejects_non_positive_expiry_wording(
    tmp_path: Path,
    replacement: str,
):
    root = write_repository(tmp_path, ledger_document())
    waiver = root / activation.TH3_USAGE_WAIVER_PATH
    waiver.write_text(
        waiver.read_text(encoding="utf-8").replace(
            activation.TH3_USAGE_WAIVER_EXPIRY,
            replacement,
        ),
        encoding="utf-8",
    )

    result = activation.validate_repository(root)

    assert not result.valid
    assert any(
        finding["record"] == "WVR-001"
        and "expiry is not the exact positive contract"
        in str(finding["message"])
        for finding in result.findings
    )


@pytest.mark.parametrize(
    "replacement",
    (
        (
            "Any of: a usage adapter becomes available but produces no "
            "`measured` or `estimated` samples for TH3; the waived scope is "
            "extended beyond usage evidence; TH3 is superseded or re-scoped "
            "by a PCR record"
        ),
        (
            "Any of: a usage adapter may become available and may produce "
            "`measured` or `estimated` samples for TH3; the waived scope is "
            "extended beyond usage evidence; TH3 is superseded or re-scoped "
            "by a PCR record"
        ),
        (
            "Any of: a usage adapter becomes available and does not need to "
            "produce `measured` or `estimated` samples for TH3; the waived "
            "scope is extended beyond usage evidence; TH3 is superseded or "
            "re-scoped by a PCR record"
        ),
    ),
)
def test_usage_waiver_rejects_non_positive_invalidation_wording(
    tmp_path: Path,
    replacement: str,
):
    root = write_repository(tmp_path, ledger_document())
    waiver = root / activation.TH3_USAGE_WAIVER_PATH
    waiver.write_text(
        waiver.read_text(encoding="utf-8").replace(
            activation.TH3_USAGE_WAIVER_INVALIDATION,
            replacement,
        ),
        encoding="utf-8",
    )

    result = activation.validate_repository(root)

    assert not result.valid
    assert any(
        finding["record"] == "WVR-001"
        and "invalidation is not the exact positive contract"
        in str(finding["message"])
        for finding in result.findings
    )


def test_missing_th3_usage_map_reports_explicit_unknown_while_waiver_is_valid(
    tmp_path: Path,
):
    root = write_repository(tmp_path, ledger_document())
    backlog_path = root / activation.BACKLOG_PATH
    backlog = yaml.safe_load(backlog_path.read_text(encoding="utf-8"))
    del backlog["backlog"]["active-themes"][0]["usage"]
    backlog_path.write_text(yaml.safe_dump(backlog, sort_keys=False), encoding="utf-8")

    result = activation.validate_repository(root)

    assert result.valid
    assert result.payload["acceptance-report"]["usage"] == {
        "value": None,
        "confidence": "unknown",
        "source": "none",
        "sampled-at": None,
    }
    assert result.payload["acceptance-report"]["open-waivers"][0]["id"] == "WVR-001"


@pytest.mark.parametrize(
    ("scope_kind", "scope_id"),
    (
        ("theme", "TH3"),
        ("epic", "TH3.E1"),
        ("story", "TH3.E1.US1"),
    ),
)
def test_instrumented_usage_blocks_missing_th3_usage_maps(
    tmp_path: Path,
    scope_kind: str,
    scope_id: str,
):
    document = ledger_document()
    usage_control = control(document, "CTL-010")
    usage_control["state"] = "INSTRUMENTED"
    usage_control["promoted-by"] = dict(PROMOTION)
    root = write_repository(tmp_path, document)
    backlog_path = root / activation.BACKLOG_PATH
    backlog = yaml.safe_load(backlog_path.read_text(encoding="utf-8"))
    theme = backlog["backlog"]["active-themes"][0]
    if scope_kind == "theme":
        del theme["usage"]
    elif scope_kind == "epic":
        del theme["epics"][0]["usage"]
    else:
        del theme["epics"][0]["stories"][0]["usage"]
    backlog_path.write_text(yaml.safe_dump(backlog, sort_keys=False), encoding="utf-8")

    result = activation.validate_repository(root)

    assert not result.valid
    assert result.payload["acceptance-report"]["usage"] == {
        "value": None,
        "confidence": "unknown",
        "source": "none",
        "sampled-at": None,
    }
    assert any(
        finding["record"] == "WVR-001"
        and scope_id in str(finding["message"])
        and "usage evidence is missing or unknown" in str(finding["message"])
        and "measured or estimated usage evidence"
        in str(finding["remediation"])
        for finding in result.findings
    )


def test_missing_usage_is_unknown_and_never_fabricated_as_zero(tmp_path: Path):
    root = write_repository(tmp_path, ledger_document())
    backlog_path = root / activation.BACKLOG_PATH
    backlog = yaml.safe_load(backlog_path.read_text(encoding="utf-8"))
    backlog["backlog"]["active-themes"][0]["usage"]["value"] = 0
    backlog_path.write_text(yaml.safe_dump(backlog, sort_keys=False), encoding="utf-8")

    result = activation.validate_repository(root)

    assert not result.valid
    assert result.payload["acceptance-report"]["usage"]["value"] == 0
    assert result.payload["acceptance-report"]["usage"]["confidence"] == "unknown"
    assert any(
        finding["record"] == "WVR-001"
        and "never zero" in str(finding["message"])
        for finding in result.findings
    )


def test_usage_waiver_cannot_replace_missing_verification_evidence(
    tmp_path: Path,
):
    root = write_repository(tmp_path, ledger_document())
    backlog_path = root / activation.BACKLOG_PATH
    backlog = yaml.safe_load(backlog_path.read_text(encoding="utf-8"))
    story = backlog["backlog"]["active-themes"][0]["epics"][3]["stories"][3]
    assert story["id"] == "TH3.E4.US4"
    story["evidence"]["verification"] = []
    story["verification"]["waivers"] = [
        {
            "check": "verification",
            "authority": "facilitator",
            "reviewer": "reviewer",
            "rationale": "Cites usage waiver",
            "record": "WVR-001",
        }
    ]
    backlog_path.write_text(yaml.safe_dump(backlog, sort_keys=False), encoding="utf-8")

    result = activation.validate_repository(root)

    assert not result.valid
    assert any(
        finding["record"] == "TH3.E4.US4"
        and "covers usage evidence only" in str(finding["message"])
        and "verification waiver" in str(finding["message"])
        for finding in result.findings
    )


def test_usage_waiver_record_rejects_scope_broadened_to_verification(
    tmp_path: Path,
):
    root = write_repository(tmp_path, ledger_document())
    waiver = root / activation.TH3_USAGE_WAIVER_PATH
    waiver.write_text(
        waiver.read_text(encoding="utf-8").replace(
            activation.TH3_USAGE_WAIVER_SCOPE,
            (
                "Missing AI-credit usage and verification evidence for every "
                "TH3 story, epic, and theme gate, for the duration of TH3"
            ),
        ),
        encoding="utf-8",
    )

    result = activation.validate_repository(root)

    assert not result.valid
    assert any(
        finding["record"] == "WVR-001"
        and "scope is not limited" in str(finding["message"])
        for finding in result.findings
    )


def test_manual_control_accepts_named_operator_without_automation_evidence(
    tmp_path: Path,
):
    document = ledger_document()
    manual = control(document, "CTL-004")
    manual["evidence"] = ["docs/ADRs/ADR-008-multi-theme-lock-and-activation-ledger.md"]
    root = write_repository(tmp_path, document)

    result = activation.validate_repository(root)

    assert result.valid
    assert not any(item["record"] == "CTL-004" for item in result.findings)


def test_unknown_state_fails_closed_with_closed_vocabulary(tmp_path: Path):
    document = ledger_document()
    control(document, "CTL-005")["state"] = "AUTOMATED"
    root = write_repository(tmp_path, document)

    result = activation.validate_repository(root)

    finding = next(item for item in result.findings if item["record"] == "CTL-005")
    assert not result.valid
    assert "outside the closed vocabulary" in finding["message"]
    assert all(state in finding["message"] for state in activation.STATES)


def test_empty_enforced_evidence_names_missing_bypass_and_recovery(
    tmp_path: Path,
):
    document = ledger_document()
    enforced = control(document, "CTL-001")
    enforced["evidence"] = []
    root = write_repository(tmp_path, document)

    result = activation.validate_repository(root)

    messages = [
        str(item["message"]) for item in result.findings if item["record"] == "CTL-001"
    ]
    assert not result.valid
    assert any(
        "missing bypass-attempt and restore-and-pass evidence" in message
        for message in messages
    )


@pytest.mark.parametrize(
    ("control_id", "checks"),
    (
        ("CTL-001", ("gates",)),
        ("CTL-002", ("schema",)),
        ("CTL-003", ("lock", "trace")),
        ("CTL-014", ("docs",)),
    ),
)
def test_each_enforced_target_missing_recovery_fails_closed_and_names_control(
    tmp_path: Path,
    control_id: str,
    checks: tuple[str, ...],
):
    document = ledger_document()
    item = control(document, control_id)
    item["state"] = "ENFORCED"
    item["promoted-by"] = dict(PROMOTION)
    item["evidence"] = [
        evidence
        for evidence in item["evidence"]
        if not (
            isinstance(evidence, str)
            and evidence.endswith("-restore-and-pass.yaml")
        )
    ]
    root = write_repository(tmp_path, document)

    result = activation.validate_repository(root)

    messages = [
        str(finding["message"])
        for finding in result.findings
        if finding["record"] == control_id
    ]
    assert not result.valid
    assert any("missing restore-and-pass evidence" in message for message in messages)


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    (
        ("actor", "reviewer-agent", "actor"),
        ("timestamp", "2026-09-06", "timestamp"),
        ("record", "", "record"),
    ),
)
def test_non_attributable_promotion_fails_closed(
    tmp_path: Path,
    field: str,
    value: str,
    expected: str,
):
    document = ledger_document()
    promoted = control(document, "CTL-004")
    promoted["promoted-by"] = {**PROMOTION, field: value}
    root = write_repository(tmp_path, document)

    result = activation.validate_repository(root)

    assert not result.valid
    assert any(
        item["record"] == "CTL-004" and expected in str(item["message"])
        for item in result.findings
    )


def test_claim_above_repository_implementation_fails_closed(tmp_path: Path):
    document = ledger_document()
    unsupported = control(document, "CTL-014")
    unsupported["state"] = "VERIFIED"
    unsupported["promoted-by"] = dict(PROMOTION)
    root = write_repository(tmp_path, document)

    result = activation.validate_repository(root)

    assert not result.valid
    assert any(
        item["record"] == "CTL-014"
        and "contradicts repository implementation" in str(item["message"])
        and "at most ENFORCED" in str(item["message"])
        for item in result.findings
    )


def test_verified_requires_evidence_from_a_completed_theme(tmp_path: Path):
    missing_document = ledger_document()
    control(missing_document, "CTL-001")["state"] = "VERIFIED"
    missing_root = write_repository(tmp_path / "missing", missing_document)

    missing = activation.validate_repository(missing_root)

    assert any(
        item["record"] == "CTL-001"
        and "lacks evidence from a completed theme" in str(item["message"])
        for item in missing.findings
    )

    complete_document = ledger_document()
    verified = control(complete_document, "CTL-001")
    verified["state"] = "VERIFIED"
    completed_path = (
        "docs/plan/evidence/control-activation/CTL-001-completed-theme.yaml"
    )
    verified["evidence"].append(completed_path)
    complete_root = write_repository(tmp_path / "complete", complete_document)
    set_promotion_decision(
        complete_root,
        "Promote CTL-001 to VERIFIED; promote CTL-002 and CTL-003 to "
        "ENFORCED; promote CTL-014 to ENFORCED.",
    )
    evidence_path = complete_root / completed_path
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        yaml.safe_dump(
            {
                "evidence-version": 1,
                "control-id": "CTL-001",
                "evidence-kind": "completed-theme",
                "theme": "TH1",
                "acceptance-record": "docs/plan/backlog-archive/TH1.yaml",
                "observed-at": "2026-09-06T23:19:56+01:00",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    complete = activation.validate_repository(complete_root)

    assert complete.valid


def test_missing_control_and_malformed_duplicate_yaml_fail_closed(tmp_path: Path):
    incomplete = ledger_document()
    incomplete["controls"] = incomplete["controls"][:-1]
    incomplete_root = write_repository(tmp_path / "incomplete", incomplete)
    incomplete_result = activation.validate_repository(incomplete_root)

    assert any(
        item["record"] == "controls" and "missing CTL-014" in item["message"]
        for item in incomplete_result.findings
    )

    malformed_root = tmp_path / "malformed"
    ledger = malformed_root / activation.LEDGER_PATH
    ledger.parent.mkdir(parents=True)
    ledger.write_text(
        "ledger-version: 1\nledger-version: 1\ncontrols: []\n",
        encoding="utf-8",
    )
    malformed_result = activation.validate_repository(malformed_root)

    assert not malformed_result.valid
    assert len(malformed_result.findings) == 1
    assert "duplicate keys" in malformed_result.findings[0]["message"]


def test_promoted_noncanonical_ledger_control_id_fails_closed(tmp_path: Path):
    document = ledger_document()
    promoted = copy.deepcopy(control(document, "CTL-004"))
    promoted["id"] = "CTL-000"
    controls = document["controls"]
    assert isinstance(controls, list)
    controls.append(promoted)
    root = write_repository(tmp_path, document)

    result = activation.validate_repository(root)

    assert not result.valid
    assert any(
        finding["record"] == "CTL-000"
        and "ledger control ID 'CTL-000' is not canonical"
        in str(finding["message"])
        for finding in result.findings
    )


def test_evidence_path_cannot_escape_repository(tmp_path: Path):
    document = ledger_document()
    item = control(document, "CTL-005")
    item["evidence"] = ["../../outside.yaml"]
    root = write_repository(tmp_path, document)

    result = activation.validate_repository(root)

    assert not result.valid
    assert any(
        finding["record"] == "CTL-005" and "unsafe" in str(finding["message"])
        for finding in result.findings
    )


@pytest.mark.parametrize(
    ("mutation", "expected"),
    (
        ("missing", "cannot be resolved safely"),
        ("unsafe-reference", "cannot be resolved safely"),
        ("actor", "does not match ledger actor"),
        ("timestamp", "does not match ledger timestamp"),
        ("control", "control/target-state decision"),
        ("target-state", "control/target-state decision"),
    ),
)
def test_adversarial_finding_1_promotion_record_must_resolve_and_match_ledger(
    tmp_path: Path,
    mutation: str,
    expected: str,
):
    document = ledger_document()
    root = write_repository(tmp_path, document)
    record_path = root / PROMOTION["record"]
    if mutation == "missing":
        record_path.unlink()
    elif mutation == "unsafe-reference":
        control(document, "CTL-001")["promoted-by"]["record"] = "README.md"
        (root / activation.LEDGER_PATH).write_text(
            yaml.safe_dump(document, sort_keys=False),
            encoding="utf-8",
        )
    else:
        text = record_path.read_text(encoding="utf-8")
        replacements = {
            "actor": (
                "| Actor | Human: designer |",
                "| Actor | Human: release owner |",
            ),
            "timestamp": (
                "| Timestamp | 2026-09-07T03:06:55+01:00 |",
                "| Timestamp | 2026-09-07T02:17:56+01:00 |",
            ),
            "control": (
                "Promote CTL-001, CTL-002, CTL-003, and CTL-014 to ENFORCED",
                "Promote CTL-002, CTL-003, and CTL-014 to ENFORCED",
            ),
            "target-state": (
                "Promote CTL-001, CTL-002, CTL-003, and CTL-014 to ENFORCED",
                "Promote CTL-001 to MANUAL; promote CTL-002, CTL-003, and "
                "CTL-014 to ENFORCED",
            ),
        }
        old, new = replacements[mutation]
        record_path.write_text(text.replace(old, new), encoding="utf-8")

    result = activation.validate_repository(root)

    assert not result.valid
    assert any(
        finding["record"] == "CTL-001" and expected in str(finding["message"])
        for finding in result.findings
    )


def test_promotion_decision_rejects_noncanonical_ctl_000_mutation(
    tmp_path: Path,
):
    root = write_repository(tmp_path, ledger_document())
    set_promotion_decision(
        root,
        "Promote CTL-001, CTL-002, CTL-003, and CTL-000 to ENFORCED; "
        "promote CTL-014 to ENFORCED.",
    )

    result = activation.validate_repository(root)

    assert not result.valid
    assert any(
        finding["record"] == "CTL-001"
        and "noncanonical control identifier: CTL-000"
        in str(finding["message"])
        for finding in result.findings
    )


@pytest.mark.parametrize(
    ("mutation", "value"),
    (
        ("arbitrary-test-file", "README.md"),
        (
            "missing-test-node",
            "tests/test_method_activation.py::test_no_such_recovery",
        ),
        (
            "test-mismatch",
            "tests/test_method_activation.py::"
            "test_real_ledger_has_complete_honest_control_inventory_and_validates",
        ),
        ("run-mismatch", "different-recovery-run"),
        ("control-mismatch", "CTL-002"),
        ("check-mismatch", "schema"),
        ("fixture-mismatch", "different generated fixture"),
    ),
)
def test_adversarial_finding_2_recovery_pair_binds_test_run_and_subject(
    tmp_path: Path,
    mutation: str,
    value: str,
):
    document = ledger_document()
    enforced = control(document, "CTL-001")
    bypass_path = "docs/plan/evidence/control-activation/adversarial-bypass.yaml"
    restore_path = "docs/plan/evidence/control-activation/adversarial-restore.yaml"
    enforced["evidence"] = [bypass_path, restore_path]
    root = write_repository(tmp_path, document)
    write_recovery_evidence(
        root,
        bypass_path,
        control_id="CTL-001",
        kind="bypass-attempt",
        check="gates",
    )
    restore_values = {
        "control_id": "CTL-001",
        "check": "gates",
        "recovery_case": "fixture-recovery",
        "fixture": "generated repository fixture",
        "test_reference": (
            "tests/test_method_activation.py::"
            "test_each_enforced_target_missing_recovery_fails_closed_"
            "and_names_control"
        ),
    }
    keys = {
        "arbitrary-test-file": "test_reference",
        "missing-test-node": "test_reference",
        "test-mismatch": "test_reference",
        "run-mismatch": "recovery_case",
        "control-mismatch": "control_id",
        "check-mismatch": "check",
        "fixture-mismatch": "fixture",
    }
    restore_values[keys[mutation]] = value
    write_recovery_evidence(
        root,
        restore_path,
        kind="restore-and-pass",
        **restore_values,
    )

    result = activation.validate_repository(root)

    assert not result.valid
    assert any(
        finding["record"] == "CTL-001"
        and (
            "incomplete recovery facts" in str(finding["message"])
            or "must contain exactly" in str(finding["message"])
            or "missing restore-and-pass evidence" in str(finding["message"])
            or "is not bound to the same control" in str(finding["message"])
        )
        for finding in result.findings
    )


@pytest.mark.parametrize(
    "mutation",
    ("arbitrary-acceptance", "different-theme", "unlocked-summary"),
)
def test_adversarial_finding_3_verified_resolves_canonical_accepted_theme(
    tmp_path: Path,
    mutation: str,
):
    document = ledger_document()
    verified = control(document, "CTL-001")
    verified["state"] = "VERIFIED"
    evidence_relative = (
        "docs/plan/evidence/control-activation/CTL-001-adversarial-completed-theme.yaml"
    )
    verified["evidence"].append(evidence_relative)
    root = write_repository(tmp_path, document)
    set_promotion_decision(
        root,
        "Promote CTL-001 to VERIFIED; promote CTL-002 and CTL-003 to "
        "ENFORCED; promote CTL-014 to ENFORCED.",
    )
    theme = "TH1"
    acceptance = "docs/plan/backlog-archive/TH1.yaml"
    if mutation == "arbitrary-acceptance":
        acceptance = "docs/plan/evidence/control-activation/arbitrary.txt"
        arbitrary = root / acceptance
        arbitrary.parent.mkdir(parents=True, exist_ok=True)
        arbitrary.write_text("accepted", encoding="utf-8")
    elif mutation == "different-theme":
        theme = "TH2"
    else:
        backlog_path = root / activation.BACKLOG_PATH
        backlog = yaml.safe_load(backlog_path.read_text(encoding="utf-8"))
        backlog["backlog"]["archived-themes"][0]["locked"] = False
        backlog_path.write_text(
            yaml.safe_dump(backlog, sort_keys=False),
            encoding="utf-8",
        )
    evidence = root / evidence_relative
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(
        yaml.safe_dump(
            {
                "evidence-version": 1,
                "control-id": "CTL-001",
                "evidence-kind": "completed-theme",
                "theme": theme,
                "acceptance-record": acceptance,
                "observed-at": "2026-09-06T23:19:56+01:00",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = activation.validate_repository(root)

    assert not result.valid
    assert any(
        finding["record"] == "CTL-001"
        and "canonical backlog" in str(finding["message"])
        for finding in result.findings
    )


def test_verified_rejects_redirected_archive_ref_with_matching_locked_theme(
    tmp_path: Path,
):
    document = ledger_document()
    verified = control(document, "CTL-001")
    verified["state"] = "VERIFIED"
    evidence_relative = (
        "docs/plan/evidence/control-activation/CTL-001-redirected-theme.yaml"
    )
    verified["evidence"].append(evidence_relative)
    root = write_repository(tmp_path, document)
    set_promotion_decision(
        root,
        "Promote CTL-001 to VERIFIED; promote CTL-002 and CTL-003 to "
        "ENFORCED; promote CTL-014 to ENFORCED.",
    )
    redirected = "docs/plan/backlog-archive/TH1-redirected.yaml"
    backlog_path = root / activation.BACKLOG_PATH
    backlog_document = yaml.safe_load(backlog_path.read_text(encoding="utf-8"))
    backlog_document["backlog"]["archived-themes"][0]["archive-ref"] = redirected
    backlog_path.write_text(
        yaml.safe_dump(backlog_document, sort_keys=False),
        encoding="utf-8",
    )
    redirected_path = root / redirected
    shutil.copy2(
        root / "docs/plan/backlog-archive/TH1.yaml",
        redirected_path,
    )
    evidence = root / evidence_relative
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(
        yaml.safe_dump(
            {
                "evidence-version": 1,
                "control-id": "CTL-001",
                "evidence-kind": "completed-theme",
                "theme": "TH1",
                "acceptance-record": redirected,
                "observed-at": "2026-09-06T23:19:56+01:00",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = activation.validate_repository(root)

    assert not result.valid
    assert any(
        finding["record"] == "CTL-001"
        and "canonical backlog" in str(finding["message"])
        for finding in result.findings
    )


@pytest.mark.parametrize(
    ("control_id", "relative", "old", "new", "check"),
    (
        (
            "CTL-001",
            "methodlib/cli.py",
            'if check == "gates":',
            'if check == "gates-disabled":',
            "gates",
        ),
        (
            "CTL-002",
            "methodlib/backlog.py",
            "return _validate_repository(repository_root)",
            "return ValidationResult(())",
            "schema",
        ),
        (
            "CTL-003",
            "methodlib/trace.py",
            "return _validate_repository(repository_root)",
            "return ValidationResult((), (), ())",
            "trace",
        ),
    ),
)
def test_adversarial_finding_4_support_requires_live_cli_capability_contract(
    tmp_path: Path,
    control_id: str,
    relative: str,
    old: str,
    new: str,
    check: str,
):
    root = write_repository(tmp_path, ledger_document())
    capability = root / relative
    original = capability.read_text(encoding="utf-8")
    assert old in original
    capability.write_text(original.replace(old, new, 1), encoding="utf-8")
    assert capability.is_file()

    result = activation.validate_repository(root)

    assert not result.valid
    assert any(
        finding["record"] == control_id
        and "CLI capability contracts are unavailable" in str(finding["message"])
        and check in str(finding["message"])
        for finding in result.findings
    )


@pytest.mark.parametrize("source", ("dangling", "other-prd"))
def test_adversarial_finding_5_requirement_refs_resolve_in_applicable_prd(
    tmp_path: Path,
    source: str,
):
    document = ledger_document()
    control(document, "CTL-004")["requirements"] = ["PR-999"]
    root = write_repository(tmp_path, document)
    if source == "other-prd":
        wrong_prd = root / "docs/requirements/VP99-other/PRD.md"
        wrong_prd.parent.mkdir(parents=True)
        wrong_prd.write_text(
            "\n".join(
                (
                    "# Wrong PRD",
                    "",
                    "| Field | Value |",
                    "|---|---|",
                    "| Product | Other |",
                    "| Vision | VP99: Other |",
                    "| Status | Approved |",
                    "",
                    "## Functional requirements",
                    "",
                    "| ID | Requirement | Traces |",
                    "|---|---|---|",
                    "| PR-999 | Unrelated requirement. | VO-001 |",
                    "",
                )
            ),
            encoding="utf-8",
        )

    result = activation.validate_repository(root)

    assert not result.valid
    assert any(
        finding["record"] == "CTL-004"
        and "PR-999 does not resolve in the applicable canonical PRD"
        in str(finding["message"])
        for finding in result.findings
    )
