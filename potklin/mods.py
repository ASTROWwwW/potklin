"""Built-in mods. No generated code, shell eval, or automatic plugin installation."""
from pathlib import Path
import os
import re
import subprocess
import sys
from .core import Tool, Registry
from .windows import status, wait_visible
from .review import review
from .manifests import validate
from .codeinspect import symbols
from .documents import inspect as inspect_html
from .search import search
from .dependencies import inventory
from .edits import replace,digest
from .file_actions import create,move,remove

class Workspace:
    def __init__(self, root):
        self.root = Path(root).resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError("workspace must be a directory")

    def path(self, name):
        relative = Path(name)
        if relative.is_absolute() or relative.anchor or ".." in relative.parts or ":" in name or "\x00" in name:
            raise PermissionError("unsafe workspace path")
        p = self.root / relative
        resolved = p.resolve()
        if not resolved.is_relative_to(self.root):
            raise PermissionError("outside workspace")
        # Reject symlinks and Windows junctions in existing path components.
        current = p
        while current != self.root and current.is_relative_to(self.root):
            if current.is_symlink() or getattr(current, "is_junction", lambda: False)() or (current.exists() and getattr(current.lstat(), "st_file_attributes", 0) & 0x400):
                raise PermissionError("linked path")
            current = current.parent
        return resolved

    def read(self, path):
        p = self.path(path)
        if not p.is_file() or p.stat().st_size > 65536:
            raise ValueError("not a bounded text file")
        with p.open("rb") as f:
            data = f.read(65537)
        if len(data) > 65536:
            raise ValueError("file too large")
        return {"path": path, "text": data.decode("utf-8")}

    def list(self, path):
        p = self.path(path)
        if not p.is_dir():
            raise ValueError("not a directory")
        from itertools import islice
        return {"path": path, "entries": sorted(x.name for x in islice(p.iterdir(), 201))[:200]}

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
        findings, scanned = [], 0
        for base, dirs, names in os.walk(p, followlinks=False):
            dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in {"node_modules", "venv", "__pycache__"} and not Path(base,d).is_symlink() and not getattr(Path(base,d), "is_junction", lambda: False)())
            for name in sorted(names):
                f = Path(base, name)
                if f.suffix != ".py" or f.is_symlink() or scanned >= 500:
                    continue
                try:
                    rel = str(f.relative_to(self.root))
                    data = self.read(rel)["text"]
                except (OSError, UnicodeError, ValueError, PermissionError):
                    continue
                scanned += 1
                for i, line in enumerate(data.splitlines(), 1):
                    for cwe, pattern in rules.items():
                        if pattern.search(line) and len(findings) < 1000:
                            findings.append({"path": rel, "line": i, "rule": cwe, "status": "unverified"})
            if scanned >= 500:
                break
        return {"scanned": scanned, "findings": findings, "truncated": scanned >= 500}

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

def build_registry(root):
    w = Workspace(root)
    r = Registry()
    r.register(Tool("files.read", "filesystem", "Read bounded UTF-8 file", ("path",), w.read,
                    lambda v, path: v == w.read(path)))
    r.register(Tool("files.list", "filesystem", "List directory", ("path",), w.list,
                    lambda v, path: v == w.list(path)))
    r.register(Tool("cyber.audit", "cyber", "Read-only Python source pattern review", ("path",), w.audit,
                    lambda v, path: v == w.audit(path)))
    # Launch request does not establish that the target UI is visible.
    r.register(Tool("windows.launch", "windows", "Launch allowlisted application", ("app",), windows_launch,
                    lambda v, app: False, True))
    r.register(Tool("windows.status","windows","Observe visible allowlisted application",("app",),status,lambda v,app: v["visible"] and status(app)["visible"]))
    r.register(Tool("cyber.ast_review","cyber","Review local Python AST for security leads",("path",),lambda path:review(w,path),lambda v,path:v==review(w,path)))
    r.register(Tool("coding.symbols","coding","Inspect Python syntax and symbols",("path",),lambda path:symbols(w,path),lambda v,path:v==symbols(w,path)))
    r.register(Tool("files.search","filesystem","Find literal text in local files",("path","query"),lambda path,query:search(w,path,query),lambda v,path,query:v==search(w,path,query)))
    r.register(Tool("documents.html","documents","Read local HTML visible text and links without executing scripts",("path",),lambda path:inspect_html(w,path),lambda v,path:v==inspect_html(w,path)))
    r.register(Tool("coding.dependencies","coding","Inventory local dependency manifest",("path",),lambda path:inventory(w,path),lambda v,path:v==inventory(w,path)))
    r.register(Tool("files.replace","filesystem","Explicit compare-and-swap text edit",("path","expected_sha256","old","new"),lambda path,expected_sha256,old,new:replace(w,path,expected_sha256,old,new),lambda v,path,**kw:digest(w.path(path).read_bytes())==v["sha256"],True))
    r.register(Tool("files.create","filesystem","Explicit exclusive UTF-8 creation",("path","text"),lambda path,text:create(w,path,text),lambda v,path,text:digest(w.path(path).read_bytes())==v["sha256"],True))
    r.register(Tool("files.move","filesystem","Explicit verified move without overwrite",("source","destination","expected_sha256"),lambda source,destination,expected_sha256:move(w,source,destination,expected_sha256),lambda v,source,destination,**kw:not w.path(source).exists() and digest(w.path(destination).read_bytes())==v["sha256"],True))
    r.register(Tool("files.remove","filesystem","Explicit removal of matching revision",("path","expected_sha256"),lambda path,expected_sha256:remove(w,path,expected_sha256),lambda v,path,**kw:not w.path(path).exists(),True))
    validate(r)
    return r
