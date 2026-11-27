"""Acceptance criteria written by the user. The model can neither add nor change them."""
import fnmatch
import os
import posixpath
import sys
from dataclasses import dataclass
from pathlib import Path
from .edits import digest

NEVER_WALKED = {".git", "__pycache__", ".pytest_cache"}
# Large dependency trees are walked only when a pattern reaches into them.
HEAVY_DIRS = {"node_modules", ".venv", "venv"}
MAX_PROTECTED = 5000


@dataclass(frozen=True)
class Check:
    kind: str
    target: str
    value: str = ""

    @property
    def label(self):
        # The expected value stays hidden so the model cannot simply paste it.
        return self.kind + ":" + self.target


def parse(spec):
    kind, _, rest = spec.partition(":")
    if kind in {"exists", "absent", "command"}:
        target, value = rest, ""
    elif kind in {"contains", "sha256"}:
        target, _, value = rest.partition("::")
        if not value:
            raise ValueError(f"{kind} check needs the form {kind}:path::value")
    else:
        raise ValueError("unknown check kind; use exists, absent, contains, sha256 or command")
    if not target:
        raise ValueError("check target is empty: " + spec)
    return Check(kind, target, value)


def validate(checks, workspace, commands):
    """Fail before the mission starts rather than report a typo as a failed task."""
    for check in checks:
        if check.kind == "command":
            if commands is None or check.target not in commands.names:
                raise ValueError("command check refers to an undeclared command: " + check.target)
        else:
            workspace.path(check.target)


def evaluate(checks, workspace, commands=None):
    results = []
    for check in checks:
        detail = ""
        try:
            if check.kind == "command":
                run = commands.run(check.target)
                passed = run["exit_code"] == 0
                detail = "" if passed else f"exit code {run['exit_code']}\n{run['output']}"
            elif check.kind in {"exists", "absent"}:
                passed = workspace.path(check.target).exists() == (check.kind == "exists")
            elif check.kind == "contains":
                body = workspace.load(check.target).decode("utf-8").replace("\r\n", "\n")
                passed = check.value.replace("\r\n", "\n") in body
            else:
                passed = digest(workspace.load(check.target)) == check.value.lower()
        except (OSError, ValueError) as error:
            passed, detail = False, type(error).__name__
        results.append({"check": check.label, "passed": passed, "detail": detail})
    return results


ASCII_LOWER = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")


def normalize(relative, allow=False):
    value = posixpath.normpath(relative.replace("\\", "/")).strip("/")
    if allow:
        # Unicode folding would equate names the disk keeps apart (long s, sharp s, Kelvin sign).
        return value.translate(ASCII_LOWER) if os.name == "nt" else value
    return value.casefold() if os.name == "nt" or sys.platform == "darwin" else value


def matches(relative, patterns, allow=False):
    """Only * and ? are wildcards; brackets are literal, as in app/[id].tsx.

    With allow=True the patterns grant access and compare strictly; otherwise they protect and compare broadly.
    """
    name = normalize(relative, allow)
    return any(name == p or name.startswith(p + "/") or fnmatch.fnmatchcase(name, p.replace("[", "[[]"))
               for p in (normalize(pattern, allow) for pattern in patterns))


def fingerprint(root, patterns):
    """Hash every protected file, so changes made by a command are detected too."""
    found = {}
    if not patterns:
        return found

    def worth_walking(base, name):
        if name in NEVER_WALKED:
            return False
        if name not in HEAVY_DIRS:
            return True
        relative = Path(base, name).relative_to(root).as_posix()
        return matches(relative, patterns) or any(normalize(p).startswith(normalize(relative) + "/") for p in patterns)

    for base, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if worth_walking(base, d)]
        for name in names:
            file = Path(base, name)
            relative = file.relative_to(root).as_posix()
            if not matches(relative, patterns):
                continue
            if len(found) >= MAX_PROTECTED:
                raise ValueError("too many protected files")
            found[relative] = "link" if file.is_symlink() else digest(file.read_bytes())
    return found
