import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GITFLOW = ROOT / "bin" / "gitflow-operator"


def run(cmd, cwd=None, check=True, env=None):
    return subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
        env=env,
    )


def init_repo(path: Path) -> None:
    path.mkdir()
    run(["git", "init"], cwd=path)
    run(["git", "config", "user.email", "test@example.com"], cwd=path)
    run(["git", "config", "user.name", "Test User"], cwd=path)
    (path / "README.md").write_text("hello\n")
    run(["git", "add", "README.md"], cwd=path)
    run(["git", "commit", "-m", "initial"], cwd=path)


def test_branch_from_develop_blocks_when_develop_missing(tmp_path):
    repo = tmp_path / "repo"
    init_repo(repo)
    result = run([str(GITFLOW), "--repo", str(repo), "--item-id", "TH2.E1.US1", "branch-from-develop", "--branch", "feature/x"])
    data = json.loads(result.stdout)
    assert data["operation"] == "branch-from-develop"
    assert data["status"] == "blocked"
    assert "develop branch missing" in data["reason"]


def test_branch_from_develop_creates_branch(tmp_path):
    repo = tmp_path / "repo"
    init_repo(repo)
    run(["git", "checkout", "-b", "develop"], cwd=repo)
    result = run([str(GITFLOW), "--repo", str(repo), "--item-id", "TH2.E1.US1", "branch-from-develop", "--branch", "feature/x"])
    data = json.loads(result.stdout)
    assert data["status"] == "created"
    assert data["branch"] == "feature/x"
    assert data["target_branch"] == "feature/x"


def test_prepare_release_notes_outputs_evidence(tmp_path):
    repo = tmp_path / "repo"
    init_repo(repo)
    result = run([str(GITFLOW), "--repo", str(repo), "--item-id", "TH2.E1.US2", "prepare-release-notes", "--summary", "Ship gitflow", "--tests", "pytest"])
    data = json.loads(result.stdout)
    assert data["operation"] == "prepare-release-notes"
    assert data["status"] == "prepared"
    assert "Ship gitflow" in data["release_notes"]
    assert "pytest" in data["release_notes"]


def test_squash_merge_uses_current_pull_request_without_unsupported_base(tmp_path):
    repo = tmp_path / "repo"
    init_repo(repo)
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    args_file = tmp_path / "gh-args"
    gh = fake_bin / "gh"
    gh.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$GH_ARGS_FILE"\necho merged\n')
    gh.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["GH_ARGS_FILE"] = str(args_file)

    result = run(
        [
            str(GITFLOW),
            "--repo",
            str(repo),
            "--item-id",
            "TH3",
            "squash-merge-to-develop",
        ],
        env=env,
    )

    data = json.loads(result.stdout)
    assert data["status"] == "merged"
    assert args_file.read_text().splitlines() == ["pr", "merge", "--squash"]
