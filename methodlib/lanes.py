"""Local delivery evidence, not a product queue or an authorization service."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Mapping, Sequence

from methodlib import backlog, gates


DIRECTORY = "docs/plan/runtime/lanes"
MAX_BYTES = 2 * 1024 * 1024
MAX_FILES = 10000
MAX_RECORDS = 1000
ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
HASH = re.compile(r"sha256:[0-9a-f]{64}")
CONTRACT = Path(__file__).resolve().parents[1] / (
    ".github/skills/the-copilot-build-method/SKILL.md"
)


class LaneFailure(ValueError):
    """An explicit refusal with remediation, rendered by the CLI."""


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise LaneFailure("Expected a JSON object with string keys.")
    return dict(value)


def _text(value: object) -> str:
    if not isinstance(value, str) or not value.strip() or gates.PLACEHOLDER.search(value):
        raise LaneFailure("Expected nonempty, non-placeholder text.")
    return value.strip()


def _strings(value: object, *, empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not value and not empty):
        raise LaneFailure("Expected a nonempty list.")
    result = [_text(item) for item in value]
    if len(set(result)) != len(result):
        raise LaneFailure("Duplicate entries are not permitted.")
    return result


def _unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise LaneFailure(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _json(raw: bytes) -> dict[str, object]:
    if len(raw) > MAX_BYTES:
        raise LaneFailure("Evidence exceeds the bounded read limit.")
    return _object(json.loads(raw, object_pairs_hook=_unique))


def _bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def digest(value: object) -> str:
    return "sha256:" + hashlib.sha256(_bytes(value)).hexdigest()


def contract() -> dict[str, list[str]]:
    text = CONTRACT.read_text(encoding="utf-8")
    match = re.search(
        r"<!-- delivery-lanes-contract:start -->\s*```json\s*(.*?)\s*```",
        text, re.DOTALL,
    )
    if match is None:
        raise LaneFailure("Packaged canonical lane contract is missing.")
    return {key: _strings(value) for key, value in _json(match[1].encode()).items()}


def _path(root: Path, relative: str) -> Path:
    path = PurePosixPath(relative)
    if (
        path.is_absolute() or str(path) != relative
        or any(part in {"..", ".", ".git"} for part in path.parts)
        or not path.parts or "\\" in relative
    ):
        raise LaneFailure(f"Unsafe or broad repository path: {relative}")
    target = root
    for part in path.parts:
        target = target / part
        if target.is_symlink():
            raise LaneFailure(f"Symlinks are not permitted: {relative}")
    return target


def _under(path: str, scope: str) -> bool:
    return path == scope or path.startswith(scope + "/")


def _overlap(left: str, right: str) -> bool:
    return _under(left, right) or _under(right, left)


def _file_hash(root: Path, relative: str) -> str:
    path = _path(root, relative)
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise LaneFailure(f"Missing, non-regular or oversized evidence file: {relative}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True)
class Brief:
    task: str
    owner: str
    outcome: str
    scope: list[str]
    acceptance: list[str]
    checks: list[str]
    kind: str
    design: str
    certainty: str
    risk: str
    non_goals: list[str] = field(default_factory=list)
    integration_checks: list[str] = field(default_factory=list)
    design_evidence: list[str] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)
    review_profile: str = "standard"
    substantial: bool = False
    multi_session: bool = False
    admitted_item: str | None = None
    verification_outputs: list[str] = field(default_factory=list)

    @classmethod
    def parse(cls, data: Mapping[str, object]) -> Brief:
        required = {
            "task", "owner", "outcome", "scope", "acceptance", "checks",
            "kind", "design", "certainty", "risk",
        }
        optional = {
            "non_goals", "integration_checks", "design_evidence", "triggers",
            "review_profile", "substantial", "multi_session", "admitted_item",
            "verification_outputs",
        }
        if not required <= data.keys() or data.keys() - required - optional:
            raise LaneFailure("Brief fields are missing or unknown; use the canonical brief format.")
        values = contract()
        texts = {key: _text(data[key]) for key in required - {"scope", "acceptance", "checks"}}
        for key, vocabulary in (
            ("kind", "kinds"), ("design", "designs"), ("certainty", "certainty"), ("risk", "risks"),
        ):
            if texts[key] not in values[vocabulary]:
                raise LaneFailure(f"Unknown {key}: {texts[key]}")
        profile = _text(data.get("review_profile", "standard"))
        triggers = _strings(data.get("triggers", []), empty=True)
        if profile not in values["profiles"] or set(triggers) - set(values["governed-triggers"]):
            raise LaneFailure("Unknown review profile or consequential trigger.")
        for key in ("substantial", "multi_session"):
            if not isinstance(data.get(key, False), bool):
                raise LaneFailure(f"{key} must be a boolean.")
        brief = cls(
            **texts,
            scope=_strings(data["scope"]), acceptance=_strings(data["acceptance"]),
            checks=_strings(data["checks"]),
            non_goals=_strings(data.get("non_goals", []), empty=True),
            integration_checks=_strings(data.get("integration_checks", []), empty=True),
            design_evidence=_strings(data.get("design_evidence", []), empty=True),
            triggers=triggers, review_profile=profile,
            substantial=data.get("substantial", False) is True,
            multi_session=data.get("multi_session", False) is True,
            admitted_item=None if data.get("admitted_item") is None else _text(data["admitted_item"]),
            verification_outputs=_strings(data.get("verification_outputs", []), empty=True),
        )
        if not ID.fullmatch(brief.task):
            raise LaneFailure("Task must be a bounded lowercase hyphenated identifier.")
        if set(brief.checks) & set(brief.integration_checks):
            raise LaneFailure("Targeted and integration check names must be distinct.")
        return brief


def classify(brief: Brief, floor: str = "Direct") -> tuple[str, list[str], list[str]]:
    rules = contract()
    reasons = list(brief.triggers)
    if brief.admitted_item:
        reasons.append("existing-admitted-contract")
    if brief.design == "new":
        reasons.append("new-product-or-design-decision")
    if brief.risk == "R3":
        reasons.append("R3")
    if any(_overlap(path, guarded) for path in brief.scope for guarded in rules["governed-paths"]):
        reasons.append("formal-product-or-planning-scope")
    if any(_overlap(path, guarded) for path in brief.scope for guarded in rules["enforcement-paths"]):
        reasons.append("method-enforcement-scope")
    lane = "Governed" if reasons else "Direct"
    if not reasons and (
        brief.kind not in rules["maintenance"] or brief.substantial
        or brief.multi_session or brief.risk == "R2"
    ):
        lane = "Managed"
        reasons.append("substantial-feature-multi-session-or-R2")
    lane = rules["lanes"][max(rules["lanes"].index(lane), rules["lanes"].index(floor))]
    blockers = []
    if brief.design == "unknown" or brief.certainty != "clear":
        blockers.append("Clarify design and scope/risk uncertainty before execution.")
    if lane == "Managed":
        if not brief.non_goals or not brief.integration_checks or not brief.design_evidence:
            blockers.append("Managed requires non-goals, integration checks and existing design evidence.")
    if lane == "Governed":
        blockers.append("Use explicit human authority and applicable lifecycle admission/mission packets; this record grants no packet authority.")
    return lane, reasons, blockers


def assess(brief: Brief, requested: str | None = None) -> dict[str, object]:
    lane, reasons, blockers = classify(brief)
    if requested is not None:
        if requested not in contract()["lanes"]:
            raise LaneFailure("Unknown requested lane; use the canonical vocabulary.")
        if contract()["lanes"].index(requested) < contract()["lanes"].index(lane):
            blockers.append("Requested lane would downgrade required controls.")
        else:
            lane, reasons, extra = classify(brief, requested)
            blockers = list(dict.fromkeys([*blockers, *extra]))
    return {
        "lane": lane, "reasons": reasons, "blockers": blockers,
        "brief_revision": digest(asdict(brief)),
        "route": "packet" if lane == "Governed" else "local",
        "execution": "closed" if blockers else "eligible",
        "authorized_external_operations": [],
    }


def _checkout_root(root: Path) -> None:
    repository = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10,
    )
    if Path(os.fsdecode(repository.stdout).strip()).resolve() != root:
        raise LaneFailure("Lane execution must name the Git checkout root, not a subtree that hides product authority.")


def _snapshot(root: Path, brief: Brief) -> dict[str, str]:
    paths: set[str] = set()
    for directory, directories, files in os.walk(root, followlinks=False):
        for name in list(directories):
            item = (Path(directory) / name).relative_to(root).as_posix()
            if item == ".git" or _under(item, DIRECTORY) or any(
                _under(item, output) for output in brief.verification_outputs
            ):
                directories.remove(name)
            else:
                _path(root, item)
        for name in files:
            item = (Path(directory) / name).relative_to(root).as_posix()
            if item == ".git" or _under(item, DIRECTORY) or any(
                _under(item, output) for output in brief.verification_outputs
            ):
                continue
            paths.add(item)
            if len(paths) > MAX_FILES:
                raise LaneFailure("Repository inventory exceeds the bounded lane limit; use packets.")
    if len(paths) > MAX_FILES:
        raise LaneFailure("Repository inventory exceeds the bounded lane limit; use packets.")
    snapshot: dict[str, str] = {}
    for relative in sorted(paths):
        if _under(relative, DIRECTORY):
            continue
        path = _path(root, relative)
        if path.exists():
            snapshot[relative] = f"{path.stat().st_mode & 0o777}:{_file_hash(root, relative)}"
        else:
            snapshot[relative] = "deleted"
    return snapshot


def _evidence(root: Path, brief: Brief) -> dict[str, str]:
    for relative in brief.scope:
        _path(root, relative)
        if _overlap(relative, DIRECTORY):
            raise LaneFailure("Working evidence cannot be implementation scope.")
    if any(_overlap(path, evidence) for path in brief.scope for evidence in brief.design_evidence):
        raise LaneFailure("Accepted design evidence is read-only; scope cannot overlap it.")
    guarded = [
        *brief.scope, *brief.design_evidence, *contract()["governed-paths"],
        *contract()["enforcement-paths"], DIRECTORY,
    ]
    for output in brief.verification_outputs:
        _path(root, output)
        if any(_overlap(output, path) for path in guarded):
            raise LaneFailure("Verification output grants cannot overlap implementation, accepted evidence or control paths.")
    return {path: _file_hash(root, path) for path in brief.design_evidence}


def _product_context(root: Path) -> None:
    path = _path(root, backlog.BACKLOG_PATH.as_posix())
    if not path.exists():
        return
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise LaneFailure("Cannot establish existing product authority from the backlog.")
    document = _object(backlog.yaml.load(path.read_text(encoding="utf-8"), Loader=backlog.UniqueKeyLoader))
    state = _object(document.get("backlog"))
    themes = state.get("active-themes")
    if not isinstance(themes, list):
        raise LaneFailure("Cannot establish existing product authority from the backlog.")
    for value in themes:
        theme = _object(value)
        if theme.get("status") != "done":
            raise LaneFailure("Unfinished product backlog work exists; use its packet/admission route, not an unproven lighter reassignment.")


def _load(root: Path, task: str, expected: str) -> dict[str, object]:
    if not ID.fullmatch(task) or not HASH.fullmatch(expected):
        raise LaneFailure("Task or retained revision is invalid.")
    record = _json(_path(root, f"{DIRECTORY}/{task}.json").read_bytes())
    if digest(record) != expected:
        raise LaneFailure("Working record is stale or modified; recover the retained revision, never silently re-anchor.")
    brief = Brief.parse(_object(record["brief"]))
    if (
        record["version"] != 1 or brief.task != task or record["lane"] not in contract()["lanes"]
        or record["status"] not in {"active", "paused", "complete"}
    ):
        raise LaneFailure("Unknown working record version, task or lane.")
    lane, _reasons, _blockers = classify(brief, _text(record["lane"]))
    if record["lane"] != lane:
        raise LaneFailure("Record lane contradicts the brief's mandatory controls.")
    return record


def _save(root: Path, task: str, record: dict[str, object]) -> dict[str, object]:
    destination = _path(root, f"{DIRECTORY}/{task}.json")
    raw = _bytes(record)
    if len(raw) > MAX_BYTES:
        raise LaneFailure("Working evidence exceeds the bounded limit.")
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as output:
        temporary = Path(output.name)
        try:
            output.write(raw)
            output.flush()
            os.fsync(output.fileno())
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
    directory_fd = os.open(destination.parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    return _payload(task, record)


def _payload(task: str, record: Mapping[str, object]) -> dict[str, object]:
    return {
        "task": task, "lane": record["lane"], "status": record["status"],
        "record": f"{DIRECTORY}/{task}.json", "revision": digest(record),
        "route": "packet" if record["lane"] == "Governed" else "local",
        "next_action": record["next_action"],
        "implementation_complete": record["status"] == "complete",
        "release_readiness": "not-assessed", "product_acceptance": "not-granted",
        "production_activation": "not-authorized", "authorized_external_operations": [],
    }


def _content(snapshot: Mapping[str, str], brief: Brief) -> str:
    return digest({path: value for path, value in snapshot.items() if any(_under(path, scope) for scope in brief.scope)})


def _guard(root: Path, record: Mapping[str, object], brief: Brief) -> dict[str, str]:
    _product_context(root)
    current = _snapshot(root, brief)
    baseline = _object(record["baseline"])
    changed = [
        path for path in baseline.keys() | current.keys()
        if baseline.get(path) != current.get(path) and not any(_under(path, scope) for scope in brief.scope)
    ]
    if changed:
        raise LaneFailure("Out-of-scope files changed: " + ", ".join(sorted(changed)))
    if _evidence(root, brief) != record["design_evidence"]:
        raise LaneFailure("Existing design evidence changed; pause for applicable product/design gates.")
    return current


def _blocked(record: dict[str, object], reason: str, *, refusal: bool = False) -> None:
    record.update(status="paused", next_action=reason)
    if refusal:
        record["authority_refused"] = True
        record["lane"] = "Governed"


def execute(
    root: Path, action: str, *, brief: Brief | None = None,
    task: str | None = None, expected: str | None = None, owner: str | None = None,
    requested: str | None = None, name: str | None = None,
    argv: Sequence[str] = (), covered: Sequence[str] = (),
    report: str | None = None, reviewer: str | None = None,
    independent: bool = False, verdict: str | None = None,
    reason: str | None = None, authority_refused: bool = False,
    gitflow: str | None = None,
    repair: bool = False,
) -> tuple[dict[str, object], bool]:
    root = root.resolve(strict=True)
    _checkout_root(root)
    if action == "assess":
        if brief is None:
            raise LaneFailure("Assess requires a brief.")
        _evidence(root, brief)
        _product_context(root)
        payload = assess(brief, requested)
        return payload, payload["execution"] == "closed"
    directory = _path(root, DIRECTORY)
    directory.mkdir(parents=True, exist_ok=True)
    mutex = directory / ".lock"
    try:
        fd = os.open(mutex, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as error:
        raise LaneFailure("Lane evidence is locked by another writer; inspect/recover its owner before retrying.") from error
    try:
        os.close(fd)
        if action == "start":
            if brief is None:
                raise LaneFailure("Start requires a brief.")
            task = brief.task
            target = _path(root, f"{DIRECTORY}/{task}.json")
            if target.exists():
                raise LaneFailure("Task already has evidence; resume/amend it, never overwrite.")
            others = sorted(directory.glob("*.json"))
            if len(others) >= MAX_RECORDS:
                raise LaneFailure("Too many working records; use the existing record or packets.")
            for path in others:
                other = _json(_path(root, path.relative_to(root).as_posix()).read_bytes())
                other_brief = Brief.parse(_object(other["brief"]))
                if other["status"] != "complete" and any(
                    _overlap(left, right) for left in brief.scope for right in other_brief.scope
                ):
                    raise LaneFailure("Overlapping unfinished/refused work exists; resume its evidence instead of resetting authority.")
            selection = assess(brief, requested)
            blockers = _strings(selection["blockers"], empty=True)
            evidence = _evidence(root, brief)
            _product_context(root)
            record = {
                "version": 1, "brief": asdict(brief), "lane": selection["lane"],
                "status": "paused" if blockers else "active",
                "next_action": "; ".join(blockers) or "Implement within scope; run declared checks.",
                "baseline": _snapshot(root, brief), "design_evidence": evidence,
                "runs": {}, "review": None, "repair_failures": 0, "authority_refused": False,
                "history": [],
            }
        else:
            if task is None or expected is None:
                raise LaneFailure("A task and caller-retained --expected-revision are required.")
            record = _load(root, task, expected)
            revised = brief
            old = Brief.parse(_object(record["brief"]))
            if owner != old.owner:
                raise LaneFailure("Retained owner mismatch; obtain explicit human disposition instead of silently replacing the owner.")
            brief = old
            if record["status"] == "complete":
                if action != "preflight":
                    raise LaneFailure("Completed evidence is immutable; start a genuinely new task.")
            if action == "pause":
                _blocked(record, _text(reason), refusal=authority_refused)
            elif action == "amend":
                if revised is None or revised.task != task or revised.owner != old.owner:
                    raise LaneFailure("Amend requires the same task and retained owner.")
                if set(old.triggers) - set(revised.triggers):
                    raise LaneFailure("Consequential triggers cannot be removed to evade controls.")
                if set(old.design_evidence) - set(revised.design_evidence):
                    raise LaneFailure("Accepted design evidence cannot be removed by amendment.")
                if _evidence(root, old) != record["design_evidence"]:
                    raise LaneFailure("Accepted design evidence changed; use human product/design gates.")
                if revised.verification_outputs != old.verification_outputs:
                    raise LaneFailure("Output grants cannot be expanded during repair to hide changed files.")
                if not all(any(_under(path, scope) for scope in revised.scope) for path in old.scope):
                    raise LaneFailure("Amend cannot shed previously authorized scope; preserve history.")
                lane, _reasons, blockers = classify(revised, _text(record["lane"]))
                evidence = _evidence(root, revised)
                _guard(root, {**record, "design_evidence": evidence}, revised)
                record.update(
                    brief=asdict(revised), lane=lane, design_evidence=evidence,
                    runs={}, review=None,
                )
                _blocked(record, "; ".join(blockers) or "Brief changed; reassess scope and explicitly resume before work.")
                history = record["history"]
                if not isinstance(history, list):
                    raise LaneFailure("Invalid working history.")
                history.append({"prior_brief": asdict(old)})
            elif action == "resume":
                _guard(root, record, old)
                _lane, _reasons, blockers = classify(old, _text(record["lane"]))
                if record["authority_refused"]:
                    blockers.append("Authority was refused; use human disposition and the governed route.")
                if blockers:
                    _blocked(record, "; ".join(blockers))
                else:
                    record.update(status="active", next_action="Continue within the retained scope.")
            else:
                if record["status"] == "paused" or record["lane"] == "Governed":
                    raise LaneFailure("Execution is paused; do not bypass scope, authority or packet gates.")
                try:
                    snapshot = _guard(root, record, old)
                except LaneFailure as error:
                    if record["status"] == "complete":
                        raise
                    _blocked(record, str(error))
                    return _save(root, task, record), True
                content = _content(snapshot, old)
                if action == "check":
                    if name not in old.checks + old.integration_checks or not argv:
                        raise LaneFailure("Supply a declared check name and explicit command after --.")
                    valid_criteria = {f"AC{number}" for number in range(1, len(old.acceptance) + 1)}
                    if not covered or set(covered) - valid_criteria:
                        raise LaneFailure("Check must name valid --covered acceptance criterion IDs.")
                    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
                        try:
                            result = subprocess.run(list(argv), cwd=root, stdout=stdout, stderr=stderr, timeout=300)
                            code = result.returncode
                        except subprocess.TimeoutExpired:
                            code = 124
                        stdout.seek(0)
                        stderr.seek(0)
                        output_hashes = []
                        for stream in (stdout, stderr):
                            hasher = hashlib.sha256()
                            for chunk in iter(lambda: stream.read(65536), b""):
                                hasher.update(chunk)
                            output_hashes.append(hasher.hexdigest())
                    runs = _object(record["runs"])
                    runs[name] = {
                        "command": list(argv), "exit_code": code, "covered": list(covered),
                        "content": content, "output_hashes": output_hashes,
                    }
                    record["runs"] = runs
                    record["review"] = None
                    try:
                        after = _guard(root, record, old)
                    except LaneFailure as error:
                        _blocked(record, str(error))
                        return _save(root, task, record), True
                    if _content(after, old) != content:
                        _blocked(record, "Verification changed implementation; rerun checks against the delivered revision.")
                    elif code != 0:
                        record["next_action"] = f"Check {name} failed with exit {code}; diagnose and repair."
                        if repair:
                            failures = record["repair_failures"]
                            if not isinstance(failures, int):
                                raise LaneFailure("Invalid repair evidence.")
                            record["repair_failures"] = failures + 1
                            if failures + 1 >= 2:
                                _blocked(record, "Two unsuccessful owner repairs; obtain specialist/human disposition.")
                                record["lane"] = "Governed"
                elif action == "review":
                    _verified(record, old, content)
                    if not report or not reviewer or verdict not in {"approved", "request-changes"}:
                        raise LaneFailure("Review requires real report, actor and explicit verdict.")
                    requires_independent = old.risk in {"R2", "R3"} or old.review_profile != "standard"
                    if requires_independent and not independent:
                        raise LaneFailure("This risk/profile requires actual independent review.")
                    if independent == (reviewer == old.owner):
                        raise LaneFailure("Self-review must name the owner; independent review must name a different actor.")
                    record["review"] = {
                        "report": report, "sha256": _file_hash(root, report),
                        "actor": reviewer, "independent": independent,
                        "verdict": verdict, "content": content,
                    }
                    if verdict == "request-changes":
                        _blocked(record, "Required review refused; return to owner for bounded repair.")
                elif action == "complete":
                    _verified(record, old, content)
                    _approved(root, record, old, content)
                    delivery = _text(gitflow)
                    if delivery.startswith("not-applicable:"):
                        _text(delivery.removeprefix("not-applicable:"))
                        record["gitflow"] = {"not_applicable": delivery}
                    else:
                        record["gitflow"] = {"report": delivery, "sha256": _file_hash(root, delivery)}
                    record.update(status="complete", next_action="Implementation complete only; other boundaries require separate evidence/authority.")
                elif action != "preflight":
                    raise LaneFailure(f"Unknown lane action: {action}")
                elif record["status"] == "complete":
                    _verified(record, old, content)
                    _approved(root, record, old, content)
                    return _payload(task, record), False
        if task is None:
            raise LaneFailure("Task is required.")
        history = record["history"]
        if not isinstance(history, list):
            raise LaneFailure("Invalid working history.")
        history.append({"action": action, "at": datetime.now().astimezone().isoformat(), "owner": owner or brief.owner})
        payload = _save(root, task, record)
        failed_check = action == "check" and _object(_object(record["runs"])[_text(name)]).get("exit_code") != 0
        return payload, record["status"] == "paused" or failed_check
    finally:
        mutex.unlink()


def _verified(record: Mapping[str, object], brief: Brief, content: str) -> None:
    runs = _object(record["runs"])
    coverage: set[str] = set()
    for check in brief.checks + brief.integration_checks:
        run = _object(runs.get(check))
        if run.get("exit_code") != 0 or run.get("content") != content:
            raise LaneFailure(f"Missing, failing or stale verification: {check}")
        coverage.update(_strings(run.get("covered")))
    if coverage != {f"AC{number}" for number in range(1, len(brief.acceptance) + 1)}:
        raise LaneFailure("Acceptance coverage is incomplete.")


def _approved(root: Path, record: Mapping[str, object], brief: Brief, content: str) -> None:
    review = _object(record["review"])
    if (
        review.get("verdict") != "approved" or review.get("content") != content
        or review.get("sha256") != _file_hash(root, _text(review.get("report")))
        or (brief.risk in {"R2", "R3"} or brief.review_profile != "standard")
        and review.get("independent") is not True
    ):
        raise LaneFailure("Actual approved review evidence is missing, changed or stale.")
