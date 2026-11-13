"""Risk-scaled execution, using real commands and disposable Git checkouts."""

import json
import subprocess
import sys
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from methodlib import cli, lanes


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def repo(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "src").mkdir()
    (tmp_path / "src/code.txt").write_text("before\n")
    (tmp_path / "README.md").write_text("existing intent\n")
    return tmp_path


def brief(**changes):
    return replace(lanes.Brief(
        task="routine-fix", owner="developer", outcome="Correct the bounded defect",
        scope=["src"], acceptance=["The defect is fixed"], checks=["unit"],
        kind="fix", design="existing", certainty="clear", risk="R1",
    ), **changes)


def perform(repo, action, previous, **kwargs):
    return lanes.execute(
        repo, action, task=previous["task"], expected=previous["revision"],
        owner="developer", **kwargs,
    )


def start(repo, selected=None, **kwargs):
    result, refused = lanes.execute(repo, "start", brief=selected or brief(), **kwargs)
    assert not refused, result
    return result


def check(repo, previous, name="unit", code="assert True", repair=False):
    return perform(
        repo, "check", previous, name=name,
        argv=[sys.executable, "-c", code], covered=["AC1"], repair=repair,
    )


def review(repo, previous, independent=False, verdict="approved"):
    report = f"{lanes.DIRECTORY}/review.md"
    (repo / report).write_text("Actual fixture review of the delivered implementation.\n")
    return perform(
        repo, "review", previous, report=report,
        reviewer="reviewer" if independent else "developer",
        independent=independent, verdict=verdict,
    )


def test_direct_real_cli_needs_no_synthetic_planning(repo):
    result = subprocess.run(
        [str(ROOT / "bin/method"), "lane", "start",
         "--task", "readme-fix", "--owner", "developer",
         "--outcome", "Correct the CLI spelling", "--scope", "README.md",
         "--acceptance", "Help uses the documented spelling", "--check", "help",
         "--kind", "docs", "--design", "existing", "--certainty", "clear", "--risk", "R0"],
        cwd=repo, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    selected = json.loads(result.stdout)
    assert selected["lane"] == "Direct"
    assert not (repo / "docs/vision_of_product").exists()
    assert not (repo / "docs/themes").exists()
    assert not (repo / "docs/plan/backlog.yaml").exists()
    (repo / "README.md").write_text("Corrected spelling.\n")
    verified, refused = check(repo, selected, name="help", code="from pathlib import Path; assert 'Corrected' in Path('README.md').read_text()")
    assert not refused
    reviewed, refused = review(repo, verified)
    assert not refused
    done, refused = perform(repo, "complete", reviewed, gitflow="not-applicable: local-only fixture")
    assert not refused
    assert done["implementation_complete"]
    assert done["release_readiness"] == "not-assessed"
    assert done["product_acceptance"] == "not-granted"
    assert done["production_activation"] == "not-authorized"


def test_managed_retains_scope_owner_and_checks_across_processes(repo):
    selected = brief(
        kind="feature", multi_session=True, risk="R2",
        non_goals=["No activation"], integration_checks=["integration"],
        design_evidence=["README.md"],
    )
    initial = start(repo, selected)
    assert initial["lane"] == "Managed"
    preflight = subprocess.run(
        [str(ROOT / "bin/method"), "lane", "--repo", str(repo), "preflight",
         "--task", selected.task, "--owner", selected.owner,
         "--expected-revision", initial["revision"]],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert preflight.returncode == 0, preflight.stderr
    resumed = json.loads(preflight.stdout)
    state = json.loads((repo / resumed["record"]).read_text())
    assert state["brief"]["non_goals"] == ["No activation"]
    assert state["brief"]["scope"] == ["src"]
    unit, _ = check(repo, resumed)
    with pytest.raises(lanes.LaneFailure):
        review(repo, unit)
    integrated, refused = check(repo, unit, name="integration")
    assert not refused
    with pytest.raises(lanes.LaneFailure, match="independent review"):
        review(repo, integrated)
    approved, _ = review(repo, integrated, independent=True)
    done, refused = perform(repo, "complete", approved, gitflow="not-applicable: no delivery authorized")
    assert not refused and done["implementation_complete"]


@pytest.mark.parametrize("trigger", lanes.contract()["governed-triggers"])
def test_governed_trigger_cannot_be_downgraded_or_executed_locally(repo, trigger):
    selected = brief(triggers=[trigger])
    assessment, refused = lanes.execute(repo, "assess", brief=selected, requested="Direct")
    assert refused and assessment["lane"] == "Governed"
    initial, refused = lanes.execute(repo, "start", brief=selected, requested="Direct")
    assert refused and initial["route"] == "packet"
    for action in ("preflight", "check", "complete"):
        with pytest.raises(lanes.LaneFailure, match="paused"):
            perform(repo, action, initial)
    resumed, refused = perform(repo, "resume", initial)
    assert refused and resumed["lane"] == "Governed"
    with pytest.raises(lanes.LaneFailure, match="triggers cannot be removed"):
        perform(repo, "amend", resumed, brief=brief())
    with pytest.raises(lanes.LaneFailure, match="Overlapping"):
        lanes.execute(repo, "start", brief=brief(task="other-name"))


@pytest.mark.parametrize("changes", [
    {"design": "new"}, {"risk": "R3"},
    {"scope": ["docs/ADRs/new.md"]}, {"admitted_item": "TH9.E1.US1"},
])
def test_consequential_decisions_and_admitted_work_keep_existing_route(repo, changes):
    result, refused = lanes.execute(repo, "assess", brief=brief(**changes))
    assert refused and result["route"] == "packet"
    assert not (repo / lanes.DIRECTORY).exists()


def test_scope_expansion_pauses_invalidates_and_escalates(repo):
    initial = start(repo)
    verified, _ = check(repo, initial)
    reviewed, _ = review(repo, verified)
    expanded = brief(
        scope=["src", "README.md"], substantial=True,
        non_goals=["No activation"], integration_checks=["integration"],
        design_evidence=["design.md"],
    )
    # Design evidence belongs in working evidence if added during the task.
    design_path = f"{lanes.DIRECTORY}/design.md"
    (repo / design_path).write_text("Existing accepted design.\n")
    expanded = replace(expanded, design_evidence=[design_path])
    changed, refused = perform(repo, "amend", reviewed, brief=expanded)
    assert refused and changed["status"] == "paused" and changed["lane"] == "Managed"
    state = json.loads((repo / changed["record"]).read_text())
    assert state["runs"] == {} and state["review"] is None
    assert any("prior_brief" in entry for entry in state["history"])
    with pytest.raises(lanes.LaneFailure, match="paused"):
        check(repo, changed)
    resumed, refused = perform(repo, "resume", changed)
    assert not refused
    governed, refused = perform(
        repo, "amend", resumed, brief=replace(expanded, triggers=["authorization"]),
    )
    assert refused and governed["lane"] == "Governed"
    with pytest.raises(lanes.LaneFailure, match="triggers cannot be removed"):
        perform(repo, "amend", governed, brief=expanded)


def test_unknown_scope_and_unapproved_decisions_refuse(repo):
    initial, refused = lanes.execute(repo, "start", brief=brief(certainty="unknown"))
    assert refused and initial["status"] == "paused"
    resumed, refused = perform(repo, "resume", initial)
    assert refused
    clarified, _ = perform(repo, "amend", resumed, brief=brief())
    resumed, refused = perform(repo, "resume", clarified)
    assert not refused


def test_authority_refusal_is_sticky_and_owner_cannot_be_replaced(repo):
    initial = start(repo)
    paused, _ = perform(repo, "pause", initial, reason="Human refused activation", authority_refused=True)
    revised, _ = perform(repo, "amend", paused, brief=brief(outcome="Local fix only"))
    resumed, refused = perform(repo, "resume", revised)
    assert refused and resumed["lane"] == "Governed"
    with pytest.raises(lanes.LaneFailure, match="owner mismatch"):
        lanes.execute(repo, "preflight", task=initial["task"], expected=resumed["revision"], owner="different")


def test_failures_and_repair_bound_are_real_not_success_shaped(repo):
    initial = start(repo)
    failed, refused = check(repo, initial, code="raise SystemExit(7)")
    assert refused
    state = json.loads((repo / failed["record"]).read_text())
    assert state["runs"]["unit"]["exit_code"] == 7
    assert state["runs"]["unit"]["output_hashes"]
    with pytest.raises(lanes.LaneFailure, match="failing"):
        perform(repo, "complete", failed, gitflow="not-applicable: fixture")
    once, refused = check(repo, failed, code="raise SystemExit(1)", repair=True)
    assert refused and once["status"] == "active"
    twice, refused = check(repo, once, code="raise SystemExit(1)", repair=True)
    assert refused and twice["status"] == "paused"


def test_stale_checks_review_and_missing_coverage_block_completion(repo):
    initial = start(repo)
    with pytest.raises(lanes.LaneFailure):
        perform(repo, "complete", initial, gitflow="not-applicable: fixture")
    verified, _ = check(repo, initial)
    reviewed, _ = review(repo, verified)
    (repo / "src/code.txt").write_text("changed after review\n")
    with pytest.raises(lanes.LaneFailure, match="stale verification"):
        perform(repo, "complete", reviewed, gitflow="not-applicable: fixture")
    with pytest.raises(lanes.LaneFailure, match="stale or modified"):
        perform(repo, "preflight", initial)


def test_scope_guard_does_not_silently_accept_unrelated_changes(repo):
    initial = start(repo)
    (repo / "README.md").write_text("unrelated mutation\n")
    stopped, refused = perform(repo, "preflight", initial)
    assert refused and stopped["status"] == "paused"
    assert "Out-of-scope" in stopped["next_action"]


def test_review_refusal_and_changed_reports_cannot_complete(repo):
    initial = start(repo)
    verified, _ = check(repo, initial)
    rejected, refused = review(repo, verified, verdict="request-changes")
    assert refused
    with pytest.raises(lanes.LaneFailure, match="paused"):
        perform(repo, "complete", rejected, gitflow="not-applicable: fixture")
    resumed, _ = perform(repo, "resume", rejected)
    approved, _ = review(repo, resumed)
    (repo / lanes.DIRECTORY / "review.md").write_text("different review\n")
    with pytest.raises(lanes.LaneFailure, match="review evidence"):
        perform(repo, "complete", approved, gitflow="not-applicable: fixture")


def test_invalid_inputs_symlinks_and_missing_commands_fail_explicitly(repo):
    (repo / "link").symlink_to(repo / "src", target_is_directory=True)
    with pytest.raises(lanes.LaneFailure, match="Symlinks"):
        start(repo, brief(scope=["link"]))
    (repo / "link").unlink()
    result = cli.dispatch(["lane", "start", "--task", "missing"], probe_directory=repo)
    assert result.exit_code == 2 and result.payload["status"] == "refused"
    initial = start(repo)
    result = cli.dispatch([
        "lane", "check", "--task", initial["task"], "--owner", "developer",
        "--expected-revision", initial["revision"], "--name", "unit",
        "--covered", "AC1", "--", "/nonexistent/verification-command",
    ], probe_directory=repo)
    assert result.exit_code == 2 and result.diagnostics


def test_inline_and_optional_brief_cannot_conflict(repo):
    path = repo / "brief.json"
    path.write_text(json.dumps(asdict(brief())))
    result = cli.dispatch(["lane", "assess", "--brief", str(path), "--task", "override"], probe_directory=repo)
    assert result.exit_code == 2 and "not both" in result.payload["findings"][0]


def test_active_entry_surfaces_route_lighter_work_without_forcing_packets():
    for relative in (
        ".github/copilot-instructions.md", ".github/skills/autopilot/SKILL.md",
        ".github/skills/plan/SKILL.md", ".github/agents/developer.agent.md",
        ".github/agents/orchestrator.agent.md", ".github/prompts/run-autopilot.prompt.md",
    ):
        text = (ROOT / relative).read_text()
        assert "Direct/Managed" in text or ("Direct" in text and "Managed" in text)
    assert "delivery-lanes-contract:start" in lanes.CONTRACT.read_text()


def test_ignored_implementation_files_are_included_in_verification_revision(repo):
    (repo / ".gitignore").write_text("src/ignored.txt\n")
    (repo / "src/ignored.txt").write_text("first\n")
    initial = start(repo)
    verified, _ = check(repo, initial)
    approved, _ = review(repo, verified)
    (repo / "src/ignored.txt").write_text("second\n")
    with pytest.raises(lanes.LaneFailure, match="stale verification"):
        perform(repo, "complete", approved, gitflow="not-applicable: fixture")


def test_amend_cannot_remove_or_rewrite_existing_design_evidence(repo):
    selected = brief(
        substantial=True, non_goals=["No product changes"],
        design_evidence=["README.md"], integration_checks=["integration"],
    )
    initial = start(repo, selected)
    with pytest.raises(lanes.LaneFailure, match="cannot be removed"):
        perform(repo, "amend", initial, brief=replace(selected, design_evidence=[]))
    (repo / "README.md").write_text("Unaccepted changed design\n")
    with pytest.raises(lanes.LaneFailure, match="design evidence changed"):
        perform(repo, "amend", initial, brief=selected)


def test_completion_requires_actual_delivery_evidence_or_reason(repo):
    initial = start(repo)
    verified, _ = check(repo, initial)
    approved, _ = review(repo, verified)
    for claim in ("not-applicable:", "pushed successfully", "nonexistent-report.json"):
        with pytest.raises(lanes.LaneFailure):
            perform(repo, "complete", approved, gitflow=claim)


def test_complete_evidence_remains_immutable_and_cannot_describe_a_later_revision(repo):
    initial = start(repo)
    verified, _ = check(repo, initial)
    approved, _ = review(repo, verified)
    done, _ = perform(repo, "complete", approved, gitflow="not-applicable: fixture")
    path = repo / done["record"]
    original = path.read_bytes()
    result, refused = perform(repo, "preflight", done)
    assert not refused and result["revision"] == done["revision"]
    assert path.read_bytes() == original
    (repo / "src/code.txt").write_text("New implementation\n")
    with pytest.raises(lanes.LaneFailure, match="stale verification"):
        perform(repo, "preflight", done)
    assert path.read_bytes() == original


def test_admitted_work_is_detected_even_when_the_caller_omits_identity(repo):
    path = repo / "docs/plan/backlog.yaml"
    path.parent.mkdir(parents=True)
    path.write_text("backlog:\n  active-themes:\n    - id: TH9\n      status: in-progress\n")
    for action in ("assess", "start"):
        with pytest.raises(lanes.LaneFailure, match="Unfinished product backlog"):
            lanes.execute(repo, action, brief=brief())
    assert not list((repo / lanes.DIRECTORY).glob("*.json"))


@pytest.mark.parametrize("path", [
    "methodlib/lanes.py", "bin/method", ".github/copilot-instructions.md",
    ".github/skills/the-copilot-build-method/SKILL.md",
    ".github/prompts/review.prompt.md",
])
def test_enforcement_paths_are_governed_without_caller_trigger(repo, path):
    result, refused = lanes.execute(repo, "assess", brief=brief(scope=[path], risk="R0"))
    assert refused and result["lane"] == "Governed"


def test_ignored_out_of_scope_changes_are_not_invisible(repo):
    (repo / ".gitignore").write_text("cache.out\n")
    initial = start(repo)
    result, refused = check(
        repo, initial, code="from pathlib import Path; Path('cache.out').write_text('unexpected')",
    )
    assert refused and result["status"] == "paused"
    assert "cache.out" in result["next_action"]


def test_generated_output_grants_are_explicit_not_a_scope_bypass(repo):
    selected = brief(verification_outputs=["test-output"])
    initial = start(repo, selected)
    result, refused = check(
        repo, initial, code="from pathlib import Path; Path('test-output').mkdir(); Path('test-output/result').write_text('generated')",
    )
    assert not refused
    with pytest.raises(lanes.LaneFailure, match="Output grants"):
        perform(repo, "amend", result, brief=replace(selected, verification_outputs=["test-output", "other"]))
    with pytest.raises(lanes.LaneFailure, match="cannot overlap"):
        lanes.execute(repo, "assess", brief=brief(verification_outputs=["src"]))


def test_subtree_invocation_cannot_hide_the_product_backlog(repo):
    with pytest.raises(lanes.LaneFailure, match="checkout root"):
        lanes.execute(repo / "src", "start", brief=brief())


def test_existing_cli_commands_do_not_need_the_new_lane_contract(monkeypatch, tmp_path):
    monkeypatch.setattr(lanes, "CONTRACT", tmp_path / "missing-canonical-skill.md")
    result = cli.dispatch(["doctor"], probe_directory=tmp_path)
    assert result.exit_code == 0
    assert result.payload["command"] == "doctor"
