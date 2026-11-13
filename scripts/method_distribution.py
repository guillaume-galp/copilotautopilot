#!/usr/bin/env python3
"""Build and check reproducible, package-only Copilot method distributions."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")
OVERLAY_HEADING = b"## Shared Credential Preflight\n"
PACKAGE_PATHS = (
    ".github/agents",
    ".github/skills",
    ".github/prompts",
    ".github/copilot-instructions.md",
    "bin",
    "methodlib",
    "scripts/method_distribution.py",
    "README.md",
    "CHANGELOG.md",
    "docs/architecture/project-setup.md",
    "VERSION",
)


def read_version(root: Path) -> str:
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    if not VERSION_PATTERN.fullmatch(version):
        raise ValueError(f"{root / 'VERSION'} must contain a semantic version")
    return version


def _git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def _is_generated_file(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    return "__pycache__" in relative.parts or path.suffix == ".pyc"


def source_provenance(root: Path, version: str) -> dict[str, object]:
    commit = _git(root, "rev-parse", "HEAD")
    dirty = bool(_git(root, "status", "--porcelain", "--untracked-files=all"))
    tags = set(_git(root, "tag", "--points-at", "HEAD").splitlines())
    release_ref = f"v{version}"
    is_release = not dirty and release_ref in tags
    short_commit = commit[:7]
    build_version = (
        version
        if is_release
        else f"{version}+dev.g{short_commit}{'.dirty' if dirty else ''}"
    )
    branch = _git(root, "branch", "--show-current")
    return {
        "version": version,
        "build_version": build_version,
        "source_commit": commit,
        "source_ref": release_ref if release_ref in tags else branch or commit,
        "source_dirty": dirty,
        "release": is_release,
    }


def _source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for relative in PACKAGE_PATHS:
        asset = root / relative
        if not asset.exists():
            raise ValueError(f"required distribution resource is missing: {relative}")
        if asset.is_symlink():
            raise ValueError(f"distribution resources cannot be symlinks: {relative}")
        if asset.is_file():
            files.append(asset)
            continue
        if not asset.is_dir():
            raise ValueError(f"unsupported distribution resource: {relative}")
        for path in sorted(asset.rglob("*")):
            if path.is_symlink():
                raise ValueError(
                    f"distribution resources cannot be symlinks: "
                    f"{path.relative_to(root)}"
                )
            if path.is_file() and not _is_generated_file(path, root):
                files.append(path)

    skills_root = root / ".github/skills"
    for skill in sorted(path for path in skills_root.iterdir() if path.is_dir()):
        if not (skill / "SKILL.md").is_file():
            raise ValueError(f"skill is missing its SKILL.md: {skill.name}")
    return sorted(files, key=lambda path: path.relative_to(root).as_posix())


def build_manifest(root: Path) -> tuple[dict[str, object], list[Path]]:
    version = read_version(root)
    files = _source_files(root)
    provenance = source_provenance(root, version)
    entries = []
    for path in files:
        relative = path.relative_to(root).as_posix()
        entries.append(
            {
                "path": relative,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "mode": path.stat().st_mode & 0o777,
            }
        )
    manifest: dict[str, object] = {
        "schema_version": 1,
        **provenance,
        "compatibility": {
            "method_runtime_version": provenance["build_version"],
            "skill_format": "copilot-skill-v1",
        },
        "user_overlays": {
            "credential_preflight": "external-user-managed",
            "included_in_package": False,
        },
        "files": entries,
    }
    return manifest, files


def package_distribution(
    root: Path,
    output: Path,
    *,
    development: bool = False,
) -> dict[str, object]:
    manifest, files = build_manifest(root)
    if not manifest["release"] and not development:
        raise ValueError(
            "source is not a clean matching release tag; pass --development "
            "to label the archive as a development build"
        )

    resolved_output = output.resolve()
    if resolved_output.is_relative_to(root.resolve()):
        raise ValueError("archive output must be outside the source checkout")
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    manifest_bytes = (
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    archive_entries: dict[str, tuple[bytes, int]] = {}
    for path in files:
        archive_entries[path.relative_to(root).as_posix()] = (
            path.read_bytes(),
            path.stat().st_mode & 0o777,
        )
    archive_entries["distribution-manifest.json"] = (manifest_bytes, 0o644)

    with zipfile.ZipFile(resolved_output, "x") as archive:
        for name in sorted(archive_entries):
            content, mode = archive_entries[name]
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = mode << 16
            archive.writestr(
                info,
                content,
                compress_type=zipfile.ZIP_DEFLATED,
                compresslevel=9,
            )
    return manifest


def _credential_overlay_matches(expected: bytes, actual: bytes) -> bool:
    if not actual.startswith(expected):
        return False
    suffix = actual[len(expected) :].lstrip(b"\r\n")
    return suffix.startswith(OVERLAY_HEADING)


def compare_tree(
    source: Path,
    target: Path,
    *,
    allow_credential_overlay: bool = False,
    check_executable: bool = False,
    check_extra: bool = False,
    managed_roots: set[str] | None = None,
) -> tuple[list[str], int]:
    if not source.is_dir():
        return [f"source directory missing: {source}"], 0
    if not target.is_dir():
        return [f"target directory missing: {target}"], 0

    findings: list[str] = []
    overlays = 0
    source_files = sorted(
        path
        for path in source.rglob("*")
        if path.is_file() and not _is_generated_file(path, source)
    )
    source_paths = {path.relative_to(source).as_posix() for path in source_files}
    for source_file in source_files:
        relative = source_file.relative_to(source)
        target_file = target / relative
        label = relative.as_posix()
        if not target_file.is_file():
            findings.append(f"missing resource: {label}")
            continue
        if target_file.is_symlink():
            findings.append(f"symlink resource: {label}")
            continue
        expected = source_file.read_bytes()
        actual = target_file.read_bytes()
        if actual != expected:
            if (
                allow_credential_overlay
                and relative.name == "SKILL.md"
                and _credential_overlay_matches(expected, actual)
            ):
                overlays += 1
                continue
            findings.append(f"modified resource: {label}")
            continue
        if check_executable and bool(source_file.stat().st_mode & 0o111) != bool(
            target_file.stat().st_mode & 0o111
        ):
            findings.append(f"executable mode drift: {label}")
    if check_extra:
        for target_file in sorted(
            path
            for path in target.rglob("*")
            if path.is_file() and not _is_generated_file(path, target)
        ):
            relative = target_file.relative_to(target)
            label = relative.as_posix()
            if label in source_paths:
                continue
            if managed_roots is not None and relative.parts[0] not in managed_roots:
                continue
            kind = "symlink resource" if target_file.is_symlink() else "unexpected resource"
            findings.append(f"{kind}: {label}")
    return findings, overlays


def compare_agents(source: Path, target: Path) -> list[str]:
    if not source.is_dir():
        return [f"source directory missing: {source}"]
    if not target.is_dir():
        return [f"target directory missing: {target}"]
    findings: list[str] = []
    for source_file in sorted(source.glob("*.agent.md")):
        target_file = target / source_file.name
        if not target_file.is_file():
            findings.append(f"missing active agent: {source_file.name}")
        elif target_file.read_bytes() != source_file.read_bytes():
            findings.append(f"modified active agent: {source_file.name}")
    return findings


def resolve_command(
    name: str,
    repository_root: Path,
    *,
    path: str | None = None,
) -> Path | None:
    local = repository_root / "bin" / name
    if local.is_file() and os.access(local, os.X_OK):
        return local.resolve()
    resolved = shutil.which(name, path=path)
    return Path(resolved).resolve() if resolved else None


def _target_version(root: Path) -> str | None:
    manifest_path = root / "distribution-manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        version = manifest.get("build_version")
        return version if isinstance(version, str) else None
    version_path = root / "VERSION"
    if version_path.is_file():
        return version_path.read_text(encoding="utf-8").strip()
    match = re.fullmatch(r"v?(\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?)", root.name)
    return match.group(1) if match else None


def check_runtime(
    root: Path,
    manifest: dict[str, object],
    *,
    source_root: Path = ROOT,
) -> list[str]:
    findings: list[str] = []
    target_version = _target_version(root)
    expected_version = manifest["build_version"]
    if target_version is None:
        findings.append("runtime provenance missing: no distribution version found")
    elif target_version != expected_version:
        findings.append(
            f"runtime version drift: expected {expected_version}, found {target_version}"
        )

    for relative in PACKAGE_PATHS:
        source = source_root / relative
        target = root / relative
        if source.is_dir():
            differences, _ = compare_tree(
                source,
                target,
                check_executable=relative == "bin",
                check_extra=True,
            )
            findings.extend(f"{relative}/{item}" for item in differences)
        elif not target.is_file():
            findings.append(f"missing runtime resource: {relative}")
        elif source.read_bytes() != target.read_bytes():
            findings.append(f"modified runtime resource: {relative}")
    return findings


def _check_command(arguments: argparse.Namespace) -> int:
    manifest, _ = build_manifest(ROOT)
    findings: list[str] = []
    overlay_counts: dict[str, int] = {}
    if arguments.workspace_root:
        workspace = arguments.workspace_root
        findings.extend(
            f"workspace: {item}"
            for item in compare_agents(
                ROOT / ".github/agents", workspace / ".github/agents"
            )
        )
        for relative in (".github/prompts",):
            differences, _ = compare_tree(ROOT / relative, workspace / relative)
            findings.extend(
                f"workspace: {relative}/{item}" for item in differences
            )
        differences, found_overlays = compare_tree(
            ROOT / ".github/skills",
            workspace / ".github/skills",
            allow_credential_overlay=True,
            check_extra=True,
            managed_roots={
                path.name
                for path in (ROOT / ".github/skills").iterdir()
                if path.is_dir()
            },
        )
        findings.extend(
            f"workspace: .github/skills/{item}" for item in differences
        )
        overlay_counts["workspace"] = found_overlays
    if arguments.skills_root:
        differences, found_overlays = compare_tree(
            ROOT / ".github/skills",
            arguments.skills_root,
            allow_credential_overlay=True,
            check_extra=True,
            managed_roots={
                path.name
                for path in (ROOT / ".github/skills").iterdir()
                if path.is_dir()
            },
        )
        findings.extend(f"user-skills: {item}" for item in differences)
        overlay_counts["user_skills"] = found_overlays
    if arguments.runtime_root:
        findings.extend(
            f"runtime: {item}"
            for item in check_runtime(arguments.runtime_root, manifest)
        )

    result = {
        "status": "ok" if not findings else "drift",
        "build_version": manifest["build_version"],
        "source_commit": manifest["source_commit"],
        "source_dirty": manifest["source_dirty"],
        "credential_overlays_preserved": overlay_counts,
        "findings": findings,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not findings else 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    package = commands.add_parser("package", help="build a deterministic ZIP archive")
    package.add_argument("--output", type=Path, required=True)
    package.add_argument(
        "--development",
        action="store_true",
        help="allow and label a non-release or dirty source tree",
    )

    check = commands.add_parser("check", help="compare explicit distribution targets")
    check.add_argument("--workspace-root", type=Path)
    check.add_argument("--skills-root", type=Path)
    check.add_argument("--runtime-root", type=Path)

    resolve = commands.add_parser(
        "resolve-command",
        help="resolve a workspace-local bin command, then PATH",
    )
    resolve.add_argument("name")
    resolve.add_argument("--repository-root", type=Path, default=Path.cwd())
    resolve.add_argument("--path")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _build_parser().parse_args(argv)
    try:
        if arguments.command == "package":
            manifest = package_distribution(
                ROOT,
                arguments.output,
                development=arguments.development,
            )
            print(
                json.dumps(
                    {
                        "status": "packaged",
                        "output": str(arguments.output.resolve()),
                        "build_version": manifest["build_version"],
                        "source_commit": manifest["source_commit"],
                        "source_dirty": manifest["source_dirty"],
                    },
                    sort_keys=True,
                )
            )
            return 0
        if arguments.command == "check":
            if not any(
                (
                    arguments.workspace_root,
                    arguments.skills_root,
                    arguments.runtime_root,
                )
            ):
                raise ValueError("check requires at least one explicit target")
            return _check_command(arguments)
        resolved = resolve_command(
            arguments.name,
            arguments.repository_root,
            path=arguments.path,
        )
        if resolved is None:
            print(
                f"command not found in {arguments.repository_root / 'bin'} or PATH: "
                f"{arguments.name}",
                file=sys.stderr,
            )
            return 127
        print(resolved)
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"method distribution: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
