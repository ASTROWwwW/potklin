"""Built-in mods. No generated code, shell eval, or automatic plugin installation."""
from itertools import islice
from pathlib import Path
import os
import re
import subprocess
import sys
from .core import Tool, Registry
from .windows import status
from .review import review
from .manifests import validate
from .codeinspect import symbols
from .documents import inspect as inspect_html
from .search import search
from .dependencies import inventory
from .edits import MAX_FILE, overwrite, replace, digest
from .file_actions import create, move, remove
from .gitmod import inspect as inspect_git

# Writing there can run code outside the mission (git hooks, editor tasks) or alter agent state.
PROTECTED_NAMES = {".git", ".potklin", ".vscode", ".idea"}
READ_LIMIT = 65536
# Windows opens these as devices wherever they appear, with or without an extension.
DEVICE_NAME = re.compile(r"(?i)con|prn|aux|nul|conin\$|conout\$|clock\$|(com|lpt)[0-9\u00b9\u00b2\u00b3]")


def is_protected_name(part):
    name = part.casefold()
    return name in PROTECTED_NAMES or name == ".env" or (name.startswith(".env.") and name != ".env.example")


class Workspace:
    def __init__(self, root):
        self.root = Path(root).resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError("workspace must be a directory")

    def path(self, name):
        relative = Path(name)
        if relative.is_absolute() or relative.anchor or ".." in relative.parts or ":" in name or "\x00" in name:
            raise PermissionError("unsafe workspace path")
        # Windows silently strips trailing dots and spaces, so ".git." opens ".git".
        if any(part != part.rstrip(" .") for part in relative.parts):
            raise PermissionError("unsafe workspace path")
        if any(ord(c) < 32 or c in '<>"|?*' for c in name) or any(DEVICE_NAME.fullmatch(part.split(".")[0].rstrip(" ")) for part in relative.parts):
            raise PermissionError("unsafe workspace path")
        p = self.root / relative
        resolved = p.resolve()
        if not resolved.is_relative_to(self.root):
            raise PermissionError("outside workspace")
        # Both spellings: resolve() expands Windows short names such as GIT~1.
        if any(is_protected_name(part) for part in (*relative.parts, *resolved.relative_to(self.root).parts)):
            raise PermissionError("protected path")
        # Reject symlinks and Windows junctions in existing path components.
        current = p
        while current != self.root and current.is_relative_to(self.root):
            if current.is_symlink() or getattr(current, "is_junction", lambda: False)() or (current.exists() and getattr(current.lstat(), "st_file_attributes", 0) & 0x400):
                raise PermissionError("linked path")
            current = current.parent
        return resolved

    def load(self, path, limit=MAX_FILE):
        p = self.path(path)
        if p.is_dir():
            raise ValueError(f"not a file: {path} is a directory; use files.list")
        if not p.is_file():
            raise ValueError(f"not a file: {path} does not exist")
        if p.stat().st_size > limit:
            raise ValueError(f"file too large for this tool (limit {limit} bytes); use files.search or files.read_lines")
        with p.open("rb") as f:
            data = f.read(limit + 1)
        if len(data) > limit:
            raise ValueError("file too large")
        return data

    def read(self, path):
        data = self.load(path, READ_LIMIT)
        return {"path": path, "text": data.decode("utf-8"), "sha256": digest(data)}

    def read_lines(self, path, start, count):
        first, wanted = int(start), int(count)
        if first < 1 or not 1 <= wanted <= 400:
            raise ValueError("start must be >= 1 and count within 1..400")
        data = self.load(path)
        lines = data.decode("utf-8").splitlines()
        return {"path": path, "start": first, "total_lines": len(lines),
                "text": "\n".join(lines[first - 1:first - 1 + wanted]), "sha256": digest(data)}

    def list(self, path):
        p = self.path(path)
        if not p.is_dir():
            raise ValueError("not a directory")
        return {"path": path, "entries": sorted(x.name + ("/" if x.is_dir() else "") for x in islice(p.iterdir(), 201))[:200]}

    def audit(self, path):
        """Read-only local source review. Findings are leads, not proven vulnerabilities."""
        p = self.path(path)
        if not p.is_dir():
            raise ValueError("audit requires directory")
        rules = {
            "CWE-78": re.compile(r"shell\s*=\s*True"),
            "CWE-95": re.compile(r"\b(?:eval|exec)\s*\("),
            "CWE-327": re.compile(r"\b(?:md5|sha1)\s*\("),
            "CWE-89": re.compile(r"\.execute\s*\(\s*f[\x22\x27]"),
        }
        findings, scanned, skipped = [], 0, 0
        for base, dirs, names in os.walk(p, followlinks=False):
            dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in {"node_modules", "venv", "__pycache__"} and not Path(base, d).is_symlink() and not getattr(Path(base, d), "is_junction", lambda: False)())
            for name in sorted(names):
                f = Path(base, name)
                if f.suffix != ".py" or f.is_symlink() or scanned >= 500:
                    continue
                try:
                    rel = str(f.relative_to(self.root))
                    data = self.read(rel)["text"]
                except (OSError, UnicodeError, ValueError, PermissionError):
                    skipped += 1
                    continue
                scanned += 1
                for i, line in enumerate(data.splitlines(), 1):
                    for cwe, pattern in rules.items():
                        if pattern.search(line) and len(findings) < 1000:
                            findings.append({"path": rel, "line": i, "rule": cwe, "status": "unverified"})
            if scanned >= 500:
                break
        return {"scanned": scanned, "skipped": skipped, "findings": findings,
                "truncated": scanned >= 500 or len(findings) >= 1000}


def windows_launch(app):
    """Explicitly allowlisted native launch; no arbitrary executable arguments."""
    if sys.platform != "win32":
        raise OSError("Windows only")
    if app.lower() == "notepad":
        exe = Path(os.environ["SystemRoot"]) / "System32" / "notepad.exe"
        cmd = [str(exe)]
    elif app.lower() == "discord":
        exe = Path(os.environ["LOCALAPPDATA"]) / "Discord" / "Update.exe"
        cmd = [str(exe), "--processStart", "Discord.exe"]
    else:
        raise ValueError("unknown application")
    if not exe.is_file():
        raise FileNotFoundError(app)
    proc = subprocess.Popen(cmd, shell=False)
    return {"app": app.lower(), "launcher_pid": proc.pid, "status": "launch_requested"}


def build_registry(root, commands=None):
    w = Workspace(root)
    r = Registry()

    def observe(name, mod, description, arguments, execute):
        # A re-read only proves the observation is stable, not that it is correct.
        r.register(Tool(name, mod, description, arguments, execute, lambda v, **kw: v == execute(**kw)))

    observe("files.read", "filesystem", "Read a whole UTF-8 file up to 64 KiB. path is relative to the workspace.", ("path",), w.read)
    observe("files.read_lines", "filesystem", "Read part of a large file. start is the first line number, count is at most 400.", ("path", "start", "count"), w.read_lines)
    observe("files.list", "filesystem", "List a directory; '.' is the workspace root. Directories end with '/'.", ("path",), w.list)
    observe("files.search", "filesystem", "Find literal text (case-insensitive) in one file or in all files under a directory. Returns line numbers.", ("path", "query"), lambda path, query: search(w, path, query))
    observe("cyber.audit", "cyber", "Read-only Python source pattern review of a directory", ("path",), w.audit)
    observe("cyber.ast_review", "cyber", "Review the Python AST of a directory for security leads", ("path",), lambda path: review(w, path))
    observe("coding.symbols", "coding", "Check the Python syntax of one file and list its symbols", ("path",), lambda path: symbols(w, path))
    observe("coding.dependencies", "coding", "Inventory a local dependency manifest file", ("path",), lambda path: inventory(w, path))
    observe("coding.git", "coding", "Show git status and the uncommitted diff of a repository directory", ("path",), lambda path: inspect_git(w, path))
    observe("documents.html", "documents", "Read local HTML visible text and links without executing scripts", ("path",), lambda path: inspect_html(w, path))

    # Launch request does not establish that the target UI is visible.
    r.register(Tool("windows.launch", "windows", "Launch allowlisted application", ("app",), windows_launch,
                    lambda v, app: False, True))
    r.register(Tool("windows.status", "windows", "Observe visible allowlisted application", ("app",), status,
                    lambda v, app: v["visible"] and status(app)["visible"]))

    r.register(Tool("files.replace", "filesystem", "Edit a file: replace the snippet `old`, which must occur exactly once, with `new`. Read the file first.",
                    ("path", "expected_sha256", "old", "new"),
                    lambda path, expected_sha256, old, new: replace(w, path, expected_sha256, old, new),
                    lambda v, path, **kw: digest(w.load(path)) == v["sha256"], True))
    r.register(Tool("files.write", "filesystem", "Replace the whole content of an existing file with `text`. Read the file first. Best for small files.",
                    ("path", "expected_sha256", "text"),
                    lambda path, expected_sha256, text: overwrite(w, path, expected_sha256, text),
                    lambda v, path, **kw: digest(w.load(path)) == v["sha256"], True))
    r.register(Tool("files.create", "filesystem", "Create a new file with the full content `text`. Fails if it exists. Parent directories are created.",
                    ("path", "text"), lambda path, text: create(w, path, text),
                    lambda v, path, text: w.load(path) == text.encode("utf-8"), True))
    r.register(Tool("files.move", "filesystem", "Rename a file without overwriting. Read the source first.",
                    ("source", "destination", "expected_sha256"),
                    lambda source, destination, expected_sha256: move(w, source, destination, expected_sha256),
                    lambda v, source, destination, **kw: not w.path(source).exists() and digest(w.load(destination)) == v["sha256"], True))
    r.register(Tool("files.remove", "filesystem", "Delete a file. Read it first.", ("path", "expected_sha256"),
                    lambda path, expected_sha256: remove(w, path, expected_sha256),
                    lambda v, path, **kw: not w.path(path).exists(), True))
    validate(r)
    if commands is not None:
        r.register(Tool("commands.run", "commands",
                        "Run one user-declared command by name and return its exit code and output. Available names: " + ", ".join(commands.names),
                        ("name",), commands.run, lambda v, name: v["exit_code"] == 0, True))
    return r
