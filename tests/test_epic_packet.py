"""Epic packet contracts exercise the shared legacy-safe runtime end to end."""

from copy import deepcopy
from pathlib import Path
import shutil

import pytest
import yaml

from methodlib import backlog, exits, lock, migrate, packet, trace
from test_epic_backlog import v3_backlog
from test_epic_trace import EPIC_PATH, make_epic_repository
from test_method_backlog import ROOT
from test_method_trace import write


def repository(base: Path, children: int = 0):
    root = make_epic_repository(base, status="todo")
    traced = yaml.safe_load((root / backlog.BACKLOG_PATH).read_text())["backlog"]["active-themes"][0]
    document = v3_backlog()
    state = document["backlog"]
    state["archived-themes"] = []
    theme = state["active-themes"][0]
    theme.update({key: traced[key] for key in ("id", "vision-ref", "discovery-ref", "requirements-ref")})
    theme.update({"status": "todo", "depends-on": []})
    epic = theme["epics"][0]
    epic.update({"id": "TH9.E1", "name": "Epic outcome", "file": EPIC_PATH,
                 "status": "todo", "depends-on": [], "review-profile": "standard"})
    epic["risk"]["tier"] = "R1"
    epic["evidence"] = {key: [] for key in packet.EVIDENCE_KEYS}
    spec = {
        "id": epic["id"], "title": epic["name"], "type": "standard",
        "traceability": {"vision": [], "requirements": ["PR-001"], "adrs": [], "invariants": []},
        "acceptance-criteria": [{"AC1": "Deliver the complete epic"}],
    }
    write(root, EPIC_PATH, "---\n" + yaml.safe_dump(spec) + "---\n")
    if children:
        epic["stories"] = []
    for number in range(1, children + 1):
        child = {
            "id": f"TH9.E1.US{number}", "title": f"Slice {number}", "status": "todo",
            "file": f"docs/themes/TH9-trace/epics/E1-trace/stories/US{number}-slice.md",
            "depends-on": [] if number == 1 else [f"TH9.E1.US{number - 1}"],
        }
        epic["stories"].append(child)
        write(root, child["file"], "---\n" + yaml.safe_dump({
            "id": child["id"], "title": child["title"],
            "acceptance-criteria": [{"AC1": f"Accept slice {number}"}],
        }) + "---\n")
    for name in ("backlog-management", "the-copilot-build-method", "code-quality"):
        path = root / f".github/skills/{name}/SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path.relative_to(root), path)
    write(root, "docs/architecture/README.md", "# Architecture\n")
    write(root, backlog.BACKLOG_PATH.as_posix(), yaml.safe_dump(document))
    assert backlog.validate_repository(root).valid
    allowed = base / "implementation"
    (allowed / "checkout").mkdir(parents=True)
    return root, allowed


def build(root, allowed, **kwargs):
    return packet.build_packet(
        root, task="epic-delivery", mode="developer",
        implementation_root=str(allowed / "checkout"),
        allowed_implementation_root=str(allowed), planning_roots=[str(root)],
        **kwargs,
    )


def call(action, root, allowed, previous):
    return action(
        root, packet_path=previous.payload["packet"],
        allowed_implementation_root=str(allowed),
        expected_authorization_hash=previous.payload["authorization_hash"],
    )


def change(root, mutate):
    path = root / backlog.BACKLOG_PATH
    document = yaml.safe_load(path.read_text())
    state = document["backlog"]
    state["revision"] += 1
    mutate(state, state["active-themes"][0], state["active-themes"][0]["epics"][0])
    path.write_text(yaml.safe_dump(document))


def start(state, theme, epic):
    theme["status"] = epic["status"] = "in-progress"


def finish(state, theme, epic):
    epic["status"] = "done"
    for child in epic.get("stories", []):
        child["status"] = "done"
    epic["evidence"]["verification"] = ["lint passed", "unit passed", "integration passed"]
    epic["evidence"]["review"] = ["self-review approved"]
    epic["evidence"]["gitflow"] = ["not-applicable: isolated fixture"]


@pytest.mark.parametrize("children", [0, 2])
def test_epic_atomic_lifecycle_and_separate_theme_acceptance(tmp_path, children):
    root, allowed = repository(tmp_path, children)
    projection = packet.project_next(root)
    assert projection.exit_code == exits.SUCCESS, projection.payload
    assert projection.payload["projection"]["work-item"]["id"] == "TH9.E1"
    built = build(root, allowed, epic_id="TH9.E1")
    assert built.exit_code == exits.SUCCESS, built.payload
    payload = yaml.safe_load((root / built.payload["packet"]).read_text())
    assert "story" not in payload
    assert payload["scope"]["maximum-epics"] == 1
    assert len(payload["acceptance-children"]) == children
    assert len(payload["scope"]["optional-children"]) == children
    assert call(packet.preflight_packet, root, allowed, built).exit_code == exits.SUCCESS
    change(root, start)
    assert call(packet.verify_packet, root, allowed, built).exit_code != exits.SUCCESS
    running = call(packet.reconcile_packet, root, allowed, built)
    assert running.exit_code == exits.SUCCESS, running.payload
    assert call(packet.verify_packet, root, allowed, built).exit_code != exits.SUCCESS
    assert call(packet.verify_packet, root, allowed, running).exit_code == exits.SUCCESS
    change(root, finish)
    done = call(packet.reconcile_packet, root, allowed, running)
    assert done.exit_code == exits.SUCCESS, done.payload
    verified = call(packet.verify_packet, root, allowed, done)
    assert verified.exit_code == exits.SUCCESS, verified.payload
    change(root, lambda state, theme, epic: theme.update(status="done"))
    accepted = call(packet.reconcile_packet, root, allowed, done)
    assert accepted.exit_code == exits.SUCCESS, accepted.payload


@pytest.mark.parametrize("status", ["failed", "blocked"])
def test_failed_epic_requires_explicit_recovery_and_resumes(tmp_path, status):
    root, allowed = repository(tmp_path)
    built = build(root, allowed)
    assert built.exit_code == exits.SUCCESS, built.payload
    change(root, start)
    running = call(packet.reconcile_packet, root, allowed, built)
    assert running.exit_code == exits.SUCCESS, running.payload
    change(root, lambda state, theme, epic: epic.update(status=status))
    paused = call(packet.reconcile_packet, root, allowed, running)
    assert paused.exit_code == exits.SUCCESS, paused.payload
    assert call(packet.preflight_packet, root, allowed, paused).exit_code != exits.SUCCESS
    assert packet.project_next(root).exit_code != exits.SUCCESS
    assert build(root, allowed).exit_code != exits.SUCCESS
    change(root, lambda state, theme, epic: epic.update(status="in-progress"))
    resumed = call(packet.reconcile_packet, root, allowed, paused)
    assert resumed.exit_code == exits.SUCCESS, resumed.payload
    assert packet.project_next(root).payload["projection"]["work-item"]["status"] == "in-progress"


@pytest.mark.parametrize("field", ["scope", "acceptance-children", "backlog-snapshot", "work-item"])
def test_epic_scope_tampering_is_bound_to_caller_anchor(tmp_path, field):
    root, allowed = repository(tmp_path, 2)
    built = build(root, allowed)
    assert built.exit_code == exits.SUCCESS, built.payload
    path = root / built.payload["packet"]
    document = yaml.safe_load(path.read_text())
    document[field] = {}
    document["authorization-hash"] = packet._authorization_hash(document)
    path.write_text(yaml.safe_dump(document))
    assert call(packet.verify_packet, root, allowed, built).exit_code != exits.SUCCESS


@pytest.mark.parametrize("mutation", ["unrelated", "unfinished", "evidence", "combined"])
def test_epic_completion_and_reconciliation_fail_closed(tmp_path, mutation):
    root, allowed = repository(tmp_path, 2)
    built = build(root, allowed)
    assert built.exit_code == exits.SUCCESS, built.payload
    change(root, start)
    running = call(packet.reconcile_packet, root, allowed, built)
    assert running.exit_code == exits.SUCCESS, running.payload

    def mutate(state, theme, epic):
        finish(state, theme, epic)
        if mutation == "unrelated":
            state["project"] = "Unauthorized change"
        elif mutation == "unfinished":
            epic["stories"][0]["status"] = "todo"
        elif mutation == "evidence":
            epic["evidence"]["review"] = []
        else:
            theme["status"] = "done"

    change(root, mutate)
    assert call(packet.reconcile_packet, root, allowed, running).exit_code != exits.SUCCESS


def test_epic_child_source_and_accepted_reference_freshness(tmp_path):
    root, allowed = repository(tmp_path, 2)
    built = build(root, allowed)
    assert built.exit_code == exits.SUCCESS, built.payload
    path = root / "docs/themes/TH9-trace/epics/E1-trace/stories/US1-slice.md"
    path.write_text(path.read_text() + "\nChanged acceptance scope\n")
    change(root, start)
    assert call(packet.reconcile_packet, root, allowed, built).exit_code != exits.SUCCESS
    assert call(packet.verify_packet, root, allowed, built).exit_code != exits.SUCCESS


@pytest.mark.parametrize("profile", ["standard", "adversarial", "critical"])
@pytest.mark.parametrize("tier", ["R0", "R1", "R2", "R3"])
@pytest.mark.parametrize("approval", [
    "self-review approved", "native review approved", "independent approved",
])
def test_epic_review_evidence_policy(tmp_path, profile, tier, approval):
    routine = profile == "standard" and tier in {"R0", "R1"}
    valid = routine or approval == "independent approved"
    root, allowed = repository(tmp_path)
    change(root, lambda state, theme, epic: (
        epic.update({"review-profile": profile}), epic["risk"].update(tier=tier)
    ))
    built = build(root, allowed)
    assert built.exit_code == exits.SUCCESS, built.payload
    mission = yaml.safe_load((root / built.payload["packet"]).read_text())
    expected_tokens = (
        ["independent approved", "native review approved", "self-review approved"]
        if routine else ["independent approved"]
    )
    assert mission["evidence-requirements"]["review"]["required"] is True
    assert mission["evidence-requirements"]["review"]["accepted-approval-tokens"] == expected_tokens
    change(root, start)
    running = call(packet.reconcile_packet, root, allowed, built)
    assert running.exit_code == exits.SUCCESS, running.payload
    change(root, lambda state, theme, epic: (
        finish(state, theme, epic), epic["evidence"].update(review=[approval])
    ))
    result = call(packet.reconcile_packet, root, allowed, running)
    assert (result.exit_code == exits.SUCCESS) is valid, result.payload


def add_external_epic(root):
    def mutate(state, theme, epic):
        external = deepcopy(epic)
        external.update({
            "id": "TH9.E2", "name": "Dependency", "priority": "low",
            "file": "docs/themes/TH9-trace/epics/E2-dependency/README.md",
            "stories": [{
                "id": "TH9.E2.US1", "title": "External slice", "status": "todo",
                "file": "docs/themes/TH9-trace/epics/E2-dependency/stories/US1-slice.md",
                "depends-on": [],
            }],
        })
        theme["epics"].append(external)
        spec = yaml.safe_load((root / EPIC_PATH).read_text().split("---")[1])
        spec.update(id="TH9.E2", title="Dependency")
        write(root, external["file"], "---\n" + yaml.safe_dump(spec) + "---\n")
        spec.update(id="TH9.E2.US1", title="External slice")
        write(root, external["stories"][0]["file"], "---\n" + yaml.safe_dump(spec) + "---\n")
    change(root, mutate)


@pytest.mark.parametrize("kind", ["epic", "child"])
def test_external_dependencies_gate_entire_epic(tmp_path, kind):
    root, allowed = repository(tmp_path, 2)
    add_external_epic(root)
    def require(state, theme, epic):
        if kind == "epic":
            epic["depends-on"] = ["TH9.E2"]
        else:
            epic["stories"][0]["depends-on"] = ["TH9.E2.US1"]
    change(root, require)
    assert build(root, allowed, epic_id="TH9.E1").exit_code != exits.SUCCESS
    assert packet.project_next(root).payload["projection"]["work-item"]["id"] == "TH9.E2"
    def complete_dependency(state, theme, epic):
        dependency = theme["epics"][1]
        dependency["status"] = "done"
        dependency["stories"][0]["status"] = "done"
    change(root, complete_dependency)
    built = build(root, allowed, epic_id="TH9.E1")
    assert built.exit_code == exits.SUCCESS, built.payload
    # An external dependency cannot be reopened underneath a retained grant.
    change(root, lambda state, theme, epic: theme["epics"][1].update(status="in-progress"))
    assert call(packet.reconcile_packet, root, allowed, built).exit_code != exits.SUCCESS


def test_theme_dependencies_and_mixed_legacy_archives(tmp_path):
    from test_method_backlog import v1_theme, v2_archive_theme

    root, allowed = repository(tmp_path, 2)
    archives = {"TH1": v1_theme("TH1"), "TH2": v2_archive_theme("TH2")}
    def mutate(state, theme, epic):
        for identifier, archived in archives.items():
            if identifier == "TH2":
                archived.update({key: theme[key] for key in (
                    "vision-ref", "discovery-ref", "requirements-ref",
                )})
                historical = archived["epics"][0]["stories"][0]
                historical["file"] = "docs/themes/TH2-history/epics/E1-history/stories/US1-history.md"
                historical["evidence"] = {key: [] for key in packet.EVIDENCE_KEYS}
            path = f"docs/plan/backlog-archive/{identifier}.yaml"
            write(root, path, yaml.safe_dump({"theme": archived}))
            for historical_epic in archived["epics"]:
                for story in historical_epic["stories"]:
                    spec = {
                        "id": story["id"], "title": story["title"], "type": "trivial",
                        "agents": ["developer"], "skills": ["bdd-stories"], "depends-on": [],
                        "traceability": {key: [] for key in ("vision", "requirements", "adrs", "invariants")},
                        "acceptance-criteria": [{"AC1": "Historical acceptance"}],
                    }
                    write(root, story["file"], "---\n" + yaml.safe_dump(spec) + "---\n")
            state["archived-themes"].append({
                "id": identifier, "name": archived["name"], "schema-version": 1 if identifier == "TH1" else 2,
                "status": "done", "locked": True, "completed-at": "2026-09-01T00:00:00+00:00",
                "archive-ref": path, "stats": {"epics": 1, "stories": 1},
            })
        theme["depends-on"] = ["TH1", "TH2"]
        epic["depends-on"] = ["TH1.E1", "TH2.E1"]
        epic["stories"][0]["depends-on"] = ["TH1.E1.US1", "TH2.E1.US1"]
    change(root, mutate)
    before = {p: p.read_bytes() for p in (root / "docs/plan/backlog-archive").glob("*.yaml")}
    built = build(root, allowed)
    assert built.exit_code == exits.SUCCESS, built.payload
    assert before == {p: p.read_bytes() for p in before}
    # A valid but unfinished external theme is a blocker, not an archive shortcut.
    def unfinished(state, theme, epic):
        dependency = deepcopy(archives["TH2"])
        dependency.update({"locked": False, "status": "in-progress"})
        state["active-themes"].append(dependency)
        state["archived-themes"] = [
            item for item in state["archived-themes"] if item["id"] != "TH2"
        ]
    change(root, unfinished)
    assert build(root, allowed, epic_id="TH9.E1").exit_code != exits.SUCCESS


def test_epic_resume_precedes_later_priority_and_legacy_child_selector(tmp_path):
    root, allowed = repository(tmp_path, 2)
    add_external_epic(root)
    change(root, lambda state, theme, epic: (
        start(state, theme, epic), epic.update(priority="low"),
        theme["epics"][1].update(priority="high"),
    ))
    assert packet.project_next(root).payload["projection"]["work-item"]["id"] == "TH9.E1"
    assert build(root, allowed, story_id="TH9.E1.US1").exit_code != exits.SUCCESS
    assert build(root, allowed, story_id="TH9.E1.US1", epic_id="TH9.E1").exit_code != exits.SUCCESS


def add_active_legacy_theme(root, priority="medium"):
    from test_method_backlog import v2_theme

    def mutate(state, theme, epic):
        legacy = v2_theme()
        legacy.update({
            key: theme[key]
            for key in ("vision-ref", "discovery-ref", "requirements-ref")
        })
        legacy["depends-on"] = []
        story = legacy["epics"][0]["stories"][0]
        story.update({
            "priority": priority,
            "file": "docs/themes/TH3-legacy/epics/E1-legacy/stories/US1-legacy.md",
            "evidence": {key: [] for key in packet.EVIDENCE_KEYS},
        })
        write(root, story["file"], "---\n" + yaml.safe_dump({
            "id": story["id"], "title": story["title"], "type": "trivial",
            "agents": ["developer"], "skills": ["bdd-stories"], "depends-on": [],
            "traceability": {
                key: [] for key in ("vision", "requirements", "adrs", "invariants")
            },
            "acceptance-criteria": [{"AC1": "Retain legacy delivery"}],
        }) + "---\n")
        epic["priority"] = "medium"
        state["active-themes"].append(legacy)

    change(root, mutate)


@pytest.mark.parametrize("legacy_first", [False, True])
@pytest.mark.parametrize("legacy_priority", ["medium", "high"])
def test_active_legacy_and_epic_sequence_numbers_do_not_collide(
    tmp_path, legacy_first, legacy_priority
):
    root, allowed = repository(tmp_path)
    add_active_legacy_theme(root, priority=legacy_priority)
    if legacy_first:
        change(root, lambda state, theme, epic: state["active-themes"].reverse())
    assert backlog.validate_repository(root).valid
    assert trace.validate_repository(root).valid
    projected = packet.project_next(root)
    assert projected.exit_code == exits.SUCCESS, projected.payload
    key, identifier = (
        ("story", "TH3.E1.US1")
        if legacy_priority == "high" else ("work-item", "TH9.E1")
    )
    assert projected.payload["projection"][key]["id"] == identifier
    built = build(root, allowed, **{
        "story_id" if key == "story" else "epic_id": identifier,
    })
    assert built.exit_code == exits.SUCCESS, built.payload
    assert call(packet.verify_packet, root, allowed, built).exit_code == exits.SUCCESS


@pytest.mark.parametrize("status", ["failed", "blocked"])
def test_explicit_recovery_barrier_includes_independent_legacy_work(tmp_path, status):
    root, allowed = repository(tmp_path)
    add_active_legacy_theme(root, priority="high")
    change(root, lambda state, theme, epic: epic.update(status=status))
    projected = packet.project_next(root)
    assert projected.exit_code != exits.SUCCESS
    assert any(
        finding["record"] == "epic-recovery-required"
        for finding in projected.payload["findings"]
    )


@pytest.mark.parametrize("target", ["epic", "child"])
@pytest.mark.parametrize("criteria", [
    None, "not a list", [], ["not a mapping"],
    [{"AC1": ""}], [{"AC0": "Invalid identifier"}],
    [{"AC1": "First"}, {"AC1": "Duplicate"}],
])
def test_acceptance_contract_is_consistent_at_trace_and_packet_build(
    tmp_path, target, criteria
):
    root, allowed = repository(tmp_path, 2)
    path = root / (
        EPIC_PATH if target == "epic"
        else "docs/themes/TH9-trace/epics/E1-trace/stories/US1-slice.md"
    )
    spec = yaml.safe_load(path.read_text().split("---")[1])
    if criteria is None:
        del spec["acceptance-criteria"]
    else:
        spec["acceptance-criteria"] = criteria
    path.write_text("---\n" + yaml.safe_dump(spec) + "---\n")
    assert backlog.validate_repository(root).valid
    traced = trace.validate_repository(root)
    assert not traced.valid
    assert any("acceptance" in finding["message"] for finding in traced.findings)
    assert build(root, allowed).exit_code != exits.SUCCESS


def test_epic_sources_participate_in_lock_and_migration_indexes(tmp_path):
    root, allowed = repository(tmp_path)
    state = yaml.safe_load((root / backlog.BACKLOG_PATH).read_text())["backlog"]
    theme = state["active-themes"][0]
    assert lock._story_paths(theme) == (EPIC_PATH,)
    theme["epics"][0]["status"] = "in-progress"
    # Migration's executable index must not call an epic-only theme unstarted.
    scope = migrate.Scope("VP9", "TH9", theme, False, False, None)
    assert migrate._execution_present(scope)


@pytest.mark.parametrize("explicit_epic_edge", [False, True])
def test_effective_epic_dependency_cycles_fail_schema(tmp_path, explicit_epic_edge):
    root, allowed = repository(tmp_path, 2)
    add_external_epic(root)
    def mutate(state, theme, epic):
        external = theme["epics"][1]
        epic["stories"][0]["depends-on"] = ["TH9.E2.US1"]
        epic["stories"][1]["depends-on"] = []
        if explicit_epic_edge:
            external["depends-on"] = ["TH9.E1"]
        else:
            external["stories"][0]["depends-on"] = ["TH9.E1.US2"]
    change(root, mutate)
    result = backlog.validate_repository(root)
    assert not result.valid
    assert any("dependency cycle" in finding["message"] for finding in result.findings)
    assert packet.project_next(root).exit_code != exits.SUCCESS


def test_oversized_packet_build_refuses_before_persisting(tmp_path, monkeypatch):
    root, allowed = repository(tmp_path)
    monkeypatch.setattr(packet, "MAX_PACKET_BYTES", 512)
    result = build(root, allowed)
    assert result.exit_code != exits.SUCCESS
    assert "safety limit" in result.payload["message"]
    assert not (root / packet.DEFAULT_RUNTIME_DIRECTORY / "TH9.E1/epic-delivery.yaml").exists()


def test_oversized_reconciliation_preserves_previous_packet(tmp_path, monkeypatch):
    root, allowed = repository(tmp_path)
    built = build(root, allowed)
    assert built.exit_code == exits.SUCCESS, built.payload
    path = root / built.payload["packet"]
    before = path.read_bytes()
    monkeypatch.setattr(packet, "MAX_PACKET_BYTES", len(before) + 100)
    change(root, start)
    result = call(packet.reconcile_packet, root, allowed, built)
    assert result.exit_code != exits.SUCCESS
    assert "safety limit" in result.payload["message"]
    assert path.read_bytes() == before


@pytest.mark.parametrize("kind,value", [
    ("verification", []),
    ("verification", ["lint passed", "unit failed", "integration passed"]),
    ("gitflow", []),
    ("gitflow", ["not-applicable"]),
    ("review", ["approved"]),
])
def test_epic_completion_requires_positive_aggregate_evidence(tmp_path, kind, value):
    root, allowed = repository(tmp_path)
    built = build(root, allowed)
    assert built.exit_code == exits.SUCCESS, built.payload
    change(root, start)
    running = call(packet.reconcile_packet, root, allowed, built)
    assert running.exit_code == exits.SUCCESS, running.payload
    change(root, lambda state, theme, epic: (
        finish(state, theme, epic), epic["evidence"].update({kind: value})
    ))
    assert call(packet.reconcile_packet, root, allowed, running).exit_code != exits.SUCCESS


def test_epic_packet_destination_rejects_symlinked_runtime_directory(tmp_path):
    root, allowed = repository(tmp_path)
    target = root / "redirected"
    target.mkdir()
    directory = root / packet.DEFAULT_RUNTIME_DIRECTORY
    directory.parent.mkdir(parents=True, exist_ok=True)
    directory.symlink_to(target, target_is_directory=True)
    result = build(root, allowed)
    assert result.exit_code != exits.SUCCESS
    assert not list(target.iterdir())
