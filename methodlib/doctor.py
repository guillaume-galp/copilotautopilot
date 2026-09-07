"""Capability probes used by ``method doctor``.

The probes perform only local runtime and filesystem checks. A missing
capability is represented as a finding instead of being raised as an error.
"""

from __future__ import annotations

import os
import platform
import shutil
import sys
import tempfile
from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import Callable, Sequence


Finding = dict[str, object]
PathValue = str | bytes | os.PathLike[str] | os.PathLike[bytes]


def _available(capability: str, **details: object) -> Finding:
    return {"capability": capability, "available": True, **details}


def _unavailable(capability: str, reason: str, **details: object) -> Finding:
    return {
        "capability": capability,
        "available": False,
        "reason": reason,
        **details,
    }


def probe_python(
    version_info: Sequence[int] | None = None,
    version: str | None = None,
) -> Finding:
    """Report whether the running Python satisfies the supported baseline."""

    current = tuple(version_info or sys.version_info)
    rendered_version = version or platform.python_version()
    supported = current >= (3, 11)
    if not supported:
        return _unavailable(
            "python",
            "Python 3.11 or newer is required",
            version=rendered_version,
            required=">=3.11",
        )
    return _available(
        "python",
        version=rendered_version,
        required=">=3.11",
    )


def probe_pyyaml(
    importer: Callable[[str], ModuleType] = import_module,
) -> Finding:
    """Import PyYAML and report a missing or broken installation."""

    try:
        yaml_module = importer("yaml")
    except ModuleNotFoundError as error:
        if error.name != "yaml":
            return _unavailable(
                "pyyaml",
                f"PyYAML dependency is missing: {error.name}",
            )
        return _unavailable("pyyaml", "PyYAML is not installed")
    except ImportError as error:
        return _unavailable("pyyaml", f"PyYAML could not be imported: {error}")

    version = getattr(yaml_module, "__version__", None)
    if version is None:
        return _unavailable("pyyaml", "PyYAML does not report a version")
    return _available("pyyaml", version=str(version))


def probe_git(
    finder: Callable[[str], str | None] = shutil.which,
) -> Finding:
    """Report whether a local git executable is available."""

    executable = finder("git")
    if executable is None:
        return _unavailable("git", "git executable was not found on PATH")
    return _available("git", executable=executable)


def probe_atomic_replace(
    directory: Path,
    replace_file: Callable[[PathValue, PathValue], None] | None = None,
) -> Finding:
    """Exercise same-filesystem replacement and verify its visible result."""

    replacer = (
        replace_file
        if replace_file is not None
        else getattr(os, "replace", None)
    )
    if replacer is None:
        return _unavailable("atomic-replace", "os.replace is unavailable")

    try:
        with tempfile.TemporaryDirectory(
            prefix=".method-doctor-replace-", dir=directory
        ) as temporary:
            probe_dir = Path(temporary)
            source = probe_dir / "source"
            destination = probe_dir / "destination"
            source.write_bytes(b"replacement")
            destination.write_bytes(b"original")
            replacer(source, destination)
            if source.exists() or destination.read_bytes() != b"replacement":
                return _unavailable(
                    "atomic-replace",
                    "replace operation did not produce the expected result",
                )
    except (OSError, NotImplementedError) as error:
        return _unavailable("atomic-replace", f"replace probe failed: {error}")
    return _available("atomic-replace")


def probe_exclusive_create(
    directory: Path,
    open_file: Callable[[PathValue, int, int], int] | None = None,
) -> Finding:
    """Verify that O_EXCL rejects a second create for the same path."""

    exclusive_flag = getattr(os, "O_EXCL", None)
    create_flag = getattr(os, "O_CREAT", None)
    write_flag = getattr(os, "O_WRONLY", None)
    opener = open_file if open_file is not None else getattr(os, "open", None)
    if (
        exclusive_flag is None
        or create_flag is None
        or write_flag is None
        or opener is None
    ):
        return _unavailable(
            "exclusive-create",
            "exclusive file creation is unavailable",
        )

    flags = exclusive_flag | create_flag | write_flag
    try:
        with tempfile.TemporaryDirectory(
            prefix=".method-doctor-exclusive-", dir=directory
        ) as temporary:
            target = Path(temporary) / "lock"
            descriptor = opener(target, flags, 0o600)
            os.close(descriptor)
            try:
                duplicate_descriptor = opener(target, flags, 0o600)
            except FileExistsError:
                return _available("exclusive-create")
            except (OSError, NotImplementedError) as error:
                return _unavailable(
                    "exclusive-create",
                    f"second exclusive create failed unexpectedly: {error}",
                )
            else:
                os.close(duplicate_descriptor)
                return _unavailable(
                    "exclusive-create",
                    "a second exclusive create unexpectedly succeeded",
                )
    except (OSError, NotImplementedError) as error:
        return _unavailable(
            "exclusive-create",
            f"exclusive-create probe failed: {error}",
        )


def probe_fsync(
    directory: Path,
    sync_file: Callable[[int], None] | None = None,
) -> Finding:
    """Verify that file data can be flushed through the local filesystem."""

    syncer = sync_file if sync_file is not None else getattr(os, "fsync", None)
    if syncer is None:
        return _unavailable("fsync", "os.fsync is unavailable")

    try:
        with tempfile.TemporaryDirectory(
            prefix=".method-doctor-fsync-", dir=directory
        ) as temporary:
            target = Path(temporary) / "data"
            with target.open("wb") as stream:
                stream.write(b"method doctor")
                stream.flush()
                syncer(stream.fileno())
    except (OSError, NotImplementedError) as error:
        return _unavailable("fsync", f"fsync probe failed: {error}")
    return _available("fsync")


def _unresolved_probe_directory_findings(error: OSError) -> list[Finding]:
    """Report filesystem probes that cannot run without a usable root."""

    detail = error.strerror or type(error).__name__
    if error.errno is not None:
        detail = f"[Errno {error.errno}] {detail}"
    reason = f"probe directory unavailable: {detail}"
    return [
        _unavailable("atomic-replace", reason),
        _unavailable("exclusive-create", reason),
        _unavailable("fsync", reason),
    ]


def build_report(directory: Path | None = None) -> tuple[dict[str, object], list[str]]:
    """Run all doctor probes and return machine and human representations."""

    findings = [
        probe_python(),
        probe_pyyaml(),
        probe_git(),
    ]
    try:
        probe_directory = (directory or Path.cwd()).resolve()
    except OSError as error:
        probe_directory = None
        findings.extend(_unresolved_probe_directory_findings(error))
    else:
        findings.extend(
            [
                probe_atomic_replace(probe_directory),
                probe_exclusive_create(probe_directory),
                probe_fsync(probe_directory),
            ]
        )
    missing = [
        str(finding["capability"])
        for finding in findings
        if not finding["available"]
    ]
    transition_controls: dict[str, object] = {
        "status": "blocked" if missing else "ready",
        "blocked_above": "MANUAL" if missing else None,
        "limitations": missing,
    }
    report: dict[str, object] = {
        "command": "doctor",
        "status": "limited" if missing else "ok",
        "probe_directory": (
            str(probe_directory) if probe_directory is not None else None
        ),
        "findings": findings,
        "transition_controls": transition_controls,
    }

    diagnostics = []
    for finding in findings:
        capability = finding["capability"]
        if finding["available"]:
            version = finding.get("version")
            suffix = f" ({version})" if version else ""
            diagnostics.append(f"method doctor: {capability}: available{suffix}")
        else:
            diagnostics.append(
                f"method doctor: {capability}: unavailable: {finding['reason']}"
            )
    if missing:
        diagnostics.append(
            "method doctor: transition controls are blocked above MANUAL"
        )
    return report, diagnostics
