"""Argument surface for risk-scaled local delivery."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable

from methodlib import lanes


def configure(
    subcommands: argparse._SubParsersAction,
    parser_class: type[argparse.ArgumentParser],
    handler: Callable,
) -> None:
    parser = subcommands.add_parser("lane", help="assess, execute and resume risk-scaled delivery")
    parser.add_argument("--repo", dest="lane_repo", type=Path, help="target Git checkout; defaults to current directory")
    actions = parser.add_subparsers(dest="lane_action", required=True, parser_class=parser_class)
    for action in ("assess", "start", "preflight", "amend", "resume", "check", "review", "pause", "complete"):
        command = actions.add_parser(action)
        command.set_defaults(handler=handler)
        if action in {"assess", "start", "amend"}:
            command.add_argument("--brief", type=Path, help="optional JSON brief instead of inline fields")
            command.add_argument("--task")
            command.add_argument("--owner")
            command.add_argument("--outcome")
            command.add_argument("--scope", action="append")
            command.add_argument("--acceptance", action="append")
            command.add_argument("--check", dest="checks", action="append")
            command.add_argument("--integration-check", dest="integration_checks", action="append")
            command.add_argument("--non-goal", dest="non_goals", action="append")
            command.add_argument("--design-evidence", action="append")
            command.add_argument("--kind")
            command.add_argument("--design")
            command.add_argument("--certainty")
            command.add_argument("--risk")
            command.add_argument("--trigger", dest="triggers", action="append")
            command.add_argument("--review-profile")
            command.add_argument("--substantial", action="store_true", default=None)
            command.add_argument("--multi-session", action="store_true", default=None)
            command.add_argument("--admitted-item")
            command.add_argument("--verification-output", dest="verification_outputs", action="append")
            if action != "amend":
                command.add_argument("--lane")
        else:
            command.add_argument("--task", required=True)
            command.add_argument("--owner", required=True)
        if action not in {"assess", "start"}:
            command.add_argument("--expected-revision", required=True)
        if action == "check":
            command.add_argument("--name", required=True)
            command.add_argument("--covered", action="append", required=True)
            command.add_argument("--repair", action="store_true")
            command.add_argument("argv", nargs=argparse.REMAINDER)
        if action == "review":
            command.add_argument("--report", required=True)
            command.add_argument("--reviewer", required=True)
            command.add_argument("--independent", action="store_true")
            command.add_argument("--verdict", choices=("approved", "request-changes"), required=True)
        if action == "pause":
            command.add_argument("--reason", required=True)
            command.add_argument("--authority-refused", action="store_true")
        if action == "complete":
            command.add_argument("--gitflow", required=True, help="evidence reference or explicit not-applicable rationale")


def invoke(arguments: argparse.Namespace, root: Path) -> tuple[dict[str, object], bool]:
    brief = None
    if arguments.lane_action in {"assess", "start", "amend"}:
        fields = set(lanes.Brief.__dataclass_fields__)
        data = {
            key: value for key in fields
            if (value := getattr(arguments, key, None)) is not None
        }
        if arguments.brief is not None:
            if data:
                raise lanes.LaneFailure("Use either --brief or inline brief fields, not both.")
            data = lanes._json(arguments.brief.read_bytes())
        brief = lanes.Brief.parse(data)
    argv = getattr(arguments, "argv", [])
    if argv and argv[0] == "--":
        argv = argv[1:]
    return lanes.execute(
        root, arguments.lane_action, brief=brief,
        task=brief.task if brief else arguments.task,
        owner=brief.owner if brief else arguments.owner,
        expected=getattr(arguments, "expected_revision", None),
        requested=getattr(arguments, "lane", None),
        name=getattr(arguments, "name", None), argv=argv,
        covered=getattr(arguments, "covered", []),
        report=getattr(arguments, "report", None),
        reviewer=getattr(arguments, "reviewer", None),
        independent=getattr(arguments, "independent", False),
        verdict=getattr(arguments, "verdict", None),
        reason=getattr(arguments, "reason", None),
        authority_refused=getattr(arguments, "authority_refused", False),
        gitflow=getattr(arguments, "gitflow", None),
        repair=getattr(arguments, "repair", False),
    )
