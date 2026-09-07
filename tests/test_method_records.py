import ast
import os
from pathlib import Path

from methodlib import records
import pytest


ROOT = Path(__file__).resolve().parents[1]


VP3_DISCOVERY = ROOT / "docs/discovery/VP3-discovery-led-cost-aware-methodology"
VP3_REQUIREMENTS = ROOT / "docs/requirements/VP3-discovery-led-cost-aware-methodology"
FIXTURES = ROOT / "tests/fixtures/method_records"


def assert_finding_shape(finding: records.Finding) -> None:
    assert set(finding) == {
        "check",
        "severity",
        "file",
        "record",
        "message",
        "remediation",
    }
    assert finding["check"] == "records"
    assert finding["severity"] == "error"


def test_real_accepted_vp3_discovery_indexes_legacy_and_file_records():
    index = records.index_vp(VP3_DISCOVERY, repository_root=ROOT)

    expected_counts = {
        "DQ": 16,
        "EV": 12,
        "ASM": 10,
        "DEC": 25,
        "INV": 12,
        "RSK": 12,
        "DEF": 5,
        "EXP": 4,
        "DR": 1,
    }
    for prefix, count in expected_counts.items():
        parsed = [record for record in index.records if record.prefix == prefix]
        assert len(parsed) == count
        assert all(record.file.startswith("docs/discovery/VP3-") for record in parsed)
        assert all(record.line >= 1 for record in parsed)
        assert all(len(index.by_id[record.id]) == 1 for record in parsed)

    assert index.findings == ()
    assert index.resolve("DQ-001").columns["Vision outcomes"] == "VO-001, VO-003"
    assert index.resolve("EXP-001").form == "file"
    assert index.resolve("EXP-001").columns["Outcome"] == "`VALIDATED_WITH_LIMITATIONS`"
    assert index.resolve("DR-001").columns["Affected records"].startswith("DEC-001")


def test_real_accepted_vp3_prd_legacy_rows_remain_parseable():
    index = records.index_vp(VP3_REQUIREMENTS, repository_root=ROOT)

    assert index.findings == ()
    assert len([item for item in index.records if item.prefix == "PR"]) == 46
    assert len([item for item in index.records if item.prefix == "QR"]) == 16
    assert index.resolve("PR-001").columns["Requirement"].startswith("The method")
    assert "Schema version" not in index.resolve("PR-001").columns
    assert "Traces" not in index.resolve("QR-001").columns


def test_current_schema_rows_and_multi_value_references_are_preserved():
    result = records.parse_markdown(
        "\n".join(
            (
                "| ID | Schema version | Traces | Decision |",
                "|:---|---:|:---:|---|",
                "| DEC-001 | 1 | DEC-002, DEC-012 | inert data |",
            )
        ),
        file="scope/decisions.md",
    )
    record = result.records[0]
    index = records.build_index(result.records, result.findings)

    assert result.findings == ()
    assert record.columns == {
        "ID": "DEC-001",
        "Schema version": "1",
        "Traces": "DEC-002, DEC-012",
        "Decision": "inert data",
    }
    assert record.references == ("DEC-002", "DEC-012")
    assert record.reference_columns == {
        "Traces": ("DEC-002", "DEC-012")
    }
    assert [edge.source_id for edge in index.references["DEC-002"]] == ["DEC-001"]
    assert records.split_references("DEC-002 and DEC-012") == ()
    assert records.split_references("DEC-000") == ()


def test_zero_id_is_malformed_and_later_rows_continue():
    result = records.parse_markdown(
        "\n".join(
            (
                "| ID | Value |",
                "|---|---|",
                "| DEC-000 | reserved zero |",
                "| DEC-001 | valid |",
            )
        )
    )

    assert [record.id for record in result.records] == ["DEC-001"]
    assert len(result.findings) == 1
    assert result.findings[0]["record"] is None
    assert "three digits" in result.findings[0]["message"]


def test_malformed_row_reports_width_and_continues_fixture():
    result = records.parse_file(
        FIXTURES / "malformed/records.md",
        repository_root=ROOT,
    )

    assert [record.id for record in result.records] == [
        "DEC-001",
        "DEC-003",
        "DEC-004",
    ]
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert_finding_shape(finding)
    assert finding["record"] == "DEC-002"
    assert "line 6" in finding["message"]
    assert "has 2 cells; expected 3" in finding["message"]
    assert "DEC-999" not in {record.id for record in result.records}


def test_bad_separator_is_deterministic_and_rows_still_parse():
    text = "\n".join(
        (
            "| ID | Value |",
            "|--|---|",
            "| DEC-001 | first |",
            "| DEC-002 | second |",
        )
    )

    first = records.parse_markdown(text, file="records.md")
    second = records.parse_markdown(text, file="records.md")

    assert first == second
    assert [record.id for record in first.records] == ["DEC-001", "DEC-002"]
    assert len(first.findings) == 1
    assert "requires a markdown separator with 2 cells" in first.findings[0]["message"]


@pytest.mark.parametrize(
    ("header", "message"),
    (
        ("| ID | ID | Value |", "exactly one canonical ID"),
        ("| ID | | Value |", "non-empty"),
        ("| ID | **Value** |", "well-formed"),
        ("| Value | ID |", "ID column first"),
    ),
)
def test_invalid_headers_emit_findings_omit_their_rows_and_continue(
    header: str,
    message: str,
):
    result = records.parse_markdown(
        "\n".join(
            (
                header,
                "|" + "---|" * (header.count("|") - 1),
                "| DEC-001 | invalid table row |"
                + (" ignored |" if header.count("|") == 4 else ""),
                "",
                "| ID | Value |",
                "|---|---|",
                "| DEC-002 | valid later table row |",
            )
        ),
        file="records.md",
    )

    assert [record.id for record in result.records] == ["DEC-002"]
    assert any(message in str(finding["message"]) for finding in result.findings)
    assert all(finding["record"] is None for finding in result.findings)
    assert all(set(finding) == {
        "check",
        "severity",
        "file",
        "record",
        "message",
        "remediation",
    } for finding in result.findings)


@pytest.mark.parametrize(
    ("opening", "wrong_close"),
    (
        ("```markdown", "````"),
        ("~~~~text", "```"),
    ),
)
def test_mismatched_fence_delimiters_do_not_expose_example_records(
    opening: str,
    wrong_close: str,
):
    result = records.parse_markdown(
        "\n".join(
            (
                opening,
                "| ID | Value |",
                "|---|---|",
                "| DEC-001 | example only |",
                wrong_close,
                "| ID | Value |",
                "|---|---|",
                "| DEC-002 | still fenced |",
            )
        )
    )

    assert result == records.ParseResult()


def test_duplicate_reuse_and_renumbering_have_distinct_semantics():
    def item(identifier: str, statement: str, line: int) -> records.Record:
        return records.Record(
            file="VP7/decisions.md",
            line=line,
            prefix="DEC",
            id=identifier,
            columns={"ID": identifier, "Statement": statement},
        )

    index = records.build_index(
        (
            item("DEC-001", "alpha", 3),
            item("DEC-001", "alpha", 4),
            item("DEC-001", "different fact", 5),
            item("DEC-003", "alpha", 6),
        )
    )
    messages = [str(finding["message"]) for finding in index.findings]

    assert any("ID DEC-001 is duplicated" in message for message in messages)
    assert any("ID DEC-001 is reused" in message for message in messages)
    assert any(
        "record content is renumbered as DEC-003" in message
        for message in messages
    )
    assert index.resolve("DEC-001") is None
    assert len(index.by_id["DEC-001"]) == 3
    assert all("VP7/decisions.md:" in message for message in messages[:3])


def test_file_per_record_id_mismatch_reports_finding_and_omits_record():
    text = "\n".join(
        (
            "# PCR-002: Safe inert change",
            "",
            "| Field | Value |",
            "|---|---|",
            "| Schema version | 1 |",
            "| Affected PR | PR-001, PR-002 |",
            "| Change | `__import__('os').system('false')` |",
        )
    )
    result = records.parse_markdown(
        text,
        file="changes/PCR-001-safe.md",
        path="changes/PCR-001-safe.md",
    )

    assert result.records == ()
    assert "does not match filename ID PCR-001" in result.findings[0]["message"]
    assert_finding_shape(result.findings[0])


def test_file_per_record_cross_prefix_mismatch_never_builds_inconsistent_record():
    result = records.parse_markdown(
        "\n".join(
            (
                "# DR-001: Wrong record kind",
                "",
                "| Field | Value |",
                "|---|---|",
                "| Outcome | rejected |",
            )
        ),
        file="experiments/EXP-001-wrong-kind.md",
        path="experiments/EXP-001-wrong-kind.md",
    )

    assert result.records == ()
    assert len(result.findings) == 1
    assert result.findings[0]["record"] == "DR-001"
    assert (
        result.findings[0]["message"]
        == "line 1: title ID DR-001 does not match filename ID EXP-001"
    )
    assert_finding_shape(result.findings[0])


def test_repository_content_is_never_imported_evaluated_or_executed(
    monkeypatch: pytest.MonkeyPatch,
):
    calls = []

    def forbidden(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("repository data was interpreted")

    monkeypatch.setattr(os, "system", forbidden)

    result = records.parse_markdown(
        "\n".join(
            (
                "| ID | Value |",
                "|---|---|",
                "| DEC-001 | __import__('malicious').run(); os.system('x') |",
            )
        )
    )

    assert result.records[0].columns["Value"].startswith("__import__")
    assert calls == []

    tree = ast.parse((ROOT / "methodlib/records.py").read_text())
    called_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    imported_roots = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert called_names.isdisjoint({"eval", "exec", "compile", "__import__"})
    assert imported_roots.isdisjoint({"subprocess", "importlib"})


def test_symlink_escape_invalid_utf8_and_oserror_become_findings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root = tmp_path / "repository"
    root.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("| ID | Value |\n|---|---|\n| DEC-001 | outside |\n")
    link = root / "escape.md"
    link.symlink_to(outside)
    invalid = root / "invalid.md"
    invalid.write_bytes(b"\xff")

    escaped = records.parse_file(link, repository_root=root)
    invalid_result = records.parse_file(invalid, repository_root=root)

    original_read_text = Path.read_text

    def fail_read(path: Path, *args, **kwargs):
        if path.name == "unreadable.md":
            raise OSError("sensitive platform detail")
        return original_read_text(path, *args, **kwargs)

    unreadable = root / "unreadable.md"
    unreadable.touch()
    monkeypatch.setattr(Path, "read_text", fail_read)
    unreadable_result = records.parse_file(unreadable, repository_root=root)

    assert "outside the trusted repository boundary" in escaped.findings[0]["message"]
    assert "not valid UTF-8" in invalid_result.findings[0]["message"]
    assert "could not be read" in unreadable_result.findings[0]["message"]
    for result in (escaped, invalid_result, unreadable_result):
        assert result.records == ()
        assert_finding_shape(result.findings[0])


def test_parse_file_valueerror_from_resolution_and_reading_becomes_findings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    embedded_nul = records.parse_file(
        "invalid\x00.md",
        repository_root=tmp_path,
    )

    source = tmp_path / "value-error.md"
    source.touch()
    original_read_text = Path.read_text

    def fail_read(path: Path, *args, **kwargs):
        if path == source:
            raise ValueError("sensitive platform detail")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fail_read)
    unreadable = records.parse_file(source, repository_root=tmp_path)

    assert "could not be resolved" in embedded_nul.findings[0]["message"]
    assert "could not be read" in unreadable.findings[0]["message"]
    assert "\x00" not in embedded_nul.findings[0]["file"]
    for result in (embedded_nul, unreadable):
        assert result.records == ()
        assert len(result.findings) == 1
        assert "sensitive platform detail" not in result.findings[0]["message"]
        assert_finding_shape(result.findings[0])


def test_index_vp_valueerror_from_embedded_nul_becomes_finding(tmp_path: Path):
    result = records.index_vp(
        "docs/discovery/VP8-invalid\x00",
        repository_root=tmp_path,
    )

    assert result.records == ()
    assert len(result.findings) == 1
    assert "VP scope could not be resolved" in result.findings[0]["message"]
    assert_finding_shape(result.findings[0])


def test_index_walk_rejects_symlink_directory_without_leaving_scope(tmp_path: Path):
    root = tmp_path / "repository"
    scope = root / "docs/discovery/VP8-safe"
    scope.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "records.md").write_text(
        "| ID | Value |\n|---|---|\n| DEC-001 | outside |\n"
    )
    (scope / "linked").symlink_to(outside, target_is_directory=True)
    (scope / "records.md").write_text(
        "| ID | Value |\n|---|---|\n| DEC-001 | inside |\n"
    )

    index = records.index_vp(scope, repository_root=root)

    assert [record.id for record in index.records] == ["DEC-001"]
    assert len(index.findings) == 1
    assert index.findings[0]["file"].endswith("/linked")
    assert "source directory could not be read" in index.findings[0]["message"]


def test_repository_relative_inputs_are_resolved_beneath_explicit_root(
    tmp_path: Path,
):
    source = tmp_path / "docs/discovery/VP8-safe/records.md"
    source.parent.mkdir(parents=True)
    source.write_text(
        "| ID | Value |\n|---|---|\n| DEC-001 | inside |\n",
        encoding="utf-8",
    )

    parsed = records.parse_file(
        "docs/discovery/VP8-safe/records.md",
        repository_root=tmp_path,
    )
    indexed = records.index_vp(
        "docs/discovery/VP8-safe",
        repository_root=tmp_path,
    )

    assert parsed.records[0].file == "docs/discovery/VP8-safe/records.md"
    assert indexed.resolve("DEC-001") is not None
    assert indexed.findings == ()
