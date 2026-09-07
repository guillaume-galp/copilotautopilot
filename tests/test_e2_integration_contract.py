"""Cross-validator release gate for TH3.E2."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from methodlib import exits, gates, records, trace as trace_validator  # noqa: E402


METHOD = ROOT / "bin" / "method"
VP3_DISCOVERY = "docs/discovery/VP3-discovery-led-cost-aware-methodology"


def run_method(
    *arguments: str,
) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
    result = subprocess.run(
        [str(METHOD), *arguments],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    lines = result.stdout.splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert isinstance(payload, dict)
    return result, payload


def test_real_e2_release_gate_has_accepted_architecture_and_zero_trace_findings():
    """The real gate accepts the canonical architecture trace without residuals."""

    doctor_result, doctor = run_method("doctor")
    assert doctor_result.returncode == exits.SUCCESS
    assert doctor["status"] == "ok"

    discovery_records = records.index_vp(
        VP3_DISCOVERY,
        repository_root=ROOT,
    )
    assert not discovery_records.findings
    assert {
        "DQ",
        "EV",
        "ASM",
        "DEC",
        "INV",
        "RSK",
        "DEF",
        "EXP",
        "DR",
    } <= {record.prefix for record in discovery_records.records}

    schema_result, schema = run_method("validate", "schema", "--json")
    assert schema_result.returncode == exits.SUCCESS
    assert schema["findings"] == []

    for stage in ("discovery", "requirements", "architecture"):
        gate_result, gate = run_method(
            "validate",
            "gates",
            "--vp",
            "VP3",
            "--stage",
            stage,
            "--json",
        )
        assert gate_result.returncode == exits.SUCCESS
        assert gate["stage_entry"] == "open"
        assert gate["findings"] == []

    planning_result, planning = run_method(
        "validate",
        "gates",
        "--vp",
        "VP3",
        "--stage",
        "planning",
        "--json",
    )
    assert planning_result.returncode == exits.SUCCESS
    assert planning["stage_entry"] == "open"
    assert planning["findings"] == []
    acceptance = planning["upstream_gates"][0]
    assert acceptance["actor"] == "Human: product owner"
    assert acceptance["timestamp"] == "2026-09-07T18:06:28+01:00"
    assert acceptance["scope"] == (
        "VP3 architecture packet dispatch, workspace authorization, "
        "reconciliation, and Cockpit boundary"
    )
    assert acceptance["verdict"] == "Accepted"
    architecture_readme = ROOT / "docs/architecture/README.md"
    assert acceptance["source_revision"] == gates._architecture_revision(
        ROOT, architecture_readme
    )

    scope, mappings, accepted, declaration_findings = (
        trace_validator._architecture_trace_declaration(ROOT)
    )
    assert scope == "VP3"
    assert accepted
    assert declaration_findings == []
    by_record = {
        record: [mapping for mapping in mappings if record in mapping.records]
        for mapping in mappings
        for record in mapping.records
    }
    for record in ("ASM-001", "ASM-009", "DEC-003"):
        assert any(
            mapping.theme == "TH3"
            and "ADR-002" in mapping.adrs
            and mapping.requirements
            and mapping.stories
            for mapping in by_record[record]
        )
    residual_records = {
        *(f"ASM-{number:03d}" for number in range(1, 11)),
        "DEC-003",
        "DEC-009",
        "DEC-022",
        "QR-016",
        *(
            f"RSK-{number:03d}"
            for number in (1, 2, 3, 5, 6, 7, 9, 10, 11, 12)
        ),
        *(f"PR-{number:03d}" for number in range(101, 116)),
        *(f"PR-{number:03d}" for number in range(201, 216)),
    }
    assert residual_records <= set(by_record)
    assert all(
        not mapping.stories
        for mapping in mappings
        if mapping.theme in {"TH4", "TH5"}
    )

    lock_result, lock = run_method("validate", "lock", "--json")
    assert lock_result.returncode == exits.SUCCESS
    assert lock["findings"] == []
    manifest = lock["manifest"]
    assert isinstance(manifest, dict)
    assert {theme["id"] for theme in manifest["themes"]} == {"TH1", "TH2", "TH3"}
    assert {adr["id"] for adr in manifest["adrs"]} == {
        f"ADR-{number:03d}" for number in range(1, 9)
    }
    vp3 = next(vp for vp in manifest["vps"] if vp["id"] == "VP3")
    assert vp3["status"] == "unlocked"
    assert vp3["mapped_themes"] == ["TH3", "TH4", "TH5"]

    trace_result, trace = run_method("validate", "trace", "--json")
    assert trace_result.returncode == exits.SUCCESS
    assert trace["status"] == "ok"
    assert trace["findings"] == []
