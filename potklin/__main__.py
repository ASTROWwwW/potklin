import os
import sys

# `python -m potklin` puts the current directory first on the module path, where a mission may write
# json.py or argparse.py. Drop it before anything else is imported.
if __name__ == "__main__" and sys.path and sys.path[0] in ("", os.getcwd()):
    del sys.path[0]

import argparse
import json
import sqlite3
import subprocess
from dataclasses import asdict
from pathlib import Path
from . import __version__, profile
from .checkpoint import Checkpoints
from .core import Executor, Journal
from .execution import CommandSet
from .manifests import MANIFESTS
from .mission import MissionRunner
from .mods import Workspace, build_registry
from .ollama import Ollama
from .router import route

DEFAULT_MODEL = "huihui_ai/Qwen3.6-abliterated:35b-a3b"
DEFAULT_MODS = ["filesystem", "coding"]
ALL_MODS = ["filesystem", "cyber", "windows", "coding", "documents"]


def parser():
    p = argparse.ArgumentParser(prog="potklin")
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("--workspace", default=".")
    p.add_argument("--journal", default="", help="default: ~/.potklin/journal.sqlite3")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--context", type=int, default=24576, help="model context window in tokens")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("tools")
    sub.add_parser("mods")
    sub.add_parser("gui")
    sub.add_parser("doctor", help="check that the local model is ready")
    mission = sub.add_parser("mission", help="run a bounded agent task")
    mission.add_argument("request")
    mission.add_argument("--profile", help="JSON scope kept outside the workspace: only, protect, check, holdout, commands...")
    mission.add_argument("--mods", nargs="+", choices=ALL_MODS, help="default: filesystem coding")
    mission.add_argument("--steps", type=int, help="default: 20")
    mission.add_argument("--think", action="store_true")
    mission.add_argument("--allow-write", action="store_true", help="let the agent create, edit, move and remove files")
    mission.add_argument("--allow-delete", action="store_true", help="also let the agent delete files")
    mission.add_argument("--only", action="append", default=[], help="path or glob; when given, nothing else may be written")
    mission.add_argument("--commands", help="JSON file: {name: [program, argument, ...]}")
    mission.add_argument("--allow-exec", action="store_true", help="let declared commands run; they execute workspace code without a sandbox")
    mission.add_argument("--command-timeout", type=int, help="default: 120 seconds")
    mission.add_argument("--check", action="append", default=[], help="exists:p, absent:p, contains:p::text, sha256:p::hex or command:name")
    mission.add_argument("--holdout", action="append", default=[], help="check the model never sees, run once at the end")
    mission.add_argument("--protect", action="append", default=[], help="path or glob the mission must not change")
    mission.add_argument("--rollback-on-failure", action="store_true")
    rollback = sub.add_parser("rollback", help="undo the file writes of a mission")
    rollback.add_argument("mission")
    rollback.add_argument("--force", action="store_true", help="also overwrite files edited since the mission")
    diff = sub.add_parser("diff", help="show what a mission changed and has not been rolled back")
    diff.add_argument("mission")
    log = sub.add_parser("log", help="show journal events")
    log.add_argument("mission", nargs="?")
    log.add_argument("--limit", type=int, default=50)
    direct = sub.add_parser("run")
    direct.add_argument("tool")
    direct.add_argument("args")
    direct.add_argument("--allow-write", action="store_true")
    instant = sub.add_parser("instant")
    instant.add_argument("request")
    instant.add_argument("--allow-write", action="store_true")
    plan = sub.add_parser("plan")
    plan.add_argument("request")
    plan.add_argument("--mods", nargs="+", choices=["filesystem", "cyber", "coding", "documents"], required=True)
    return p


def show(value):
    print(json.dumps(value, ensure_ascii=False, indent=2))


def journal_path(value):
    if value:
        return value
    folder = Path.home() / ".potklin"
    folder.mkdir(exist_ok=True)
    return folder / "journal.sqlite3"


def progress(kind, detail):
    label = {"started": "mission", "step": "tool", "rejected": "rejected reply", "checks_failed": "checks failed"}[kind]
    print(f"[{label}] {detail}", file=sys.stderr, flush=True)


def mission_scope(a):
    """Merge the profile into the arguments: lists add up, a single value on the command line wins."""
    scope = profile.load(a.profile, a.workspace) if a.profile else {}
    if a.commands and "commands" in scope:
        raise ValueError("commands are declared both in --commands and in the profile; keep one")
    for key in ("only", "protect", "check", "holdout"):
        setattr(a, key, scope.get(key, []) + getattr(a, key))
    a.mods = a.mods or scope.get("mods") or DEFAULT_MODS
    unknown = sorted(set(a.mods) - set(ALL_MODS))
    if unknown:
        raise ValueError("unknown mods: " + ", ".join(unknown))
    a.steps = a.steps if a.steps is not None else scope.get("steps", 20)
    a.command_timeout = a.command_timeout if a.command_timeout is not None else scope.get("command_timeout", 120)
    a.rollback_on_failure = a.rollback_on_failure or scope.get("rollback_on_failure", False)
    return scope.get("commands")


def run_mission(a, journal):
    declared = mission_scope(a)
    if (a.commands or declared is not None) and not a.allow_exec:
        raise PermissionError("declared commands require --allow-exec: they run workspace code without a sandbox")
    if declared is not None:
        commands = CommandSet(a.workspace, declared, a.command_timeout)
    else:
        commands = CommandSet.load(a.commands, a.workspace, a.command_timeout) if a.commands else None
    registry = build_registry(a.workspace, commands)
    if not 8192 <= a.context <= 262144:
        raise ValueError("--context must be within 8192..262144")
    # About two characters of history per token left once the reply and the tool schemas are reserved.
    budget = max(4000, min(128000, (a.context - 6000) * 2))
    runner = MissionRunner(registry, journal, Ollama(a.model, context=a.context), Workspace(a.workspace), commands, progress, budget)
    mods = set(a.mods) | ({"commands"} if commands else set())
    result = runner.run(a.request, mods, a.steps, a.think, a.allow_write, a.check, a.protect, a.rollback_on_failure,
                        a.allow_delete, a.only, a.holdout)
    show(result)
    if result["verified"]:
        return 0
    if result["status"] == "failed":
        return 2
    # Without checks there is nothing to fail: finishing is the best available outcome.
    return 0 if result["status"] == "model_finished_unverified" else 1


def dispatch(a):
    if a.command == "gui":
        from .ui import launch
        launch(a.workspace, a.model, journal_path(a.journal))
        return 0
    if a.command == "mods":
        show([asdict(m) for m in MANIFESTS])
        return 0
    if a.command == "doctor":
        models = Ollama(a.model, timeout=10).models()
        show({"ollama": "reachable", "model": a.model, "model_installed": a.model in models, "installed": models})
        return 0 if a.model in models else 1
    if a.command == "tools":
        show(list(build_registry(a.workspace).select(set(ALL_MODS))))
        return 0
    if a.command == "plan":
        show(Ollama(a.model).propose(a.request, build_registry(a.workspace).select(a.mods)))
        return 0
    journal = Journal(journal_path(a.journal))
    try:
        if a.command == "mission":
            return run_mission(a, journal)
        if a.command == "rollback":
            result = Checkpoints(journal.db).rollback(a.mission, a.force)
            journal.append(a.mission, "rollback", result)
            show(result)
            return 1 if result["unrestored"] else 0
        if a.command == "diff":
            if not journal.events(a.mission, 1):
                raise ValueError("unknown mission")
            print(Checkpoints(journal.db).diff(a.mission))
            return 0
        if a.command == "log":
            events = journal.events(a.mission, a.limit)
            if a.mission and not events:
                raise ValueError("unknown mission")
            show(events)
            return 0
        registry = build_registry(a.workspace)
        if a.command == "instant":
            action = route(a.request)
            if action is None:
                raise ValueError("no deterministic route; use plan or explicit run")
            show(Executor(registry, journal).run(action["name"], action["args"], {action["mod"]}, a.allow_write))
        else:
            show(Executor(registry, journal).run(a.tool, json.loads(a.args), set(ALL_MODS), a.allow_write))
        return 0
    finally:
        journal.close()


def main(argv=None):
    # A redirected Windows console defaults to a legacy code page that cannot print most results.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    # Processes started from here must not search the current directory for programs either.
    os.environ.setdefault("NoDefaultCurrentDirectoryInExePath", "1")
    a = parser().parse_args(argv)
    try:
        return dispatch(a)
    except (ValueError, PermissionError, OSError, RuntimeError, subprocess.SubprocessError, sqlite3.Error) as error:
        print(f"error: {type(error).__name__}: {error}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("interrupted. Undo the writes with: potklin rollback <mission>   (add --force only if it reports conflicts "
              "and you accept losing later edits to those files)", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
