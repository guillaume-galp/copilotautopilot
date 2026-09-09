"""Session summaries count epic jobs, not optional acceptance children."""

import subprocess
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".github/hooks/scripts/save-session-state.sh"


def run_hook(tmp_path: Path, themes: list[dict] | None = None):
    if themes is not None:
        backlog = tmp_path / "docs/plan/backlog.yaml"
        backlog.parent.mkdir(parents=True)
        backlog.write_text(
            yaml.safe_dump({"backlog": {"active-themes": themes}}),
            encoding="utf-8",
        )
    return subprocess.run(
        ["bash", str(HOOK)], cwd=tmp_path, text=True, capture_output=True
    )


def test_hook_counts_v3_epics_and_legacy_stories_separately(tmp_path: Path):
    result = run_hook(
        tmp_path,
        [
            {
                "schema-version": 3,
                "epics": [
                    {
                        "status": "in-progress",
                        "stories": [{"status": "todo"}, {"status": "done"}],
                    },
                    {"status": "blocked"},
                ],
            },
            {
                "schema-version": 2,
                "epics": [
                    {"status": "in-progress", "stories": [{"status": "failed"}]}
                ],
            },
        ],
    )
    assert result.returncode == 0, result.stderr
    log = (tmp_path / "docs/plan/session-log.md").read_text()
    assert "- Epics: todo: 0 | in-progress: 1 | blocked: 1 | failed: 0 | done: 0" in log
    assert "- Legacy stories: todo: 0 | in-progress: 0 | blocked: 0 | failed: 1 | done: 0" in log


def test_hook_records_empty_active_backlog_without_grep_failure(tmp_path: Path):
    result = run_hook(tmp_path, [])
    assert result.returncode == 0, result.stderr
    assert "Epics: todo: 0" in (tmp_path / "docs/plan/session-log.md").read_text()


def test_hook_records_absent_backlog(tmp_path: Path):
    result = run_hook(tmp_path)
    assert result.returncode == 0, result.stderr
    assert "No backlog file found" in (tmp_path / "docs/plan/session-log.md").read_text()


def test_hook_does_not_append_success_summary_for_invalid_state(tmp_path: Path):
    result = run_hook(
        tmp_path, [{"schema-version": 3, "epics": [{"status": "invented"}]}]
    )
    assert result.returncode != 0
    assert "unknown delivery status" in result.stderr
    assert not (tmp_path / "docs/plan/session-log.md").exists()
