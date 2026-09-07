"""Closed recovery-case definitions and content digests for TH3 controls.

Recovery evidence is repository data, not an instruction source.  The runner
and maturity validator share these hard-coded cases; neither reads a command
from an evidence record.  Digests cover the repository input snapshot that a
case used, while excluding generated evidence and orchestrator-owned mutable
state which changes after a story run.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


FIXTURE_PATH = "tests/fixtures/method_recovery/cases.yaml"
RUNNER_PATH = "bin/run-th3-e4-us5-evidence"
TEST_REFERENCE = (
    "tests/test_e4_self_hosted_validation.py::"
    "test_recovery_runner_outputs_are_bound_and_consumed"
)
EVIDENCE_DIRECTORY = "docs/plan/evidence/control-activation"
RUN_OUTPUT_DIRECTORY = f"{EVIDENCE_DIRECTORY}/runs"
COMMAND_ENTRYPOINTS = ("bin/method", RUNNER_PATH)


@dataclass(frozen=True)
class RecoveryCase:
    control_id: str
    validator_check: str
    recovery_case: str
    target: str
    mutation: str
    arguments: tuple[str, ...]

    @property
    def key(self) -> tuple[str, str]:
        return self.control_id, self.validator_check

    @property
    def stem(self) -> str:
        return f"{self.control_id}-{self.validator_check}"


CASES = (
    RecoveryCase(
        "CTL-001",
        "gates",
        "requirements-gate-blocked-then-restored",
        "docs/discovery/VP3-discovery-led-cost-aware-methodology/README.md",
        "blocked-discovery-gate",
        (
            "validate",
            "gates",
            "--vp",
            "VP3",
            "--stage",
            "requirements",
            "--json",
        ),
    ),
    RecoveryCase(
        "CTL-002",
        "schema",
        "backlog-malformed-then-restored",
        "docs/plan/backlog.yaml",
        "malformed-backlog",
        ("validate", "schema", "--json"),
    ),
    RecoveryCase(
        "CTL-003",
        "lock",
        "locked-story-edited-then-restored",
        (
            "docs/themes/TH2-gitflow-operator/E1-gitflow-operator/"
            "stories/US1-develop-branch-workflow.md"
        ),
        "edited-locked-story",
        ("validate", "lock", "--json"),
    ),
    RecoveryCase(
        "CTL-003",
        "trace",
        "story-trace-dangling-then-restored",
        (
            "docs/themes/TH3-discovery-requirements-foundation/epics/"
            "E4-activation-migration-integration/stories/"
            "US5-self-hosted-validation-run.md"
        ),
        "dangling-story-trace",
        ("validate", "trace", "--json"),
    ),
    RecoveryCase(
        "CTL-014",
        "docs",
        "active-doc-stale-then-removed",
        ".github/skills/stale-recovery-fixture/SKILL.md",
        "stale-active-document",
        ("validate", "docs", "--json"),
    ),
)
CASE_BY_KEY: Mapping[tuple[str, str], RecoveryCase] = {
    case.key: case for case in CASES
}


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _is_regular_local_file(root: Path, relative: Path) -> bool:
    current = root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            return False
    return current.is_file()


def command_dependency_files(root: Path) -> tuple[str, ...]:
    """Return the deterministic transitive local implementation dependency set."""

    # Both command entrypoints import through the shared methodlib package.
    # Binding its complete Python source tree is deliberately conservative:
    # it includes every currently imported transitive module and ensures a new
    # local module cannot become an undeclared implementation dependency.
    candidates = {
        *COMMAND_ENTRYPOINTS,
        *(
            path.relative_to(root).as_posix()
            for path in (root / "methodlib").rglob("*.py")
        ),
    }
    dependencies = tuple(sorted(candidates))
    for relative in dependencies:
        if not _is_regular_local_file(root, Path(relative)):
            raise ValueError(
                f"local command dependency is missing or unsafe: {relative}"
            )
    return dependencies


def _input_files(
    root: Path,
    dependency_files: Sequence[str] | None = None,
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                FIXTURE_PATH,
                TEST_REFERENCE.split("::", 1)[0],
                *(
                    command_dependency_files(root)
                    if dependency_files is None
                    else dependency_files
                ),
            }
        )
    )


def _mutated_content(case: RecoveryCase, original: bytes | None) -> bytes | None:
    if case.mutation == "blocked-discovery-gate":
        assert original is not None
        old = b"| Verdict | READY_WITH_DEFERRALS |"
        assert original.count(old) == 1
        return original.replace(old, b"| Verdict | BLOCKED |", 1)
    if case.mutation == "malformed-backlog":
        return b"backlog:\n  active-themes: [\n"
    if case.mutation == "edited-locked-story":
        assert original is not None
        return original + b"\nunauthorized recovery mutation\n"
    if case.mutation == "dangling-story-trace":
        assert original is not None
        old = b"requirements: [PR-015, QR-002, QR-003, QR-010, QR-011]"
        assert original.count(old) == 1
        return original.replace(
            old,
            b"requirements: [PR-999, QR-002, QR-003, QR-010, QR-011]",
            1,
        )
    if case.mutation == "stale-active-document":
        assert original is None
        return (
            b"# Stale recovery fixture\n\nThe lifecycle has "
            + b"four"
            + b" stages.\n"
        )
    raise ValueError(f"unknown closed recovery mutation: {case.mutation}")


def input_digest(
    root: Path,
    case: RecoveryCase,
    kind: str,
    *,
    dependency_files: Sequence[str] | None = None,
) -> str:
    """Digest immutable case inputs and the closed executed phase.

    Mutable repository state is intentionally not called an immutable
    baseline.  The retained fixture manifest, test, runner, CLI, and validator
    implementation are the immutable inputs.  The bypass digest additionally
    commits to the hard-coded mutation identifier and target.
    """

    if kind not in {"bypass-attempt", "restore-and-pass"}:
        raise ValueError("recovery kind is not supported")
    entries = {
        relative: (root / relative).read_bytes()
        for relative in _input_files(root, dependency_files)
    }
    if kind == "bypass-attempt":
        entries[f"mutation:{case.target}"] = case.mutation.encode("ascii")
    digest = hashlib.sha256()
    for relative, content in sorted(entries.items()):
        encoded_path = relative.encode("utf-8")
        digest.update(len(encoded_path).to_bytes(8, "big"))
        digest.update(encoded_path)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def apply_bypass(root: Path, case: RecoveryCase) -> bytes | None:
    """Apply one closed mutation and return the prior bytes, if any."""

    target = root / case.target
    original = target.read_bytes() if target.is_file() else None
    mutated = _mutated_content(case, original)
    target.parent.mkdir(parents=True, exist_ok=True)
    if mutated is None:
        target.unlink(missing_ok=True)
    else:
        target.write_bytes(mutated)
    return original


def restore(root: Path, case: RecoveryCase, original: bytes | None) -> None:
    target = root / case.target
    if original is None:
        target.unlink(missing_ok=True)
        try:
            target.parent.rmdir()
        except OSError:
            pass
    else:
        target.write_bytes(original)


def output_relative(case: RecoveryCase, kind: str) -> str:
    return f"{RUN_OUTPUT_DIRECTORY}/{case.stem}-{kind}.json"


def evidence_relative(case: RecoveryCase, kind: str) -> str:
    return f"{EVIDENCE_DIRECTORY}/{case.stem}-{kind}.yaml"


def file_digest_fields(root: Path) -> dict[str, str]:
    test_path = TEST_REFERENCE.split("::", 1)[0]
    return {
        "fixture-sha256": sha256_file(root / FIXTURE_PATH),
        "test-sha256": sha256_file(root / test_path),
        "runner-sha256": sha256_file(root / RUNNER_PATH),
    }


__all__ = [
    "CASES",
    "CASE_BY_KEY",
    "EVIDENCE_DIRECTORY",
    "FIXTURE_PATH",
    "RUNNER_PATH",
    "RUN_OUTPUT_DIRECTORY",
    "TEST_REFERENCE",
    "RecoveryCase",
    "apply_bypass",
    "command_dependency_files",
    "evidence_relative",
    "file_digest_fields",
    "input_digest",
    "output_relative",
    "restore",
    "sha256_bytes",
    "sha256_file",
]
