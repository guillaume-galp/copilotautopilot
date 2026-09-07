import ast
import io
import json
import stat
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from methodlib import cli, doctor, exits  # noqa: E402


METHOD = ROOT / "bin" / "method"
EXPECTED_RESERVED_COMMANDS = (
    "tx",
    "packet",
    "usage",
    "budget",
    "report",
)
EXPECTED_COMMANDS = ("validate", "doctor", *EXPECTED_RESERVED_COMMANDS, "migrate")
EXPECTED_VALIDATE_CHECKS = (
    "all",
    "gates",
    "schema",
    "lock",
    "trace",
    "maturity",
    "docs",
    "dod",
)


def run_method(*arguments: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(METHOD), *arguments],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def one_json_object(output: str) -> dict[str, object]:
    decoder = json.JSONDecoder()
    value, end = decoder.raw_decode(output)
    assert output[end:].strip() == ""
    assert isinstance(value, dict)
    assert len(output.splitlines()) == 1
    return value


def findings_by_capability(report: dict[str, object]) -> dict[str, dict[str, object]]:
    findings = report["findings"]
    assert isinstance(findings, list)
    return {finding["capability"]: finding for finding in findings}


def test_entrypoint_is_executable_and_imports_from_repository_when_run_elsewhere(
    tmp_path: Path,
):
    assert METHOD.stat().st_mode & stat.S_IXUSR

    result = run_method("doctor", cwd=tmp_path)

    assert result.returncode == exits.SUCCESS
    report = one_json_object(result.stdout)
    assert report["command"] == "doctor"
    assert report["probe_directory"] == str(tmp_path)


def test_doctor_happy_path_reports_every_capability_and_succeeds(tmp_path: Path):
    result = run_method("doctor", cwd=tmp_path)

    assert result.returncode == exits.SUCCESS
    report = one_json_object(result.stdout)
    findings = findings_by_capability(report)
    assert set(findings) == {
        "python",
        "pyyaml",
        "git",
        "atomic-replace",
        "exclusive-create",
        "fsync",
    }
    assert all(finding["available"] for finding in findings.values())
    assert findings["python"]["version"]
    assert findings["pyyaml"]["version"]
    assert findings["git"]["executable"]
    assert report["status"] == "ok"
    assert report["transition_controls"] == {
        "status": "ready",
        "blocked_above": None,
        "limitations": [],
    }
    assert "method doctor:" in result.stderr


def test_doctor_reports_deleted_working_directory_as_filesystem_limit(
    tmp_path: Path,
):
    deleted_cwd = tmp_path / "deleted-cwd"
    deleted_cwd.mkdir()
    launcher = "\n".join(
        (
            "import os",
            "import sys",
            "os.chdir(sys.argv[2])",
            "os.rmdir(sys.argv[2])",
            "os.execv(sys.executable, "
            "[sys.executable, sys.argv[1], 'doctor'])",
        )
    )

    result = subprocess.run(
        [sys.executable, "-c", launcher, str(METHOD), str(deleted_cwd)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == exits.SUCCESS
    report = one_json_object(result.stdout)
    findings = findings_by_capability(report)
    assert report["command"] == "doctor"
    assert report["status"] == "limited"
    assert report["probe_directory"] is None
    assert report["transition_controls"] == {
        "status": "blocked",
        "blocked_above": "MANUAL",
        "limitations": ["atomic-replace", "exclusive-create", "fsync"],
    }
    for capability in ("atomic-replace", "exclusive-create", "fsync"):
        assert findings[capability]["available"] is False
        assert (
            "probe directory unavailable" in findings[capability]["reason"]
        )
    assert "Traceback" not in result.stderr
    assert result.stderr
    assert all(
        line.startswith("method doctor:")
        for line in result.stderr.splitlines()
    )


def test_unknown_subcommand_is_one_usage_json_object_with_valid_names():
    result = run_method("frobnicate")

    assert result.returncode == exits.USAGE_ERROR
    report = one_json_object(result.stdout)
    assert report["status"] == "usage-error"
    assert report["valid_subcommands"] == list(EXPECTED_COMMANDS)
    assert "frobnicate" in report["message"]
    assert "usage error" in result.stderr
    assert "frobnicate" in result.stderr


@pytest.mark.parametrize("command", EXPECTED_RESERVED_COMMANDS)
def test_later_commands_are_reserved_and_use_blocked_exit(command: str):
    result = run_method(command, "future", "--option")

    assert result.returncode == exits.PAUSE_OR_BLOCKED
    report = one_json_object(result.stdout)
    assert report["command"] == command
    assert report["status"] == "reserved"
    assert "not implemented" in result.stderr


@pytest.mark.parametrize(
    "check",
    tuple(
        check
        for check in EXPECTED_VALIDATE_CHECKS
        if check
        not in {"all", "gates", "schema", "lock", "trace", "maturity", "docs"}
    ),
)
def test_validate_foundation_dispatches_without_implementing_later_checks(check: str):
    result = run_method("validate", check, "--json")

    assert result.returncode == exits.PAUSE_OR_BLOCKED
    report = one_json_object(result.stdout)
    assert report == {
        "command": "validate",
        "check": check,
        "status": "reserved",
        "message": (
            f"validate {check} is reserved by the foundation; "
            "its checks are not implemented in TH3.E2.US1"
        ),
    }
    assert "not implemented" in result.stderr


def test_validate_gates_requires_its_stage_scope_arguments():
    result = run_method("validate", "gates", "--json")

    assert result.returncode == exits.USAGE_ERROR
    report = one_json_object(result.stdout)
    assert report["status"] == "usage-error"
    assert "--vp" in report["message"]
    assert "--stage" in report["message"]


def test_validate_schema_is_implemented_and_preserves_json_framing():
    result = run_method("validate", "schema", "--json")

    assert result.returncode == exits.SUCCESS
    report = one_json_object(result.stdout)
    assert report == {
        "command": "validate",
        "check": "schema",
        "status": "ok",
        "findings": [],
    }
    assert result.stderr == ""


def test_validate_docs_and_all_are_real_checks_with_json_framing():
    docs_result = run_method("validate", "docs", "--json")
    all_result = run_method("validate", "all", "--json")

    assert docs_result.returncode == exits.SUCCESS
    docs_report = one_json_object(docs_result.stdout)
    assert docs_report["check"] == "docs"
    assert docs_report["status"] == "ok"
    assert docs_report["checked_files"]

    assert all_result.returncode == exits.SUCCESS
    all_report = one_json_object(all_result.stdout)
    assert all_report["check"] == "all"
    assert all_report["status"] == "ok"
    assert [item["check"] for item in all_report["checks"]] == [
        "schema",
        "gates",
        "lock",
        "trace",
        "maturity",
        "docs",
    ]
    assert all_report["checked_files"] == docs_report["checked_files"]


def test_documented_command_surface_matches_the_cli_contract():
    assert cli.VALID_COMMANDS == EXPECTED_COMMANDS
    assert cli.RESERVED_COMMANDS == EXPECTED_RESERVED_COMMANDS
    assert cli.VALIDATE_CHECKS == EXPECTED_VALIDATE_CHECKS


def test_shared_exit_codes_are_complete_and_stable():
    assert exits.ALL == (0, 1, 2, 3, 4, 5)
    assert exits.SUCCESS == 0
    assert exits.USAGE_ERROR == 1
    assert exits.VALIDATION_FAILURE == 2
    assert exits.CONFLICT == 3
    assert exits.PAUSE_OR_BLOCKED == 4
    assert exits.RECOVERY_REQUIRED == 5


def test_help_and_parser_errors_preserve_json_stdout_contract():
    help_result = run_method("--help")
    error_result = run_method("doctor", "--unexpected")

    assert help_result.returncode == exits.SUCCESS
    assert one_json_object(help_result.stdout)["command"] == "help"
    assert "usage: method" in help_result.stderr

    assert error_result.returncode == exits.USAGE_ERROR
    assert one_json_object(error_result.stdout)["status"] == "usage-error"
    assert "--unexpected" in error_result.stderr


def test_atomic_replace_limitation_blocks_transition_controls_above_manual(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    def unavailable(_directory: Path) -> doctor.Finding:
        return {
            "capability": "atomic-replace",
            "available": False,
            "reason": "simulated unsupported filesystem",
        }

    monkeypatch.setattr(doctor, "probe_atomic_replace", unavailable)

    result = cli.dispatch(["doctor"], probe_directory=tmp_path)
    report = result.payload

    finding = findings_by_capability(report)["atomic-replace"]
    assert result.exit_code == exits.SUCCESS
    assert finding["available"] is False
    assert "simulated unsupported filesystem" in finding["reason"]
    assert report["status"] == "limited"
    assert report["transition_controls"]["status"] == "blocked"
    assert report["transition_controls"]["blocked_above"] == "MANUAL"
    assert "atomic-replace" in report["transition_controls"]["limitations"]
    assert any("blocked above MANUAL" in line for line in result.diagnostics)


def test_each_probe_returns_a_finding_when_its_capability_is_missing(
    tmp_path: Path,
):
    def missing_yaml(_name: str):
        raise ModuleNotFoundError("No module named 'yaml'", name="yaml")

    def failed_replace(_source, _destination):
        raise OSError("replace disabled")

    def failed_open(_path, _flags, _mode):
        raise OSError("exclusive create disabled")

    def failed_sync(_descriptor):
        raise OSError("fsync disabled")

    findings = [
        doctor.probe_python((3, 10), "3.10.0"),
        doctor.probe_pyyaml(missing_yaml),
        doctor.probe_git(lambda _name: None),
        doctor.probe_atomic_replace(tmp_path, failed_replace),
        doctor.probe_exclusive_create(tmp_path, failed_open),
        doctor.probe_fsync(tmp_path, failed_sync),
    ]

    assert [finding["capability"] for finding in findings] == [
        "python",
        "pyyaml",
        "git",
        "atomic-replace",
        "exclusive-create",
        "fsync",
    ]
    assert all(finding["available"] is False for finding in findings)
    assert all(finding["reason"] for finding in findings)


def test_missing_nested_pyyaml_dependency_is_reported_without_masking_it():
    def broken_yaml(_name: str):
        raise ModuleNotFoundError("No module named 'missing_extension'", name="missing_extension")

    finding = doctor.probe_pyyaml(broken_yaml)

    assert finding["available"] is False
    assert "missing_extension" in finding["reason"]


def test_emit_writes_diagnostics_only_to_stderr_and_one_json_object_to_stdout():
    stdout = io.StringIO()
    stderr = io.StringIO()
    result = cli.CommandResult(
        exits.VALIDATION_FAILURE,
        {"status": "failed"},
        ("human diagnostic",),
    )

    exit_code = cli.emit(result, stdout=stdout, stderr=stderr)

    assert exit_code == exits.VALIDATION_FAILURE
    assert one_json_object(stdout.getvalue()) == {"status": "failed"}
    assert stderr.getvalue() == "human diagnostic\n"


def test_runtime_imports_are_standard_library_pyyaml_or_methodlib_only():
    allowed_roots = set(getattr(__import__("sys"), "stdlib_module_names"))
    allowed_roots.update({"yaml", "methodlib", "__future__"})
    runtime_files = [METHOD, *sorted((ROOT / "methodlib").glob("*.py"))]

    imported_roots = set()
    for path in runtime_files:
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".", 1)[0])

    assert imported_roots <= allowed_roots
    assert imported_roots.isdisjoint(
        {"ftplib", "http", "socket", "urllib", "xmlrpc"}
    )


def test_capability_probes_do_not_use_broad_exception_handlers():
    tree = ast.parse((ROOT / "methodlib" / "doctor.py").read_text())
    broad_handlers = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        if node.type is None:
            broad_handlers.append(node)
        elif isinstance(node.type, ast.Name) and node.type.id in {
            "Exception",
            "BaseException",
        }:
            broad_handlers.append(node)

    assert broad_handlers == []
