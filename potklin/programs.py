"""Find programs without ever searching the current directory or a mission's workspace.

shutil.which, and Windows itself, look in the current directory first. A mission runs next to
files the model may write, so only absolute PATH entries count here.
"""
import os
from pathlib import Path


def candidates(name):
    """Yield every executable called `name` on the absolute PATH entries, in search order."""
    if os.name == "nt":
        extensions = ([""] if Path(name).suffix else []) + os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD").split(";")
    else:
        extensions = [""]
    for folder in os.environ.get("PATH", "").split(os.pathsep):
        if not os.path.isabs(folder):
            continue
        for extension in filter(lambda e: e or os.name != "nt" or Path(name).suffix, extensions):
            file = Path(folder, name + extension)
            if file.is_file() and os.access(file, os.X_OK):
                yield file


def find_program(name, outside=None):
    """First match that does not live under `outside`."""
    root = None if outside is None else Path(outside).resolve()
    for file in candidates(name):
        if root is None or not file.resolve().is_relative_to(root):
            return str(file)
    raise FileNotFoundError(name)
