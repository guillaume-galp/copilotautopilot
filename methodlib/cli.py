"""Argument dispatch and output framing for ``bin/method``."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, TextIO

from methodlib import (
    activation,
    backlog,
    docs,
    doctor,
    exits,
    gates,
    lock,
    migrate,
    trace,
)


VALIDATE_CHECKS = (
    "all",
    "gates",
    "schema",
    "lock",
    "trace",
    "maturity",
    "docs",
    "dod",
)
RESERVED_COMMANDS = ("tx", "packet", "usage", "budget", "report")
VALID_COMMANDS = ("validate", "doctor", *RESERVED_COMMANDS, "migrate")


@dataclass(frozen=True)
class CommandResult:
    exit_code: int
    payload: dict[str, object]
    diagnostics: tuple[str, ...] = ()


class UsageFailure(Exception):
    """A command-line usage error that must be rendered as JSON."""


class ParserExit(Exception):
    """A non-error parser exit, such as ``--help``."""

    def __init__(self, status: int) -> None:
        super().__init__(status)
        self.status = status


class MethodArgumentParser(argparse.ArgumentParser):
    """Keep argparse's human output off stdout and under CLI framing control."""

    def error(self, message: str) -> None:
        raise UsageFailure(message)

    def exit(self, status: int = 0, message: str | None = None) -> None:
        if message:
            self._print_message(message, sys.stderr)
        if status:
            raise UsageFailure(message or "invalid command line")
        raise ParserExit(status)

    def print_help(self, file: TextIO | None = None) -> None:
        super().print_help(file=sys.stderr if file is None else file)


def _doctor_command(
    _arguments: argparse.Namespace,
    probe_directory: Path | None,
) -> CommandResult:
    payload, diagnostics = doctor.build_report(probe_directory)
    return CommandResult(exits.SUCCESS, payload, tuple(diagnostics))


def _validate_command(
    arguments: argparse.Namespace,
    probe_directory: Path | None,
) -> CommandResult:
    check = arguments.check
    repository_root = (
        probe_directory
        if probe_directory is not None
        else Path(__file__).resolve().parents[1]
    )
    if check == "gates":
        if arguments.vp is None or arguments.stage is None:
            missing = []
            if arguments.vp is None:
                missing.append("--vp")
            if arguments.stage is None:
                missing.append("--stage")
            return _usage_result(
                "validate gates requires " + " and ".join(missing)
            )
        if not gates.VP_PATTERN.fullmatch(arguments.vp):
            return _usage_result("--vp must have the form VP<n>, with n >= 1")
        result = gates.validate_repository(
            repository_root,
            vp=arguments.vp,
            stage=arguments.stage,
            material_scope_expanded=arguments.material_scope_expanded,
        )
        diagnostics = tuple(
            "method validate gates: "
            f"{finding['file']} {finding['record']}: {finding['message']}"
            for finding in result.findings
        )
        return CommandResult(
            exits.SUCCESS if result.valid else exits.VALIDATION_FAILURE,
            dict(result.payload),
            diagnostics,
        )
    if check == "schema":
        result = backlog.validate_repository(repository_root)
        status = "ok" if result.valid else "failed"
        diagnostics = tuple(
            "method validate schema: "
            f"{finding['file']} {finding['record']}: {finding['message']}"
            for finding in result.findings
        )
        return CommandResult(
            exits.SUCCESS if result.valid else exits.VALIDATION_FAILURE,
            {
                "command": "validate",
                "check": "schema",
                "status": status,
                "findings": list(result.findings),
            },
            diagnostics,
        )
    if check == "lock":
        result = lock.validate_repository(repository_root)
        status = "ok" if result.valid else "failed"
        diagnostics = tuple(
            "method validate lock: "
            f"{finding['file']} {finding['record']}: {finding['message']}"
            for finding in result.findings
        )
        return CommandResult(
            exits.SUCCESS if result.valid else exits.VALIDATION_FAILURE,
            {
                "command": "validate",
                "check": "lock",
                "status": status,
                "manifest": dict(result.manifest),
                "findings": list(result.findings),
            },
            diagnostics,
        )
    if check == "trace":
        result = trace.validate_repository(repository_root)
        diagnostics = tuple(
            "method validate trace: "
            f"{finding['file']} {finding['record']}: {finding['message']}"
            for finding in result.findings
        )
        return CommandResult(
            exits.SUCCESS if result.valid else exits.VALIDATION_FAILURE,
            dict(result.payload),
            diagnostics,
        )
    if check == "maturity":
        result = activation.validate_repository(repository_root)
        diagnostics = tuple(
            "method validate maturity: "
            f"{finding['file']} {finding['record']}: {finding['message']}"
            for finding in result.findings
        )
        return CommandResult(
            exits.SUCCESS if result.valid else exits.VALIDATION_FAILURE,
            dict(result.payload),
            diagnostics,
        )
    if check == "docs":
        result = docs.validate_repository(repository_root)
        diagnostics = tuple(
            "method validate docs: "
            f"{finding['file']}:{finding['line']} {finding['message']}"
            for finding in result.findings
        )
        return CommandResult(
            exits.SUCCESS if result.valid else exits.VALIDATION_FAILURE,
            dict(result.payload),
            diagnostics,
        )
    if check == "all":
        return _validate_all(arguments, repository_root)
    message = (
        f"validate {check} is reserved by the foundation; "
        "its checks are not implemented in TH3.E2.US1"
    )
    return CommandResult(
        exits.PAUSE_OR_BLOCKED,
        {
            "command": "validate",
            "check": check,
            "status": "reserved",
            "message": message,
        },
        (f"method: {message}",),
    )


def _active_vps(repository_root: Path) -> tuple[str, ...]:
    """Discover gate scopes as inert path declarations in the active backlog."""

    path = repository_root / backlog.BACKLOG_PATH
    try:
        if path.stat().st_size > backlog.MAX_YAML_BYTES:
            return ()
        document = backlog.yaml.load(
            path.read_text(encoding="utf-8"),
            Loader=backlog.UniqueKeyLoader,
        )
    except (OSError, UnicodeError, ValueError, backlog.yaml.YAMLError):
        return ()
    if not isinstance(document, dict):
        return ()
    body = document.get("backlog")
    if not isinstance(body, dict):
        return ()
    themes = body.get("active-themes")
    archived = body.get("archived-themes")
    if not isinstance(themes, list) or not isinstance(archived, list):
        return ()
    all_themes = list(themes)
    for summary in archived:
        if not isinstance(summary, dict) or summary.get("schema-version") != 2:
            continue
        archive_ref = summary.get("archive-ref")
        if not isinstance(archive_ref, str):
            continue
        archive = repository_root / archive_ref
        try:
            if (
                archive.is_symlink()
                or not archive.is_file()
                or archive.stat().st_size > backlog.MAX_YAML_BYTES
                or not archive.resolve().is_relative_to(repository_root.resolve())
            ):
                continue
            snapshot = backlog.yaml.load(
                archive.read_text(encoding="utf-8"),
                Loader=backlog.UniqueKeyLoader,
            )
        except (OSError, UnicodeError, ValueError, backlog.yaml.YAMLError):
            continue
        if (
            isinstance(snapshot, dict)
            and set(snapshot) == {"theme"}
            and isinstance(snapshot.get("theme"), dict)
            and snapshot["theme"].get("id") == summary.get("id")
        ):
            all_themes.append(snapshot["theme"])
    scopes: set[str] = set()
    for theme in all_themes:
        if not isinstance(theme, dict):
            continue
        reference = theme.get("vision-ref")
        if not isinstance(reference, str):
            continue
        match = gates.VP_PATTERN.match(Path(reference).name)
        if match is not None:
            scopes.add(match.group(0))
    return tuple(sorted(scopes))


def _validate_all(
    arguments: argparse.Namespace,
    repository_root: Path,
) -> CommandResult:
    """Run every implemented TH3 repository check without short-circuiting."""

    summaries: list[dict[str, object]] = []
    findings: list[dict[str, object]] = []

    schema_result = backlog.validate_repository(repository_root)
    summaries.append(
        {
            "check": "schema",
            "status": "ok" if schema_result.valid else "failed",
            "finding_count": len(schema_result.findings),
        }
    )
    findings.extend(schema_result.findings)

    gate_findings: list[dict[str, object]] = []
    gate_scopes = (
        (arguments.vp,) if arguments.vp is not None else _active_vps(repository_root)
    )
    for vp in gate_scopes:
        if not gates.VP_PATTERN.fullmatch(vp):
            return _usage_result("--vp must have the form VP<n>, with n >= 1")
        for stage in gates.STAGES:
            result = gates.validate_repository(
                repository_root,
                vp=vp,
                stage=stage,
                material_scope_expanded=arguments.material_scope_expanded,
            )
            gate_findings.extend(result.findings)
    summaries.append(
        {
            "check": "gates",
            "status": "ok" if not gate_findings else "failed",
            "finding_count": len(gate_findings),
            "scopes": list(gate_scopes),
        }
    )
    findings.extend(gate_findings)

    for name, validator in (
        ("lock", lock.validate_repository),
        ("trace", trace.validate_repository),
        ("maturity", activation.validate_repository),
    ):
        result = validator(repository_root)
        summaries.append(
            {
                "check": name,
                "status": "ok" if result.valid else "failed",
                "finding_count": len(result.findings),
            }
        )
        findings.extend(result.findings)

    docs_result = docs.validate_repository(repository_root)
    summaries.append(
        {
            "check": "docs",
            "status": "ok" if docs_result.valid else "failed",
            "finding_count": len(docs_result.findings),
        }
    )
    findings.extend(docs_result.findings)

    valid = not findings
    diagnostics = tuple(
        "method validate all: "
        f"{finding['check']} {finding['file']}"
        f"{':' + str(finding['line']) if 'line' in finding else ''}: "
        f"{finding['message']}"
        for finding in findings
    )
    return CommandResult(
        exits.SUCCESS if valid else exits.VALIDATION_FAILURE,
        {
            "command": "validate",
            "check": "all",
            "status": "ok" if valid else "failed",
            "checks": summaries,
            "checked_files": list(docs_result.checked_files),
            "findings": findings,
        },
        diagnostics,
    )


def _reserved_command(
    arguments: argparse.Namespace,
    _probe_directory: Path | None,
) -> CommandResult:
    command = arguments.command
    message = f"{command} is a reserved command and is not implemented"
    return CommandResult(
        exits.PAUSE_OR_BLOCKED,
        {
            "command": command,
            "status": "reserved",
            "message": message,
        },
        (f"method: {message}",),
    )


def _migrate_command(
    arguments: argparse.Namespace,
    probe_directory: Path | None,
) -> CommandResult:
    repository_root = (
        probe_directory
        if probe_directory is not None
        else Path(__file__).resolve().parents[1]
    )
    try:
        result = migrate.assess_repository(
            repository_root,
            output=arguments.output,
        )
    except migrate.AssessmentError as error:
        finding = error.finding
        diagnostic = (
            "method migrate assess: "
            f"{finding['file']} {finding['record']}: {finding['message']}"
        )
        return CommandResult(
            exits.VALIDATION_FAILURE,
            {
                "command": "migrate",
                "action": "assess",
                "status": "failed",
                "output": arguments.output,
                "changed": False,
                "findings": [finding],
            },
            (diagnostic,),
        )
    return CommandResult(
        exits.SUCCESS,
        {
            "command": "migrate",
            "action": "assess",
            "status": "ok",
            "output": result.output,
            "changed": result.changed,
            "findings": list(result.findings),
        },
    )


def build_parser() -> MethodArgumentParser:
    parser = MethodArgumentParser(
        prog="method",
        description="Local, network-free Copilot Build Method tooling",
    )
    subcommands = parser.add_subparsers(
        dest="command",
        required=True,
        parser_class=MethodArgumentParser,
    )

    validate = subcommands.add_parser(
        "validate",
        help="run a repository contract check",
    )
    validate.add_argument("check", choices=VALIDATE_CHECKS)
    validate.add_argument(
        "--vp",
        help="VP scope for stage-scoped gate validation (for example VP3)",
    )
    validate.add_argument(
        "--stage",
        choices=gates.STAGES,
        help="lifecycle stage whose upstream entry gate is validated",
    )
    validate.add_argument(
        "--material-scope-expanded",
        action="store_true",
        help=(
            "declare the current caller-known material-expansion fact when "
            "validating a WAIVED Discovery disposition"
        ),
    )
    validate.add_argument(
        "--json",
        action="store_true",
        help="retained for compatibility; output is always JSON",
    )
    validate.set_defaults(handler=_validate_command)

    doctor_parser = subcommands.add_parser(
        "doctor",
        help="probe local runtime and filesystem capabilities",
    )
    doctor_parser.set_defaults(handler=_doctor_command)

    for command in RESERVED_COMMANDS:
        reserved = subcommands.add_parser(
            command,
            help="reserved for a later method capability",
        )
        reserved.add_argument("arguments", nargs=argparse.REMAINDER)
        reserved.set_defaults(handler=_reserved_command)

    migrate_parser = subcommands.add_parser(
        "migrate",
        help="assess prospective adoption for an existing repository",
    )
    migrate_actions = migrate_parser.add_subparsers(
        dest="migrate_action",
        required=True,
        parser_class=MethodArgumentParser,
    )
    assess = migrate_actions.add_parser(
        "assess",
        help="write a deterministic migration assessment",
    )
    assess.add_argument(
        "--output",
        default=migrate.DEFAULT_OUTPUT,
        help=(
            "safe repository-relative Markdown output path "
            f"(default: {migrate.DEFAULT_OUTPUT})"
        ),
    )
    assess.set_defaults(handler=_migrate_command)
    return parser


def _usage_result(message: str) -> CommandResult:
    return CommandResult(
        exits.USAGE_ERROR,
        {
            "command": None,
            "status": "usage-error",
            "message": message,
            "valid_subcommands": list(VALID_COMMANDS),
        },
        (f"method: usage error: {message}",),
    )


def _help_result() -> CommandResult:
    return CommandResult(
        exits.SUCCESS,
        {
            "command": "help",
            "status": "ok",
            "valid_subcommands": list(VALID_COMMANDS),
        },
    )


def dispatch(
    argv: Sequence[str] | None = None,
    *,
    probe_directory: Path | None = None,
) -> CommandResult:
    """Parse and dispatch without writing either output stream."""

    parser = build_parser()
    try:
        arguments = parser.parse_args(argv)
    except UsageFailure as error:
        return _usage_result(str(error))
    except ParserExit:
        return _help_result()
    return arguments.handler(arguments, probe_directory)


def emit(
    result: CommandResult,
    *,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    """Write exactly one JSON object and any human diagnostics."""

    for diagnostic in result.diagnostics:
        print(diagnostic, file=stderr)
    print(
        json.dumps(result.payload, sort_keys=True, separators=(",", ":")),
        file=stdout,
    )
    return result.exit_code


def main(argv: Sequence[str] | None = None) -> int:
    return emit(dispatch(argv))
