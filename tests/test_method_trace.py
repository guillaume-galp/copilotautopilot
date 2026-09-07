import ast
import io
import json
import os
import shutil
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from methodlib import cli, exits, trace  # noqa: E402


STORY_PATH = (
    "docs/themes/TH9-trace/epics/E1-trace/stories/US1-trace.md"
)


def write(root: Path, relative: str, text: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def story_text(
    *,
    story_type: str = "standard",
    traceability: str | None = None,
    body: str = "Body mentions are explanatory only.",
) -> str:
    block = (
        traceability
        if traceability is not None
        else "\n".join(
            (
                "traceability:",
                "  vision: [VO-001]",
                "  requirements: [PR-001]",
                "  adrs: [ADR-009]",
                "  invariants: [INV-001]",
            )
        )
    )
    return "\n".join(
        (
            "---",
            "id: TH9.E1.US1",
            'title: "Trace fixture"',
            f"type: {story_type}",
            "agents: [developer]",
            "skills: [bdd-stories]",
            block,
            "acceptance-criteria:",
            '  - AC1: "Trace fixture passes."',
            "depends-on: []",
            "---",
            "",
            body,
            "",
        )
    )


def make_repository(
    tmp_path: Path,
    *,
    story: str | None = None,
    requirements: str | None = None,
    evidence: dict[str, list[str]] | None = None,
    story_status: str = "done",
) -> Path:
    root = tmp_path / "repository"
    root.mkdir(parents=True)
    skill = root / trace.SKILL_PATH
    skill.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / trace.SKILL_PATH, skill)

    write(
        root,
        "docs/vision_of_product/VP9-trace/VP9.md",
        "# VP9\n\nTraceable work is the product intent.\n",
    )
    write(
        root,
        "docs/discovery/VP9-trace/discovery-questions.md",
        "\n".join(
            (
                "# Questions",
                "",
                "| ID | Schema version | Traces | Question | Consequence | Method | "
                "Budget | Stop condition | Outcome | Resolved records | "
                "Classification | Provenance | Confidence / limitations | "
                "Owner | Disposition |",
                "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
                "| DQ-001 | 1 | VO-001 | What is needed? | Defines scope. | "
                "Review records. | 10 minutes | Link chosen. | Links are needed. | "
                "DEC-001 | question | Test fixture | High confidence. | "
                "Human: reviewer | resolved |",
            )
        ),
    )
    (root / "docs/discovery/VP9-trace/experiments").mkdir()
    write(
        root,
        "docs/discovery/VP9-trace/decisions.md",
        "\n".join(
            (
                "# Decisions",
                "",
                "| ID | Schema version | Decision | Rationale | Consequence | "
                "Alternatives | Traces | Classification | Provenance | "
                "Confidence / limitations | Owner | Disposition |",
                "|---|---|---|---|---|---|---|---|---|---|---|---|",
                "| DEC-001 | 1 | Preserve the link. | Prevent drift. | "
                "Requirements retain lineage. | None | DQ-001 | decision | "
                "Test fixture | High confidence. | Human: reviewer | accepted |",
            )
        ),
    )
    write(
        root,
        "docs/discovery/VP9-trace/risks-and-failure-modes.md",
        "\n".join(
            (
                "# Invariants",
                "",
                "| ID | Schema version | Invariant | Rationale | Failure consequence | "
                "Traces | Classification | Provenance | Confidence / limitations | "
                "Owner | Disposition |",
                "|---|---|---|---|---|---|---|---|---|---|---|",
                "| INV-001 | 1 | Links resolve. | Prevent drift. | Validation fails. | "
                "DQ-001 | invariant | Test fixture | High confidence. | "
                "Human: reviewer | accepted |",
            )
        ),
    )
    requirement_rows = requirements or (
        "| PR-001 | 1 | The product shall preserve links. | "
        "Validation exits zero. | consequential | Changes behavior. | "
        "VO-001, DEC-001, INV-001 |"
    )
    write(
        root,
        "docs/requirements/VP9-trace/PRD.md",
        "\n".join(
            (
                "# VP9 PRD",
                "",
                "## Vision outcomes",
                "",
                "| ID | Outcome |",
                "|---|---|",
                "| VO-001 | Traceable work. |",
                "",
                "## Functional requirements",
                "",
                "| ID | Schema version | Requirement | Measure | Impact | "
                "Impact rationale | Traces |",
                "|---|---|---|---|---|---|---|",
                requirement_rows,
            )
        ),
    )
    write(
        root,
        "docs/ADRs/ADR-009-trace.md",
        "# ADR-009: Trace architecture\n\n## Status\n\nAccepted\n",
    )
    write(root, STORY_PATH, story or story_text())

    evidence = evidence if evidence is not None else {
        "packets": [],
        "verification": ["tests/trace-verification.txt"],
        "review": [],
        "gitflow": [],
        "usage": [],
    }
    write(root, "tests/trace-verification.txt", "fixture verification\n")
    backlog = {
        "backlog": {
            "active-themes": [
                {
                    "id": "TH9",
                    "locked": False,
                    "vision-ref": "docs/vision_of_product/VP9-trace/",
                    "discovery-ref": "docs/discovery/VP9-trace/",
                    "requirements-ref": "docs/requirements/VP9-trace/PRD.md",
                    "epics": [
                        {
                            "stories": [
                                {
                                    "id": "TH9.E1.US1",
                                    "status": story_status,
                                    "file": STORY_PATH,
                                    "evidence": evidence,
                                }
                            ]
                        }
                    ],
                }
            ]
        }
    }
    write(root, "docs/plan/backlog.yaml", yaml.safe_dump(backlog, sort_keys=False))
    return root


def write_architecture_trace(
    root: Path,
    mappings: str,
    *,
    vp: str = "VP9",
) -> None:
    write(
        root,
        "docs/architecture/components.md",
        "# Components\n\n## Validator\n\nThe local validator component.\n",
    )
    write(
        root,
        "docs/architecture/README.md",
        "\n".join(
            (
                "# Architecture",
                "",
                "## Acceptance",
                "",
                "| Field | Value |",
                "|---|---|",
                "| Actor | Human: product owner |",
                "| Timestamp | 2026-09-06T21:41:37+01:00 |",
                f"| Scope | {vp} architecture |",
                "| Verdict | Accepted |",
                "| Rationale | Architecture accepted. |",
                f"| Source revision | sha256:{'a' * 64} |",
                "",
                trace.ARCHITECTURE_TRACE_START,
                "```yaml",
                "schema-version: 1",
                f"vp: {vp}",
                "mappings:",
                mappings,
                "```",
                trace.ARCHITECTURE_TRACE_END,
                "",
            )
        ),
    )


def assert_finding_shape(finding: trace.Finding) -> None:
    assert set(finding) == {
        "check",
        "severity",
        "file",
        "record",
        "message",
        "remediation",
    }
    assert finding["check"] == "trace"
    assert finding["severity"] == "error"


def test_real_current_th3_has_zero_unexplained_trace_findings():
    result = trace.validate_repository(ROOT)

    assert result.valid
    scoped_ids = {
        node.identifier for node in result.nodes if node.scope == "VP3"
    }
    assert "VO-007" in scoped_ids
    assert {"EXP-001", "EXP-002", "EXP-003", "EXP-004"} <= scoped_ids
    assert {"DEF-001", "DEF-002", "DEF-003", "DEF-004", "DEF-005"} <= scoped_ids

    categories = {
        "wrong-vo-owner": [
            item for item in result.findings
            if str(item["record"]).startswith("VO-")
            and "wrong canonical owner" in item["message"]
        ],
        "unresolved-vo": [
            item for item in result.findings
            if "declared reference VO-" in item["message"]
            and "does not resolve" in item["message"]
        ],
        "wrong-def-owner": [
            item for item in result.findings
            if str(item["record"]).startswith("DEF-")
            and "wrong canonical owner" in item["message"]
        ],
        "def-orphan": [
            item for item in result.findings
            if str(item["record"]).startswith("DEF-")
            and "no downstream link" in item["message"]
        ],
        # Validator defects fixed by this rework.
        "validator-evidence-label": [
            item for item in result.findings if "evidence." in item["message"]
        ],
        "validator-exp-dangling": [
            item for item in result.findings
            if "EXP-" in item["message"] and "does not resolve" in item["message"]
        ],
    }
    assert {key: len(value) for key, value in categories.items()} == {
        "wrong-vo-owner": 0,
        "unresolved-vo": 0,
        "wrong-def-owner": 0,
        "def-orphan": 0,
        "validator-evidence-label": 0,
        "validator-exp-dangling": 0,
    }
    assert not any(
        node.identifier == "evidence:TH3.E2.US6:packets:1"
        for node in result.nodes
    )
    assert not any(
        item["record"] == "TH3.E2.US6"
        and "evidence.packets" in item["message"]
        for item in result.findings
    )
    assert any(node.kind == "evidence" for node in result.nodes)
    assert result.findings == ()


def test_trace_recovery_rejects_corruption_then_accepts_restored_fixture(
    tmp_path: Path,
):
    root = make_repository(tmp_path)
    story = root / STORY_PATH
    original = story.read_text(encoding="utf-8")
    story.write_text(original.replace("PR-001", "PR-999"), encoding="utf-8")

    bypass_attempt = trace.validate_repository(root)
    bypass_cli = cli.dispatch(
        ["validate", "trace", "--json"], probe_directory=root
    )
    story.write_text(original, encoding="utf-8")
    restore_and_pass = trace.validate_repository(root)
    restore_cli = cli.dispatch(
        ["validate", "trace", "--json"], probe_directory=root
    )

    assert not bypass_attempt.valid
    assert bypass_cli.exit_code == exits.VALIDATION_FAILURE
    assert any("PR-999" in item["message"] for item in bypass_attempt.findings)
    assert restore_and_pass.valid
    assert restore_cli.exit_code == exits.SUCCESS


def test_cli_trace_emits_one_json_object_and_exit_two_for_dangling_story_id(
    tmp_path: Path,
):
    root = make_repository(
        tmp_path,
        story=story_text(
            traceability="\n".join(
                (
                    "traceability:",
                    "  vision: [VO-001]",
                    "  requirements: [PR-999]",
                    "  adrs: [ADR-009]",
                    "  invariants: [INV-001]",
                )
            )
        ),
    )

    result = cli.dispatch(["validate", "trace", "--json"], probe_directory=root)
    stdout, stderr = io.StringIO(), io.StringIO()
    status = cli.emit(result, stdout=stdout, stderr=stderr)
    report = json.loads(stdout.getvalue())

    assert status == exits.VALIDATION_FAILURE
    assert len(stdout.getvalue().splitlines()) == 1
    assert report["check"] == "trace"
    finding = next(
        item for item in report["findings"] if "PR-999" in item["message"]
    )
    assert finding["file"] == STORY_PATH
    assert finding["record"] == "TH9.E1.US1"
    assert_finding_shape(finding)
    assert "PR-999" in stderr.getvalue()


def test_consequential_requirement_needs_upstream_but_low_impact_doc_passes(
    tmp_path: Path,
):
    missing = make_repository(
        tmp_path / "missing",
        requirements=(
            "| PR-001 | 1 | The product shall preserve links. | "
            "Validation exits zero. | consequential | Changes behavior. | None |"
        ),
    )
    missing_result = trace.validate_repository(missing)

    assert not missing_result.valid
    assert any(
        item["record"] == "PR-001" and "no resolving upstream" in item["message"]
        for item in missing_result.findings
    )

    passing = make_repository(
        tmp_path / "passing",
        story=story_text(
            story_type="trivial",
            traceability="\n".join(
                (
                    "traceability:",
                    "  vision: []",
                    "  requirements: []",
                    "  adrs: []",
                    "  invariants: []",
                )
            ),
        ),
        requirements=(
            "| PR-001 | 1 | Completion Report Heading uses Title Case. | "
            "Review the rendered copy. | low-impact | Changing presentation "
            "cannot alter behavior. | "
            "DOC:docs/discovery/VP9-trace/editorial-guidance.md"
            "#completion-report-heading |"
        ),
    )
    for relative in (
        "docs/discovery/VP9-trace/discovery-questions.md",
        "docs/discovery/VP9-trace/decisions.md",
        "docs/discovery/VP9-trace/risks-and-failure-modes.md",
    ):
        (passing / relative).unlink()
    write(
        passing,
        "docs/discovery/VP9-trace/editorial-guidance.md",
        "# Completion Report Heading\n\nThe completion report heading uses title case.\n",
    )
    passing_result = trace.validate_repository(passing)

    assert passing_result.valid
    assert not any(
        "consequential traceability" in item["message"]
        for item in passing_result.findings
    )


def test_consequential_record_without_downstream_link_is_reported(
    tmp_path: Path,
):
    root = make_repository(
        tmp_path,
        requirements="\n".join(
            (
                "| PR-001 | 1 | The product shall preserve links. | Pass. | "
                "consequential | Changes behavior. | VO-001 |",
                "| PR-002 | 1 | The product shall report links. | Pass. | "
                "consequential | Changes behavior. | VO-001 |",
            )
        ),
    )
    write_architecture_trace(
        root,
        "\n".join(
            (
                "  - records: [PR-001]",
                "    theme: TH9",
                "    requirements: []",
                "    adrs: [ADR-009]",
                "    components: [docs/architecture/components.md#validator]",
                "    stories: [TH9.E1.US1]",
            )
        ),
    )

    result = trace.validate_repository(root)

    finding = next(item for item in result.findings if item["record"] == "PR-002")
    assert "no transitively reachable architecture link" in finding["message"]
    assert_finding_shape(finding)
    assert not any(
        item["record"] == "PR-001" and "architecture link" in item["message"]
        for item in result.findings
    )


def test_downstream_satisfaction_uses_vp_scoped_transitive_intermediate_nodes(
    tmp_path: Path,
):
    root = make_repository(tmp_path)
    write_architecture_trace(
        root,
        "\n".join(
            (
                "  - records: [DEC-001]",
                "    theme: TH9",
                "    requirements: [PR-001]",
                "    adrs: [ADR-009]",
                "    components: [docs/architecture/components.md#validator]",
                "    stories: [TH9.E1.US1]",
            )
        ),
    )

    result = trace.validate_repository(root)
    edges = {(edge.scope, edge.source, edge.target) for edge in result.edges}

    assert ("VP9", "DEC-001", "PR-001") in edges
    assert ("VP9", "PR-001", "ADR-009") in edges
    assert ("VP9", "ADR-009", "docs/architecture/components.md#validator") in edges
    assert not any(
        item["record"] in {"DQ-001", "DEC-001"}
        and "architecture link" in item["message"]
        for item in result.findings
    )


def test_inactive_mapped_theme_requires_architecture_but_not_story_or_evidence(
    tmp_path: Path,
):
    root = make_repository(
        tmp_path,
        requirements="\n".join(
            (
                "| PR-001 | 1 | The product shall preserve links. | Pass. | "
                "consequential | Changes behavior. | VO-001, DEC-001, INV-001 |",
                "| PR-002 | 1 | Later work shall preserve links. | Pass. | "
                "consequential | Changes behavior. | VO-001 |",
            )
        ),
    )
    write_architecture_trace(
        root,
        "\n".join(
            (
                "  - records: [PR-002]",
                "    theme: TH10",
                "    requirements: []",
                "    adrs: [ADR-009]",
                "    components: [docs/architecture/components.md#validator]",
                "    stories: []",
            )
        ),
    )

    result = trace.validate_repository(root)

    assert not any(
        item["record"] == "PR-002"
        and (
            "architecture link" in item["message"]
            or "story" in item["message"]
            or "evidence" in item["message"]
        )
        for item in result.findings
    )


def test_evidence_edges_are_status_gated_and_completed_mapped_work_requires_one(
    tmp_path: Path,
):
    mapping = "\n".join(
        (
            "  - records: [PR-001]",
            "    theme: TH9",
            "    requirements: []",
            "    adrs: [ADR-009]",
            "    components: [docs/architecture/components.md#validator]",
            "    stories: [TH9.E1.US1]",
        )
    )
    planned = make_repository(
        tmp_path / "planned",
        story_status="todo",
        evidence={
            "packets": [],
            "verification": ["tests/trace-verification.txt"],
            "review": [],
            "gitflow": [],
            "usage": [],
        },
    )
    write_architecture_trace(planned, mapping)
    planned_result = trace.validate_repository(planned)
    assert not any(node.kind == "evidence" for node in planned_result.nodes)
    assert not any(
        item["record"] == "TH9.E1.US1" and "evidence link" in item["message"]
        for item in planned_result.findings
    )

    completed = make_repository(
        tmp_path / "completed",
        story_status="done",
        evidence={key: [] for key in trace.EVIDENCE_KEYS},
    )
    write_architecture_trace(completed, mapping)
    completed_result = trace.validate_repository(completed)
    assert any(
        item["record"] == "TH9.E1.US1"
        and "completed applicable story has no downstream evidence link"
        in item["message"]
        for item in completed_result.findings
    )


def test_architecture_prose_cannot_create_trace_edges(tmp_path: Path):
    root = make_repository(
        tmp_path,
        requirements="\n".join(
            (
                "| PR-001 | 1 | The product shall preserve links. | Pass. | "
                "consequential | Changes behavior. | VO-001, DEC-001, INV-001 |",
                "| PR-002 | 1 | Prose must not satisfy this record. | Pass. | "
                "consequential | Changes behavior. | VO-001 |",
            )
        ),
    )
    write_architecture_trace(
        root,
        "\n".join(
            (
                "  - records: [PR-001]",
                "    theme: TH9",
                "    requirements: []",
                "    adrs: [ADR-009]",
                "    components: [docs/architecture/components.md#validator]",
                "    stories: [TH9.E1.US1]",
            )
        ),
    )
    architecture = root / "docs/architecture/README.md"
    architecture.write_text(
        architecture.read_text()
        + "\nProse claims that PR-002 maps to ADR-009 and TH9.E1.US1.\n",
        encoding="utf-8",
    )

    result = trace.validate_repository(root)

    assert any(
        item["record"] == "PR-002"
        and "no transitively reachable architecture link" in item["message"]
        for item in result.findings
    )


def test_story_body_references_are_not_authoritative(tmp_path: Path):
    root = make_repository(
        tmp_path,
        story=story_text(body="An example mentions PR-999 and ADR-999."),
    )

    result = trace.validate_repository(root)

    assert result.valid
    assert "PR-999" not in {node.identifier for node in result.nodes}


def test_undefined_key_and_missing_traceability_fail_with_expected_keys(
    tmp_path: Path,
):
    undefined = make_repository(
        tmp_path / "undefined",
        story=story_text(
            traceability="\n".join(
                (
                    "traceability:",
                    "  vision: [VO-001]",
                    "  requirements: [PR-001]",
                    "  adrs: [ADR-009]",
                    "  invariants: [INV-001]",
                    "  stories: [TH9.E1.US1]",
                )
            )
        ),
    )
    missing = make_repository(
        tmp_path / "missing",
        story=story_text(traceability="description: no trace block"),
    )

    undefined_result = trace.validate_repository(undefined)
    missing_result = trace.validate_repository(missing)

    undefined_finding = next(
        item for item in undefined_result.findings if "undefined" in item["message"]
    )
    assert undefined_finding["file"] == STORY_PATH
    assert "'stories'" in undefined_finding["message"]
    assert "vision, requirements, adrs, invariants" in undefined_finding["message"]
    assert any(
        "required frontmatter key 'traceability'" in item["message"]
        for item in missing_result.findings
    )


def test_story_traceability_prefixes_are_loaded_from_the_skill_contract(
    tmp_path: Path,
):
    root = make_repository(
        tmp_path,
        story=story_text(
            traceability="\n".join(
                (
                    "traceability:",
                    "  vision: [PR-001]",
                    "  requirements: [VO-001]",
                    "  adrs: [INV-001]",
                    "  invariants: [ADR-009]",
                )
            )
        ),
    )

    result = trace.validate_repository(root)

    assert not result.valid
    messages = [item["message"] for item in result.findings]
    assert any("traceability.vision" in message and "VO" in message for message in messages)
    assert any(
        "traceability.requirements" in message and "PR, QR" in message
        for message in messages
    )
    assert any("traceability.adrs" in message and "ADR" in message for message in messages)
    assert any(
        "traceability.invariants" in message and "INV" in message
        for message in messages
    )


def test_standard_and_spike_require_links_while_trivial_allows_empty_lists(
    tmp_path: Path,
):
    empty = "\n".join(
        (
            "traceability:",
            "  vision: []",
            "  requirements: []",
            "  adrs: []",
            "  invariants: []",
        )
    )
    for story_type in ("standard", "spike"):
        root = make_repository(
            tmp_path / story_type,
            story=story_text(story_type=story_type, traceability=empty),
        )
        result = trace.validate_repository(root)
        assert not result.valid
        assert {
            item["message"].split("traceability.", 1)[1].split(" ", 1)[0]
            for item in result.findings
            if "must contain at least one" in item["message"]
        } == {"vision", "requirements", "adrs", "invariants"}

    trivial = make_repository(
        tmp_path / "trivial",
        story=story_text(story_type="trivial", traceability=empty),
        requirements=(
            "| PR-001 | 1 | Completion Report Heading uses Title Case. | "
            "Review copy. | low-impact | Presentation only. | "
            "DOC:docs/discovery/VP9-trace/editorial-guidance.md"
            "#completion-report-heading |"
        ),
    )
    write(
        trivial,
        "docs/discovery/VP9-trace/editorial-guidance.md",
        "# Completion Report Heading\n\nThe completion report heading uses title case.\n",
    )
    for relative in (
        "docs/discovery/VP9-trace/discovery-questions.md",
        "docs/discovery/VP9-trace/decisions.md",
        "docs/discovery/VP9-trace/risks-and-failure-modes.md",
    ):
        (trivial / relative).unlink()
    assert trace.validate_repository(trivial).valid


def test_bdd_skill_contract_is_machine_readable_pinned_and_has_worked_example(
    tmp_path: Path,
):
    contract = trace.load_contract(ROOT)
    skill = (ROOT / trace.SKILL_PATH).read_text(encoding="utf-8")

    assert tuple(contract["keys"]) == (
        "vision",
        "requirements",
        "adrs",
        "invariants",
    )
    assert contract["keys"]["vision"]["prefixes"] == ["VO"]
    assert contract["keys"]["requirements"]["prefixes"] == ["PR", "QR"]
    assert contract["keys"]["adrs"]["prefixes"] == ["ADR"]
    assert contract["keys"]["invariants"]["prefixes"] == ["INV"]
    assert "Every `standard` and `spike` story must declare" in skill
    assert "A `trivial` story" in skill
    assert "Worked example:" in skill

    root = make_repository(tmp_path)
    contract_path = root / trace.SKILL_PATH
    contract_path.write_text(
        contract_path.read_text().replace("prefixes: [VO]", "prefixes: [DQ]", 1),
        encoding="utf-8",
    )
    result = trace.validate_repository(root)

    assert not result.valid
    assert len(result.findings) == 1
    assert result.findings[0]["record"] == "traceability-contract"
    assert "drifted" in result.findings[0]["message"]


def test_frontmatter_is_inert_duplicate_safe_and_story_path_cannot_escape(
    tmp_path: Path,
    monkeypatch,
):
    calls: list[tuple[object, ...]] = []

    def forbidden(*arguments):
        calls.append(arguments)
        raise AssertionError("repository content was executed")

    monkeypatch.setattr(os, "system", forbidden)
    malicious = story_text(body="__import__('os').system('false')")
    root = make_repository(tmp_path / "inert", story=malicious)

    assert trace.validate_repository(root).valid
    assert calls == []

    duplicate = make_repository(tmp_path / "duplicate")
    story_path = duplicate / STORY_PATH
    story_path.write_text(
        story_path.read_text().replace(
            "  vision: [VO-001]",
            "  vision: [VO-001]\n  vision: [VO-001]",
        ),
        encoding="utf-8",
    )
    duplicate_result = trace.validate_repository(duplicate)
    assert any("duplicate" in item["message"] for item in duplicate_result.findings)

    aliased = make_repository(tmp_path / "aliased")
    story_path = aliased / STORY_PATH
    anchored = story_path.read_text().replace(
        "traceability:\n  vision: [VO-001]",
        "traceability: &trace\n  vision: [VO-001]",
    )
    frontmatter, body = anchored.rsplit("---", 1)
    story_path.write_text(
        frontmatter + "copied-traceability: *trace\n---" + body,
        encoding="utf-8",
    )
    alias_result = trace.validate_repository(aliased)
    assert any("alias" in item["message"] for item in alias_result.findings)

    escaped = make_repository(tmp_path / "escaped")
    outside = tmp_path / "outside.md"
    outside.write_text(story_text(), encoding="utf-8")
    target = escaped / STORY_PATH
    target.unlink()
    target.symlink_to(outside)
    escaped_result = trace.validate_repository(escaped)
    assert any(
        item["record"] == "TH9.E1.US1"
        and "not a regular contained" in item["message"]
        for item in escaped_result.findings
    )

    tree = ast.parse((ROOT / "methodlib/trace.py").read_text())
    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert called.isdisjoint({"eval", "exec", "compile", "__import__"})


def test_findings_and_graph_are_deterministic(tmp_path: Path):
    root = make_repository(
        tmp_path,
        story=story_text(
            traceability="\n".join(
                (
                    "traceability:",
                    "  vision: [VO-999]",
                    "  requirements: [PR-999]",
                    "  adrs: [ADR-999]",
                    "  invariants: [INV-999]",
                )
            )
        ),
    )

    first = trace.validate_repository(root)
    second = trace.validate_repository(root)

    assert first == second
    assert all(set(item) == {
        "check",
        "severity",
        "file",
        "record",
        "message",
        "remediation",
    } for item in first.findings)


def test_counterfeit_ids_in_wrong_owner_or_schema_never_resolve(tmp_path: Path):
    root = make_repository(
        tmp_path,
        story=story_text(
            traceability="\n".join(
                (
                    "traceability:",
                    "  vision: [VO-999]",
                    "  requirements: [PR-001]",
                    "  adrs: [ADR-009]",
                    "  invariants: [INV-001]",
                )
            )
        ),
    )
    vision = root / "docs/vision_of_product/VP9-trace/VP9.md"
    vision.write_text(
        vision.read_text()
        + "\n## Counterfeit records\n\n| ID | Outcome |\n|---|---|\n"
        + "| VO-999 | Counterfeit Vision-sketch copy. |\n",
        encoding="utf-8",
    )
    prd = root / "docs/requirements/VP9-trace/PRD.md"
    prd.write_text(
        prd.read_text()
        + "\n## Counterfeit schema\n\n| ID | Requirement |\n|---|---|\n"
        + "| VO-998 | Counterfeit schema. |\n",
        encoding="utf-8",
    )
    decisions = root / "docs/discovery/VP9-trace/decisions.md"
    decisions.write_text(
        decisions.read_text()
        + "\n## Counterfeit question table\n\n"
        + "| ID | Vision outcomes | Question | Consequence | Outcome | Resolved by |\n"
        + "|---|---|---|---|---|---|\n"
        + "| DQ-999 | VO-001 | Counterfeit? | Wrong owner. | None. | DEC-001 |\n",
        encoding="utf-8",
    )

    result = trace.validate_repository(root)
    scoped_ids = {
        node.identifier for node in result.nodes if node.scope == "VP9"
    }

    assert {"VO-998", "VO-999", "DQ-999"}.isdisjoint(scoped_ids)
    assert any(
        item["record"] == "VO-999" and "wrong canonical owner" in item["message"]
        for item in result.findings
    )
    assert any(item["record"] == "VO-998" and "canonical" in item["message"]
               for item in result.findings)
    assert any(
        item["record"] == "DQ-999" and "wrong canonical owner" in item["message"]
        for item in result.findings
    )
    assert any(
        item["record"] == "TH9.E1.US1"
        and "VO-999 does not resolve" in item["message"]
        for item in result.findings
    )


def test_all_schema_traced_families_and_legacy_requirements_are_consequential(
    tmp_path: Path,
):
    root = make_repository(tmp_path)
    write(
        root,
        "docs/discovery/VP9-trace/decisions.md",
        "\n".join(
            (
                "# Decisions",
                "",
                "| ID | Schema version | Decision | Rationale | Consequence | "
                "Alternatives | Traces | Classification | Provenance | "
                "Confidence / limitations | Owner | Disposition |",
                "|---|---|---|---|---|---|---|---|---|---|---|---|",
                "| DEC-001 | 1 | Preserve links. | Prevent drift. | Changes "
                "requirements. | None | None | decision | Test fixture | "
                "High confidence. | Human: reviewer | accepted |",
            )
        ),
    )
    prd = root / "docs/requirements/VP9-trace/PRD.md"
    prd.write_text(
        prd.read_text()
        + "\n## Additional quality requirements\n\n"
        + "| ID | Schema version | Requirement | Measure | Impact | "
        + "Impact rationale | Traces |\n"
        + "|---|---|---|---|---|---|---|\n"
        + "| QR-002 | 1 | Validation shall remain deterministic. | "
        + "Repeated runs match. | consequential | Changes quality. | VO-001 |\n",
        encoding="utf-8",
    )

    result = trace.validate_repository(root)

    assert any(
        item["record"] == "DEC-001"
        and "no resolving upstream" in item["message"]
        for item in result.findings
    )
    assert not any(item["record"] == "QR-002" for item in result.findings)
    qr = next(node for node in result.nodes if node.identifier == "QR-002")
    assert qr.consequential
    legacy_result = trace.validate_repository(ROOT)
    legacy_qr = next(
        node
        for node in legacy_result.nodes
        if node.scope == "VP3" and node.identifier == "QR-002"
    )
    assert legacy_qr.consequential


def test_identical_ids_are_scoped_and_other_vp_records_never_resolve(
    tmp_path: Path,
):
    root = make_repository(
        tmp_path,
        requirements="\n".join(
            (
                "| PR-001 | 1 | The product shall preserve links. | Pass. | "
                "consequential | Changes behavior. | VO-001, DEC-001, INV-001 |",
                "| PR-777 | 1 | VP9 shall own this record. | Pass. | "
                "consequential | VP9 only. | VO-001 |",
            )
        ),
    )
    for category in ("vision_of_product", "discovery", "requirements"):
        source = next((root / "docs" / category).glob("VP9-*"))
        target = root / "docs" / category / source.name.replace("VP9", "VP10", 1)
        shutil.copytree(source, target)
    vp10_vision = root / "docs/vision_of_product/VP10-trace/VP9.md"
    vp10_vision.rename(vp10_vision.with_name("VP10.md"))
    vp10_prd = root / "docs/requirements/VP10-trace/PRD.md"
    vp10_prd.write_text(
        "\n".join(
            line for line in vp10_prd.read_text().splitlines() if "PR-777" not in line
        )
        + "\n",
        encoding="utf-8",
    )
    second_path = (
        "docs/themes/TH10-trace/epics/E1-trace/stories/US1-trace.md"
    )
    write(
        root,
        second_path,
        story_text(
            traceability="\n".join(
                (
                    "traceability:",
                    "  vision: [VO-001]",
                    "  requirements: [PR-777]",
                    "  adrs: [ADR-009]",
                    "  invariants: [INV-001]",
                )
            )
        ).replace("TH9.E1.US1", "TH10.E1.US1"),
    )
    backlog_path = root / "docs/plan/backlog.yaml"
    backlog = yaml.safe_load(backlog_path.read_text())
    backlog["backlog"]["active-themes"].append(
        {
            "id": "TH10",
            "locked": False,
            "vision-ref": "docs/vision_of_product/VP10-trace/",
            "discovery-ref": "docs/discovery/VP10-trace/",
            "requirements-ref": "docs/requirements/VP10-trace/PRD.md",
            "epics": [
                {
                    "stories": [
                        {
                            "id": "TH10.E1.US1",
                            "file": second_path,
                            "evidence": {
                                "packets": [],
                                "verification": ["tests/trace-verification.txt"],
                                "review": [],
                                "gitflow": [],
                                "usage": [],
                            },
                        }
                    ]
                }
            ],
        }
    )
    backlog_path.write_text(yaml.safe_dump(backlog, sort_keys=False), encoding="utf-8")

    result = trace.validate_repository(root)

    assert any(
        item["record"] == "TH10.E1.US1"
        and "PR-777 does not resolve" in item["message"]
        for item in result.findings
    )
    vo_nodes = [
        node for node in result.nodes if node.identifier == "VO-001"
    ]
    assert {node.scope for node in vo_nodes} == {"VP9", "VP10"}
    scoped_edges = {
        (edge.scope, edge.source, edge.target) for edge in result.edges
    }
    assert ("VP9", "VO-001", "DQ-001") in scoped_edges
    assert ("VP10", "VO-001", "DQ-001") in scoped_edges


def test_malformed_backlog_has_no_story_scan_fallback(tmp_path: Path):
    root = make_repository(tmp_path)
    write(root, "docs/plan/backlog.yaml", "backlog: [\n")

    result = trace.validate_repository(root)

    assert not result.valid
    assert result.nodes == ()
    assert any(
        "backlog is invalid" in item["message"] and "no fallback" in item["remediation"]
        for item in result.findings
    )


def test_unlisted_story_is_inventory_error_and_still_validated(tmp_path: Path):
    root = make_repository(tmp_path)
    unlisted = (
        "docs/themes/TH9-trace/epics/E1-trace/stories/US2-unlisted.md"
    )
    write(
        root,
        unlisted,
        "\n".join(
            (
                "---",
                "id: TH9.E1.US2",
                'title: "Unlisted"',
                "type: standard",
                "agents: [developer]",
                "skills: [bdd-stories]",
                "acceptance-criteria: [AC1]",
                "depends-on: []",
                "---",
            )
        ),
    )

    result = trace.validate_repository(root)

    assert any(
        item["file"] == unlisted and "not listed in backlog" in item["message"]
        for item in result.findings
    )
    assert any(
        item["file"] == unlisted
        and "required frontmatter field 'traceability'" in item["message"]
        for item in result.findings
    )
    assert any(
        item["file"] == unlisted
        and "required frontmatter key 'traceability'" in item["message"]
        for item in result.findings
    )


def test_low_impact_doc_rejects_architecture_cross_vp_unrelated_and_item_bypass(
    tmp_path: Path,
):
    cases = {
        "architecture": (
            "docs/architecture/editorial.md",
            "# Completion Heading\n\nCompletion heading title case.\n",
            "exactly one canonical same-VP",
        ),
        "cross-vp": (
            "docs/discovery/VP8-other/editorial.md",
            "# Completion Heading\n\nCompletion heading title case.\n",
            "exactly one canonical same-VP",
        ),
        "unrelated": (
            "docs/discovery/VP9-trace/editorial.md",
            "# Database Retention\n\nDatabase backup retention policy.\n",
            "relevant to the low-impact detail",
        ),
        "item-bypass": (
            "docs/discovery/VP9-trace/editorial.md",
            "# Completion Heading\n\nVO-001 defines completion heading title case.\n",
            "applicable item-level ID",
        ),
    }
    for name, (document, content, expected) in cases.items():
        anchor = (
            "database-retention" if name == "unrelated" else "completion-heading"
        )
        root = make_repository(
            tmp_path / name,
            requirements=(
                "| PR-001 | 1 | Completion Heading Uses Title Case. | "
                "Editorial review. | low-impact | Presentation only. | "
                f"DOC:{document}#{anchor} |"
            ),
        )
        write(root, document, content)
        result = trace.validate_repository(root)
        assert any(
            item["record"] == "PR-001" and expected in item["message"]
            for item in result.findings
        ), name


def test_completed_evidence_labels_and_paths_link_but_invalid_paths_fail_closed(
    tmp_path: Path,
):
    root = make_repository(
        tmp_path,
        evidence={
            "packets": ["docs/plan/runtime/packets/TH9.E1.US1/"],
            "verification": ["tests/trace-verification.txt", "not path evidence"],
            "review": ["missing/review.txt"],
            "gitflow": [],
            "usage": [],
            "other": ["tests/trace-verification.txt"],
        },
    )

    result = trace.validate_repository(root)
    evidence_ids = {
        node.identifier for node in result.nodes if node.kind == "evidence"
    }

    assert evidence_ids == {
        "evidence:TH9.E1.US1:verification:1",
        "evidence:TH9.E1.US1:verification:2",
    }
    assert any("undefined evidence key 'other'" in item["message"] for item in result.findings)
    assert not any("evidence.packets[0]" in item["message"] for item in result.findings)
    assert not any("evidence.verification[1]" in item["message"] for item in result.findings)
    assert any("evidence.review[0]" in item["message"] for item in result.findings)


def test_evidence_rejects_only_empty_or_unambiguous_invalid_path_claims(
    tmp_path: Path,
):
    root = make_repository(
        tmp_path,
        evidence={
            "packets": ["wrong/story/packet"],
            "verification": [
                "targeted suite: 12 passed",
                "../outside.txt",
                "missing-verification.txt",
            ],
            "review": ["APPROVED after review iteration 1"],
            "gitflow": [
                "Gitflow not applicable: branch/develop was unavailable"
            ],
            "usage": [""],
        },
    )

    result = trace.validate_repository(root)

    messages = [item["message"] for item in result.findings]
    assert any("packet evidence path does not match its story" in item for item in messages)
    assert any("verification[1] leaves repository scope" in item for item in messages)
    assert any("verification[2] claimed path" in item for item in messages)
    assert any("usage[0] must be a non-empty label or path" in item for item in messages)
    assert not any("gitflow[0]" in item for item in messages)


def _exp_text(
    identifier: str = "EXP-001",
    *,
    supports: str = "PR-001",
) -> str:
    return "\n".join(
        (
            f"# {identifier}: Trace Experiment",
            "",
            "| Field | Value |",
            "|---|---|",
            "| Schema version | 1 |",
            "| Classification | observed |",
            "| Question | Does trace indexing work? |",
            "| Method | Run the local validator. |",
            "| Budget | 10 minutes |",
            "| Stop condition | The record resolves. |",
            "| Outcome | Validated. |",
            "| Evidence | tests/trace-verification.txt |",
            f"| Supports | {supports} |",
            "| Provenance | Test fixture, version 1, 2026-09-06. |",
            "| Confidence / limitations | High confidence. |",
            "| Owner | Human: reviewer |",
            "| Disposition | validated |",
            "",
        )
    )


def test_canonical_exp_file_is_vp_scoped_and_links_into_the_graph(tmp_path: Path):
    root = make_repository(
        tmp_path,
        requirements=(
            "| PR-001 | 1 | The product shall preserve links. | Pass. | "
            "consequential | Changes behavior. | VO-001, EXP-001 |"
        ),
    )
    write(
        root,
        "docs/discovery/VP9-trace/experiments/EXP-001-trace.md",
        _exp_text(),
    )

    result = trace.validate_repository(root)

    experiment = next(node for node in result.nodes if node.identifier == "EXP-001")
    assert experiment.scope == "VP9"
    assert experiment.file.endswith("/experiments/EXP-001-trace.md")
    assert experiment.consequential
    assert ("VP9", "EXP-001", "PR-001") in {
        (edge.scope, edge.source, edge.target) for edge in result.edges
    }


def test_exp_malformed_schema_and_counterfeit_owner_have_precise_diagnostics(
    tmp_path: Path,
):
    root = make_repository(
        tmp_path,
        requirements=(
            "| PR-001 | 1 | The product shall preserve links. | Pass. | "
            "consequential | Changes behavior. | VO-001, EXP-001 |"
        ),
    )
    write(
        root,
        "docs/discovery/VP9-trace/experiments/EXP-001-trace.md",
        _exp_text().replace("| Budget | 10 minutes |\n", ""),
    )
    write(
        root,
        "docs/discovery/VP9-trace/experiments/EXP-003-title.md",
        _exp_text("EXP-004"),
    )
    write(
        root,
        "docs/discovery/VP9-trace/experiments/EXP-005_bad.md",
        _exp_text("EXP-005"),
    )
    decisions = root / "docs/discovery/VP9-trace/decisions.md"
    decisions.write_text(
        decisions.read_text()
        + "\n\n| ID | Schema version | Classification | Question | Method | Budget | "
        "Stop condition | Outcome | Evidence | Supports | Provenance | "
        "Confidence / limitations | Owner | Disposition |\n"
        + "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
        + "| EXP-002 | 1 | observed | Counterfeit? | Inspect. | 1 minute | "
        "Found. | None | tests/trace-verification.txt | PR-001 | Fixture. | "
        "High. | Human: reviewer | validated |\n",
        encoding="utf-8",
    )

    result = trace.validate_repository(root)

    assert any(
        item["record"] == "EXP-001"
        and "file-per-record metadata schema" in item["message"]
        for item in result.findings
    )
    assert not any(
        item["record"] == "PR-001"
        and "EXP-001 does not resolve" in item["message"]
        for item in result.findings
    )
    assert any(
        item["record"] == "EXP-002"
        and "wrong canonical owner" in item["message"]
        for item in result.findings
    )
    assert any(
        item["record"] == "EXP-004"
        and "does not match filename ID EXP-003" in item["message"]
        for item in result.findings
    )
    assert any(
        item["record"] == "EXP-005"
        and "malformed filename" in item["message"]
        for item in result.findings
    )
    assert {"EXP-001", "EXP-002"}.isdisjoint(
        {node.identifier for node in result.nodes}
    )


def test_exp_reference_cannot_resolve_from_another_vp(tmp_path: Path):
    root = make_repository(
        tmp_path,
        requirements=(
            "| PR-001 | 1 | The product shall preserve links. | Pass. | "
            "consequential | Changes behavior. | VO-001, EXP-001 |"
        ),
    )
    other = root / "docs/discovery/VP10-other/experiments"
    other.mkdir(parents=True)
    write(
        root,
        "docs/discovery/VP10-other/experiments/EXP-001-trace.md",
        _exp_text(),
    )

    result = trace.validate_repository(root)

    assert any(
        item["record"] == "PR-001"
        and "EXP-001 does not resolve" in item["message"]
        for item in result.findings
    )


def test_vp3_legacy_exp_format_is_narrowly_accepted(tmp_path: Path):
    root = make_repository(tmp_path)
    discovery = root / "docs/discovery/VP9-trace"
    vp3_discovery = discovery.with_name("VP3-trace")
    discovery.rename(vp3_discovery)
    backlog = yaml.safe_load((root / "docs/plan/backlog.yaml").read_text())
    theme = backlog["backlog"]["active-themes"][0]
    theme["vision-ref"] = "docs/vision_of_product/VP3-trace/"
    theme["discovery-ref"] = "docs/discovery/VP3-trace/"
    theme["requirements-ref"] = "docs/requirements/VP3-trace/PRD.md"
    for category in ("vision_of_product", "requirements"):
        source = next((root / "docs" / category).glob("VP9-*"))
        target = source.with_name(source.name.replace("VP9", "VP3", 1))
        source.rename(target)
        if category == "vision_of_product":
            (target / "VP9.md").rename(target / "VP3.md")
    (root / "docs/plan/backlog.yaml").write_text(
        yaml.safe_dump(backlog, sort_keys=False), encoding="utf-8"
    )
    legacy = "\n".join(
        (
            "# EXP-001: Accepted Legacy Experiment",
            "",
            "| Field | Value |",
            "|---|---|",
            "| Outcome | Validated. |",
            "| Question | Does it work? |",
            "| Method | Inspect it. |",
            "| Stop condition | Evidence found. |",
            "",
        )
    )
    write(
        root,
        "docs/discovery/VP3-trace/experiments/EXP-001-legacy.md",
        legacy,
    )

    result = trace.validate_repository(root)

    assert any(
        node.scope == "VP3" and node.identifier == "EXP-001"
        for node in result.nodes
    )
    assert not any(
        item["record"] == "EXP-001" and "schema" in item["message"]
        for item in result.findings
    )


def test_def_uses_readme_owner_schema_and_consequential_graph_rules(tmp_path: Path):
    root = make_repository(
        tmp_path,
        requirements=(
            "| PR-001 | 1 | The product shall preserve links. | Pass. | "
            "consequential | Changes behavior. | VO-001, DEF-001 |"
        ),
    )
    write(
        root,
        "docs/discovery/VP9-trace/README.md",
        "\n".join(
            (
                "# Dossier",
                "",
                "| ID | Schema version | Deferral | Reason | Impact | Trigger | "
                "Treatment | Traces | Classification | Provenance | "
                "Confidence / limitations | Owner | Disposition |",
                "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
                "| DEF-001 | 1 | Defer UI polish. | Lower priority. | Changes "
                "scope. | Core flow complete. | Schedule later. | DQ-001 | "
                "decision | Test fixture. | Known scope. | Human: reviewer | "
                "deferred |",
            )
        ),
    )

    result = trace.validate_repository(root)
    node = next(item for item in result.nodes if item.identifier == "DEF-001")

    assert node.scope == "VP9"
    assert node.consequential
    edges = {(item.scope, item.source, item.target) for item in result.edges}
    assert ("VP9", "DQ-001", "DEF-001") in edges
    assert ("VP9", "DEF-001", "PR-001") in edges
    assert not any(item["record"] == "DEF-001" for item in result.findings)


def test_prd_deferral_table_cites_discovery_owner_without_copying_record(
    tmp_path: Path,
):
    root = make_repository(tmp_path)
    write(
        root,
        "docs/discovery/VP9-trace/README.md",
        "\n".join(
            (
                "# Dossier",
                "",
                "| ID | Schema version | Deferral | Reason | Impact | Trigger | "
                "Treatment | Traces | Classification | Provenance | "
                "Confidence / limitations | Owner | Disposition |",
                "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
                "| DEF-001 | 1 | Defer UI polish. | Lower priority. | Changes "
                "scope. | Core flow complete. | Schedule later. | DQ-001 | "
                "decision | Test fixture. | Known scope. | Human: reviewer | "
                "deferred |",
            )
        ),
    )
    prd = root / "docs/requirements/VP9-trace/PRD.md"
    prd.write_text(
        prd.read_text()
        + "\n## Constraints and deferrals\n\n"
        + "The Discovery dossier owns the `DEF-###` definitions.\n\n"
        + "| ID | Constraint or deferral |\n"
        + "|---|---|\n"
        + "| DEF-001 | UI polish remains deferred. |\n",
        encoding="utf-8",
    )

    result = trace.validate_repository(root)
    matching_nodes = [
        node for node in result.nodes if node.identifier == "DEF-001"
    ]
    edges = {(edge.scope, edge.source, edge.target) for edge in result.edges}

    assert len(matching_nodes) == 1
    assert matching_nodes[0].file.endswith(
        "docs/discovery/VP9-trace/README.md"
    )
    assert ("VP9", "DEF-001", "PRD:VP9") in edges
    assert not any(
        item["record"] == "DEF-001"
        and (
            "wrong canonical owner" in item["message"]
            or "no downstream link" in item["message"]
        )
        for item in result.findings
    )


def test_def_wrong_owner_missing_upstream_and_orphan_fail_closed(tmp_path: Path):
    root = make_repository(tmp_path)
    write(
        root,
        "docs/discovery/VP9-trace/README.md",
        "\n".join(
            (
                "# Dossier",
                "",
                "| ID | Schema version | Deferral | Reason | Impact | Trigger | "
                "Treatment | Traces | Classification | Provenance | "
                "Confidence / limitations | Owner | Disposition |",
                "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
                "| DEF-001 | 1 | Defer UI polish. | Lower priority. | Changes "
                "scope. | Core flow complete. | Schedule later. | None | "
                "decision | Test fixture. | Known scope. | Human: reviewer | "
                "deferred |",
            )
        ),
    )
    decisions = root / "docs/discovery/VP9-trace/decisions.md"
    decisions.write_text(
        decisions.read_text()
        + "\n\n| ID | Schema version | Deferral | Reason | Impact | Trigger | "
        "Treatment | Traces | Classification | Provenance | "
        "Confidence / limitations | Owner | Disposition |\n"
        + "|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
        + "| DEF-002 | 1 | Counterfeit. | None. | Scope. | Later. | Track. | "
        "DQ-001 | decision | Fixture. | Known. | Human: reviewer | deferred |\n",
        encoding="utf-8",
    )

    result = trace.validate_repository(root)

    assert any(
        item["record"] == "DEF-001" and "no resolving upstream" in item["message"]
        for item in result.findings
    )
    assert not any(
        item["record"] == "DEF-001" and "architecture link" in item["message"]
        for item in result.findings
    )
    assert any(
        item["record"] == "DEF-002" and "wrong canonical owner" in item["message"]
        for item in result.findings
    )
