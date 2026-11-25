"""Trusted, developer-authored tool registry and bounded mission execution."""
from dataclasses import dataclass
from typing import Callable
import json
import sqlite3
import time
import uuid

@dataclass(frozen=True)
class Tool:
    name: str
    mod: str
    description: str
    arguments: tuple[str, ...]
    execute: Callable
    verify: Callable
    side_effect: bool = False

class Registry:
    def __init__(self):
        self._tools = {}

    def register(self, tool):
        if tool.name in self._tools:
            raise ValueError("duplicate tool")
        self._tools[tool.name] = tool

    def select(self, mods):
        return {k: v for k, v in self._tools.items() if v.mod in mods}

class Journal:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY, mission TEXT, kind TEXT, payload TEXT, timestamp REAL)")
        self.db.commit()

    def append(self, mission, kind, payload):
        self.db.execute("INSERT INTO events(mission,kind,payload,timestamp) VALUES(?,?,?,?)",
                        (mission, kind, json.dumps(payload, ensure_ascii=False), time.time()))
        self.db.commit()

    def close(self):
        self.db.close()

class Executor:
    def __init__(self, registry, journal):
        self.registry, self.journal = registry, journal

    def run(self, name, args, mods, allow_write=False):
        mission = uuid.uuid4().hex
        tools = self.registry.select(mods)
        if name not in tools:
            raise PermissionError("tool not in selected mods")
        tool = tools[name]
        if not isinstance(args, dict) or set(args) != set(tool.arguments):
            raise ValueError("invalid argument schema")
        if any(not isinstance(v, str) or len(v) > 8192 for v in args.values()):
            raise ValueError("invalid argument value")
        if tool.side_effect and not allow_write:
            raise PermissionError("explicit action permission required")
        # Journal metadata only: do not persist arbitrary file contents or secrets.
        self.journal.append(mission, "started", {"tool": name})
        try:
            value = tool.execute(**args)
            verified = bool(tool.verify(value, **args))
            self.journal.append(mission, "finished", {"tool": name, "verified": verified})
            return {"mission": mission, "verified": verified, "result": value}
        except Exception as exc:
            self.journal.append(mission, "failed", {"type": type(exc).__name__})
            raise
