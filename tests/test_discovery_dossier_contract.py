import re
import shutil
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

import test_artefact_templates_contract as template_contract


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / ".github" / "skills" / "discovery-dossier" / "SKILL.md"
ARCHITECTURE_DATA_MODEL = ROOT / "docs" / "architecture" / "data-model.md"

CLASSIFICATIONS = {
    "observed",
    "inferred",
    "hypothesis",
    "assumption",
    "preference",
    "decision",
    "unknown",
}

OWNERS = {
    "`README.md`": (
        "Dossier identity, source Vision, scope, dossier disposition, "
        "`DEF-###` records, readiness verdict, `## Working state`, and "
        "`## Acceptance`"
    ),
    "`discovery-questions.md`": "`DQ-###` Discovery questions",
    "`system-map.md`": (
        "System context, actors, external dependencies, and trust and "
        "authority boundaries"
    ),
    "`domain-ontology.md`": (
        "Dossier-specific domain terms, meanings, relationships, and "
        "instances only; it references but must not redefine canonical "
        "record prefixes or schemas"
    ),
    "`mechanisms.md`": (
        "Candidate mechanisms and comparisons; accepted directions are "
        "references to `DEC-###`, not duplicate decisions"
    ),
    "`evidence-index.md`": "`EV-###` evidence records",
    "`assumptions.md`": "`ASM-###` assumptions and accepted preferences",
    "`decisions.md`": "`DEC-###` accepted decisions",
    "`risks-and-failure-modes.md`": (
        "`INV-###` invariants and `RSK-###` risks, failure modes, and treatments"
    ),
    "`prd-recommendations.md`": (
        "Recommendations for requirements and explicit non-requirements; "
        "it does not own `PR-###` records"
    ),
    "`architecture-handoff.md`": (
        "Evidence-backed constraints, unresolved architecture decisions, "
        "and dossier record references"
    ),
    "`experiments/EXP-###-<slug>.md`": "One `EXP-###` experiment per file",
    "`revisions/DR-###-<slug>.md`": (
        "One append-only `DR-###` Discovery Revision per file"
    ),
}

TABLE_SCHEMAS = {
    "DQ": [
        "ID",
        "Schema version",
        "Traces",
        "Question",
        "Consequence",
        "Method",
        "Budget",
        "Stop condition",
        "Outcome",
        "Resolved records",
        "Classification",
        "Provenance",
        "Confidence / limitations",
        "Owner",
        "Disposition",
    ],
    "EV": [
        "ID",
        "Schema version",
        "Evidence",
        "Supports",
        "Source revision",
        "Method",
        "Observed at",
        "Reproduction notes",
        "Classification",
        "Provenance",
        "Confidence / limitations",
        "Owner",
        "Disposition",
    ],
    "ASM": [
        "ID",
        "Schema version",
        "Statement",
        "Evidence",
        "Impact",
        "Invalidation",
        "Traces",
        "Classification",
        "Provenance",
        "Confidence / limitations",
        "Owner",
        "Disposition",
    ],
    "DEC": [
        "ID",
        "Schema version",
        "Decision",
        "Rationale",
        "Consequence",
        "Alternatives",
        "Traces",
        "Classification",
        "Provenance",
        "Confidence / limitations",
        "Owner",
        "Disposition",
    ],
    "INV": [
        "ID",
        "Schema version",
        "Invariant",
        "Rationale",
        "Failure consequence",
        "Traces",
        "Classification",
        "Provenance",
        "Confidence / limitations",
        "Owner",
        "Disposition",
    ],
    "RSK": [
        "ID",
        "Schema version",
        "Risk",
        "Impact",
        "Likelihood",
        "Treatment",
        "Trigger",
        "Traces",
        "Classification",
        "Provenance",
        "Confidence / limitations",
        "Owner",
        "Disposition",
    ],
    "DEF": [
        "ID",
        "Schema version",
        "Deferral",
        "Reason",
        "Impact",
        "Trigger",
        "Treatment",
        "Traces",
        "Classification",
        "Provenance",
        "Confidence / limitations",
        "Owner",
        "Disposition",
    ],
}

PREFIX_FILES = {
    "DQ": "discovery-questions.md",
    "EV": "evidence-index.md",
    "ASM": "assumptions.md",
    "DEC": "decisions.md",
    "INV": "risks-and-failure-modes.md",
    "RSK": "risks-and-failure-modes.md",
    "DEF": "README.md",
}

EXP_FIELDS = [
    "Schema version",
    "Classification",
    "Question",
    "Method",
    "Budget",
    "Stop condition",
    "Outcome",
    "Evidence",
    "Supports",
    "Provenance",
    "Confidence / limitations",
    "Owner",
    "Disposition",
]

DR_FIELDS = [
    "Schema version",
    "Classification",
    "Reason",
    "Requestor",
    "Affected records",
    "Downstream impact set",
    "Invalidated gates",
    "Actor",
    "Timestamp",
    "Scope",
    "Verdict",
    "Rationale",
    "Source revision",
    "Provenance",
    "Confidence / limitations",
    "Owner",
    "Disposition",
]

DR_ACCEPTANCE_FIELDS = [
    "Actor",
    "Timestamp",
    "Scope",
    "Verdict",
    "Rationale",
    "Source revision",
]

REQUIRED_FILES = {
    "README.md",
    "discovery-questions.md",
    "system-map.md",
    "domain-ontology.md",
    "mechanisms.md",
    "evidence-index.md",
    "assumptions.md",
    "decisions.md",
    "risks-and-failure-modes.md",
    "prd-recommendations.md",
    "architecture-handoff.md",
}

BASE_ACCEPTANCE_FIELDS = [
    "Actor",
    "Timestamp",
    "Scope",
    "Disposition",
    "Verdict",
    "Rationale",
    "Source revision",
]

NA_FIELDS = ["Status", "Reason", "Owner", "Source revision"]

ACCEPTANCE_SUFFIX = [
    "Acceptance actor",
    "Acceptance timestamp",
    "Acceptance scope",
    "Acceptance verdict",
    "Acceptance rationale",
    "Acceptance source revision",
]

ADJACENT_ACCEPTANCE_FIELDS = [
    "Record ID",
    "Actor",
    "Timestamp",
    "Scope",
    "Verdict",
    "Rationale",
    "Source revision",
]

RECORD_ID = re.compile(
    r"^(?:DQ|EV|ASM|DEC|INV|RSK|DEF|EXP|DR)-(?:00[1-9]|0[1-9]\d|[1-9]\d{2})$"
)
VO_ID = re.compile(r"^VO-(?:00[1-9]|0[1-9]\d|[1-9]\d{2})$")
DOWNSTREAM_ID = re.compile(
    r"^(?:(?:PR|QR|ADR)-(?:00[1-9]|0[1-9]\d|[1-9]\d{2})"
    r"|TH[1-9]\d*\.E[1-9]\d*\.US[1-9]\d*)$"
)
TIMESTAMP_WITH_OFFSET = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    r"(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)
LIFECYCLE_EXPIRY = re.compile(
    r"^until (?:TH[1-9]\d* (?:acceptance|release)"
    r"|VP[1-9]\d* (?:acceptance|Discovery reclassification))$"
)
DR_HUMAN_ACTOR = re.compile(r"^Human: \S(?:.*\S)?$")
IMMUTABLE_SOURCE_REVISION = re.compile(
    r"^(?:git:[0-9a-f]{40}|sha256:[0-9a-f]{64})$"
)


def section(text: str, heading: str) -> str:
    """Return a markdown section, stopping at the next same-or-higher heading."""
    level = len(heading) - len(heading.lstrip("#"))
    lines = text.splitlines()
    try:
        start = lines.index(heading) + 1
    except ValueError:
        raise AssertionError(f"missing section {heading}") from None

    body = []
    fenced = False
    for line in lines[start:]:
        if line.startswith("```"):
            fenced = not fenced
        if not fenced and re.match(rf"^#{{1,{level}}} ", line):
            break
        body.append(line)
    return "\n".join(body)


def pipe_rows(text: str) -> list[list[str]]:
    rows = []
    for line in text.splitlines():
        if not line.startswith("|") or re.fullmatch(r"[|: -]+", line):
            continue
        rows.append([cell.strip() for cell in line.strip("|").split("|")])
    return rows


def markdown_table_blocks(
    text: str,
) -> list[tuple[list[list[str]], bool]]:
    blocks = []
    current: list[list[str]] = []
    for line in [*text.splitlines(), ""]:
        if line.startswith("|"):
            current.append(
                [cell.strip() for cell in line.strip("|").split("|")]
            )
        elif current:
            separator_is_second = (
                len(current) >= 2
                and len(current[1]) == len(current[0])
                and all(
                    re.fullmatch(r":?-{3,}:?", cell)
                    for cell in current[1]
                )
            )
            rows = [
                row
                for row in current
                if not (
                    row
                    and all(
                        re.fullmatch(r":?-{3,}:?", cell)
                        for cell in row
                    )
                )
            ]
            blocks.append((rows, separator_is_second))
            current = []
    return blocks


def markdown_tables(text: str) -> list[list[list[str]]]:
    return [table for table, _ in markdown_table_blocks(text)]


def table_with_header(
    text: str,
    header: list[str],
    *,
    require_separator: bool = False,
    path: Path | None = None,
) -> list[list[str]]:
    matches = [
        (table, separator_is_valid)
        for table, separator_is_valid in markdown_table_blocks(text)
        if table and table[0] == header
    ]
    assert len(matches) == 1, f"expected one table with header {header}"
    table, separator_is_valid = matches[0]
    if require_separator:
        assert separator_is_valid, (
            f"{path or 'markdown table'}: separator must be the second row "
            "and match the header width"
        )
    return table


def id_tables(text: str, path: Path) -> list[list[list[str]]]:
    tables = []
    for table, separator_is_valid in markdown_table_blocks(text):
        if not table or not table[0] or table[0][0] != "ID":
            continue
        assert separator_is_valid, (
            f"{path}: ID table separator must be the second row and "
            "match the header width"
        )
        tables.append(table)
    return tables


def ownership_map(
    text: str, heading: str = "## Dossier Location and Ownership"
) -> dict[str, str]:
    rows = pipe_rows(section(text, heading))
    assert rows[0] == ["Required path", "Sole ownership"]
    return {row[0]: row[1] for row in rows[1:]}


def schema_map(text: str) -> dict[str, list[str]]:
    rows = pipe_rows(section(text, "### Required table columns"))
    assert rows[0] == ["Prefix", "Owning file", "Complete required columns"]
    return {
        row[0].strip("`"): [
            value.strip().strip("`") for value in row[2].split(",")
        ]
        for row in rows[1:]
        if len(row) == 3 and row[0].strip("`") in TABLE_SCHEMAS
    }


def exact_metadata_fields(grammar: str, prefix: str, ending: str) -> list[str]:
    article = "An" if prefix == "EXP" else "A"
    start = (
        f"{article} `{prefix}-###` metadata table requires exactly these fields "
        "in this order:\n"
    )
    assert start in grammar, f"missing exact {prefix} metadata contract"
    field_text = grammar.split(start, 1)[1].split(ending, 1)[0]
    return re.findall(r"`([^`]+)`", field_text)


def record_values(
    prefix: str, overrides: dict[str, str] | None = None
) -> list[str]:
    classifications = {
        "ASM": "assumption",
        "DEC": "decision",
        "DEF": "decision",
    }
    values = {
        "ID": f"{prefix}-001",
        "Schema version": "1",
        "Traces": "VO-001",
        "Question": "What outcome must be understood?",
        "Consequence": "Wrong scope",
        "Method": "Inspect safe local source",
        "Budget": "30 minutes",
        "Stop condition": "One reproducible answer",
        "Outcome": "Resolved",
        "Resolved records": "DEC-001",
        "Evidence": "Safe aggregate result",
        "Supports": "DQ-001",
        "Source revision": "source-v1",
        "Observed at": "2026-09-05T12:00:00+01:00",
        "Reproduction notes": "Repeat local inspection",
        "Statement": "Condition holds",
        "Impact": "Bounded impact",
        "Invalidation": "Scope changes",
        "Decision": "Use the bounded option",
        "Rationale": "Evidence supports it",
        "Alternatives": "None",
        "Invariant": "History remains intact",
        "Failure consequence": "Audit history is lost",
        "Risk": "Scope may expand",
        "Likelihood": "low",
        "Treatment": "Reclassify",
        "Trigger": "Material scope expansion",
        "Deferral": "Later measurement",
        "Reason": "No production sample yet",
        "Classification": classifications.get(prefix, "observed"),
        "Provenance": "docs/source.md@v1; local inspection; 2026-09-05",
        "Confidence / limitations": "High; bounded sample",
        "Owner": "discovery facilitator",
        "Disposition": {
            "DEF": "deferred",
            "RSK": "risk-accepted",
        }.get(prefix, "accepted"),
        "Acceptance actor": "Human product owner",
        "Acceptance timestamp": "2026-09-05T12:00:00+01:00",
        "Acceptance scope": "VP99 fixture",
        "Acceptance verdict": "Accepted",
        "Acceptance rationale": "Accepted for the bounded fixture",
        "Acceptance source revision": "fixture-v1",
    }
    values.update(overrides or {})
    return [values[field] for field in TABLE_SCHEMAS[prefix] + ACCEPTANCE_SUFFIX]


def record_table(
    prefix: str,
    acceptance: str = "none",
    overrides: dict[str, str] | None = None,
) -> str:
    assert acceptance in {"none", "suffix", "adjacent"}
    header = TABLE_SCHEMAS[prefix] + (
        ACCEPTANCE_SUFFIX if acceptance == "suffix" else []
    )
    separator = ["---"] * len(header)
    values = record_values(prefix, overrides)
    row = values if acceptance == "suffix" else values[: len(TABLE_SCHEMAS[prefix])]
    table = "\n".join(
        f"| {' | '.join(row)} |"
        for row in (header, separator, row)
    )
    if acceptance == "adjacent":
        table = "\n\n".join([table, adjacent_acceptance(f"{prefix}-001")])
    return table


def adjacent_acceptance(record_id: str) -> str:
    values = [
        ("Record ID", record_id),
        ("Actor", "Human product owner"),
        ("Timestamp", "2026-09-05T12:00:00+01:00"),
        ("Scope", "VP99 fixture"),
        ("Verdict", "Accepted"),
        ("Rationale", "Accepted for the bounded fixture"),
        ("Source revision", "fixture-v1"),
    ]
    return "\n".join(
        [
            f"### Acceptance: {record_id}",
            "",
            "| Field | Value |",
            "|---|---|",
            *(f"| {field} | {value} |" for field, value in values),
        ]
    )


def applicability_marker(reason: str = "Assessed and not applicable") -> str:
    return "\n".join(
        [
            "## Applicability",
            "",
            "| Field | Value |",
            "|---|---|",
            "| Status | not-applicable |",
            f"| Reason | {reason} |",
            "| Owner | discovery facilitator |",
            "| Source revision | fixture-v1 |",
        ]
    )


def acceptance_table(
    disposition: str,
    verdict: str = "READY",
    expiry: str = "2026-10-01",
    invalidation: str = "Material scope expansion",
) -> str:
    rows = [
        ("Actor", "Human product owner"),
        ("Timestamp", "2026-09-05T12:00:00+01:00"),
        ("Scope", "VP99 fixture"),
        ("Disposition", disposition),
        ("Verdict", verdict),
        ("Rationale", "Fixture is decision-ready"),
        ("Source revision", "fixture-v1"),
    ]
    if disposition == "WAIVED":
        rows.extend(
            [
                ("Expiry", expiry),
                ("Invalidation", invalidation),
            ]
        )
    return "\n".join(
        [
            "## Acceptance",
            "",
            "| Field | Value |",
            "|---|---|",
            *(f"| {field} | {value} |" for field, value in rows),
        ]
    )


def metadata_document(
    record_id: str, title: str, fields: list[str], overrides: dict[str, str] | None = None
) -> str:
    values = {
        "Schema version": "1",
        "Classification": "observed",
        "Question": "Can the bounded behavior be reproduced?",
        "Method": "Inspect safe local aggregate",
        "Budget": "20 minutes",
        "Stop condition": "One reproducible outcome",
        "Outcome": "Confirmed",
        "Evidence": "EV-001",
        "Supports": "DQ-001",
        "Provenance": "docs/source.md@v1; local inspection; 2026-09-05",
        "Confidence / limitations": "High; fixture only",
        "Owner": "discovery facilitator",
        "Disposition": "accepted",
        "Reason": "Correct accepted decision",
        "Requestor": "Product owner",
        "Affected records": "DEC-001",
        "Downstream impact set": "PR-001, ADR-001, TH99.E1.US1",
        "Invalidated gates": "Discovery",
        "Actor": "Human: product owner",
        "Timestamp": "2026-09-05T12:00:00+01:00",
        "Scope": "DR-001 over the VP99 fixture dossier",
        "Verdict": "Accepted",
        "Rationale": "The correction preserves the accepted intent",
        "Source revision": "sha256:" + ("a" * 64),
    }
    values.update(overrides or {})
    return "\n".join(
        [
            f"# {record_id}: {title}",
            "",
            "| Field | Value |",
            "|---|---|",
            *(f"| {field} | {values[field]} |" for field in fields),
            "",
        ]
    )


def create_dossier(root: Path, disposition: str) -> Path:
    root.mkdir()
    (root / "experiments").mkdir()
    (root / "revisions").mkdir()

    identity = "\n".join(
        [
            "# Fixture Discovery Dossier",
            "",
            "| Field | Value |",
            "|---|---|",
            "| Vision | docs/vision_of_product/VP99-fixture/VP99.md |",
            "| Schema version | 1 |",
        ]
    )

    if disposition == "FULL":
        readme = "\n\n".join(
            [
                identity,
                record_table("DEF", acceptance="adjacent"),
                acceptance_table("FULL"),
            ]
        )
        contents = {
            "discovery-questions.md": record_table("DQ"),
            "system-map.md": "# System Map\n\nBounded safe system context.",
            "domain-ontology.md": "# Domain Ontology\n\nFixture-specific terms.",
            "mechanisms.md": "# Mechanisms\n\nBounded comparison.",
            "evidence-index.md": record_table("EV"),
            "assumptions.md": record_table("ASM", acceptance="suffix"),
            "decisions.md": record_table("DEC", acceptance="suffix"),
            "risks-and-failure-modes.md": "\n\n".join(
                [record_table("INV"), record_table("RSK", acceptance="suffix")]
            ),
            "prd-recommendations.md": "# PRD Recommendations\n\nBounded recommendation.",
            "architecture-handoff.md": "# Architecture Handoff\n\nDEC-001.",
        }
        (root / "experiments" / "EXP-001-fixture.md").write_text(
            metadata_document("EXP-001", "Fixture", EXP_FIELDS)
        )
    elif disposition == "LIGHTWEIGHT":
        readme = "\n\n".join(
            [
                identity,
                applicability_marker("No deferrals apply"),
                acceptance_table("LIGHTWEIGHT"),
            ]
        )
        contents = {
            "discovery-questions.md": record_table("DQ"),
            "system-map.md": applicability_marker(),
            "domain-ontology.md": applicability_marker(),
            "mechanisms.md": applicability_marker(),
            "evidence-index.md": record_table("EV"),
            "assumptions.md": applicability_marker(),
            "decisions.md": record_table("DEC", acceptance="suffix"),
            "risks-and-failure-modes.md": applicability_marker(),
            "prd-recommendations.md": applicability_marker(),
            "architecture-handoff.md": applicability_marker(),
        }
    else:
        assert disposition == "WAIVED"
        waiver_reference = (
            "WAIVED by README.md#Acceptance for the exact VP99 fixture scope"
        )
        readme = "\n\n".join(
            [
                identity,
                applicability_marker(
                    f"No deferrals apply; {waiver_reference}"
                ),
                acceptance_table("WAIVED"),
            ]
        )
        contents = {
            relative: applicability_marker(waiver_reference)
            for relative in REQUIRED_FILES - {"README.md"}
        }

    (root / "README.md").write_text(readme)
    for relative, content in contents.items():
        (root / relative).write_text(content)
    (root / "experiments" / ".gitkeep").touch()
    (root / "revisions" / ".gitkeep").touch()
    return root


def validate_applicability(text: str, path: Path) -> None:
    marker = section(text, "## Applicability")
    rows = table_with_header(marker, ["Field", "Value"])
    assert [row[0] for row in rows[1:]] == NA_FIELDS, path
    assert all(len(row) == 2 and row[1] for row in rows[1:]), path
    assert dict(rows[1:])["Status"] == "not-applicable", path


def validate_iso_timestamp(value: str, path: Path) -> None:
    assert TIMESTAMP_WITH_OFFSET.fullmatch(value), path
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise AssertionError(path) from None


def validate_human_actor(value: str, path: Path) -> None:
    assert value and re.search(r"\bhuman\b", value, flags=re.IGNORECASE), path


def validate_human_acceptance(values: dict[str, str], path: Path) -> None:
    validate_human_actor(values["Actor"], path)
    validate_iso_timestamp(values["Timestamp"], path)
    assert values["Scope"], path
    assert values["Verdict"] == "Accepted", path
    assert values["Rationale"], path
    assert values["Source revision"], path


def validate_dr_acceptance(values: dict[str, str], path: Path) -> None:
    actor = values["Actor"]
    placeholder = template_contract.PLACEHOLDER.search(actor)
    assert placeholder is None, (
        f"{path}: Actor contains unfilled placeholder {placeholder.group(0)}. "
        "Replace Actor with a completed Human: name-or-accountable-role value."
    )
    assert DR_HUMAN_ACTOR.fullmatch(actor), (
        f"{path}: Actor must be a completed Human: name-or-accountable-role value"
    )
    validate_iso_timestamp(values["Timestamp"], path)
    assert values["Scope"], path
    assert values["Verdict"] in {"Accepted", "Rejected"}, path
    assert values["Rationale"], path
    assert IMMUTABLE_SOURCE_REVISION.fullmatch(values["Source revision"]), path


def adjacent_acceptance_records(text: str, path: Path) -> dict[str, dict[str, str]]:
    """Return only formal acceptances directly following their owning table."""
    records: dict[str, dict[str, str]] = {}
    consumed_heading_lines: set[int] = set()
    lines = text.splitlines()
    cursor = 0
    while cursor < len(lines):
        if not lines[cursor].startswith("|"):
            cursor += 1
            continue
        table_start = cursor
        while cursor < len(lines) and lines[cursor].startswith("|"):
            cursor += 1
        table = pipe_rows("\n".join(lines[table_start:cursor]))
        if not table or not table[0] or table[0][0] != "ID":
            continue
        owning_ids = {row[0] for row in table[1:] if row}
        next_line = cursor
        while next_line < len(lines) and not lines[next_line].strip():
            next_line += 1
        while next_line < len(lines):
            heading = re.fullmatch(
                r"### Acceptance: (?P<id>[A-Z]+-\d{3})", lines[next_line]
            )
            if not heading:
                break
            consumed_heading_lines.add(next_line)
            record_id = heading.group("id")
            assert RECORD_ID.fullmatch(record_id), path
            assert record_id in owning_ids, (
                f"{path}: acceptance {record_id} is not adjacent to its owning table"
            )
            assert record_id not in records, path
            body_start = next_line + 1
            body_end = body_start
            while body_end < len(lines) and not re.match(
                r"^#{1,3} ", lines[body_end]
            ):
                body_end += 1
            body = "\n".join(lines[body_start:body_end])
            body_content = [line for line in body.splitlines() if line.strip()]
            assert body_content and all(
                line.startswith("|") for line in body_content
            ), path
            assert len(markdown_tables(body)) == 1, path
            acceptance = table_with_header(
                body,
                ["Field", "Value"],
                require_separator=True,
                path=path,
            )
            assert [row[0] for row in acceptance[1:]] == (
                ADJACENT_ACCEPTANCE_FIELDS
            ), path
            assert all(
                len(row) == 2 and row[1] for row in acceptance[1:]
            ), path
            values = dict(acceptance[1:])
            assert values["Record ID"] == record_id, path
            validate_human_acceptance(values, path)
            records[record_id] = values
            next_line = body_end
            while next_line < len(lines) and not lines[next_line].strip():
                next_line += 1

    all_heading_lines = {
        index
        for index, line in enumerate(lines)
        if line.startswith("### Acceptance: ")
    }
    assert all_heading_lines == consumed_heading_lines, (
        f"{path}: formal record acceptance is not directly adjacent "
        "to its owning row table"
    )
    return records


def validate_metadata(
    path: Path, prefix: str, fields: list[str]
) -> tuple[str, dict[str, str]]:
    text = path.read_text()
    filename = re.fullmatch(
        rf"(?P<id>{prefix}-(?:00[1-9]|0[1-9]\d|[1-9]\d{{2}}))"
        r"-(?:[a-z0-9]+(?:-[a-z0-9]+)*)\.md",
        path.name,
    )
    assert filename, path
    record_id = filename.group("id")
    assert RECORD_ID.fullmatch(record_id), path
    assert re.match(rf"^# {re.escape(record_id)}: \S", text), path
    table = table_with_header(
        text,
        ["Field", "Value"],
        require_separator=True,
        path=path,
    )
    assert [row[0] for row in table[1:]] == fields, path
    assert len({row[0] for row in table[1:]}) == len(fields), path
    assert all(len(row) == 2 and row[1] for row in table[1:]), path
    values = dict(table[1:])
    assert values["Schema version"] == "1", path
    assert values["Classification"] in CLASSIFICATIONS, path
    return record_id, values


def validate_dossier(
    root: Path,
    *,
    as_of: date | datetime = date(2026, 9, 5),
    material_scope_expanded: bool = False,
    occurred_lifecycle_events: set[str] | None = None,
) -> bool:
    """Test-only schema oracle; production validation belongs to later stories."""
    assert {path.name for path in root.iterdir() if path.is_file()} == REQUIRED_FILES
    assert (root / "experiments").is_dir()
    assert (root / "revisions").is_dir()

    readme = (root / "README.md").read_text()
    identity_tables = [
        table
        for table in markdown_tables(readme)
        if table[0] == ["Field", "Value"]
        and any(row[0] == "Schema version" for row in table[1:])
    ]
    assert len(identity_tables) == 1
    assert dict(identity_tables[0][1:])["Schema version"] == "1"

    acceptance = table_with_header(
        section(readme, "## Acceptance"),
        ["Field", "Value"],
        require_separator=True,
        path=root / "README.md",
    )
    acceptance_fields = [row[0] for row in acceptance[1:]]
    acceptance_values = dict(acceptance[1:])
    disposition = acceptance_values["Disposition"]
    expected_gate = BASE_ACCEPTANCE_FIELDS + (
        ["Expiry", "Invalidation"] if disposition == "WAIVED" else []
    )
    assert acceptance_fields == expected_gate
    assert all(len(row) == 2 and row[1] for row in acceptance[1:])
    validate_human_actor(acceptance_values["Actor"], root / "README.md")
    validate_iso_timestamp(
        acceptance_values["Timestamp"], root / "README.md"
    )
    assert acceptance_values["Scope"], root / "README.md"
    assert acceptance_values["Rationale"], root / "README.md"
    assert acceptance_values["Source revision"], root / "README.md"
    assert disposition in {"FULL", "LIGHTWEIGHT", "WAIVED"}
    assert acceptance_values["Verdict"] in {
        "READY",
        "READY_WITH_DEFERRALS",
        "BLOCKED",
    }

    if disposition == "WAIVED":
        assert "material scope expansion" in acceptance_values[
            "Invalidation"
        ].lower()
        for relative in REQUIRED_FILES:
            text = (root / relative).read_text()
            validate_applicability(text, root / relative)
            reason = dict(
                table_with_header(
                    section(text, "## Applicability"), ["Field", "Value"]
                )[1:]
            )["Reason"]
            assert "WAIVED" in reason
            assert "README.md#Acceptance" in reason

    prefixes_by_file: dict[str, list[str]] = {}
    for prefix, relative in PREFIX_FILES.items():
        prefixes_by_file.setdefault(relative, []).append(prefix)
    for relative, prefixes in prefixes_by_file.items():
        path = root / relative
        for table in id_tables(path.read_text(), path):
            allowed_headers = [
                header
                for prefix in prefixes
                for header in (
                    TABLE_SCHEMAS[prefix],
                    TABLE_SCHEMAS[prefix] + ACCEPTANCE_SUFFIX,
                )
            ]
            assert table[0] in allowed_headers, path

    found: set[str] = set()
    records_requiring_acceptance: list[
        tuple[str, Path, dict[str, str], bool]
    ] = []
    for prefix, relative in PREFIX_FILES.items():
        path = root / relative
        text = path.read_text()
        tables = id_tables(text, path)
        matching = []
        for table in tables:
            header = table[0]
            if header in (
                TABLE_SCHEMAS[prefix],
                TABLE_SCHEMAS[prefix] + ACCEPTANCE_SUFFIX,
            ):
                matching.append(table)
        if not matching:
            validate_applicability(text, path)
            continue
        assert len(matching) == 1, path
        table = matching[0]
        has_acceptance_suffix = table[0] == (
            TABLE_SCHEMAS[prefix] + ACCEPTANCE_SUFFIX
        )
        for row in table[1:]:
            assert len(row) == len(table[0]), path
            assert all(row), path
            assert re.fullmatch(
                rf"{prefix}-(?:00[1-9]|0[1-9]\d|[1-9]\d{{2}})", row[0]
            ), path
            assert RECORD_ID.fullmatch(row[0]), path
            assert row[0] not in found, f"duplicate stable ID: {row[0]}"
            assert row[1] == "1", path
            values = dict(zip(table[0], row, strict=True))
            assert values["Classification"] in CLASSIFICATIONS, path
            if has_acceptance_suffix:
                validate_human_acceptance(
                    {
                        "Actor": values["Acceptance actor"],
                        "Timestamp": values["Acceptance timestamp"],
                        "Scope": values["Acceptance scope"],
                        "Verdict": values["Acceptance verdict"],
                        "Rationale": values["Acceptance rationale"],
                        "Source revision": values[
                            "Acceptance source revision"
                        ],
                    },
                    path,
                )
            if prefix == "DQ":
                assert all(
                    VO_ID.fullmatch(trace.strip())
                    for trace in row[2].split(",")
                ), path
            found.add(row[0])
            claims_human_acceptance = (
                (
                    prefix in {"DEC", "DEF"}
                    and values["Disposition"] in {"accepted", "deferred"}
                )
                or (
                    values["Classification"] in {"assumption", "preference", "decision"}
                    and values["Disposition"] == "accepted"
                )
                or (
                    prefix == "RSK"
                    and values["Disposition"] == "risk-accepted"
                )
            )
            if claims_human_acceptance:
                records_requiring_acceptance.append(
                    (row[0], path, values, has_acceptance_suffix)
                )

    adjacent_by_path = {
        path: adjacent_acceptance_records(path.read_text(), path)
        for path in {
            root / relative for relative in PREFIX_FILES.values()
        }
    }
    for record_id, path, values, has_suffix in records_requiring_acceptance:
        if has_suffix:
            assert record_id not in adjacent_by_path[path], path
        else:
            assert record_id in adjacent_by_path[path], path

    for path, acceptances in adjacent_by_path.items():
        assert set(acceptances) <= found, path

    if disposition == "LIGHTWEIGHT":
        assert {"DQ-001", "EV-001", "DEC-001"} <= found

    for directory, prefix, fields in (
        (root / "experiments", "EXP", EXP_FIELDS),
        (root / "revisions", "DR", DR_FIELDS),
    ):
        for path in directory.iterdir():
            if path.name == ".gitkeep":
                continue
            assert path.is_file() and path.suffix == ".md", path
            record_id, values = validate_metadata(path, prefix, fields)
            assert record_id not in found, f"duplicate stable ID: {record_id}"
            found.add(record_id)
            if prefix == "DR":
                affected = {
                    value.strip() for value in values["Affected records"].split(",")
                }
                assert affected
                assert all(RECORD_ID.fullmatch(value) for value in affected), path
                assert affected <= found - {record_id}, path
                downstream = {
                    value.strip()
                    for value in values["Downstream impact set"].split(",")
                }
                assert downstream == {"None"} or all(
                    DOWNSTREAM_ID.fullmatch(value) for value in downstream
                ), path
                validate_dr_acceptance(values, path)

    ready = acceptance_values["Verdict"] in {
        "READY",
        "READY_WITH_DEFERRALS",
    }
    if disposition == "WAIVED":
        expiry_value = acceptance_values["Expiry"]
        expiry_active: bool
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", expiry_value):
            try:
                as_of_date = (
                    as_of.date() if isinstance(as_of, datetime) else as_of
                )
                expiry_active = as_of_date <= date.fromisoformat(expiry_value)
            except ValueError:
                raise AssertionError(root / "README.md") from None
        elif TIMESTAMP_WITH_OFFSET.fullmatch(expiry_value):
            validate_iso_timestamp(expiry_value, root / "README.md")
            assert (
                isinstance(as_of, datetime)
                and as_of.tzinfo is not None
                and as_of.utcoffset() is not None
            ), f"{root / 'README.md'}: timestamp expiry requires aware as-of"
            expiry_active = as_of <= datetime.fromisoformat(
                expiry_value.replace("Z", "+00:00")
            )
        else:
            assert LIFECYCLE_EXPIRY.fullmatch(expiry_value), (
                root / "README.md"
            )
            expiry_active = expiry_value not in (
                occurred_lifecycle_events or set()
            )
        ready = (
            ready
            and expiry_active
            and not material_scope_expanded
        )
    return ready


def accepted_record_snapshots(root: Path) -> dict[str, tuple]:
    snapshots: dict[str, tuple] = {}
    for path in root.rglob("*.md"):
        acceptances = adjacent_acceptance_records(path.read_text(), path)
        for table in markdown_tables(path.read_text()):
            if table[0] and table[0][0] == "ID":
                try:
                    disposition_index = table[0].index("Disposition")
                except ValueError:
                    continue
                for row in table[1:]:
                    values = dict(zip(table[0], row, strict=True))
                    has_suffix = table[0][-len(ACCEPTANCE_SUFFIX):] == (
                        ACCEPTANCE_SUFFIX
                    )
                    human_accepted = (
                        row[disposition_index] == "accepted"
                        or (
                            row[0].startswith("DEF-")
                            and row[disposition_index] == "deferred"
                        )
                        or (
                            row[0].startswith("RSK-")
                            and row[disposition_index] == "risk-accepted"
                        )
                        or (
                            has_suffix
                            and values["Acceptance verdict"] == "Accepted"
                        )
                        or row[0] in acceptances
                    )
                    if human_accepted:
                        snapshots[row[0]] = (
                            "table",
                            str(path.relative_to(root)),
                            tuple(table[0]),
                            tuple(row),
                            tuple(acceptances.get(row[0], {}).items()),
                        )
        title = re.match(r"# ((?:EXP|DR)-\d{3}):", path.read_text())
        if title:
            metadata = dict(
                table_with_header(path.read_text(), ["Field", "Value"])[1:]
            )
            if (
                metadata.get("Disposition") == "accepted"
                or metadata.get("Verdict") == "Accepted"
            ):
                snapshots[title.group(1)] = (
                    "file",
                    str(path.relative_to(root)),
                    path.read_text(),
                )
    return snapshots


def validate_append_only(previous: Path, current: Path) -> None:
    before = accepted_record_snapshots(previous)
    after = accepted_record_snapshots(current)
    missing = set(before) - set(after)
    assert not missing, f"accepted records deleted: {sorted(missing)}"
    rewritten = sorted(
        record_id
        for record_id in before.keys() & after.keys()
        if before[record_id] != after[record_id]
    )
    assert not rewritten, f"accepted records rewritten: {rewritten}"


@pytest.fixture
def full_dossier(tmp_path: Path) -> Path:
    return create_dossier(tmp_path / "VP99-full", "FULL")


@pytest.fixture
def lightweight_dossier(tmp_path: Path) -> Path:
    return create_dossier(tmp_path / "VP99-lightweight", "LIGHTWEIGHT")


@pytest.fixture
def waived_dossier(tmp_path: Path) -> Path:
    return create_dossier(tmp_path / "VP99-waived", "WAIVED")


def test_canonical_ownership_is_exact_and_domain_ontology_cannot_redefine_schema():
    text = CONTRACT.read_text()
    assert "docs/discovery/VP<n>-<slug>/" in text
    assert ownership_map(text) == OWNERS
    versioning = section(text, "## Schema Version and Prospective Applicability")
    normalized = " ".join(versioning.split())
    assert "sole owner" in normalized
    assert "must not add, remove, rename, or redefine" in normalized


def test_architecture_and_skill_have_complete_equivalent_ownership_maps():
    architecture = section(
        ARCHITECTURE_DATA_MODEL.read_text(), "## 3. Discovery dossier"
    )
    architecture_owners = ownership_map(
        ARCHITECTURE_DATA_MODEL.read_text(), "## 3. Discovery dossier"
    )
    assert architecture_owners == ownership_map(CONTRACT.read_text()) == OWNERS
    assert len(pipe_rows(architecture)) == len(OWNERS) + 1
    assert set(architecture_owners) == set(OWNERS)
    assert "`DEF-###` records" in ownership_map(
        ARCHITECTURE_DATA_MODEL.read_text(), "## 3. Discovery dossier"
    )["`README.md`"]
    normalized = " ".join(architecture.split())
    assert (
        "The `discovery-dossier` skill is the canonical owner of Discovery "
        "record prefixes, ID grammar, schema versions, columns, metadata "
        "fields, and applicability-marker grammar."
    ) in normalized
    assert (
        "`domain-ontology.md` owns the dossier's domain concepts and "
        "terminology only"
    ) in normalized


def test_architecture_forbids_physical_deletion_and_requires_supersession():
    encoding = section(
        ARCHITECTURE_DATA_MODEL.read_text(), "## 1. Record encoding"
    )
    normalized = " ".join(encoding.split())
    assert "Records are never physically deleted." in normalized
    assert (
        "An accepted record is logically superseded only by retaining the "
        "original unchanged and appending a `DR-###` or `PCR-###`."
    ) in normalized


def test_table_schemas_have_exact_order_and_dq_traces_vision_outcomes():
    text = CONTRACT.read_text()
    assert schema_map(text) == TABLE_SCHEMAS
    dq_rule = section(text, "### Required table columns")
    assert "`DQ.Traces` is a required upstream relationship" in dq_rule
    assert "one or more" in dq_rule
    assert "`VO-### -> DQ-###`" in dq_rule


def test_file_record_metadata_fields_are_exact_and_ordered():
    grammar = section(CONTRACT.read_text(), "### File-per-record form")
    assert exact_metadata_fields(grammar, "EXP", ". Detailed") == EXP_FIELDS
    assert exact_metadata_fields(grammar, "DR", ". `Affected records`") == DR_FIELDS
    assert "# EXP-001: <Title>" in grammar
    assert "# DR-001: <Title>" in grammar
    assert "an `ID` metadata row is not required" in grammar


def test_dr_actor_requires_human_prefix_and_accepts_a_completed_human_role():
    grammar = " ".join(
        section(CONTRACT.read_text(), "### File-per-record form").split()
    )
    assert "Before applying that actor syntax" in grammar
    assert "shared angle-bracket placeholder rule rejects any `<...>` token" in (
        grammar
    )
    assert DR_HUMAN_ACTOR.fullmatch("Human: accountable product owner")
    assert DR_HUMAN_ACTOR.fullmatch("Human: Jane Doe")
    assert not DR_HUMAN_ACTOR.fullmatch("accountable product owner")
    assert not DR_HUMAN_ACTOR.fullmatch("Nonhuman: product owner")
    assert not DR_HUMAN_ACTOR.fullmatch("automation agent")


def test_accepted_dr_rejects_unchanged_actor_placeholder_with_remediation(
    full_dossier: Path,
):
    revision = full_dossier / "revisions" / "DR-001-correction.md"
    revision.write_text(
        metadata_document(
            "DR-001",
            "Correction",
            DR_FIELDS,
            overrides={"Actor": "Human: <name-or-accountable-role>"},
        )
    )

    with pytest.raises(AssertionError) as failure:
        validate_dossier(full_dossier)

    evidence = str(failure.value)
    assert "Actor" in evidence
    assert "<name-or-accountable-role>" in evidence
    assert "Replace Actor" in evidence


def test_attributable_acceptance_has_exact_suffix_and_adjacent_record_grammar():
    required_columns = section(CONTRACT.read_text(), "### Required table columns")
    normalized = " ".join(required_columns.split())
    assert (
        "| Acceptance actor | Acceptance timestamp | Acceptance scope | "
        "Acceptance verdict | Acceptance rationale | "
        "Acceptance source revision |"
    ) in required_columns
    assert "suffix is all-or-nothing" in normalized
    adjacent_match = re.search(
        r"directly\s+adjacent\s+formal record with this exact grammar:\s*"
        r"```text\n(?P<table>.*?)```",
        required_columns,
        flags=re.DOTALL,
    )
    assert adjacent_match
    adjacent_example = adjacent_match.group("table")
    assert [row[0] for row in pipe_rows(adjacent_example)[1:]] == (
        ADJACENT_ACCEPTANCE_FIELDS
    )
    assert "the next content after the owning row table" in normalized
    assert "remotely placed matching acceptance" in normalized
    assert "accepted decision or deferral without one complete suffix" in normalized


def test_schema_version_is_prospective_and_preserves_accepted_vp3_history():
    versioning = section(
        CONTRACT.read_text(), "## Schema Version and Prospective Applicability"
    )
    normalized = " ".join(versioning.split())
    assert "current Discovery dossier schema version is `1`" in normalized
    assert "| Schema version | 1 |" in versioning
    assert "schema version current at that record's creation" in normalized
    assert "retains that version for its entire history" in normalized
    assert "accepted, unversioned VP3 Discovery dossier is a legacy record set" in normalized
    assert "requires no rewrite, backfill, or fabricated metadata" in normalized
    assert "applies prospectively" in normalized
    assert "appends a `DR-###` plus any replacement record" in normalized


def test_closed_classifications_and_hypothesis_restriction():
    classification = section(CONTRACT.read_text(), "## Classification")
    normalized = " ".join(classification.split())
    rows = pipe_rows(classification)
    assert [row[0].strip("`") for row in rows[1:]] == [
        "observed",
        "inferred",
        "hypothesis",
        "assumption",
        "preference",
        "decision",
        "unknown",
    ]
    assert "A hypothesis may not constrain a PRD" in normalized
    assert "accepts it in an `ASM-###` record" in normalized
    assert "Merely renaming a hypothesis" in normalized


def test_security_and_redaction_rule_covers_whole_dossier_and_outputs():
    provenance = section(
        CONTRACT.read_text(), "## Provenance and Consequential Records"
    )
    normalized = " ".join(provenance.split())
    for prefix in ("DQ", "EV", "ASM", "DEC", "INV", "RSK", "DEF", "EXP", "DR"):
        assert f"`{prefix}`" in provenance
    assert "entire dossier and every output derived from it" in normalized
    for prohibited in (
        "secrets",
        "credentials",
        "access tokens",
        "private keys",
        "authentication material",
        "personal secrets",
        "unredacted sensitive payloads",
    ):
        assert prohibited in provenance
    assert "safe locator" in provenance
    assert "redact or aggregate" in provenance
    assert "must not embed credentials or secret query parameters" in normalized
    assert "before emission" in provenance


def test_waived_is_machine_readable_and_distinct_from_readiness():
    dispositions = section(CONTRACT.read_text(), "## Discovery Dispositions")
    gate = section(dispositions, "### Canonical README acceptance gate")
    normalized = " ".join(gate.split())
    tables = [
        table
        for table in markdown_tables(gate)
        if table[0] == ["Field", "Value"]
    ]
    assert [row[0] for row in tables[0][1:]] == BASE_ACCEPTANCE_FIELDS
    assert ["Disposition", "FULL or LIGHTWEIGHT"] in tables[0]
    assert [row[0] for row in tables[1][1:]] == (
        BASE_ACCEPTANCE_FIELDS + ["Expiry", "Invalidation"]
    )
    assert ["Disposition", "WAIVED"] in tables[1]
    assert "`Disposition: WAIVED`" in gate
    assert "does not imply `READY`" in gate
    assert "does not itself open the Discovery gate" in normalized
    assert "same human-issued acceptance record carries `READY` or " in normalized
    assert "`READY_WITH_DEFERRALS`" in gate
    assert "`BLOCKED` never opens it" in gate
    assert "Expiry or invalidation" in gate
    assert "material scope expansion" in dispositions
    assert "formal human gate" in gate
    assert "exactly the fields shown" in gate
    assert "`until TH<n> acceptance`" in gate
    assert "`until VP<n> Discovery reclassification`" in gate


def test_full_fixture_conforms_to_the_contract(full_dossier: Path):
    validate_dossier(full_dossier)


def test_lightweight_fixture_keeps_files_and_marks_omissions(
    lightweight_dossier: Path,
):
    assert validate_dossier(lightweight_dossier)
    files = {
        path.name for path in lightweight_dossier.iterdir() if path.is_file()
    }
    assert files == REQUIRED_FILES
    assert "not-applicable" in (
        lightweight_dossier / "risks-and-failure-modes.md"
    ).read_text()


def test_waived_fixture_has_explicit_markers_and_opens_only_while_valid(
    waived_dossier: Path,
):
    assert validate_dossier(waived_dossier)
    for relative in REQUIRED_FILES:
        text = (waived_dossier / relative).read_text()
        assert "## Applicability" in text
        assert "WAIVED" in text
        assert "README.md#Acceptance" in text

    assert not validate_dossier(
        waived_dossier, as_of=date(2026, 10, 2)
    )
    assert validate_dossier(
        waived_dossier,
        as_of=datetime(2026, 10, 1, 23, 59, tzinfo=timezone.utc),
    )
    assert not validate_dossier(
        waived_dossier, material_scope_expanded=True
    )

    readme = waived_dossier / "README.md"
    readme.write_text(
        readme.read_text().replace("| Verdict | READY |", "| Verdict | BLOCKED |")
    )
    assert not validate_dossier(waived_dossier)


def test_waived_fixture_accepts_a_bounded_lifecycle_event(
    waived_dossier: Path,
):
    readme = waived_dossier / "README.md"
    readme.write_text(
        readme.read_text().replace(
            "| Expiry | 2026-10-01 |",
            "| Expiry | until TH99 acceptance |",
        )
    )
    assert validate_dossier(waived_dossier)
    assert not validate_dossier(
        waived_dossier,
        occurred_lifecycle_events={"until TH99 acceptance"},
    )


def test_waived_fixture_accepts_an_iso_timestamp_expiry(
    waived_dossier: Path,
):
    readme = waived_dossier / "README.md"
    readme.write_text(
        readme.read_text().replace(
            "| Expiry | 2026-10-01 |",
            "| Expiry | 2026-10-01T23:59:59.123+01:00 |",
        )
    )
    assert validate_dossier(
        waived_dossier,
        as_of=datetime(2026, 10, 1, 22, 59, 59, tzinfo=timezone.utc),
    )


def test_waived_timestamp_expired_earlier_the_same_date_is_rejected(
    waived_dossier: Path,
):
    readme = waived_dossier / "README.md"
    readme.write_text(
        readme.read_text().replace(
            "| Expiry | 2026-10-01 |",
            "| Expiry | 2026-10-01T08:00:00+01:00 |",
        )
    )
    assert not validate_dossier(
        waived_dossier,
        as_of=datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc),
    )


@pytest.mark.parametrize(
    "expiry",
    [
        "until further notice",
        "until scope changes",
        "until TH0 acceptance",
        "until TH99 is accepted",
        "2026-10-01T00:00:00",
        "2026-02-30",
    ],
)
def test_malformed_or_unbounded_waiver_expiry_is_rejected(
    waived_dossier: Path, expiry: str
):
    readme = waived_dossier / "README.md"
    readme.write_text(
        readme.read_text().replace(
            "| Expiry | 2026-10-01 |", f"| Expiry | {expiry} |"
        )
    )
    with pytest.raises(AssertionError):
        validate_dossier(waived_dossier)


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("| Actor | Human product owner |", "| Actor | automation agent |"),
        (
            "| Timestamp | 2026-09-05T12:00:00+01:00 |",
            "| Timestamp | 2026-09-05 |",
        ),
        (
            "| Timestamp | 2026-09-05T12:00:00+01:00 |",
            "| Timestamp | 2026-02-30T12:00:00+01:00 |",
        ),
        ("| Verdict | READY |", "| Verdict | Accepted |"),
        ("| Scope | VP99 fixture |", "| Scope |  |"),
        (
            "| Rationale | Fixture is decision-ready |",
            "| Rationale |  |",
        ),
        ("| Source revision | fixture-v1 |", "| Source revision |  |"),
        (
            "| Source revision | fixture-v1 |",
            "| Source revision | fixture-v1 |\n| Extra | forbidden |",
        ),
    ],
)
def test_malformed_readme_human_gate_is_rejected(
    lightweight_dossier: Path, old: str, new: str
):
    readme = lightweight_dossier / "README.md"
    text = readme.read_text()
    index = text.rfind(old)
    assert index >= 0
    readme.write_text(text[:index] + new + text[index + len(old):])
    with pytest.raises(AssertionError):
        validate_dossier(lightweight_dossier)


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("| Expiry | 2026-10-01 |\n", ""),
        (
            "| Invalidation | Material scope expansion |",
            "| Invalidation | Optional review |",
        ),
        ("README.md#Acceptance", "an unspecified waiver"),
    ],
)
def test_malformed_waived_fixture_is_rejected(
    waived_dossier: Path, old: str, new: str
):
    targets = [waived_dossier / "README.md"]
    if old == "README.md#Acceptance":
        targets = [waived_dossier / "domain-ontology.md"]
    target = targets[0]
    target.write_text(target.read_text().replace(old, new, 1))
    with pytest.raises(AssertionError):
        validate_dossier(waived_dossier)


def test_removed_record_field_is_rejected(full_dossier: Path):
    decisions = full_dossier / "decisions.md"
    text = decisions.read_text()
    decisions.write_text(text.replace(" | Owner | Disposition |", " | Disposition |"))
    with pytest.raises(AssertionError):
        validate_dossier(full_dossier)


def test_duplicate_stable_id_is_rejected(full_dossier: Path):
    decisions = full_dossier / "decisions.md"
    lines = decisions.read_text().splitlines()
    duplicate = next(line for line in lines if line.startswith("| DEC-001 |"))
    decisions.write_text("\n".join([*lines, duplicate]))
    with pytest.raises(AssertionError, match="duplicate stable ID"):
        validate_dossier(full_dossier)


@pytest.mark.parametrize(
    ("relative", "old", "new"),
    [
        ("README.md", "| Schema version | 1 |", "| Schema version | 1.0 |"),
        ("decisions.md", "| DEC-001 | 1 |", "| DEC-001 | v1 |"),
        (
            "experiments/EXP-001-fixture.md",
            "| Schema version | 1 |",
            "| Schema version | 01 |",
        ),
    ],
)
def test_malformed_schema_versions_are_rejected(
    full_dossier: Path, relative: str, old: str, new: str
):
    target = full_dossier / relative
    target.write_text(target.read_text().replace(old, new, 1))
    with pytest.raises(AssertionError):
        validate_dossier(full_dossier)


@pytest.mark.parametrize(
    ("relative", "old", "new"),
    [
        ("decisions.md", "| decision |", "| opinion |"),
        (
            "experiments/EXP-001-fixture.md",
            "| Classification | observed |",
            "| Classification | measured |",
        ),
    ],
)
def test_classification_vocabulary_is_closed(
    full_dossier: Path, relative: str, old: str, new: str
):
    target = full_dossier / relative
    target.write_text(target.read_text().replace(old, new, 1))
    with pytest.raises(AssertionError):
        validate_dossier(full_dossier)


@pytest.mark.parametrize("trace", ["None", "PR-001", "VO-01", "VO-000"])
def test_dq_requires_well_formed_upstream_vo_traces(
    full_dossier: Path, trace: str
):
    questions = full_dossier / "discovery-questions.md"
    questions.write_text(
        questions.read_text().replace("| VO-001 |", f"| {trace} |", 1)
    )
    with pytest.raises(AssertionError):
        validate_dossier(full_dossier)


def test_zero_id_and_malformed_file_record_id_are_rejected(
    full_dossier: Path,
):
    decisions = full_dossier / "decisions.md"
    decisions.write_text(decisions.read_text().replace("DEC-001", "DEC-000"))
    with pytest.raises(AssertionError):
        validate_dossier(full_dossier)

    valid = create_dossier(full_dossier.parent / "second-full", "FULL")
    experiment = valid / "experiments" / "EXP-001-fixture.md"
    experiment.rename(valid / "experiments" / "EXP-01-fixture.md")
    with pytest.raises(AssertionError):
        validate_dossier(valid)


def test_record_prefix_must_match_owning_schema(full_dossier: Path):
    decisions = full_dossier / "decisions.md"
    decisions.write_text(decisions.read_text().replace("DEC-001", "ASM-001"))
    with pytest.raises(AssertionError):
        validate_dossier(full_dossier)


def test_accepted_decision_supports_complete_adjacent_acceptance(
    full_dossier: Path,
):
    decisions = full_dossier / "decisions.md"
    decisions.write_text(record_table("DEC", acceptance="adjacent"))
    assert validate_dossier(full_dossier)


def test_remote_acceptance_on_open_non_accepting_dq_is_rejected(
    full_dossier: Path,
):
    questions = full_dossier / "discovery-questions.md"
    questions.write_text(
        "\n\n".join(
            [
                record_table(
                    "DQ",
                    overrides={"Disposition": "open"},
                ),
                "Remote explanatory content.",
                adjacent_acceptance("DQ-001"),
            ]
        )
    )
    with pytest.raises(AssertionError, match="not directly adjacent"):
        validate_dossier(full_dossier)


@pytest.mark.parametrize("table_kind", ["id", "gate", "record-acceptance"])
def test_required_markdown_table_separator_is_rejected_when_missing(
    tmp_path: Path, table_kind: str
):
    dossier = create_dossier(tmp_path / table_kind, "FULL")
    if table_kind == "id":
        target = dossier / "decisions.md"
        columns = TABLE_SCHEMAS["DEC"] + ACCEPTANCE_SUFFIX
        header = f"| {' | '.join(columns)} |"
        separator = f"| {' | '.join(['---'] * len(columns))} |"
        old = f"{header}\n{separator}"
        target.write_text(target.read_text().replace(old, header, 1))
    else:
        target = dossier / "README.md"
        heading = (
            "## Acceptance"
            if table_kind == "gate"
            else "### Acceptance: DEF-001"
        )
        old = f"{heading}\n\n| Field | Value |\n|---|---|"
        new = f"{heading}\n\n| Field | Value |"
        target.write_text(target.read_text().replace(old, new, 1))

    with pytest.raises(AssertionError, match="separator"):
        validate_dossier(dossier)


@pytest.mark.parametrize(
    ("prefix", "fields"),
    [
        ("EXP", EXP_FIELDS),
        ("DR", DR_FIELDS),
    ],
)
def test_file_record_metadata_separator_is_rejected_when_missing(
    tmp_path: Path, prefix: str, fields: list[str]
):
    path = tmp_path / f"{prefix}-001-fixture.md"
    path.write_text(
        metadata_document(f"{prefix}-001", "Fixture", fields).replace(
            "|---|---|\n",
            "",
            1,
        )
    )

    with pytest.raises(AssertionError, match="separator"):
        validate_metadata(path, prefix, fields)


@pytest.mark.parametrize(
    "intervening",
    [
        "Unrelated prose.",
        "## Unrelated heading\n\nUnrelated prose.",
        "| Other | Content |\n|---|---|\n| unrelated | row |",
    ],
)
def test_non_adjacent_acceptance_is_rejected(
    full_dossier: Path, intervening: str
):
    decisions = full_dossier / "decisions.md"
    decisions.write_text(
        record_table("DEC", acceptance="adjacent").replace(
            "\n\n### Acceptance: DEC-001",
            f"\n\n{intervening}\n\n### Acceptance: DEC-001",
        )
    )
    with pytest.raises(AssertionError, match="not directly adjacent"):
        validate_dossier(full_dossier)


def test_acceptance_moved_elsewhere_in_the_file_is_rejected(
    full_dossier: Path,
):
    decisions = full_dossier / "decisions.md"
    acceptance = adjacent_acceptance("DEC-001")
    decisions.write_text(
        "\n\n".join(
            [
                acceptance,
                "# Decision register",
                record_table("DEC"),
            ]
        )
    )
    with pytest.raises(AssertionError, match="not directly adjacent"):
        validate_dossier(full_dossier)


def test_accepted_decision_without_attributable_acceptance_is_rejected(
    full_dossier: Path,
):
    decisions = full_dossier / "decisions.md"
    decisions.write_text(record_table("DEC"))
    with pytest.raises(AssertionError):
        validate_dossier(full_dossier)


def test_partial_attributable_acceptance_suffix_is_rejected(
    full_dossier: Path,
):
    header = TABLE_SCHEMAS["DEC"] + ACCEPTANCE_SUFFIX[:-1]
    row = record_values("DEC")[: len(header)]
    decisions = full_dossier / "decisions.md"
    decisions.write_text(
        "\n".join(
            f"| {' | '.join(values)} |"
            for values in (header, ["---"] * len(header), row)
        )
    )
    with pytest.raises(AssertionError):
        validate_dossier(full_dossier)


def test_complete_suffix_on_non_accepting_row_is_still_formally_validated(
    full_dossier: Path,
):
    questions = full_dossier / "discovery-questions.md"
    questions.write_text(
        record_table(
            "DQ",
            acceptance="suffix",
            overrides={"Disposition": "open"},
        )
    )
    assert validate_dossier(full_dossier)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("Acceptance verdict", "Rejected"),
        ("Acceptance verdict", "Unsupported"),
        ("Acceptance timestamp", "2026-09-05"),
        ("Acceptance timestamp", "2026-02-30T12:00:00+01:00"),
        ("Acceptance actor", "discovery facilitator agent"),
        ("Acceptance scope", ""),
        ("Acceptance source revision", ""),
    ],
)
def test_invalid_complete_suffix_on_non_accepting_row_is_rejected(
    full_dossier: Path, field: str, value: str
):
    questions = full_dossier / "discovery-questions.md"
    questions.write_text(
        record_table(
            "DQ",
            acceptance="suffix",
            overrides={"Disposition": "open", field: value},
        )
    )
    with pytest.raises(AssertionError):
        validate_dossier(full_dossier)


def test_partial_suffix_on_non_accepting_row_is_rejected(
    full_dossier: Path,
):
    header = TABLE_SCHEMAS["DQ"] + ACCEPTANCE_SUFFIX[:-1]
    row = record_values(
        "DQ", {"Disposition": "open"}
    )[: len(header)]
    questions = full_dossier / "discovery-questions.md"
    questions.write_text(
        "\n".join(
            f"| {' | '.join(values)} |"
            for values in (header, ["---"] * len(header), row)
        )
    )
    with pytest.raises(AssertionError):
        validate_dossier(full_dossier)


def test_accepted_deferral_without_adjacent_acceptance_is_rejected(
    full_dossier: Path,
):
    readme = full_dossier / "README.md"
    readme.write_text(
        re.sub(
            r"\n\n### Acceptance: DEF-001.*?(?=\n\n## Acceptance)",
            "",
            readme.read_text(),
            flags=re.DOTALL,
        )
    )
    with pytest.raises(AssertionError):
        validate_dossier(full_dossier)


@pytest.mark.parametrize(
    "missing_field",
    ["Requestor", *DR_ACCEPTANCE_FIELDS, "Owner"],
)
def test_malformed_dr_metadata_is_rejected(
    full_dossier: Path, missing_field: str
):
    revision = full_dossier / "revisions" / "DR-001-correction.md"
    revision.write_text(
        metadata_document(
            "DR-001",
            "Correction",
            [field for field in DR_FIELDS if field != missing_field],
        )
    )
    with pytest.raises(AssertionError):
        validate_dossier(full_dossier)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("Actor", "discovery facilitator agent"),
        ("Actor", "product owner"),
        ("Actor", "Nonhuman: product owner"),
        ("Actor", "Human"),
        ("Timestamp", "2026-09-05"),
        ("Timestamp", "2026-02-30T12:00:00+01:00"),
        ("Scope", ""),
        ("Verdict", "READY"),
        ("Verdict", "Approved"),
        ("Rationale", ""),
        ("Source revision", "main"),
        ("Source revision", "HEAD"),
        ("Source revision", "latest"),
        ("Source revision", "fixture-v1"),
        ("Source revision", "dossier dated 2026-09-05"),
        ("Source revision", "git:ABCDEF0123456789ABCDEF0123456789ABCDEF01"),
        ("Source revision", "sha256:abc123"),
    ],
)
def test_dr_rejects_nonhuman_missing_malformed_or_mutable_acceptance(
    full_dossier: Path, field: str, value: str
):
    revision = full_dossier / "revisions" / "DR-001-correction.md"
    revision.write_text(
        metadata_document(
            "DR-001",
            "Correction",
            DR_FIELDS,
            overrides={field: value},
        )
    )
    with pytest.raises(AssertionError):
        validate_dossier(full_dossier)


def test_malformed_exp_metadata_order_is_rejected(full_dossier: Path):
    experiment = full_dossier / "experiments" / "EXP-001-fixture.md"
    wrong_order = EXP_FIELDS.copy()
    wrong_order[2], wrong_order[3] = wrong_order[3], wrong_order[2]
    experiment.write_text(
        metadata_document("EXP-001", "Fixture", wrong_order)
    )
    with pytest.raises(AssertionError):
        validate_dossier(full_dossier)


def test_deletion_is_rejected_but_append_only_supersession_conforms(
    full_dossier: Path, tmp_path: Path
):
    deleted = tmp_path / "deleted"
    shutil.copytree(full_dossier, deleted)
    decisions = deleted / "decisions.md"
    decisions.write_text(applicability_marker("Attempted deletion"))
    with pytest.raises(AssertionError, match="DEC-001"):
        validate_append_only(full_dossier, deleted)

    superseded = tmp_path / "superseded"
    shutil.copytree(full_dossier, superseded)
    (superseded / "revisions" / "DR-001-correction.md").write_text(
        metadata_document("DR-001", "Correct DEC-001", DR_FIELDS)
    )
    validate_dossier(superseded)
    validate_append_only(full_dossier, superseded)
    assert "DEC-001" in (
        superseded / "revisions" / "DR-001-correction.md"
    ).read_text()


def test_append_only_rejects_accepted_decision_content_rewrite(
    full_dossier: Path, tmp_path: Path
):
    rewritten = tmp_path / "rewritten-decision"
    shutil.copytree(full_dossier, rewritten)
    decisions = rewritten / "decisions.md"
    decisions.write_text(
        decisions.read_text().replace(
            "Use the bounded option", "Use a different bounded option"
        )
    )
    with pytest.raises(AssertionError, match=r"rewritten: \['DEC-001'\]"):
        validate_append_only(full_dossier, rewritten)


@pytest.mark.parametrize(
    ("relative", "old", "new", "record_id"),
    [
        (
            "README.md",
            "Later measurement",
            "Rewritten measurement",
            "DEF-001",
        ),
        (
            "README.md",
            "Accepted for the bounded fixture",
            "Rewritten acceptance rationale",
            "DEF-001",
        ),
        (
            "risks-and-failure-modes.md",
            "Scope may expand",
            "Rewritten risk",
            "RSK-001",
        ),
        (
            "risks-and-failure-modes.md",
            "Accepted for the bounded fixture",
            "Rewritten acceptance rationale",
            "RSK-001",
        ),
    ],
)
def test_append_only_rejects_all_human_accepted_forms_and_evidence_rewrites(
    full_dossier: Path,
    tmp_path: Path,
    relative: str,
    old: str,
    new: str,
    record_id: str,
):
    rewritten = tmp_path / f"rewritten-{record_id.lower()}"
    shutil.copytree(full_dossier, rewritten)
    target = rewritten / relative
    target.write_text(target.read_text().replace(old, new, 1))
    with pytest.raises(
        AssertionError, match=rf"rewritten: \['{record_id}'\]"
    ):
        validate_append_only(full_dossier, rewritten)


def test_append_only_rejects_accepted_dr_content_rewrite(
    full_dossier: Path, tmp_path: Path
):
    accepted = tmp_path / "accepted-revision"
    shutil.copytree(full_dossier, accepted)
    revision = accepted / "revisions" / "DR-001-correction.md"
    revision.write_text(
        metadata_document("DR-001", "Correct DEC-001", DR_FIELDS)
    )
    validate_dossier(accepted)

    rewritten = tmp_path / "rewritten-revision"
    shutil.copytree(accepted, rewritten)
    changed = rewritten / "revisions" / "DR-001-correction.md"
    changed.write_text(
        changed.read_text().replace(
            "Correct accepted decision", "Rewrite accepted decision"
        )
    )
    with pytest.raises(AssertionError, match=r"rewritten: \['DR-001'\]"):
        validate_append_only(accepted, rewritten)


def test_append_only_contract_requires_complete_dr_and_versioned_supersession():
    grammar = section(CONTRACT.read_text(), "### File-per-record form")
    revisions = section(
        CONTRACT.read_text(), "## Append-Only History and Discovery Revisions"
    )
    normalized = " ".join(revisions.split())
    assert exact_metadata_fields(grammar, "DR", ". `Affected records`") == DR_FIELDS
    for field in DR_ACCEPTANCE_FIELDS:
        assert f"`{field}`" in grammar
    normalized_grammar = " ".join(grammar.split())
    assert "`Requestor` identifies who asked for the change" in normalized_grammar
    assert "immutable" in grammar
    assert "`git:<40 lowercase hexadecimal characters>`" in grammar
    assert "`sha256:<64 lowercase hexadecimal characters>`" in grammar
    assert "mutable source labels" in normalized_grammar
    assert "deleting accepted row `DEC-004` is invalid" in normalized
    assert "retain `DEC-004` and append a `DR-###`" in normalized
    assert "`Affected records` includes `DEC-004`" in normalized
    assert "every accepted DR are append-only" in normalized
    assert "`Disposition: deferred`" in revisions
    assert "`Disposition: risk-accepted`" in revisions
    assert "complete row or complete file" in normalized
    assert "complete acceptance evidence" in normalized
    assert "use the schema version current at their own creation" in normalized
    assert "keep their original schema version and content" in normalized
