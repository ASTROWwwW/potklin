"""A mission profile: the scope of a project's missions, kept in a file the mission cannot write.

A profile only narrows or describes a mission. Permissions stay on the command line, so no file
can grant the model the right to write, delete or execute.
"""
import json
from pathlib import Path

LISTS = ("mods", "only", "protect", "check", "holdout")
NUMBERS = ("steps", "command_timeout")
ALLOWED = (*LISTS, *NUMBERS, "commands", "rollback_on_failure")


def load(file, workspace):
    path = Path(file).resolve(strict=True)
    if path.is_relative_to(Path(workspace).resolve(strict=True)):
        raise PermissionError("keep the profile outside the workspace: a file there could be shipped or rewritten by the project")
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("a profile is a JSON object")
    unknown = sorted(set(data) - set(ALLOWED))
    if unknown:
        raise ValueError(f"unknown profile keys: {', '.join(unknown)}; permissions are command-line flags only. "
                         f"Allowed keys: {', '.join(ALLOWED)}")
    for key in LISTS:
        if key in data and not (isinstance(data[key], list) and all(isinstance(v, str) for v in data[key])):
            raise ValueError(f"profile key {key} must be a list of strings")
    for key in NUMBERS:
        if key in data and type(data[key]) is not int:
            raise ValueError(f"profile key {key} must be a whole number")
    if "rollback_on_failure" in data and type(data["rollback_on_failure"]) is not bool:
        raise ValueError("profile key rollback_on_failure must be true or false")
    if "commands" in data and not isinstance(data["commands"], dict):
        raise ValueError("profile key commands must be an object: {name: [program, argument, ...]}")
    return data
