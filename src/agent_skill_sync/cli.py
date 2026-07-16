from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .bridge import configure, status
from .engine import Paths, skill_dirs, sync


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="skill-sync", description="Sync Claude Code and Codex skills safely")
    result.add_argument("--version", action="version", version=__version__)
    result.add_argument("--claude-skills", type=Path)
    result.add_argument("--codex-skills", type=Path)
    result.add_argument("--claude-commands", type=Path)
    result.add_argument("--codex-prompts", type=Path)
    result.add_argument("--state-file", type=Path)
    subcommands = result.add_subparsers(dest="command", required=True)

    scan = subcommands.add_parser("scan", help="List discovered skills")
    scan.add_argument("--json", action="store_true")

    run = subcommands.add_parser("sync", help="Plan or apply synchronization")
    run.add_argument("--direction", choices=["claude-to-codex", "codex-to-claude", "both"], default="both")
    run.add_argument("--conflict", choices=["skip", "claude", "codex", "newest"], default="skip")
    run.add_argument("--no-commands", action="store_true")
    run.add_argument("--exclude", action="append", default=[], metavar="SKILL", help="Skip a skill name; repeatable")
    run.add_argument("--apply", action="store_true", help="Write changes; otherwise perform a dry-run")
    run.add_argument("--json", action="store_true")

    bridge = subcommands.add_parser("bridge", help="Inspect or configure the Codex/Claude MCP bridge")
    bridge.add_argument("action", choices=["status", "codex-calls-claude", "claude-calls-codex", "both"])
    return result


def configured_paths(args: argparse.Namespace) -> Paths:
    defaults = Paths.defaults()
    return Paths(
        args.claude_skills or defaults.claude_skills,
        args.codex_skills or defaults.codex_skills,
        args.claude_commands or defaults.claude_commands,
        args.state_file or defaults.state_file,
        args.codex_prompts or defaults.codex_prompts,
    )


def print_report(report, as_json: bool) -> None:
    if as_json:
        print(json.dumps(report.as_dict(), indent=2))
        return
    mode = "applied" if report.applied else "dry-run"
    for action in report.actions:
        suffix = f" ({action.detail})" if action.detail else ""
        if action.source and action.destination:
            print(f"{action.kind:10} {action.name}: {action.source} -> {action.destination}{suffix}")
        else:
            print(f"{action.kind:10} {action.name}{suffix}")
    print(f"\n{mode}: {report.changed} change(s), {report.conflicts} conflict(s)")


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    paths = configured_paths(args)
    if args.command == "scan":
        data = {
            "claude": sorted(skill_dirs(paths.claude_skills)),
            "codex": sorted(skill_dirs(paths.codex_skills)),
        }
        print(json.dumps(data, indent=2) if args.json else "\n".join(f"{side}: {len(names)}" for side, names in data.items()))
        return 0
    if args.command == "sync":
        report = sync(
            paths,
            args.direction,
            args.conflict,
            not args.no_commands,
            args.apply,
            set(args.exclude),
        )
        print_report(report, args.json)
        return 2 if report.conflicts else 0
    if args.action == "status":
        current = status()
        print(f"Codex calls Claude: {'yes' if current.codex_calls_claude else 'no'}")
        print(f"Claude calls Codex: {'yes' if current.claude_calls_codex else 'no'}")
        return 0
    if args.action == "both":
        print("Warning: enabling both directions can create recursive agent calls.", file=sys.stderr)
    completed = configure(args.action)
    print(completed.stdout, end="")
    print(completed.stderr, end="", file=sys.stderr)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
