import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts import method_distribution as distribution  # noqa: E402


def make_distribution_tree(root: Path) -> Path:
    files = {
        ".github/agents/owner.agent.md": "agent\n",
        ".github/skills/method/SKILL.md": "skill\n",
        ".github/skills/method/templates/example.md": "template\n",
        ".github/prompts/old-command.prompt.md": "alias\n",
        ".github/copilot-instructions.md": "instructions\n",
        "bin/method": "#!/bin/sh\n",
        "bin/gitflow-operator": "#!/bin/sh\n",
        "methodlib/__init__.py": "",
        "scripts/method_distribution.py": "# package tool\n",
        "README.md": "# Fixture\n",
        "CHANGELOG.md": "# Changelog\n",
        "docs/architecture/project-setup.md": "# Setup\n",
        "VERSION": "1.2.3\n",
    }
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    for relative in ("bin/method", "bin/gitflow-operator"):
        (root / relative).chmod(0o755)
    return root


def initialize_release(root: Path) -> None:
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(
        ["git", "-C", str(root), "config", "user.email", "test@example.com"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(root), "config", "user.name", "Test User"],
        check=True,
    )
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(root), "commit", "-qm", "test release"],
        check=True,
    )
    subprocess.run(["git", "-C", str(root), "tag", "v1.2.3"], check=True)


def test_missing_nested_skill_resource_is_reported(tmp_path: Path):
    source = make_distribution_tree(tmp_path / "source")
    target = tmp_path / "target"
    target.mkdir()
    (target / "method").mkdir()
    (target / "method/SKILL.md").write_text("skill\n", encoding="utf-8")

    findings, _ = distribution.compare_tree(
        source / ".github/skills",
        target,
        allow_credential_overlay=True,
    )

    assert findings == ["missing resource: method/templates/example.md"]


def test_extra_managed_resource_is_reported_but_unmanaged_skill_is_ignored(
    tmp_path: Path,
):
    source = make_distribution_tree(tmp_path / "source")
    target = tmp_path / "target"
    target.mkdir()
    (target / "method/templates").mkdir(parents=True)
    (target / "method/SKILL.md").write_text("skill\n", encoding="utf-8")
    (target / "method/templates/example.md").write_text("template\n", encoding="utf-8")
    (target / "method/notes.md").write_text("local file\n", encoding="utf-8")
    (target / "other-skill").mkdir()
    (target / "other-skill/SKILL.md").write_text("other\n", encoding="utf-8")

    findings, _ = distribution.compare_tree(
        source / ".github/skills",
        target,
        check_extra=True,
        managed_roots={"method"},
    )

    assert findings == ["unexpected resource: method/notes.md"]


def test_missing_active_agent_is_reported(tmp_path: Path):
    source = make_distribution_tree(tmp_path / "source")
    target = tmp_path / "target"
    target.mkdir()

    findings = distribution.compare_agents(
        source / ".github/agents",
        target,
    )

    assert findings == ["missing active agent: owner.agent.md"]


def test_credential_overlay_is_accepted_without_changing_target(tmp_path: Path):
    source = make_distribution_tree(tmp_path / "source")
    target = tmp_path / "target"
    target.mkdir()
    (target / "method").mkdir()
    skill = source / ".github/skills/method/SKILL.md"
    overlay = (
        "\n## Shared Credential Preflight\n"
        "User-managed policy. Never expose credential values.\n"
    )
    target_skill = target / "method/SKILL.md"
    target_skill.write_text(skill.read_text(encoding="utf-8") + overlay, encoding="utf-8")
    (target / "method/templates").mkdir()
    (target / "method/templates/example.md").write_text(
        "template\n",
        encoding="utf-8",
    )
    before = target_skill.read_bytes()

    findings, overlays = distribution.compare_tree(
        source / ".github/skills",
        target,
        allow_credential_overlay=True,
    )

    assert findings == []
    assert overlays == 1
    assert target_skill.read_bytes() == before


def test_runtime_version_drift_is_explicit(tmp_path: Path):
    root = make_distribution_tree(tmp_path / "source")
    initialize_release(root)
    manifest, _ = distribution.build_manifest(root)
    runtime = tmp_path / "runtime" / "v1.2.2"
    runtime.mkdir(parents=True)

    findings = distribution.check_runtime(runtime, manifest, source_root=root)

    assert any("runtime version drift" in finding for finding in findings)


def test_command_resolution_prefers_local_then_path(tmp_path: Path):
    repository = tmp_path / "repo"
    local_command = repository / "bin/gitflow-operator"
    local_command.parent.mkdir(parents=True)
    local_command.write_text("#!/bin/sh\n", encoding="utf-8")
    local_command.chmod(0o755)
    path_directory = tmp_path / "path"
    path_directory.mkdir()
    path_command = path_directory / "gitflow-operator"
    path_command.write_text("#!/bin/sh\n", encoding="utf-8")
    path_command.chmod(0o755)

    assert distribution.resolve_command(
        "gitflow-operator",
        repository,
        path=str(path_directory),
    ) == local_command.resolve()

    local_command.unlink()
    assert distribution.resolve_command(
        "gitflow-operator",
        repository,
        path=str(path_directory),
    ) == path_command.resolve()
    assert distribution.resolve_command(
        "missing",
        repository,
        path=str(path_directory),
    ) is None


def test_runtime_comparison_checks_executable_mode(tmp_path: Path):
    source = make_distribution_tree(tmp_path / "source")
    target = tmp_path / "target"
    (target / "bin").mkdir(parents=True)
    source_command = source / "bin/gitflow-operator"
    target_command = target / "bin/gitflow-operator"
    target_command.write_bytes(source_command.read_bytes())
    target_command.chmod(0o644)

    findings, _ = distribution.compare_tree(
        source / "bin",
        target / "bin",
        check_executable=True,
    )

    assert "executable mode drift: gitflow-operator" in findings


def test_package_is_reproducible_and_records_complete_resources(tmp_path: Path):
    source = make_distribution_tree(tmp_path / "source")
    cache_file = source / "methodlib/__pycache__/cached.cpython-311.pyc"
    cache_file.parent.mkdir()
    cache_file.write_bytes(b"generated cache")
    initialize_release(source)
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"

    first_manifest = distribution.package_distribution(source, first)
    second_manifest = distribution.package_distribution(source, second)

    assert first_manifest["release"] is True
    assert first.read_bytes() == second.read_bytes()
    with zipfile.ZipFile(first) as archive:
        manifest = json.loads(archive.read("distribution-manifest.json"))
        paths = {entry["path"] for entry in manifest["files"]}
        assert ".github/skills/method/templates/example.md" in paths
        assert ".github/agents/owner.agent.md" in paths
        assert "bin/gitflow-operator" in paths
        assert "scripts/method_distribution.py" in paths
        assert not any(path.endswith(".pyc") for path in paths)


def test_development_package_requires_explicit_opt_in(tmp_path: Path):
    source = make_distribution_tree(tmp_path / "source")
    initialize_release(source)
    (source / ".github/skills/method/SKILL.md").write_text(
        "changed\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="pass --development"):
        distribution.package_distribution(source, tmp_path / "rejected.zip")

    manifest = distribution.package_distribution(
        source,
        tmp_path / "development.zip",
        development=True,
    )
    assert manifest["release"] is False
    assert manifest["build_version"].startswith("1.2.3+dev.")


def test_package_rejects_output_inside_source_checkout(tmp_path: Path):
    source = make_distribution_tree(tmp_path / "source")
    initialize_release(source)

    with pytest.raises(ValueError, match="outside the source checkout"):
        distribution.package_distribution(
            source,
            source / "copilotautopilot.zip",
        )


def test_legacy_prompt_names_only_delegate_to_current_skills():
    aliases = {
        "kickstart-vision.prompt.md": "kickstart",
        "plan-product.prompt.md": "plan",
        "run-autopilot.prompt.md": "autopilot",
    }
    for filename, skill in aliases.items():
        prompt = (
            ROOT / ".github/prompts" / filename
        ).read_text(encoding="utf-8")
        assert f"Invoke the `{skill}` skill" in prompt
        assert "compatibility alias" in prompt


def test_gitflow_command_resolution_is_local_then_path_and_fails_closed():
    skill = (ROOT / ".github/skills/gitflow-operator/SKILL.md").read_text()

    assert "<repo>/bin/gitflow-operator" in skill
    assert "command -v" in skill
    assert "If neither exists, stop" in skill
    assert "do not silently substitute raw Git commands" in skill
    assert "bin/gitflow-operator" not in "\n".join(
        line for line in skill.splitlines() if line.startswith('"$GITFLOW_OPERATOR"')
    )
