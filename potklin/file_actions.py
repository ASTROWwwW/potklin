"""Explicit filesystem actions in a trusted workspace, no implicit overwrite."""
import shutil
from .edits import MAX_FILE, digest


def create(workspace, path, text):
    target = workspace.path(path)
    raw = text.encode("utf-8")
    if len(raw) > MAX_FILE:
        raise ValueError("size limit")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as out:
        out.write(raw)
    return {"path": path, "sha256": digest(raw)}


def move(workspace, source, destination, expected_sha256):
    a = workspace.path(source)
    b = workspace.path(destination)
    raw = workspace.load(source)
    if digest(raw) != expected_sha256:
        raise ValueError("stale revision")
    if a == b or b.exists():
        raise ValueError("destination exists")
    b.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive destination creation; remove only the specific verified source.
    with b.open("xb") as out:
        out.write(raw)
    # Never remove the source before the bytes are proven to be at the destination.
    if not b.is_file() or b.read_bytes() != raw:
        raise ValueError("destination did not receive the content")
    shutil.copymode(a, b)
    if digest(a.read_bytes()) != expected_sha256:
        b.unlink()
        raise ValueError("source changed")
    try:
        a.unlink()
    except OSError:
        b.unlink()
        raise
    return {"source": source, "destination": destination, "sha256": expected_sha256}


def remove(workspace, path, expected_sha256):
    target = workspace.path(path)
    if digest(workspace.load(path)) != expected_sha256:
        raise ValueError("stale revision")
    target.unlink()
    return {"path": path, "removed": True}
