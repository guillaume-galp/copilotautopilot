import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GITFLOW = ROOT / "bin" / "gitflow-operator"


def run(cmd, env):
    return subprocess.run(
        cmd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env=env,
    )


def test_repository_launcher_delegates_to_standalone_command(tmp_path):
    provider_bin = tmp_path / "provider"
    provider_bin.mkdir()
    args_file = tmp_path / "args.json"
    provider = provider_bin / "gitflow-operator"
    provider.write_text(
        '#!/bin/sh\nprintf \'%s\\n\' "$@" > "$GITFLOW_TEST_ARGS"\nprintf \'{"status":"delegated"}\\n\'\n',
        encoding="utf-8",
    )
    provider.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = f"{provider_bin}:/usr/bin:/bin"
    env["GITFLOW_TEST_ARGS"] = str(args_file)

    result = run(
        [str(GITFLOW), "--repo", "/tmp/repo", "status"],
        env,
    )

    assert result.returncode == 0
    assert json.loads(result.stdout) == {"status": "delegated"}
    assert args_file.read_text().splitlines() == ["--repo", "/tmp/repo", "status"]


def test_repository_launcher_fails_explicitly_without_standalone_command(tmp_path):
    env = os.environ.copy()
    env["PATH"] = f"{tmp_path}:/usr/bin:/bin"
    env.pop("GITFLOW_OPERATOR_EXECUTABLE", None)

    result = run([str(GITFLOW), "status"], env)

    assert result.returncode == 127
    evidence = json.loads(result.stdout)
    assert evidence["operation"] == "dispatch"
    assert evidence["status"] == "blocked"
    assert "not found" in evidence["reason"]
