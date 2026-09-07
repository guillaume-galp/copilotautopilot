"""Fail-closed backlog schema validation sourced from the owning skill."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator, Mapping, Sequence

import yaml


Finding = dict[str, object]
PathValue = str | Path

SKILL_PATH = Path(".github/skills/backlog-management/SKILL.md")
BACKLOG_PATH = Path("docs/plan/backlog.yaml")
ARCHIVE_DIRECTORY = Path("docs/plan/backlog-archive")
CONTRACT_START = "<!-- backlog-schema-contract:start -->"
CONTRACT_END = "<!-- backlog-schema-contract:end -->"
MAX_YAML_BYTES = 2 * 1024 * 1024

THEME_ID = re.compile(r"TH[1-9][0-9]*")
EPIC_ID = re.compile(r"TH[1-9][0-9]*\.E[1-9][0-9]*")
V1_EPIC_ID = re.compile(r"(?:TH[1-9][0-9]*\.)?E[1-9][0-9]*")
STORY_ID = re.compile(r"TH[1-9][0-9]*\.E[1-9][0-9]*\.US[1-9][0-9]*")

# This is migration evidence, not an extensible policy surface.  Each tuple
# pins one story as it existed when the confidence vocabulary changed:
# (story ID, historical confidence, accepted review evidence).
LEGACY_CONFIDENCE_MIGRATION: tuple[tuple[str, str, str], ...] = (
    (
        "TH3.E1.US1",
        "high",
        "APPROVED after developer rework iteration 1",
    ),
    (
        "TH3.E1.US2",
        "high",
        "APPROVED by final closed-checklist review: AC1-AC6, all BDD scenarios, "
        "and all adjudicated actions passed",
    ),
    (
        "TH3.E1.US3",
        "high",
        "APPROVED by final closed-checklist review: AC1-AC5, all BDD scenarios, "
        "and all adjudicated evidence actions passed",
    ),
    (
        "TH3.E1.US4",
        "high",
        "APPROVED by standard reviewer",
    ),
    (
        "TH3.E2.US1",
        "high",
        "APPROVED after rework iteration 1",
    ),
    (
        "TH3.E2.US2",
        "high",
        "APPROVED after rework iteration 1",
    ),
)


class ContractError(ValueError):
    """The canonical schema contract cannot be loaded safely."""


class UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that fails closed on duplicate mapping keys."""


def _construct_mapping(
    loader: UniqueKeyLoader,
    node: yaml.MappingNode,
    deep: bool = False,
) -> dict[object, object]:
    loader.flatten_mapping(node)
    result: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in result
        except TypeError as error:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "found an unhashable mapping key",
                key_node.start_mark,
            ) from error
        if duplicate:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,
)


@dataclass(frozen=True)
class ValidationResult:
    findings: tuple[Finding, ...]

    @property
    def valid(self) -> bool:
        return not self.findings


def _finding(
    file: str,
    path: str,
    message: str,
    remediation: str,
) -> Finding:
    return {
        "check": "schema",
        "severity": "error",
        "file": file,
        "record": path,
        "message": f"{path}: {message}",
        "remediation": remediation,
    }


def _display(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _read_text(path: Path, *, maximum: int = MAX_YAML_BYTES) -> str:
    try:
        size = path.stat().st_size
    except OSError as error:
        raise ContractError("file is missing or unreadable") from error
    if size > maximum:
        raise ContractError(f"file exceeds the {maximum}-byte safety limit")
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ContractError("file is unreadable or is not valid UTF-8") from error


def _load_yaml(text: str) -> object:
    return yaml.load(text, Loader=UniqueKeyLoader)


def _key_path(path: str, key: object) -> str:
    if isinstance(key, str) and re.fullmatch(r"[a-z][a-z0-9-]*", key):
        return f"{path}.{key}" if path else key
    return f"{path}[{key!r}]" if path else f"[{key!r}]"


def _recursive_alias_path(value: object, root_path: str) -> str | None:
    """Return the first recursive container path without recursively walking."""

    active: set[int] = set()
    stack: list[tuple[object, str, bool]] = [(value, root_path, False)]
    while stack:
        current, path, leaving = stack.pop()
        if not isinstance(current, (dict, list)):
            continue
        identity = id(current)
        if leaving:
            active.remove(identity)
            continue
        if identity in active:
            return path
        active.add(identity)
        stack.append((current, path, True))
        if isinstance(current, dict):
            children = [
                (child, _key_path(path, key), False)
                for key, child in sorted(
                    current.items(),
                    key=lambda item: str(item[0]),
                    reverse=True,
                )
            ]
        else:
            children = [
                (child, f"{path}[{index}]", False)
                for index, child in reversed(list(enumerate(current)))
            ]
        stack.extend(children)
    return None


def load_contract(repository_root: PathValue) -> dict[str, object]:
    """Load the normative contract embedded in backlog-management."""

    root = Path(repository_root).resolve()
    skill_path = root / SKILL_PATH
    if not _is_contained_file(skill_path, root):
        raise ContractError("schema contract is not a regular repository file")
    text = _read_text(skill_path)
    try:
        start = text.index(CONTRACT_START) + len(CONTRACT_START)
        end = text.index(CONTRACT_END, start)
    except ValueError as error:
        raise ContractError("schema contract markers are missing or out of order") from error
    region = text[start:end].strip()
    match = re.fullmatch(r"```yaml\s*\n(.*)\n```", region, re.DOTALL)
    if match is None:
        raise ContractError("schema contract must be one fenced yaml block")
    try:
        loaded = _load_yaml(match.group(1))
    except (yaml.YAMLError, RecursionError) as error:
        raise ContractError("schema contract contains malformed YAML") from error
    recursive_path = _recursive_alias_path(loaded, "schema-contract")
    if recursive_path is not None:
        raise ContractError(
            f"schema contract contains a recursive YAML alias at {recursive_path}"
        )
    if not isinstance(loaded, dict):
        raise ContractError("schema contract root must be a mapping")
    if loaded.get("contract-version") != 1:
        raise ContractError("schema contract-version must be 1")
    if not isinstance(loaded.get("status-vocabulary"), dict):
        raise ContractError("schema contract requires status-vocabulary")
    if not isinstance(loaded.get("schemas"), dict):
        raise ContractError("schema contract requires schemas")
    story_v2 = loaded["schemas"].get("story-v2")
    if (
        not isinstance(story_v2, dict)
        or story_v2.get("cross-field") != "story-confidence"
    ):
        raise ContractError(
            "schema contract story-v2.cross-field must be exactly story-confidence"
        )
    try:
        confidence = story_v2["properties"]["confidence"]
        legacy_enum = confidence["legacy-enum"]
        legacy_records = confidence["legacy-records"]
    except (KeyError, TypeError) as error:
        raise ContractError(
            "schema contract requires the pinned legacy confidence migration"
        ) from error
    expected_records = tuple(record[0] for record in LEGACY_CONFIDENCE_MIGRATION)
    if legacy_enum != ["high", "medium", "low"]:
        raise ContractError(
            "legacy confidence vocabulary must remain exactly high, medium, low"
        )
    if (
        not isinstance(legacy_records, list)
        or tuple(legacy_records) != expected_records
    ):
        raise ContractError(
            "legacy confidence records do not match the immutable migration cohort"
        )
    return loaded


class SchemaValidator:
    """Small deterministic validator for the skill's declarative schema."""

    def __init__(
        self,
        contract: Mapping[str, object],
        *,
        repository_root: Path,
        file: str,
    ) -> None:
        self.contract = contract
        self.repository_root = repository_root
        self.file = file
        self.findings: list[Finding] = []
        self._active_containers: set[int] = set()

    def add(self, path: str, message: str, remediation: str) -> None:
        self.findings.append(_finding(self.file, path, message, remediation))

    def validate(self, value: object, schema_name: str, path: str) -> None:
        schemas = self.contract["schemas"]
        if not isinstance(schemas, Mapping) or schema_name not in schemas:
            raise ContractError(f"schema definition {schema_name!r} is missing")
        schema = schemas[schema_name]
        if not isinstance(schema, Mapping):
            raise ContractError(f"schema definition {schema_name!r} must be a mapping")
        self._validate(value, schema, path)

    def _validate(
        self,
        value: object,
        schema: Mapping[str, object],
        path: str,
    ) -> None:
        reference = schema.get("$ref")
        if reference is not None:
            if not isinstance(reference, str):
                raise ContractError("$ref values must be strings")
            self.validate(value, reference, path)
            return

        expected = schema.get("type")
        if not self._matches_type(value, expected):
            self.add(
                path,
                f"expected {self._type_label(expected)}, got {self._actual_type(value)}",
                f"Set {path} to a value of type {self._type_label(expected)}.",
            )
            return

        if isinstance(value, (dict, list)):
            identity = id(value)
            if identity in self._active_containers:
                self.add(
                    path,
                    "recursive YAML aliases are not allowed",
                    f"Replace the alias at {path} with ordinary YAML data.",
                )
                return
            self._active_containers.add(identity)
            try:
                if isinstance(value, dict):
                    self._mapping(value, schema, path)
                else:
                    self._sequence(value, schema, path)
            finally:
                self._active_containers.remove(identity)
        else:
            self._scalar(value, schema, path)

    def _mapping(
        self,
        value: dict[object, object],
        schema: Mapping[str, object],
        path: str,
    ) -> None:
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        optional = schema.get("optional", [])
        if not isinstance(properties, Mapping):
            raise ContractError(f"{path} schema properties must be a mapping")
        if not self._string_list(required) or not self._string_list(optional):
            raise ContractError(f"{path} schema required/optional keys must be lists")

        for key in sorted(required):
            if key not in value:
                self.add(
                    f"{path}.{key}",
                    "required key is missing",
                    f"Add the required `{key}` key at {path}.",
                )

        known = set(properties)
        for key in sorted(value, key=lambda item: str(item)):
            key_path = self._key_path(path, key)
            if not isinstance(key, str):
                self.add(
                    key_path,
                    "mapping keys must be strings",
                    f"Replace the key at {key_path} with a documented string key.",
                )
                continue
            if schema.get("additional-properties") is False and key not in known:
                self.add(
                    key_path,
                    f"unknown key {key!r}",
                    f"Remove `{key}` or add it to the owning skill schema.",
                )
                continue
            child_schema = properties.get(key)
            if child_schema is None:
                continue
            if not isinstance(child_schema, Mapping):
                raise ContractError(f"schema for {key_path} must be a mapping")
            self._validate(value[key], child_schema, key_path)
        self._cross_fields(value, schema, path)

    def _sequence(
        self,
        value: list[object],
        schema: Mapping[str, object],
        path: str,
    ) -> None:
        minimum = schema.get("min-items")
        if isinstance(minimum, int) and len(value) < minimum:
            self.add(
                path,
                f"requires at least {minimum} item(s)",
                f"Add the required item(s) to {path}.",
            )
        if schema.get("unique") is True:
            seen: list[object] = []
            for index, item in enumerate(value):
                if item in seen:
                    self.add(
                        f"{path}[{index}]",
                        f"duplicate list item {item!r}",
                        f"Keep each value in {path} only once.",
                    )
                else:
                    seen.append(item)
        item_schema = schema.get("items")
        if item_schema is not None:
            if not isinstance(item_schema, Mapping):
                raise ContractError(f"{path} items schema must be a mapping")
            for index, item in enumerate(value):
                self._validate(item, item_schema, f"{path}[{index}]")

    def _scalar(
        self,
        value: object,
        schema: Mapping[str, object],
        path: str,
    ) -> None:
        enum = schema.get("enum")
        legacy_enum = schema.get("legacy-enum", [])
        if not isinstance(legacy_enum, list):
            raise ContractError(f"{path} legacy-enum must be a list")
        status = schema.get("status")
        if status is not None:
            enum = self._status_values(status)
        if enum is not None:
            if not isinstance(enum, list):
                raise ContractError(f"{path} enum must be a list")
            if value not in enum and value not in legacy_enum:
                rendered = ", ".join(str(item) for item in enum)
                self.add(
                    path,
                    f"value {value!r} is outside the documented vocabulary [{rendered}]",
                    f"Set {path} to one of: {rendered}.",
                )
                return
        minimum = schema.get("minimum")
        if minimum is not None and isinstance(value, (int, float)):
            if not isinstance(value, bool) and value < minimum:
                self.add(
                    path,
                    f"value must be at least {minimum}",
                    f"Set {path} to {minimum} or greater.",
                )
        min_length = schema.get("min-length")
        if isinstance(min_length, int) and isinstance(value, str):
            if len(value) < min_length:
                self.add(
                    path,
                    "string must not be empty",
                    f"Provide a non-empty value for {path}.",
                )
        format_name = schema.get("format")
        if format_name is not None and value is not None:
            if not isinstance(format_name, str):
                raise ContractError(f"{path} format must be a string")
            self._format(value, format_name, path)

    def _cross_fields(
        self,
        value: Mapping[object, object],
        schema: Mapping[str, object],
        path: str,
    ) -> None:
        rule = schema.get("cross-field")
        if rule is None:
            return
        if rule == "usage-sample":
            self._usage_sample(value, path)
            return
        if rule == "story-confidence":
            properties = schema.get("properties")
            confidence_schema = (
                properties.get("confidence")
                if isinstance(properties, Mapping)
                else None
            )
            legacy = (
                confidence_schema.get("legacy-enum", [])
                if isinstance(confidence_schema, Mapping)
                else []
            )
            legacy_records = (
                confidence_schema.get("legacy-records", [])
                if isinstance(confidence_schema, Mapping)
                else []
            )
            if not isinstance(legacy_records, list):
                raise ContractError(f"{path}.confidence legacy-records must be a list")
            confidence = value.get("confidence")
            if confidence in legacy:
                migration = {
                    identifier: (expected, acceptance)
                    for identifier, expected, acceptance in (
                        LEGACY_CONFIDENCE_MIGRATION
                    )
                }
                expected = migration.get(value.get("id"))
                evidence = value.get("evidence")
                reviews = (
                    evidence.get("review")
                    if isinstance(evidence, Mapping)
                    else None
                )
                accepted = (
                    expected is not None
                    and confidence == expected[0]
                    and value.get("status") == "done"
                    and isinstance(reviews, list)
                    and expected[1] in reviews
                )
                if not accepted:
                    self.add(
                        f"{path}.confidence",
                        (
                            f"legacy confidence {confidence!r} is accepted only "
                            "for its exact completed pre-v2 migration record with "
                            "pinned acceptance evidence"
                        ),
                        (
                            f"Set {path}.confidence to measured, estimated, or "
                            "unknown; do not extend or recreate legacy migration "
                            "records."
                        ),
                    )
            return
        raise ContractError(f"{path} has unknown cross-field rule {rule!r}")

    def _usage_sample(
        self,
        value: Mapping[object, object],
        path: str,
    ) -> None:
        confidence = value.get("confidence")
        actual = {
            "value": value.get("value"),
            "source": value.get("source"),
            "sampled-at": value.get("sampled-at"),
        }
        if confidence == "unknown":
            expected = {"value": None, "source": "none", "sampled-at": None}
            for key in ("value", "source", "sampled-at"):
                if actual[key] != expected[key]:
                    self.add(
                        f"{path}.{key}",
                        (
                            f"unknown usage requires {key}: "
                            f"{expected[key]!r}"
                        ),
                        (
                            f"Set {path} to value: null, confidence: unknown, "
                            "source: none, sampled-at: null."
                        ),
                    )
            return
        if confidence not in {"measured", "estimated"}:
            return
        sample_value = actual["value"]
        if not (
            isinstance(sample_value, (int, float))
            and not isinstance(sample_value, bool)
            and math.isfinite(sample_value)
            and sample_value >= 0
        ):
            self.add(
                f"{path}.value",
                f"{confidence} usage requires a nonnegative numeric value",
                f"Set {path}.value to the actual nonnegative usage sample.",
            )
        source = actual["source"]
        if (
            not isinstance(source, str)
            or not source.strip()
            or source.strip() == "none"
        ):
            self.add(
                f"{path}.source",
                f"{confidence} usage requires a named source other than 'none'",
                f"Set {path}.source to the adapter or telemetry source name.",
            )
        sampled_at = actual["sampled-at"]
        if not isinstance(sampled_at, str) or not self._is_iso8601(sampled_at):
            self.add(
                f"{path}.sampled-at",
                f"{confidence} usage requires an ISO-8601 timestamp with an offset",
                f"Set {path}.sampled-at to the sample time including its UTC offset.",
            )

    def _status_values(self, dotted: object) -> list[object]:
        if not isinstance(dotted, str) or "." not in dotted:
            raise ContractError("status references must have '<version>.<level>' form")
        version, level = dotted.split(".", 1)
        vocabulary = self.contract["status-vocabulary"]
        try:
            values = vocabulary[version][level]  # type: ignore[index]
        except (KeyError, TypeError) as error:
            raise ContractError(f"status vocabulary {dotted!r} is missing") from error
        if not isinstance(values, list):
            raise ContractError(f"status vocabulary {dotted!r} must be a list")
        return values

    def _format(self, value: object, format_name: str, path: str) -> None:
        valid = True
        label = format_name
        if not isinstance(value, str):
            return
        if format_name == "theme-id":
            valid = THEME_ID.fullmatch(value) is not None
        elif format_name == "epic-id":
            valid = EPIC_ID.fullmatch(value) is not None
        elif format_name == "v1-epic-id":
            valid = V1_EPIC_ID.fullmatch(value) is not None
        elif format_name == "story-id":
            valid = STORY_ID.fullmatch(value) is not None
        elif format_name == "repository-path":
            valid = self._is_repository_path(value)
        elif format_name == "iso-8601":
            valid = self._is_iso8601(value)
        else:
            raise ContractError(f"unknown schema format {format_name!r}")
        if not valid:
            self.add(
                path,
                f"value {value!r} is not a valid {label}",
                f"Replace {path} with a valid {label} value.",
            )

    @staticmethod
    def _is_repository_path(value: str) -> bool:
        path = Path(value)
        return bool(value) and not path.is_absolute() and ".." not in path.parts

    @staticmethod
    def _is_iso8601(value: str) -> bool:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return False
        return parsed.tzinfo is not None

    @staticmethod
    def _matches_type(value: object, expected: object) -> bool:
        choices = expected if isinstance(expected, list) else [expected]
        return any(SchemaValidator._matches_one(value, item) for item in choices)

    @staticmethod
    def _matches_one(value: object, expected: object) -> bool:
        return {
            "mapping": lambda: isinstance(value, dict),
            "sequence": lambda: isinstance(value, list),
            "string": lambda: isinstance(value, str),
            "integer": lambda: isinstance(value, int) and not isinstance(value, bool),
            "number": lambda: (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(value)
            ),
            "boolean": lambda: isinstance(value, bool),
            "null": lambda: value is None,
        }.get(expected, lambda: False)()

    @staticmethod
    def _type_label(expected: object) -> str:
        if isinstance(expected, list):
            return " or ".join(str(item) for item in expected)
        return str(expected)

    @staticmethod
    def _actual_type(value: object) -> str:
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, dict):
            return "mapping"
        if isinstance(value, list):
            return "sequence"
        if isinstance(value, str):
            return "string"
        if isinstance(value, int):
            return "integer"
        if isinstance(value, float):
            return "number"
        return type(value).__name__

    @staticmethod
    def _string_list(value: object) -> bool:
        return isinstance(value, list) and all(isinstance(item, str) for item in value)

    @staticmethod
    def _key_path(path: str, key: object) -> str:
        return _key_path(path, key)


def _load_document(
    path: Path,
    *,
    root: Path,
    record: str,
) -> tuple[object | None, list[Finding]]:
    file = _display(path, root)
    try:
        text = _read_text(path)
        document = _load_yaml(text)
    except ContractError as error:
        return None, [
            _finding(
                file,
                record,
                str(error),
                f"Restore {file} as valid, readable YAML.",
            )
        ]
    except (yaml.YAMLError, RecursionError) as error:
        problem = getattr(error, "problem", None) or "malformed YAML"
        mark = getattr(error, "problem_mark", None)
        location = f" at line {mark.line + 1}, column {mark.column + 1}" if mark else ""
        return None, [
            _finding(
                file,
                record,
                f"malformed YAML{location}: {problem}",
                f"Correct the YAML syntax in {file} and retry.",
            )
        ]
    recursive_path = _recursive_alias_path(document, "")
    if recursive_path is not None:
        if recursive_path.startswith("["):
            recursive_path = f"{record}{recursive_path}"
        return None, [
            _finding(
                file,
                recursive_path,
                "recursive YAML aliases are not allowed",
                f"Replace the alias at {recursive_path} with ordinary YAML data.",
            )
        ]
    return document, []


def _is_contained_file(path: Path, root: Path) -> bool:
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(root)
        return resolved.is_file()
    except (OSError, RuntimeError, ValueError):
        return False


def _resolved_archive_path(root: Path, reference: object) -> Path | None:
    """Resolve a snapshot only within the repository's canonical archive root."""

    if not isinstance(reference, str) or not SchemaValidator._is_repository_path(
        reference
    ):
        return None
    try:
        archive_root = (root / ARCHIVE_DIRECTORY).resolve(strict=True)
        archive_root.relative_to(root)
        if not archive_root.is_dir():
            return None
        resolved = (root / reference).resolve(strict=True)
        resolved.relative_to(archive_root)
        if not resolved.is_file():
            return None
    except (OSError, RuntimeError, ValueError):
        return None
    return resolved


def _version_for_theme(theme: Mapping[object, object], *, archived: bool) -> int | None:
    version = theme.get("schema-version")
    if version == 2:
        return 2
    if version == 1:
        return 1 if archived or theme.get("locked") is True else None
    if version is None and (archived or theme.get("locked") is True):
        return 1
    return None


def _validate_v2_archive_state(
    validator: SchemaValidator,
    theme: Mapping[object, object],
    path: str,
) -> None:
    if theme.get("locked") is not True:
        validator.add(
            f"{path}.locked",
            "version 2 archived theme must declare locked: true",
            f"Set {path}.locked to true before archiving the theme.",
        )
    if theme.get("status") != "done":
        validator.add(
            f"{path}.status",
            "version 2 archived theme must have status: done",
            f"Set {path}.status to done before archiving the theme.",
        )


def _validate_theme_identity(
    validator: SchemaValidator,
    theme: object,
    path: str,
    *,
    archived: bool,
) -> int | None:
    if not isinstance(theme, dict):
        validator.add(
            path,
            "theme must be a mapping",
            f"Replace {path} with a documented theme mapping.",
        )
        return None
    version = _version_for_theme(theme, archived=archived)
    if version is None:
        validator.add(
            f"{path}.schema-version",
            "new or unlocked theme requires schema-version: 2",
            f"Set {path}.schema-version to 2 and add every required v2 block.",
        )
        return None
    validator.validate(theme, f"theme-v{version}", path)
    return version


def _iter_entities(
    themes: Sequence[object],
    *,
    path_prefix: str = "backlog.active-themes",
) -> tuple[list[tuple[str, Mapping[object, object], str]], ...]:
    theme_items: list[tuple[str, Mapping[object, object], str]] = []
    epic_items: list[tuple[str, Mapping[object, object], str]] = []
    story_items: list[tuple[str, Mapping[object, object], str]] = []
    for ti, theme in enumerate(themes):
        theme_path = path_prefix if path_prefix == "theme" else f"{path_prefix}[{ti}]"
        if not isinstance(theme, Mapping):
            continue
        if isinstance(theme.get("id"), str):
            theme_items.append((theme["id"], theme, theme_path))
        epics = theme.get("epics")
        if not isinstance(epics, list):
            continue
        for ei, epic in enumerate(epics):
            epic_path = f"{theme_path}.epics[{ei}]"
            if not isinstance(epic, Mapping):
                continue
            if isinstance(epic.get("id"), str):
                epic_id = epic["id"]
                normalized = (
                    f"{theme['id']}.{epic_id}"
                    if V1_EPIC_ID.fullmatch(epic_id)
                    and not epic_id.startswith("TH")
                    and isinstance(theme.get("id"), str)
                    else epic_id
                )
                epic_items.append((normalized, epic, epic_path))
            stories = epic.get("stories")
            if not isinstance(stories, list):
                continue
            for si, story in enumerate(stories):
                story_path = f"{epic_path}.stories[{si}]"
                if isinstance(story, Mapping) and isinstance(story.get("id"), str):
                    story_items.append((story["id"], story, story_path))
    return theme_items, epic_items, story_items


def _validate_id_relations(
    validator: SchemaValidator,
    themes: Sequence[object],
    known_entities: tuple[set[str], set[str], set[str]],
    *,
    path_prefix: str = "backlog.active-themes",
    check_cycles: bool,
) -> None:
    theme_items, epic_items, story_items = _iter_entities(
        themes,
        path_prefix=path_prefix,
    )
    _duplicates(validator, theme_items, "theme")
    _duplicates(validator, epic_items, "epic")
    _duplicates(validator, story_items, "story")

    known_themes, known_epics, known_stories = known_entities
    _dependencies(
        validator,
        theme_items,
        known_themes,
        "theme",
        check_cycles=check_cycles,
    )
    _dependencies(
        validator,
        epic_items,
        known_epics,
        "epic",
        check_cycles=check_cycles,
    )
    _dependencies(
        validator,
        story_items,
        known_stories,
        "story",
        check_cycles=check_cycles,
    )

    for theme_id, theme, theme_path in theme_items:
        epics = theme.get("epics")
        if not isinstance(epics, list):
            continue
        for ei, epic in enumerate(epics):
            if not isinstance(epic, Mapping):
                continue
            epic_id = epic.get("id")
            epic_path = f"{theme_path}.epics[{ei}]"
            if isinstance(epic_id, str) and EPIC_ID.fullmatch(epic_id):
                if not epic_id.startswith(f"{theme_id}."):
                    validator.add(
                        f"{epic_path}.id",
                        f"epic ID {epic_id!r} does not belong to {theme_id}",
                        f"Use an epic ID beginning `{theme_id}.E`.",
                    )
            stories = epic.get("stories")
            if not isinstance(stories, list):
                continue
            normalized_epic = (
                epic_id if isinstance(epic_id, str) and epic_id.startswith("TH")
                else f"{theme_id}.{epic_id}"
            )
            for si, story in enumerate(stories):
                if not isinstance(story, Mapping):
                    continue
                story_id = story.get("id")
                if isinstance(story_id, str) and STORY_ID.fullmatch(story_id):
                    if not story_id.startswith(f"{normalized_epic}."):
                        validator.add(
                            f"{epic_path}.stories[{si}].id",
                            f"story ID {story_id!r} does not belong to {normalized_epic}",
                            f"Use a story ID beginning `{normalized_epic}.US`.",
                        )


def _duplicates(
    validator: SchemaValidator,
    items: Sequence[tuple[str, Mapping[object, object], str]],
    kind: str,
) -> None:
    paths: dict[str, list[str]] = {}
    for identifier, _, path in items:
        paths.setdefault(identifier, []).append(path)
    for identifier in sorted(paths):
        if len(paths[identifier]) > 1:
            for path in paths[identifier]:
                validator.add(
                    f"{path}.id",
                    f"duplicate {kind} ID {identifier!r}",
                    f"Keep exactly one entity with ID {identifier}.",
                )


def _dependencies(
    validator: SchemaValidator,
    items: Sequence[tuple[str, Mapping[object, object], str]],
    known: set[str],
    kind: str,
    *,
    check_cycles: bool,
) -> None:
    graph: dict[str, list[str]] = {}
    item_paths: dict[str, str] = {}
    for identifier, item, path in items:
        dependencies = item.get("depends-on")
        if not isinstance(dependencies, list) or not all(
            isinstance(dependency, str) for dependency in dependencies
        ):
            continue
        normalized_dependencies = [
            (
                f"{identifier.split('.', 1)[0]}.{dependency}"
                if kind == "epic"
                and identifier.startswith("TH")
                and V1_EPIC_ID.fullmatch(dependency)
                and not dependency.startswith("TH")
                else dependency
            )
            for dependency in dependencies
        ]
        graph[identifier] = normalized_dependencies
        item_paths[identifier] = path
        for index, (dependency, normalized_dependency) in enumerate(
            zip(dependencies, normalized_dependencies)
        ):
            dependency_path = f"{path}.depends-on[{index}]"
            if normalized_dependency == identifier:
                validator.add(
                    dependency_path,
                    f"{kind} cannot depend on itself",
                    f"Remove {identifier} from its own depends-on list.",
                )
            elif normalized_dependency not in known:
                validator.add(
                    dependency_path,
                    f"dependency {dependency!r} does not resolve to an existing {kind}",
                    f"Reference an existing {kind} ID or remove the dependency.",
                )

    if not check_cycles:
        return
    state: dict[str, int] = {}
    for root in sorted(graph):
        if state.get(root, 0) != 0:
            continue
        state[root] = 1
        active = [root]
        frames: list[tuple[str, Iterator[str]]] = [(root, iter(graph[root]))]
        while frames:
            identifier, dependencies = frames[-1]
            try:
                dependency = next(dependencies)
            except StopIteration:
                state[identifier] = 2
                frames.pop()
                active.pop()
                continue
            if dependency not in graph or dependency == identifier:
                continue
            if state.get(dependency) == 1:
                cycle_start = active.index(dependency)
                cycle = active[cycle_start:] + [dependency]
                validator.add(
                    f"{item_paths[identifier]}.depends-on",
                    f"dependency cycle detected: {' -> '.join(cycle)}",
                    "Remove one dependency edge so the graph is acyclic.",
                )
            elif state.get(dependency, 0) == 0:
                state[dependency] = 1
                active.append(dependency)
                frames.append((dependency, iter(graph[dependency])))


def _validate_story_files(
    validator: SchemaValidator,
    themes: Sequence[object],
    *,
    path_prefix: str = "backlog.active-themes",
) -> None:
    stories: list[tuple[Mapping[object, object], str]] = []
    for theme_index, theme in enumerate(themes):
        theme_path = (
            path_prefix
            if path_prefix == "theme"
            else f"{path_prefix}[{theme_index}]"
        )
        if not isinstance(theme, Mapping) or not isinstance(theme.get("epics"), list):
            continue
        for epic_index, epic in enumerate(theme["epics"]):
            if not isinstance(epic, Mapping) or not isinstance(epic.get("stories"), list):
                continue
            for story_index, story in enumerate(epic["stories"]):
                if isinstance(story, Mapping):
                    stories.append(
                        (
                            story,
                            f"{theme_path}.epics[{epic_index}].stories[{story_index}]",
                        )
                    )
    for story, path in stories:
        value = story.get("file")
        if not isinstance(value, str):
            continue
        if not validator._is_repository_path(value):
            continue
        candidate = validator.repository_root / value
        try:
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(validator.repository_root)
            regular = resolved.is_file()
        except (OSError, RuntimeError, ValueError):
            regular = False
        if not regular:
            validator.add(
                f"{path}.file",
                f"story path {value!r} is missing, not a regular file, or leaves the repository",
                "Set file to an existing regular story path inside the repository.",
            )


def _archive_snapshot(
    root: Path,
    validator: SchemaValidator,
    summary: Mapping[object, object],
    index: int,
    known_entities: tuple[set[str], set[str], set[str]],
) -> list[Finding]:
    reference = summary.get("archive-ref")
    if not isinstance(reference, str) or not validator._is_repository_path(reference):
        return []
    path = _resolved_archive_path(root, reference)
    if path is None:
        display_path = root / reference
        return [
            _finding(
                _display(display_path, root),
                f"backlog.archived-themes[{index}].archive-ref",
                (
                    f"archive path {reference!r} is missing, not a regular file, "
                    f"or is outside {ARCHIVE_DIRECTORY.as_posix()}/"
                ),
                (
                    "Set archive-ref to an existing regular snapshot under "
                    f"{ARCHIVE_DIRECTORY.as_posix()}/."
                ),
            )
        ]
    document, findings = _load_document(
        path,
        root=root,
        record="theme",
    )
    if findings:
        return findings
    file = _display(path, root)
    archive_validator = SchemaValidator(
        validator.contract,
        repository_root=root,
        file=file,
    )
    if not isinstance(document, dict):
        archive_validator.add(
            "theme",
            "archive snapshot root must be a mapping containing `theme`",
            "Wrap the archived theme under one top-level `theme` key.",
        )
        return archive_validator.findings
    if "theme" not in document:
        archive_validator.add(
            "theme",
            "required root key is missing",
            "Add the one top-level `theme` key.",
        )
        return archive_validator.findings
    for key in sorted((key for key in document if key != "theme"), key=str):
        path = SchemaValidator._key_path("", key).lstrip(".")
        archive_validator.add(
            path,
            f"unknown archive root key {key!r}",
            f"Remove {key!r}; an archive snapshot has only the `theme` root key.",
        )
    theme = document["theme"]
    expected_id = summary.get("id")
    snapshot_identity_matches = (
        isinstance(theme, Mapping)
        and isinstance(expected_id, str)
        and theme.get("id") == expected_id
    )
    version = _validate_theme_identity(
        archive_validator,
        theme,
        "theme",
        archived=snapshot_identity_matches,
    )
    if isinstance(theme, Mapping):
        if theme.get("id") != expected_id:
            archive_validator.add(
                "theme.id",
                f"snapshot ID {theme.get('id')!r} does not match archive index ID {expected_id!r}",
                f"Point backlog.archived-themes[{index}].archive-ref to the matching snapshot.",
            )
        _validate_id_relations(
            archive_validator,
            [theme],
            known_entities,
            path_prefix="theme",
            check_cycles=False,
        )
        _validate_story_files(
            archive_validator,
            [theme],
            path_prefix="theme",
        )
        if version == 1 and theme.get("locked") is not True:
            archive_validator.add(
                "theme.locked",
                "version 1 archive snapshot must be locked",
                "Restore the historical snapshot with locked: true.",
            )
        if version == 2:
            _validate_v2_archive_state(archive_validator, theme, "theme")
    return archive_validator.findings


def _repository_dependency_index(
    root: Path,
    active_themes: Sequence[object],
    archived_themes: Sequence[object],
) -> tuple[set[str], set[str], set[str]]:
    """Index normalized IDs in active state and every readable archive snapshot."""

    collections: list[tuple[Sequence[object], str]] = [
        (active_themes, "backlog.active-themes")
    ]
    for summary in archived_themes:
        if not isinstance(summary, Mapping):
            continue
        identifier = summary.get("id")
        reference = summary.get("archive-ref")
        archive_path = _resolved_archive_path(root, reference)
        if archive_path is None:
            continue
        document, findings = _load_document(
            archive_path,
            root=root,
            record="theme",
        )
        if (
            findings
            or not isinstance(document, Mapping)
            or set(document) != {"theme"}
        ):
            continue
        theme = document.get("theme")
        if (
            not isinstance(identifier, str)
            or not isinstance(theme, Mapping)
            or theme.get("id") != identifier
            or theme.get("locked") is not True
        ):
            continue
        version = _version_for_theme(theme, archived=True)
        if version is None or (version == 2 and theme.get("status") != "done"):
            continue
        collections.append(([theme], "theme"))

    known: tuple[set[str], set[str], set[str]] = (set(), set(), set())
    for themes, path_prefix in collections:
        entities = _iter_entities(themes, path_prefix=path_prefix)
        for target, items in zip(known, entities):
            target.update(identifier for identifier, _, _ in items)
    return known


def _validate_archive_index(
    validator: SchemaValidator,
    active_themes: Sequence[object],
    archived_themes: Sequence[object],
) -> None:
    active_ids = {
        theme["id"]
        for theme in active_themes
        if isinstance(theme, Mapping) and isinstance(theme.get("id"), str)
    }
    items = [
        (summary["id"], summary, f"backlog.archived-themes[{index}]")
        for index, summary in enumerate(archived_themes)
        if isinstance(summary, Mapping) and isinstance(summary.get("id"), str)
    ]
    _duplicates(validator, items, "archived theme")
    for identifier, summary, path in items:
        if identifier in active_ids:
            validator.add(
                f"{path}.id",
                f"theme ID {identifier!r} appears in both active and archived themes",
                "Keep a theme in exactly one backlog collection.",
            )
        if summary.get("schema-version") == 2 and summary.get("status") != "done":
            validator.add(
                f"{path}.status",
                "version 2 archived theme must have status: done",
                f"Set {path}.status to done before archiving the theme.",
            )


def _validate_repository(repository_root: PathValue) -> ValidationResult:

    try:
        root = Path(repository_root).resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        return ValidationResult(
            (
                _finding(
                    str(repository_root),
                    "backlog",
                    "repository root is missing or unreadable",
                    "Run the command from a readable repository checkout.",
                ),
            )
        )
    try:
        contract = load_contract(root)
    except ContractError as error:
        return ValidationResult(
            (
                _finding(
                    SKILL_PATH.as_posix(),
                    "schema-contract",
                    str(error),
                    "Restore the machine-readable contract in backlog-management.",
                ),
            )
        )

    backlog_path = root / BACKLOG_PATH
    if not _is_contained_file(backlog_path, root):
        return ValidationResult(
            (
                _finding(
                    BACKLOG_PATH.as_posix(),
                    "backlog",
                    "backlog is missing, not a regular file, or leaves the repository",
                    "Restore docs/plan/backlog.yaml inside the repository.",
                ),
            )
        )
    document, findings = _load_document(
        backlog_path,
        root=root,
        record="backlog",
    )
    if findings:
        return ValidationResult(tuple(findings))
    validator = SchemaValidator(
        contract,
        repository_root=root,
        file=BACKLOG_PATH.as_posix(),
    )
    if not isinstance(document, dict):
        validator.add(
            "backlog",
            "document root must be a mapping containing `backlog`",
            "Wrap the backlog under one top-level `backlog` key and remove siblings.",
        )
        return ValidationResult(tuple(validator.findings))
    if "backlog" not in document:
        validator.add(
            "backlog",
            "required root key is missing",
            "Add the one top-level `backlog` key.",
        )
        return ValidationResult(tuple(validator.findings))
    for key in sorted((key for key in document if key != "backlog"), key=str):
        path = SchemaValidator._key_path("", key).lstrip(".")
        validator.add(
            path,
            f"unknown document root key {key!r}",
            f"Remove {key!r}; backlog.yaml has only the `backlog` root key.",
        )
    backlog = document["backlog"]
    validator.validate(backlog, "backlog-v2", "backlog")
    if not isinstance(backlog, dict):
        return ValidationResult(tuple(validator.findings))

    active = backlog.get("active-themes")
    archived = backlog.get("archived-themes")
    active_themes = active if isinstance(active, list) else []
    archived_themes = archived if isinstance(archived, list) else []
    for index, theme in enumerate(active_themes):
        _validate_theme_identity(
            validator,
            theme,
            f"backlog.active-themes[{index}]",
            archived=False,
        )

    known_entities = _repository_dependency_index(
        root,
        active_themes,
        archived_themes,
    )
    _validate_archive_index(validator, active_themes, archived_themes)
    _validate_id_relations(
        validator,
        active_themes,
        known_entities,
        check_cycles=True,
    )
    _validate_story_files(validator, active_themes)

    for index, summary in enumerate(archived_themes):
        if isinstance(summary, Mapping):
            validator.findings.extend(
                _archive_snapshot(
                    root,
                    validator,
                    summary,
                    index,
                    known_entities,
                )
            )

    ordered = sorted(
        validator.findings,
        key=lambda finding: (
            str(finding["file"]),
            str(finding["record"]),
            str(finding["message"]),
        ),
    )
    return ValidationResult(tuple(ordered))


def validate_repository(repository_root: PathValue) -> ValidationResult:
    """Validate backlog.yaml and its indexed archive snapshots."""

    try:
        return _validate_repository(repository_root)
    except (ContractError, RecursionError, yaml.YAMLError) as error:
        return ValidationResult(
            (
                _finding(
                    SKILL_PATH.as_posix(),
                    "schema-contract",
                    str(error),
                    "Restore the machine-readable contract in backlog-management.",
                ),
            )
        )


__all__ = [
    "BACKLOG_PATH",
    "CONTRACT_END",
    "CONTRACT_START",
    "ContractError",
    "Finding",
    "LEGACY_CONFIDENCE_MIGRATION",
    "SKILL_PATH",
    "SchemaValidator",
    "ValidationResult",
    "load_contract",
    "validate_repository",
]
