import argparse
import json
from pathlib import Path
from .core import Executor, Journal
from .mods import build_registry
from .ollama import Ollama
from .router import route

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--workspace", default=".")
    p.add_argument("--journal", default="potklin-events.sqlite3")
    p.add_argument("--model", default="huihui_ai/qwen3.6-abliterated:35b")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("tools")
    direct = sub.add_parser("run")
    direct.add_argument("tool")
    direct.add_argument("args")
    direct.add_argument("--allow-write", action="store_true")
    instant = sub.add_parser("instant")
    instant.add_argument("request")
    instant.add_argument("--allow-write", action="store_true")
    plan = sub.add_parser("plan")
    plan.add_argument("request")
    plan.add_argument("--mods", nargs="+", choices=["filesystem", "cyber"], required=True)
    a = p.parse_args()
    r = build_registry(a.workspace)
    if a.command == "tools":
        print(json.dumps(list(r.select({"filesystem", "cyber", "windows"})), indent=2))
        return
    if a.command == "plan":
        result = Ollama(a.model).propose(a.request, r.select(a.mods))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    j = Journal(a.journal)
    try:
        if a.command == "instant":
            action = route(a.request)
            if action is None:
                raise ValueError("no deterministic route; use plan or explicit run")
            result = Executor(r, j).run(action["name"], action["args"], {action["mod"]}, a.allow_write)
        else:
            result = Executor(r, j).run(a.tool, json.loads(a.args), {"filesystem","cyber","windows"}, a.allow_write)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        j.close()

if __name__ == "__main__":
    main()
