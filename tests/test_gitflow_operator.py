import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GITFLOW = ROOT / "bin" / "gitflow-operator"


def run(cmd, cwd=None, check=True):
    return subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check)


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
