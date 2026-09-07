"""Integration proof for TH3.E4.US5 self-hosted validation."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Mapping, Sequence

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from methodlib import (  # noqa: E402
    activation,
    cli,
    exits,
    lock,
    recovery,
    self_hosted,
    trace,
)


METHOD = ROOT / "bin/method"
EVIDENCE_RUNNER = ROOT / recovery.RUNNER_PATH
FIXTURES = ROOT / "tests/fixtures/method_validate_all"
VERIFICATION_REPORT = ROOT / self_hosted.REPORT_PATH
PROMOTION_RECORD = ROOT / "docs/plan/control-promotions/TH3.E4.US5.md"
LOCKED_STORY = (
    "docs/themes/TH2-gitflow-operator/E1-gitflow-operator/"
    "stories/US1-develop-branch-workflow.md"
)
US5_STORY = (
    "docs/themes/TH3-discovery-requirements-foundation/epics/"
    "E4-activation-migration-integration/stories/"
    "US5-self-hosted-validation-run.md"
)
DISCOVERY_README = (
    "docs/discovery/VP3-discovery-led-cost-aware-methodology/README.md"
)
LOAD_RECORD_COUNT = self_hosted.LOAD_RECORD_COUNT
LOAD_MULTIPLIER = self_hosted.LOAD_MULTIPLIER


class SnapshotReader:
    """Immutable local baseline for copied repositories without Git metadata."""

    def __init__(self, root: Path) -> None:
        self.entries = tuple(
            self._entry(root, path)
            for path in sorted(root.rglob("*"))
            if path.is_file() or path.is_symlink()
        )

    @staticmethod
    def _entry(root: Path, path: Path) -> lock.BaselineEntry:
        if path.is_symlink():
            mode = "120000"
            content = os.fsencode(os.readlink(path))
        else:
            mode = "100755" if path.stat().st_mode & 0o111 else "100644"
            content = path.read_bytes()
        return lock.BaselineEntry(
            path=path.relative_to(root).as_posix(),
            mode=mode,
            content=content,
        )

    def read(
        self,
        _revision: str,
        paths: Sequence[str],
    ) -> tuple[lock.BaselineEntry, ...]:
        return self._within(paths)

    def read_committed(
        self,
        paths: Sequence[str],
        since_revision: str,
    ) -> tuple[str, tuple[lock.BaselineEntry, ...]]:
        return since_revision, self._within(paths)

    def _within(
        self,
        paths: Sequence[str],
    ) -> tuple[lock.BaselineEntry, ...]:
        return tuple(
            entry
            for entry in self.entries
            if any(
                entry.path == scope or entry.path.startswith(scope + "/")
                for scope in paths
            )
        )


def copy_repository(tmp_path: Path, *, include_git: bool = False) -> Path:
    root = tmp_path / "repository"
    ignored = [
        ".pytest_cache",
        ".mypy_cache",
        "__pycache__",
        ".coverage",
        "*.pyc",
    ]
    if not include_git:
        ignored.append(".git")
    shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns(*ignored))
    return root


def fixture_document(kind: str) -> Mapping[str, object]:
    path = FIXTURES / kind / "checks.yaml"
    text = path.read_text(encoding="utf-8")
    assert text.startswith("<!-- method-validate-docs: fixture -->")
    document = yaml.safe_load(text.split("\n", 1)[1])
    assert isinstance(document, Mapping)
    assert document["fixture-version"] == 1
    cases = document["cases"]
    assert isinstance(cases, Mapping)
    return cases


def control(document: Mapping[str, object], identifier: str) -> dict[str, object]:
    controls = document["controls"]
    assert isinstance(controls, list)
    return next(
        candidate
        for candidate in controls
        if isinstance(candidate, dict) and candidate.get("id") == identifier
    )


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert text.count(old) == 1
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def mutate_repository(root: Path, mutation: str) -> None:
    if mutation == "none":
        return
    if mutation == "malformed-backlog":
        (root / activation.BACKLOG_PATH).write_text(
            "backlog:\n  active-themes: [\n",
            encoding="utf-8",
        )
        return
    if mutation == "blocked-discovery-gate":
        replace_once(
            root / DISCOVERY_README,
            "| Verdict | READY_WITH_DEFERRALS |",
            "| Verdict | BLOCKED |",
        )
        return
    if mutation == "edited-locked-story":
        path = root / LOCKED_STORY
        path.write_text(
            path.read_text(encoding="utf-8") + "\nunauthorized mutation\n",
            encoding="utf-8",
        )
        return
    if mutation == "dangling-story-trace":
        replace_once(
            root / US5_STORY,
            "requirements: [PR-015, QR-002, QR-003, QR-010, QR-011]",
            "requirements: [PR-999, QR-002, QR-003, QR-010, QR-011]",
        )
        return
    if mutation == "missing-docs-recovery":
        path = root / activation.LEDGER_PATH
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        docs_control = control(document, "CTL-014")
        evidence = docs_control["evidence"]
        assert isinstance(evidence, list)
        docs_control["evidence"] = [
            item
            for item in evidence
            if not (
                isinstance(item, str)
                and item.endswith("CTL-014-docs-restore-and-pass.yaml")
            )
        ]
        path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
        return
    if mutation == "stale-active-document":
        path = root / ".github/skills/stale-fixture/SKILL.md"
        path.parent.mkdir(parents=True)
        path.write_text(
            "# Stale fixture\n\nThe lifecycle has " + "four" + " stages.\n",
            encoding="utf-8",
        )
        return
    if mutation in {
        "th3-archive-index-in-progress",
        "th3-archive-index-unlocked",
        "th3-archive-payload-in-progress",
        "th3-archive-payload-unlocked",
        "th3-archive-payload-schema-v1",
    }:
        if mutation.startswith("th3-archive-payload"):
            path = root / activation.TH3_ARCHIVE_PATH
            document = yaml.safe_load(path.read_text(encoding="utf-8"))
            payload = document["theme"]
            if mutation == "th3-archive-payload-in-progress":
                payload["status"] = "in-progress"
            elif mutation == "th3-archive-payload-unlocked":
                payload["locked"] = False
            else:
                payload["schema-version"] = 1
            path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
            return
        path = root / activation.BACKLOG_PATH
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        summaries = document["backlog"]["archived-themes"]
        summary = next(item for item in summaries if item["id"] == "TH3")
        if mutation == "th3-archive-index-in-progress":
            summary["status"] = "in-progress"
        else:
            summary["locked"] = False
        path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
        return
    if mutation in {
        "th3-release-actor",
        "th3-session-actor",
        "th3-waiver-actor",
    }:
        relative = {
            "th3-release-actor": activation.TH3_RELEASE_PATH,
            "th3-session-actor": activation.SESSION_LOG_PATH,
            "th3-waiver-actor": activation.TH3_USAGE_WAIVER_PATH,
        }[mutation]
        path = root / relative
        if mutation == "th3-session-actor":
            replace_once(
                path,
                "## TH3 Human Acceptance Boundary\n\n"
                "| Field | Value |\n|---|---|\n| Actor | Human: designer |",
                "## TH3 Human Acceptance Boundary\n\n"
                "| Field | Value |\n|---|---|\n| Actor | Human: release owner |",
            )
        else:
            replace_once(
                path,
                "| Actor | Human: designer |",
                "| Actor | Human: release owner |",
            )
        return
    raise AssertionError(f"unsupported fixture mutation: {mutation}")


def dispatch_fixture(
    root: Path,
    case: Mapping[str, object],
) -> cli.CommandResult:
    arguments = case["arguments"]
    assert isinstance(arguments, list)
    assert all(isinstance(item, str) for item in arguments)
    return cli.dispatch(arguments, probe_directory=root)


def one_json_object(output: str) -> dict[str, object]:
    decoder = json.JSONDecoder()
    value, end = decoder.raw_decode(output)
    assert isinstance(value, dict)
    assert output[end:].strip() == ""
    assert len(output.splitlines()) == 1
    return value


def replace_retained_json(
    root: Path,
    identifier: str,
    value: Mapping[str, object],
) -> None:
    relative = self_hosted.EXPECTED_ARTIFACTS[identifier][1]
    output = root / relative
    encoded = (
        json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    output.write_bytes(encoded)
    report_path = root / self_hosted.REPORT_PATH
    report = yaml.safe_load(report_path.read_text(encoding="utf-8"))
    artifact = next(
        item for item in report["artifacts"] if item["id"] == identifier
    )
    artifact["sha256"] = hashlib.sha256(encoded).hexdigest()
    report_path.write_text(
        yaml.safe_dump(report, sort_keys=False),
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    "check",
    ("schema", "gates", "lock", "trace", "maturity", "docs"),
)
def test_each_check_has_executable_passing_and_failing_fixtures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    check: str,
):
    passing = fixture_document("passing")[check]
    failing = fixture_document("failing")[check]
    assert isinstance(passing, Mapping)
    assert isinstance(failing, Mapping)
    root = copy_repository(tmp_path)
    baseline = SnapshotReader(root)
    monkeypatch.setattr(lock, "GitBaselineReader", lambda _root: baseline)

    pass_result = dispatch_fixture(root, passing)
    assert pass_result.exit_code == exits.SUCCESS
    assert pass_result.payload["check"] == check
    assert pass_result.payload["findings"] == []

    mutation = failing["mutation"]
    assert isinstance(mutation, str)
    mutate_repository(root, mutation)
    fail_result = dispatch_fixture(root, failing)
    assert fail_result.exit_code == exits.VALIDATION_FAILURE
    assert fail_result.payload["check"] == check
    expected_record = failing["expected-record"]
    assert any(
        finding["record"] == expected_record
        for finding in fail_result.payload["findings"]
    )


def test_ctl_014_docs_recovery_rejects_corruption_then_accepts_restore(
    tmp_path: Path,
):
    root = copy_repository(tmp_path)
    stale = root / ".github/skills/stale-fixture/SKILL.md"
    stale.parent.mkdir(parents=True)
    stale.write_text(
        "# Stale fixture\n\nThe lifecycle has " + "four" + " stages.\n",
        encoding="utf-8",
    )
    bypass = cli.dispatch(["validate", "docs", "--json"], probe_directory=root)
    stale.unlink()
    restored = cli.dispatch(["validate", "docs", "--json"], probe_directory=root)

    assert bypass.exit_code == exits.VALIDATION_FAILURE
    assert any(
        finding["record"] == "stale-stage-list"
        for finding in bypass.payload["findings"]
    )
    assert restored.exit_code == exits.SUCCESS
    assert restored.payload["findings"] == []


def test_missing_ctl_014_recovery_run_blocks_aggregate_validation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    root = copy_repository(tmp_path)
    baseline = SnapshotReader(root)
    monkeypatch.setattr(lock, "GitBaselineReader", lambda _root: baseline)
    mutate_repository(root, "missing-docs-recovery")

    result = cli.dispatch(["validate", "all", "--json"], probe_directory=root)

    assert result.exit_code == exits.VALIDATION_FAILURE
    assert any(
        finding["check"] == "maturity"
        and finding["record"] == "CTL-014"
        and "missing restore-and-pass evidence" in finding["message"]
        for finding in result.payload["findings"]
    )


@pytest.mark.parametrize(
    "mutation",
    ("th3-release-actor", "th3-session-actor", "th3-waiver-actor"),
)
def test_th3_human_acceptance_records_require_the_exact_canonical_actor(
    tmp_path: Path,
    mutation: str,
):
    root = copy_repository(tmp_path)
    mutate_repository(root, mutation)

    result = activation.validate_repository(root)

    assert not result.valid
    assert any(
        finding["record"] == "TH3 acceptance"
        and "canonical TH3 human checkpoint" in str(finding["message"])
        and "Actor" in str(finding["message"])
        for finding in result.findings
    )


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("Timestamp", "2026-09-07T09:22:22.528+01:00"),
        ("Scope", "TH4"),
        ("Verdict", "Approved"),
        ("Rationale", "A different rationale."),
        ("Source revision", "backlog revision 68; sha256:" + "0" * 64),
    ),
)
def test_th3_release_acceptance_requires_all_exact_checkpoint_fields(
    tmp_path: Path,
    field: str,
    replacement: str,
):
    root = copy_repository(tmp_path)
    path = root / activation.TH3_RELEASE_PATH
    replace_once(
        path,
        f"| {field} | {activation._th3_acceptance_values()[field]} |",
        f"| {field} | {replacement} |",
    )

    result = activation.validate_repository(root)

    assert not result.valid
    assert any(
        finding["record"] == "TH3 acceptance"
        and field in str(finding["message"])
        for finding in result.findings
    )


@pytest.mark.parametrize(
    "mutation",
    (
        "th3-archive-index-in-progress",
        "th3-archive-index-unlocked",
        "th3-archive-payload-in-progress",
        "th3-archive-payload-unlocked",
        "th3-archive-payload-schema-v1",
    ),
)
def test_th3_current_archive_index_is_required_by_maturity_and_self_hosted_evidence(
    tmp_path: Path,
    mutation: str,
):
    root = copy_repository(tmp_path)
    mutate_repository(root, mutation)

    maturity = activation.validate_repository(root)
    report = self_hosted.validate_report(root)

    assert not maturity.valid
    assert any(
        finding["record"] == "TH3"
        and "acceptance state" in str(finding["message"])
        for finding in maturity.findings
    )
    assert not report.valid
    assert "current maturity validation rejects retained recovery evidence" in report.findings


def test_th3_last_updated_requires_the_exact_authoritative_acceptance_boundary(
    tmp_path: Path,
):
    root = copy_repository(tmp_path)
    path = root / activation.BACKLOG_PATH
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    different_offset_aware_timestamp = "2026-09-07T08:22:22.527+00:00"
    assert (
        datetime.fromisoformat(different_offset_aware_timestamp).utcoffset()
        is not None
    )
    assert different_offset_aware_timestamp != activation.TH3_ACCEPTANCE_TIMESTAMP
    document["backlog"]["last-updated"] = different_offset_aware_timestamp
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    validation = cli.dispatch(
        ["validate", "all", "--json"],
        probe_directory=root,
    )
    report = self_hosted.validate_report(root)

    assert validation.exit_code == exits.VALIDATION_FAILURE
    assert any(
        finding["check"] == "maturity"
        and finding["record"] == "TH3"
        and "revision-68 acceptance state" in str(finding["message"])
        for finding in validation.payload["findings"]
    )
    assert not report.valid
    assert "current maturity validation rejects retained recovery evidence" in report.findings


def test_aggregate_corruption_reports_gates_trace_and_lock(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    root = copy_repository(tmp_path)
    baseline = SnapshotReader(root)
    monkeypatch.setattr(lock, "GitBaselineReader", lambda _root: baseline)
    for mutation in (
        "blocked-discovery-gate",
        "dangling-story-trace",
        "edited-locked-story",
    ):
        mutate_repository(root, mutation)

    result = cli.dispatch(["validate", "all", "--json"], probe_directory=root)

    assert result.exit_code == exits.VALIDATION_FAILURE
    reported_checks = {
        finding["check"] for finding in result.payload["findings"]
    }
    assert {"gates", "trace", "lock"} <= reported_checks


def append_load_records(root: Path) -> None:
    self_hosted._append_load_records(root)


def test_adversarial_finding_4_loaded_fixture_uses_real_subprocess_under_budget(
    tmp_path: Path,
):
    root = copy_repository(tmp_path, include_git=True)
    baseline_records = len(trace.validate_repository(root).nodes)
    append_load_records(root)
    loaded_records = len(trace.validate_repository(root).nodes)

    started = time.perf_counter()
    completed = subprocess.run(
        [str(root / "bin/method"), "validate", "all", "--json"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=20,
    )
    elapsed = time.perf_counter() - started
    result = one_json_object(completed.stdout)

    print(
        "loaded_subprocess_elapsed_seconds="
        f"{elapsed:.6f} baseline_records={baseline_records} "
        f"loaded_records={loaded_records}"
    )
    assert loaded_records > baseline_records * LOAD_MULTIPLIER
    assert completed.returncode == exits.SUCCESS
    assert completed.stderr == ""
    assert result["status"] == "ok"
    assert result["findings"] == []
    assert elapsed < 5


def test_real_self_hosted_command_is_one_object_and_under_budget():
    started = time.perf_counter()
    completed = subprocess.run(
        [str(METHOD), "validate", "all", "--json"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=20,
    )
    elapsed = time.perf_counter() - started
    report = one_json_object(completed.stdout)

    print(f"self_hosted_elapsed_seconds={elapsed:.6f}")
    assert completed.returncode == exits.SUCCESS
    assert completed.stderr == ""
    assert report["status"] == "ok"
    assert report["findings"] == []
    assert [item["check"] for item in report["checks"]] == [
        "schema",
        "gates",
        "lock",
        "trace",
        "maturity",
        "docs",
    ]
    assert elapsed < 5


def test_recovery_runner_outputs_are_bound_and_consumed():
    result = activation.validate_repository(ROOT)
    assert result.valid, result.findings
    ledger = yaml.safe_load(
        (ROOT / activation.LEDGER_PATH).read_text(encoding="utf-8")
    )
    promotion_times: dict[str, datetime] = {}

    for case in recovery.CASES:
        item = control(ledger, case.control_id)
        promoted = item["promoted-by"]
        assert isinstance(promoted, dict)
        promotion_time = datetime.fromisoformat(promoted["timestamp"])
        promotion_times[case.control_id] = promotion_time
        records = []
        for kind, expected_exit in (
            ("bypass-attempt", exits.VALIDATION_FAILURE),
            ("restore-and-pass", exits.SUCCESS),
        ):
            evidence_path = ROOT / recovery.evidence_relative(case, kind)
            record = yaml.safe_load(evidence_path.read_text(encoding="utf-8"))
            output_path = ROOT / record["run-output"]
            output_bytes = output_path.read_bytes()
            output = json.loads(output_bytes)
            records.append(record)

            assert record["evidence-version"] == 2
            assert record["control-id"] == case.control_id
            assert record["validator-check"] == case.validator_check
            assert record["recovery-case"] == case.recovery_case
            assert record["observed-exit"] == expected_exit
            assert (
                hashlib.sha256(output_bytes).hexdigest()
                == record["run-output-sha256"]
            )
            assert output["result"]["check"] == case.validator_check
            assert output["observed-exit"] == expected_exit
            assert output["control-id"] == case.control_id
            if kind == "bypass-attempt":
                assert output["result"]["findings"]
            else:
                assert output["result"]["findings"] == []
            assert datetime.fromisoformat(record["observed-at"]) >= promotion_time
        assert records[0]["source-input-sha256"] == records[1][
            "source-input-sha256"
        ]
        assert datetime.fromisoformat(records[0]["observed-at"]) < datetime.fromisoformat(
            records[1]["observed-at"]
        )

    assert set(promotion_times) == {"CTL-001", "CTL-002", "CTL-003", "CTL-014"}


def test_recovery_digest_binds_every_transitive_local_command_dependency(
    tmp_path: Path,
):
    root = copy_repository(tmp_path)
    dependencies = recovery.command_dependency_files(root)
    expected = {
        "bin/method",
        recovery.RUNNER_PATH,
        *(
            path.relative_to(root).as_posix()
            for path in (root / "methodlib").glob("*.py")
        ),
    }

    assert dependencies == tuple(sorted(dependencies))
    assert set(dependencies) == expected
    assert {"methodlib/records.py", "methodlib/exits.py"} <= set(dependencies)
    assert activation.validate_repository(root).valid

    case = recovery.CASE_BY_KEY[("CTL-001", "gates")]
    baseline = recovery.input_digest(root, case, "restore-and-pass")
    for relative in dependencies:
        path = root / relative
        original = path.read_bytes()
        path.write_bytes(original + b"\n# dependency digest mutation\n")
        assert recovery.input_digest(root, case, "restore-and-pass") != baseline
        if relative in {
            "methodlib/records.py",
            "methodlib/exits.py",
            "methodlib/doctor.py",
        }:
            result = activation.validate_repository(root)
            assert not result.valid
            assert any(
                finding["record"] == "CTL-001"
                and "stale" in str(finding["message"])
                for finding in result.findings
            )
        path.write_bytes(original)


def test_adversarial_finding_1_each_recovery_timestamp_precedes_promotion(
    tmp_path: Path,
):
    root = copy_repository(tmp_path)
    ledger = yaml.safe_load(
        (root / activation.LEDGER_PATH).read_text(encoding="utf-8")
    )
    promoted = control(ledger, "CTL-014")["promoted-by"]
    evidence_path = root / recovery.evidence_relative(
        recovery.CASE_BY_KEY[("CTL-014", "docs")],
        "restore-and-pass",
    )
    evidence = yaml.safe_load(evidence_path.read_text(encoding="utf-8"))
    evidence["observed-at"] = promoted["timestamp"]
    evidence_path.write_text(
        yaml.safe_dump(evidence, sort_keys=False),
        encoding="utf-8",
    )

    result = activation.validate_repository(root)

    assert not result.valid
    assert any(
        finding["record"] == "CTL-014"
        and "contradictory, stale, unrelated, or incomplete" in str(finding["message"])
        for finding in result.findings
    )


@pytest.mark.parametrize("mutation", ("fabricated", "unrelated", "stale"))
def test_adversarial_finding_2_rejects_unbound_recovery_output(
    tmp_path: Path,
    mutation: str,
):
    root = copy_repository(tmp_path)
    case = recovery.CASE_BY_KEY[("CTL-001", "gates")]
    evidence_path = root / recovery.evidence_relative(case, "bypass-attempt")
    evidence = yaml.safe_load(evidence_path.read_text(encoding="utf-8"))
    if mutation == "fabricated":
        evidence["run-output-sha256"] = "0" * 64
    elif mutation == "unrelated":
        other = recovery.CASE_BY_KEY[("CTL-002", "schema")]
        output = root / recovery.output_relative(other, "bypass-attempt")
        evidence["run-output"] = output.relative_to(root).as_posix()
        evidence["run-output-sha256"] = hashlib.sha256(output.read_bytes()).hexdigest()
    else:
        fixture = root / recovery.FIXTURE_PATH
        fixture.write_text(
            fixture.read_text(encoding="utf-8") + "\n# stale\n",
            encoding="utf-8",
        )
    evidence_path.write_text(
        yaml.safe_dump(evidence, sort_keys=False),
        encoding="utf-8",
    )

    result = activation.validate_repository(root)

    assert not result.valid
    assert any(
        finding["record"] == "CTL-001"
        and any(
            word in str(finding["message"])
            for word in ("stale", "unrelated", "missing bypass-attempt")
        )
        for finding in result.findings
    )


def test_adversarial_finding_3_report_consumer_rejects_stale_output(
    tmp_path: Path,
):
    if os.environ.get("METHOD_EVIDENCE_BOOTSTRAP") == "1":
        pytest.skip("stale-report test is bootstrapped before report generation")
    assert self_hosted.validate_report(ROOT).valid
    root = copy_repository(tmp_path)
    output = root / self_hosted.EXPECTED_ARTIFACTS["self-hosted"][1]
    value = json.loads(output.read_text(encoding="utf-8"))
    value["exit"] = 2
    output.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")

    result = self_hosted.validate_report(root)

    assert not result.valid
    assert any("self-hosted" in finding for finding in result.findings)


@pytest.mark.parametrize(
    ("identifier", "mutation", "output_id"),
    (
        ("self-hosted", "relabeled", "self-hosted"),
        ("loaded-validation", "relabeled", "loaded-validate-all"),
        (
            "network-namespace",
            "relabeled",
            "network-isolated-validate-all",
        ),
        ("self-hosted", "missing-check", "self-hosted"),
        ("self-hosted", "failed-check", "self-hosted"),
        ("self-hosted", "nonzero-findings", "self-hosted"),
    ),
)
def test_report_consumer_requires_exact_green_validate_all_semantics(
    tmp_path: Path,
    identifier: str,
    mutation: str,
    output_id: str,
):
    if os.environ.get("METHOD_EVIDENCE_BOOTSTRAP") == "1":
        pytest.skip("report test is bootstrapped before final report generation")
    root = copy_repository(tmp_path)
    relative = self_hosted.EXPECTED_ARTIFACTS[identifier][1]
    output = json.loads((root / relative).read_text(encoding="utf-8"))
    command_output = (
        output["validation"] if identifier == "network-namespace" else output
    )
    stdout = command_output["stdout"]
    if mutation == "relabeled":
        stdout["command"] = "doctor"
        stdout["check"] = "capabilities"
    elif mutation == "missing-check":
        stdout["checks"].pop()
    elif mutation == "failed-check":
        stdout["checks"][0]["status"] = "failed"
    else:
        stdout["checks"][0]["finding_count"] = 1
    replace_retained_json(root, identifier, output)

    result = self_hosted.validate_report(root)

    assert not result.valid
    assert (
        f"{output_id} output is not a complete successful validate all result"
        in result.findings
    )


def test_loaded_multiplier_is_strict_and_report_rejects_exactly_three_times(
    tmp_path: Path,
):
    exact = {
        "baseline-records": 10,
        "loaded-records": 30,
        "record-multiplier": 3.0,
    }
    assert not self_hosted._loaded_output_exceeds_multiplier(exact)

    if os.environ.get("METHOD_EVIDENCE_BOOTSTRAP") == "1":
        pytest.skip("report test is bootstrapped before final report generation")
    root = copy_repository(tmp_path)
    relative = self_hosted.EXPECTED_ARTIFACTS["loaded-validation"][1]
    output = json.loads((root / relative).read_text(encoding="utf-8"))
    output.update(exact)
    replace_retained_json(root, "loaded-validation", output)

    result = self_hosted.validate_report(root)

    assert not result.valid
    assert "loaded output does not prove more than 3x records" in result.findings


def test_adversarial_finding_5_network_namespace_covers_child_processes():
    output = self_hosted._network_command(ROOT)
    validation = output["validation"]

    assert output["mechanism"] == "bubblewrap --unshare-net"
    assert output["interfaces"] == ["lo"]
    assert output["namespace"] == output["child-namespace"]
    assert output["namespace"] != output["host-namespace"]
    assert output["egress-calibration-errno"] == 101
    assert validation["exit"] == exits.SUCCESS
    assert validation["stdout"]["status"] == "ok"
    assert validation["stdout"]["findings"] == []


def test_retained_promotion_is_later_and_covers_all_recovery_controls():
    ledger = yaml.safe_load(
        (ROOT / activation.LEDGER_PATH).read_text(encoding="utf-8")
    )
    expected = {
        "actor": "Human: designer",
        "record": "docs/plan/control-promotions/TH3.E4.US5.md",
    }
    for identifier in ("CTL-001", "CTL-002", "CTL-003", "CTL-014"):
        promoted = control(ledger, identifier)["promoted-by"]
        assert promoted["actor"] == expected["actor"]
        assert promoted["record"] == expected["record"]

    promotion = PROMOTION_RECORD.read_text(encoding="utf-8")
    assert "| Actor | Human: designer |" in promotion
    assert "| Record | TH3.E4.US5 |" in promotion
    assert (
        "| Decision | Promote CTL-001, CTL-002, CTL-003, and CTL-014 "
        "to ENFORCED. |"
    ) in promotion


@pytest.mark.skipif(
    not VERIFICATION_REPORT.is_file(),
    reason="verification report is retained after evidence generation",
)
def test_retained_theme_verification_report_is_current_and_complete():
    if os.environ.get("METHOD_EVIDENCE_BOOTSTRAP") == "1":
        pytest.skip("report consumer is bootstrapped before final report generation")

    result = self_hosted.validate_report(ROOT)

    assert result.valid, result.findings
    report = result.report
    assert report is not None
    assert report["report-version"] == 2
    assert report["theme-status"] == "done"
    assert report["theme-accepted"] is True
    assert report["theme-locked"] is True
    assert report["waiver"] == {"id": "WVR-001", "status": "consumed"}
    suite = json.loads(
        (
            ROOT / self_hosted.EXPECTED_ARTIFACTS["full-pytest"][1]
        ).read_text(encoding="utf-8")
    )
    assert isinstance(suite["bootstrap-report-consumer"], bool)
    assert report["bounded-snapshots"]["session-log"] == {
        "semantics": self_hosted.SESSION_LOG_SEMANTICS
    }
    assert "session-log-sha256" not in VERIFICATION_REPORT.read_text(
        encoding="utf-8"
    )
