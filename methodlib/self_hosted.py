"""Generation and fail-closed consumption of TH3.E4.US5 evidence.

The report contains identifiers and digests, never executable commands.
Generation uses a closed command table in this module.  Validation only reads
bounded local files and rejects changed inputs or outputs.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Mapping

import yaml

from methodlib import activation, recovery, trace
from methodlib.backlog import UniqueKeyLoader


REPORT_PATH = Path(
    "docs/plan/evidence/TH3.E4.US5-self-hosted-verification.yaml"
)
ARTIFACT_DIRECTORY = Path("docs/plan/evidence/self-hosted-run")
BACKLOG_SNAPSHOT_PATH = ARTIFACT_DIRECTORY / "backlog-at-validation.yaml"
LOAD_RECORD_COUNT = 800
LOAD_MULTIPLIER = 3
VALIDATE_ALL_CHECKS = (
    "schema",
    "gates",
    "lock",
    "trace",
    "maturity",
    "docs",
)
MAX_FILE_BYTES = 4 * 1024 * 1024
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
REPORT_FIELDS = {
    "report-version",
    "story",
    "theme",
    "generated-at",
    "theme-status",
    "theme-accepted",
    "theme-locked",
    "waiver",
    "control-states",
    "generator",
    "source-snapshot",
    "protected-snapshot",
    "bounded-snapshots",
    "artifacts",
    "verification",
}
EXPECTED_ARTIFACTS: Mapping[str, tuple[str, str]] = {
    "protected-lock": (
        "command-output",
        f"{ARTIFACT_DIRECTORY.as_posix()}/protected-lock.json",
    ),
    "self-hosted": (
        "command-output",
        f"{ARTIFACT_DIRECTORY.as_posix()}/self-hosted.json",
    ),
    "loaded-validation": (
        "command-output",
        f"{ARTIFACT_DIRECTORY.as_posix()}/loaded-validation.json",
    ),
    "network-namespace": (
        "network-proof",
        f"{ARTIFACT_DIRECTORY.as_posix()}/network-namespace.json",
    ),
    "full-pytest": (
        "test-output",
        f"{ARTIFACT_DIRECTORY.as_posix()}/full-pytest.json",
    ),
    "backlog-snapshot": (
        "bounded-snapshot",
        BACKLOG_SNAPSHOT_PATH.as_posix(),
    ),
}
PROTECTED_SCOPES = (
    "docs/ADRs/ADR-001-gitflow-operator.md",
    *(f"docs/ADRs/ADR-{number:03d}-{slug}.md" for number, slug in (
        (2, "six-stage-gated-lifecycle"),
        (3, "markdown-records-and-local-validator"),
        (4, "backlog-schema-v2-and-transitions"),
        (5, "agent-packets-and-source-hashing"),
        (6, "risk-verification-and-model-routing"),
        (7, "usage-adapter-and-budget-enforcement"),
        (8, "multi-theme-lock-and-activation-ledger"),
    )),
    "docs/plan/backlog-archive/TH1.yaml",
    "docs/plan/backlog-archive/TH2.yaml",
    "docs/plan/backlog-archive/TH3.yaml",
    "docs/themes/TH1-methodology-improvements",
    "docs/themes/TH2-gitflow-operator",
    "docs/themes/TH3-discovery-requirements-foundation",
    "docs/vision_of_product/VP1-mvp",
    "docs/vision_of_product/VP2-gitflow-operator",
)
PROTECTED_SNAPSHOT_SEMANTICS = (
    "immutable accepted TH1/TH2/TH3 theme, archive, and dependent ADR bytes "
    "verified before report generation"
)
MUTABLE_SNAPSHOT_SEMANTICS = (
    "point-in-time copy used by this run; not an immutable baseline and not "
    "compared with later orchestrator state"
)
SESSION_LOG_SEMANTICS = (
    "omitted: orchestrator-owned mutable log; no immutable-baseline claim"
)


@dataclass(frozen=True)
class ReportValidation:
    findings: tuple[str, ...]
    report: Mapping[str, object] | None = None

    @property
    def valid(self) -> bool:
        return not self.findings


def _timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="microseconds")


def _parsed_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _safe_file(root: Path, value: object) -> Path | None:
    if not isinstance(value, str):
        return None
    relative = PurePosixPath(value)
    if relative.is_absolute() or "." in relative.parts or ".." in relative.parts:
        return None
    candidate = root.joinpath(*relative.parts)
    try:
        resolved_root = root.resolve(strict=True)
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(resolved_root)
        if not candidate.is_file() or candidate.is_symlink():
            return None
        if candidate.stat().st_size > MAX_FILE_BYTES:
            return None
    except (OSError, RuntimeError, ValueError):
        return None
    return candidate


def _json_load(path: Path) -> object:
    def unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate key {key}")
            result[key] = value
        return result

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)


def _yaml_load(path: Path) -> object:
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("file exceeds report safety limit")
    return yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def _write_yaml(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def _digest_entries(entries: list[tuple[str, bytes]]) -> str:
    digest = hashlib.sha256()
    for relative, content in sorted(entries):
        encoded = relative.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def _files_under(root: Path, relative: str) -> list[tuple[str, bytes]]:
    path = root / relative
    candidates = [path] if path.is_file() else sorted(path.rglob("*"))
    entries: list[tuple[str, bytes]] = []
    for candidate in candidates:
        if candidate.is_file() and not candidate.is_symlink():
            name = candidate.relative_to(root).as_posix()
            entries.append((name, candidate.read_bytes()))
    return entries


def protected_snapshot(root: Path) -> dict[str, object]:
    entries: list[tuple[str, bytes]] = []
    for scope in PROTECTED_SCOPES:
        entries.extend(_files_under(root, scope))
    return {
        "semantics": PROTECTED_SNAPSHOT_SEMANTICS,
        "scopes": list(PROTECTED_SCOPES),
        "file-count": len(entries),
        "aggregate-sha256": _digest_entries(entries),
    }


def _source_paths(root: Path) -> tuple[str, ...]:
    paths: set[str] = {
        "bin/method",
        recovery.RUNNER_PATH,
        activation.LEDGER_PATH.as_posix(),
        "docs/plan/control-promotions/TH3.E4.US5.md",
        (
            "docs/themes/TH3-discovery-requirements-foundation/epics/"
            "E4-activation-migration-integration/stories/"
            "US5-self-hosted-validation-run.md"
        ),
        recovery.FIXTURE_PATH,
        "tests/fixtures/method_validate_all/passing/checks.yaml",
        "tests/fixtures/method_validate_all/failing/checks.yaml",
        (
            "tests/fixtures/method_validate_all/network_guard/"
            "sitecustomize.py"
        ),
    }
    for pattern in ("methodlib/*.py", "tests/test_*.py"):
        paths.update(
            path.relative_to(root).as_posix()
            for path in root.glob(pattern)
            if path.is_file() and not path.is_symlink()
        )
    evidence_root = root / recovery.EVIDENCE_DIRECTORY
    if evidence_root.is_dir():
        paths.update(
            path.relative_to(root).as_posix()
            for path in evidence_root.rglob("*")
            if path.is_file() and not path.is_symlink()
        )
    return tuple(sorted(paths))


def source_snapshot(root: Path) -> dict[str, object]:
    files = [
        {"path": relative, "sha256": _sha256_file(root / relative)}
        for relative in _source_paths(root)
    ]
    entries = [
        (str(item["path"]), (root / str(item["path"])).read_bytes())
        for item in files
    ]
    return {
        "semantics": (
            "freshness boundary for implementation, tests, fixtures, recovery "
            "outputs, ledger, promotion, and story"
        ),
        "aggregate-sha256": _digest_entries(entries),
        "files": files,
    }


def _method_command(
    root: Path,
    identifier: str,
    arguments: tuple[str, ...],
    *,
    timeout: int = 30,
) -> dict[str, object]:
    started_at = _timestamp()
    started = time.perf_counter()
    completed = subprocess.run(
        [str(root / "bin/method"), *arguments],
        cwd=root,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout,
    )
    elapsed = time.perf_counter() - started
    completed_at = _timestamp()
    try:
        output = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"{identifier} emitted invalid JSON: {error}") from error
    if not isinstance(output, dict):
        raise RuntimeError(f"{identifier} emitted non-object JSON")
    return {
        "output-version": 1,
        "kind": "method-command",
        "id": identifier,
        "started-at": started_at,
        "completed-at": completed_at,
        "elapsed-seconds": elapsed,
        "exit": completed.returncode,
        "stderr": completed.stderr,
        "stdout": output,
    }


def _copy_repository(source: Path, destination: Path) -> Path:
    target = destination / "repository"
    shutil.copytree(
        source,
        target,
        ignore=shutil.ignore_patterns(
            ".pytest_cache",
            ".mypy_cache",
            "__pycache__",
            ".coverage",
            "*.pyc",
        ),
    )
    return target


def _append_load_records(root: Path) -> None:
    path = root / activation.BACKLOG_PATH
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise RuntimeError("load fixture backlog is not a mapping")
    themes = document["backlog"]["active-themes"]
    if not any(theme.get("id") == "TH3" for theme in themes):
        summaries = document["backlog"]["archived-themes"]
        summary = next(item for item in summaries if item.get("id") == "TH3")
        snapshot_path = root / summary["archive-ref"]
        snapshot = yaml.safe_load(snapshot_path.read_text(encoding="utf-8"))
        if not isinstance(snapshot, dict) or not isinstance(snapshot.get("theme"), dict):
            raise RuntimeError("TH3 archive snapshot is not a theme mapping")
        # Load testing must not mutate an accepted archive or locked theme.
        # Create an isolated, unaccepted TH6 fixture from the full TH3 shape
        # instead; this keeps the real acceptance baseline in force.
        theme_text = yaml.safe_dump(snapshot["theme"], sort_keys=False).replace(
            "TH3", "TH6"
        )
        for legacy_confidence in ("high", "medium", "low"):
            theme_text = theme_text.replace(
                f"confidence: {legacy_confidence}", "confidence: unknown"
            )
        theme_text = theme_text.replace("WVR-001", "TH6-usage-pending")
        theme = yaml.safe_load(theme_text)
        theme["locked"] = False
        source_theme = root / "docs/themes/TH3-discovery-requirements-foundation"
        target_theme = root / "docs/themes/TH6-discovery-requirements-foundation"
        shutil.copytree(source_theme, target_theme)
        for story_file in target_theme.rglob("*.md"):
            story_file.write_text(
                story_file.read_text(encoding="utf-8").replace("TH3", "TH6"),
                encoding="utf-8",
            )
        themes.append(theme)
    story = next(
        story
        for theme in themes
        for epic in theme["epics"]
        for story in epic["stories"]
        if story["id"] in {"TH3.E4.US5", "TH6.E4.US5"}
    )
    story["evidence"]["verification"].extend(
        f"Local synthetic load evidence record {number}"
        for number in range(100, 100 + LOAD_RECORD_COUNT)
    )
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")


def _loaded_command(root: Path) -> dict[str, object]:
    baseline_records = len(trace.validate_repository(root).nodes)
    with tempfile.TemporaryDirectory(prefix="method-loaded-") as directory:
        fixture_root = _copy_repository(root, Path(directory))
        _append_load_records(fixture_root)
        loaded_records = len(trace.validate_repository(fixture_root).nodes)
        output = _method_command(
            fixture_root,
            "loaded-validate-all",
            ("validate", "all", "--json"),
        )
    output["baseline-records"] = baseline_records
    output["loaded-records"] = loaded_records
    output["record-multiplier"] = loaded_records / baseline_records
    return output


def _network_child(root: Path) -> dict[str, object]:
    namespace = os.readlink("/proc/self/ns/net")
    interfaces = sorted(
        line.split(":", 1)[0].strip()
        for line in Path("/proc/net/dev").read_text(encoding="utf-8").splitlines()[2:]
        if ":" in line
    )
    probe = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import json,os;"
                "print(json.dumps({'namespace':os.readlink('/proc/self/ns/net')}))"
            ),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=5,
    )
    child_namespace = json.loads(probe.stdout)["namespace"]
    attempted_at = _timestamp()
    egress_probe = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import json,socket;"
                "s=socket.socket();s.settimeout(1);"
                "\ntry:s.connect(('198.51.100.1',9));errno=0"
                "\nexcept OSError as error:errno=error.errno"
                "\nfinally:s.close()"
                "\nprint(json.dumps({'errno':errno}))"
            ),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=5,
    )
    egress_errno = json.loads(egress_probe.stdout)["errno"]
    validation = _method_command(
        root,
        "network-isolated-validate-all",
        ("validate", "all", "--json"),
    )
    return {
        "output-version": 1,
        "kind": "network-namespace-proof",
        "id": "network-namespace",
        "mechanism": "bubblewrap --unshare-net",
        "host-namespace": os.environ.get("METHOD_HOST_NETNS"),
        "namespace": namespace,
        "child-namespace": child_namespace,
        "interfaces": interfaces,
        "egress-calibration-at": attempted_at,
        "egress-calibration-errno": egress_errno,
        "validation": validation,
    }


def _network_command(root: Path) -> dict[str, object]:
    executable = Path("/usr/bin/bwrap")
    if not executable.is_file():
        raise RuntimeError(
            "network proof blocker: /usr/bin/bwrap is unavailable and strace "
            "-f is not installed"
        )
    environment = {
        **os.environ,
        "METHOD_HOST_NETNS": os.readlink("/proc/self/ns/net"),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    completed = subprocess.run(
        [
            str(executable),
            "--unshare-net",
            "--die-with-parent",
            "--ro-bind",
            "/",
            "/",
            "--dev-bind",
            "/dev",
            "/dev",
            "--proc",
            "/proc",
            "--chdir",
            str(root),
            str(Path(sys.executable).resolve()),
            str(root / recovery.RUNNER_PATH),
            "network-child",
        ],
        cwd=root,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "network proof blocker: bubblewrap network namespace failed: "
            + completed.stderr.strip()
        )
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"network namespace helper emitted invalid JSON: {error}"
        ) from error
    if not isinstance(result, dict):
        raise RuntimeError("network namespace helper emitted non-object JSON")
    return result


def _pytest_output(root: Path, *, bootstrap: bool) -> dict[str, object]:
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    if bootstrap:
        environment["METHOD_EVIDENCE_BOOTSTRAP"] = "1"
    else:
        environment.pop("METHOD_EVIDENCE_BOOTSTRAP", None)
    started_at = _timestamp()
    started = time.perf_counter()
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=root,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=300,
    )
    elapsed = time.perf_counter() - started
    completed_at = _timestamp()
    counts = {
        name: int(match.group(1)) if match is not None else 0
        for name in ("passed", "failed", "skipped")
        for match in [re.search(rf"(\d+) {name}", completed.stdout)]
    }
    return {
        "output-version": 1,
        "kind": "pytest-suite",
        "id": "full-pytest",
        "suite": "pytest -q",
        "bootstrap-report-consumer": bootstrap,
        "started-at": started_at,
        "completed-at": completed_at,
        "elapsed-seconds": elapsed,
        "exit": completed.returncode,
        **counts,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _artifact_records(root: Path) -> list[dict[str, str]]:
    records = []
    for identifier, (kind, relative) in EXPECTED_ARTIFACTS.items():
        records.append(
            {
                "id": identifier,
                "kind": kind,
                "path": relative,
                "sha256": _sha256_file(root / relative),
            }
        )
    return records


def _build_report(
    root: Path,
    *,
    protected_output: Mapping[str, object],
) -> dict[str, object]:
    states = {
        str(item["id"]): str(item["state"])
        for item in yaml.safe_load(
            (root / activation.LEDGER_PATH).read_text(encoding="utf-8")
        )["controls"]
    }
    return {
        "report-version": 2,
        "story": "TH3.E4.US5",
        "theme": "TH3",
        "generated-at": _timestamp(),
        "theme-status": "done",
        "theme-accepted": True,
        "theme-locked": True,
        "waiver": {"id": "WVR-001", "status": "consumed"},
        "control-states": states,
        "generator": {
            "path": recovery.RUNNER_PATH,
            "sha256": _sha256_file(root / recovery.RUNNER_PATH),
        },
        "source-snapshot": source_snapshot(root),
        "protected-snapshot": {
            **protected_snapshot(root),
            "verified-by": "protected-lock",
            "verified-at": protected_output["completed-at"],
        },
        "bounded-snapshots": {
            "backlog": {
                "artifact": "backlog-snapshot",
                "observed-at": protected_output["completed-at"],
                "semantics": MUTABLE_SNAPSHOT_SEMANTICS,
            },
            "session-log": {"semantics": SESSION_LOG_SEMANTICS},
        },
        "artifacts": _artifact_records(root),
        "verification": {
            "self-hosted": {
                "artifact": "self-hosted",
                "budget-seconds": 5,
            },
            "loaded": {
                "artifact": "loaded-validation",
                "record-multiplier-threshold-exclusive": LOAD_MULTIPLIER,
                "budget-seconds": 5,
            },
            "network": {
                "artifact": "network-namespace",
                "mechanism": "bubblewrap --unshare-net",
                "child-inclusive": True,
            },
            "recovery": {
                "validator": "method validate maturity",
                "controls": ["CTL-001", "CTL-002", "CTL-003", "CTL-014"],
            },
            "full-suite": {"artifact": "full-pytest"},
        },
    }


def run_report(root: Path) -> dict[str, object]:
    """Run fixed verification commands and generate the report last."""

    root = root.resolve()
    protected_output = _method_command(
        root,
        "protected-lock",
        ("validate", "lock", "--json"),
    )
    if protected_output["exit"] != 0:
        raise RuntimeError("protected hash verification failed")
    _write_json(root / EXPECTED_ARTIFACTS["protected-lock"][1], protected_output)

    backlog_bytes = (root / activation.BACKLOG_PATH).read_bytes()
    (root / BACKLOG_SNAPSHOT_PATH).parent.mkdir(parents=True, exist_ok=True)
    (root / BACKLOG_SNAPSHOT_PATH).write_bytes(backlog_bytes)

    self_hosted = _method_command(
        root,
        "self-hosted",
        ("validate", "all", "--json"),
    )
    if self_hosted["exit"] != 0:
        raise RuntimeError("self-hosted validation failed")
    _write_json(root / EXPECTED_ARTIFACTS["self-hosted"][1], self_hosted)

    loaded = _loaded_command(root)
    if (
        loaded["exit"] != 0
        or not _loaded_output_exceeds_multiplier(loaded)
        or loaded["elapsed-seconds"] >= 5
    ):
        raise RuntimeError("loaded subprocess validation failed its contract")
    _write_json(root / EXPECTED_ARTIFACTS["loaded-validation"][1], loaded)

    network = _network_command(root)
    validation = network.get("validation")
    if (
        network.get("interfaces") != ["lo"]
        or network.get("namespace") != network.get("child-namespace")
        or network.get("namespace") == network.get("host-namespace")
        or network.get("egress-calibration-errno") != 101
        or not isinstance(validation, Mapping)
        or validation.get("exit") != 0
    ):
        raise RuntimeError("network namespace did not prove isolated descendants")
    _write_json(root / EXPECTED_ARTIFACTS["network-namespace"][1], network)

    bootstrap = _pytest_output(root, bootstrap=True)
    if bootstrap["exit"] != 0:
        raise RuntimeError("bootstrap full pytest suite failed")
    _write_json(root / EXPECTED_ARTIFACTS["full-pytest"][1], bootstrap)
    _write_yaml(
        root / REPORT_PATH,
        _build_report(root, protected_output=protected_output),
    )

    final_suite = _pytest_output(root, bootstrap=False)
    if final_suite["exit"] != 0:
        raise RuntimeError("full pytest suite failed")
    _write_json(root / EXPECTED_ARTIFACTS["full-pytest"][1], final_suite)
    report = _build_report(root, protected_output=protected_output)
    _write_yaml(root / REPORT_PATH, report)
    validation_result = validate_report(root)
    if not validation_result.valid:
        raise RuntimeError(
            "generated report failed validation: "
            + "; ".join(validation_result.findings)
        )
    return report


def _artifact_map(
    root: Path,
    report: Mapping[str, object],
    findings: list[str],
) -> dict[str, object]:
    raw = report.get("artifacts")
    if not isinstance(raw, list):
        findings.append("artifacts must be a list")
        return {}
    loaded: dict[str, object] = {}
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict) or set(item) != {
            "id",
            "kind",
            "path",
            "sha256",
        }:
            findings.append("artifact records must use the exact schema")
            continue
        identifier = item.get("id")
        if not isinstance(identifier, str) or identifier in seen:
            findings.append("artifact IDs must be unique strings")
            continue
        seen.add(identifier)
        expected = EXPECTED_ARTIFACTS.get(identifier)
        if expected != (item.get("kind"), item.get("path")):
            findings.append(f"artifact {identifier} has an unexpected kind or path")
            continue
        path = _safe_file(root, item.get("path"))
        digest = item.get("sha256")
        if (
            path is None
            or SHA256_PATTERN.fullmatch(str(digest)) is None
            or _sha256_file(path) != digest
        ):
            findings.append(f"artifact {identifier} is missing or its digest is stale")
            continue
        if item.get("kind") == "bounded-snapshot":
            loaded[identifier] = path.read_bytes()
            continue
        try:
            loaded[identifier] = _json_load(path)
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
            findings.append(f"artifact {identifier} is not safe unique-key JSON")
    if seen != set(EXPECTED_ARTIFACTS):
        findings.append("artifact inventory is incomplete or unexpected")
    return loaded


def _validate_command_output(
    output: object,
    identifier: str,
    *,
    budget: float | None,
    require_validate_all: bool = False,
    findings: list[str],
) -> datetime | None:
    if not isinstance(output, dict):
        findings.append(f"{identifier} output is not an object")
        return None
    stdout = output.get("stdout")
    completed = _parsed_timestamp(output.get("completed-at"))
    if (
        output.get("output-version") != 1
        or output.get("kind") != "method-command"
        or output.get("id") != identifier
        or output.get("exit") != 0
        or output.get("stderr") != ""
        or _parsed_timestamp(output.get("started-at")) is None
        or completed is None
        or not isinstance(stdout, dict)
        or stdout.get("status") != "ok"
        or stdout.get("findings") != []
    ):
        findings.append(f"{identifier} output does not prove a successful validator run")
    elapsed = output.get("elapsed-seconds")
    if (
        budget is not None
        and (not isinstance(elapsed, (int, float)) or elapsed >= budget)
    ):
        findings.append(f"{identifier} output exceeds its {budget:g}s budget")
    if require_validate_all and not _is_successful_validate_all(stdout):
        findings.append(
            f"{identifier} output is not a complete successful validate all result"
        )
    return completed


def _is_successful_validate_all(stdout: object) -> bool:
    """Recognize the exact successful aggregate validator result semantics."""

    if (
        not isinstance(stdout, dict)
        or set(stdout)
        != {
            "command",
            "check",
            "status",
            "checks",
            "checked_files",
            "findings",
        }
        or stdout.get("command") != "validate"
        or stdout.get("check") != "all"
        or stdout.get("status") != "ok"
        or stdout.get("findings") != []
        or not isinstance(stdout.get("checked_files"), list)
        or any(not isinstance(path, str) for path in stdout["checked_files"])
    ):
        return False
    checks = stdout.get("checks")
    if not isinstance(checks, list) or len(checks) != len(VALIDATE_ALL_CHECKS):
        return False
    for expected, summary in zip(VALIDATE_ALL_CHECKS, checks):
        expected_fields = {"check", "status", "finding_count"}
        if expected == "gates":
            expected_fields.add("scopes")
        if (
            not isinstance(summary, dict)
            or set(summary) != expected_fields
            or summary.get("check") != expected
            or summary.get("status") != "ok"
            or type(summary.get("finding_count")) is not int
            or summary.get("finding_count") != 0
        ):
            return False
        if expected == "gates" and (
            not isinstance(summary.get("scopes"), list)
            or any(not isinstance(scope, str) for scope in summary["scopes"])
        ):
            return False
    return True


def _loaded_output_exceeds_multiplier(output: object) -> bool:
    """Require measured loaded records to be strictly above the threshold."""

    if not isinstance(output, dict):
        return False
    baseline = output.get("baseline-records")
    loaded = output.get("loaded-records")
    multiplier = output.get("record-multiplier")
    if (
        type(baseline) is not int
        or baseline <= 0
        or type(loaded) is not int
        or type(multiplier) not in {int, float}
        or not math.isfinite(multiplier)
    ):
        return False
    return (
        loaded > baseline * LOAD_MULTIPLIER
        and multiplier > LOAD_MULTIPLIER
        and math.isclose(
            multiplier,
            loaded / baseline,
            rel_tol=1e-12,
            abs_tol=0.0,
        )
    )


def validate_report(root: Path) -> ReportValidation:
    """Validate retained report inputs and outputs without executing them."""

    root = root.resolve()
    report_path = _safe_file(root, REPORT_PATH.as_posix())
    if report_path is None:
        return ReportValidation(("verification report is missing or unsafe",))
    try:
        value = _yaml_load(report_path)
    except (OSError, UnicodeError, ValueError, yaml.YAMLError) as error:
        return ReportValidation((f"verification report is unreadable: {error}",))
    if not isinstance(value, dict):
        return ReportValidation(("verification report root must be a mapping",))
    report: Mapping[str, object] = value
    findings: list[str] = []
    if set(report) != REPORT_FIELDS:
        findings.append("verification report does not use the exact version 2 schema")
    if (
        report.get("report-version") != 2
        or report.get("story") != "TH3.E4.US5"
        or report.get("theme") != "TH3"
        or report.get("theme-status") != "done"
        or report.get("theme-accepted") is not True
        or report.get("theme-locked") is not True
        or report.get("waiver") != {"id": "WVR-001", "status": "consumed"}
    ):
        findings.append("theme, story, lock, or open-waiver facts are incorrect")
    generated_at = _parsed_timestamp(report.get("generated-at"))
    if generated_at is None:
        findings.append("generated-at is not an offset-aware timestamp")

    generator = report.get("generator")
    if not isinstance(generator, dict) or set(generator) != {"path", "sha256"}:
        findings.append("generator declaration is invalid")
    else:
        path = _safe_file(root, generator.get("path"))
        if (
            generator.get("path") != recovery.RUNNER_PATH
            or path is None
            or SHA256_PATTERN.fullmatch(str(generator.get("sha256"))) is None
            or _sha256_file(path) != generator.get("sha256")
        ):
            findings.append("generator digest is stale")

    expected_source = source_snapshot(root)
    if report.get("source-snapshot") != expected_source:
        findings.append("source snapshot is stale")

    protected = report.get("protected-snapshot")
    expected_protected = protected_snapshot(root)
    if not isinstance(protected, dict):
        findings.append("protected snapshot is missing")
    else:
        comparable = {
            key: value
            for key, value in protected.items()
            if key not in {"verified-by", "verified-at"}
        }
        if comparable != expected_protected:
            findings.append("protected snapshot digest is stale")
        if protected.get("verified-by") != "protected-lock":
            findings.append("protected snapshot lacks prior lock verification")

    bounded = report.get("bounded-snapshots")
    if (
        not isinstance(bounded, dict)
        or bounded.get("backlog")
        != {
            "artifact": "backlog-snapshot",
            "observed-at": (
                protected.get("verified-at")
                if isinstance(protected, dict)
                else None
            ),
            "semantics": MUTABLE_SNAPSHOT_SEMANTICS,
        }
        or bounded.get("session-log") != {"semantics": SESSION_LOG_SEMANTICS}
    ):
        findings.append("mutable snapshot semantics are missing or misleading")

    artifacts = _artifact_map(root, report, findings)
    completed_times: list[datetime] = []
    for identifier, budget in (
        ("protected-lock", None),
        ("self-hosted", 5),
    ):
        completed = _validate_command_output(
            artifacts.get(identifier),
            identifier,
            budget=budget,
            require_validate_all=identifier == "self-hosted",
            findings=findings,
        )
        if completed is not None:
            completed_times.append(completed)

    loaded = artifacts.get("loaded-validation")
    loaded_completed = _validate_command_output(
        loaded,
        "loaded-validate-all",
        budget=5,
        require_validate_all=True,
        findings=findings,
    )
    if loaded_completed is not None:
        completed_times.append(loaded_completed)
    if not _loaded_output_exceeds_multiplier(loaded):
        findings.append("loaded output does not prove more than 3x records")

    network = artifacts.get("network-namespace")
    if not isinstance(network, dict):
        findings.append("network namespace output is missing")
    else:
        nested = network.get("validation")
        nested_completed = _validate_command_output(
            nested,
            "network-isolated-validate-all",
            budget=5,
            require_validate_all=True,
            findings=findings,
        )
        if nested_completed is not None:
            completed_times.append(nested_completed)
        if (
            network.get("output-version") != 1
            or network.get("kind") != "network-namespace-proof"
            or network.get("id") != "network-namespace"
            or network.get("mechanism") != "bubblewrap --unshare-net"
            or network.get("interfaces") != ["lo"]
            or network.get("namespace") != network.get("child-namespace")
            or network.get("namespace") == network.get("host-namespace")
            or network.get("egress-calibration-errno") != 101
        ):
            findings.append(
                "network output does not prove child-inclusive namespace isolation"
            )

    suite = artifacts.get("full-pytest")
    if not isinstance(suite, dict):
        findings.append("full pytest output is missing")
    else:
        suite_completed = _parsed_timestamp(suite.get("completed-at"))
        if suite_completed is not None:
            completed_times.append(suite_completed)
        if (
            suite.get("output-version") != 1
            or suite.get("kind") != "pytest-suite"
            or suite.get("id") != "full-pytest"
            or suite.get("suite") != "pytest -q"
            or not isinstance(suite.get("bootstrap-report-consumer"), bool)
            or suite.get("exit") != 0
            or not isinstance(suite.get("passed"), int)
            or suite.get("passed", 0) <= 0
            or suite.get("failed") != 0
            or _parsed_timestamp(suite.get("started-at")) is None
            or suite_completed is None
            or not isinstance(suite.get("stdout"), str)
            or not isinstance(suite.get("stderr"), str)
        ):
            findings.append("full pytest output does not prove a complete green suite")

    maturity = activation.validate_repository(root)
    if not maturity.valid:
        findings.append("current maturity validation rejects retained recovery evidence")
    states = {
        str(item.get("id")): str(item.get("state"))
        for item in maturity.controls
    }
    if report.get("control-states") != states:
        findings.append("reported control states are stale")

    verification = report.get("verification")
    expected_verification = {
        "self-hosted": {"artifact": "self-hosted", "budget-seconds": 5},
        "loaded": {
            "artifact": "loaded-validation",
            "record-multiplier-threshold-exclusive": LOAD_MULTIPLIER,
            "budget-seconds": 5,
        },
        "network": {
            "artifact": "network-namespace",
            "mechanism": "bubblewrap --unshare-net",
            "child-inclusive": True,
        },
        "recovery": {
            "validator": "method validate maturity",
            "controls": ["CTL-001", "CTL-002", "CTL-003", "CTL-014"],
        },
        "full-suite": {"artifact": "full-pytest"},
    }
    if verification != expected_verification:
        findings.append("verification declarations are incomplete or unexpected")

    protected_time = (
        _parsed_timestamp(protected.get("verified-at"))
        if isinstance(protected, dict)
        else None
    )
    if protected_time is None:
        findings.append("protected verification timestamp is invalid")
    if generated_at is not None and (
        (protected_time is not None and generated_at <= protected_time)
        or any(generated_at <= completed for completed in completed_times)
    ):
        findings.append("report was not generated after all retained outputs")
    return ReportValidation(tuple(sorted(set(findings))), report)


__all__ = [
    "ARTIFACT_DIRECTORY",
    "BACKLOG_SNAPSHOT_PATH",
    "LOAD_MULTIPLIER",
    "LOAD_RECORD_COUNT",
    "REPORT_PATH",
    "ReportValidation",
    "protected_snapshot",
    "run_report",
    "source_snapshot",
    "validate_report",
    "_network_child",
]
