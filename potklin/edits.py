"""Explicit, compare-and-swap text edits in a trusted local workspace."""
import hashlib
import os
import stat
import tempfile

MAX_FILE = 1_048_576


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_atomic(target, data, expected_sha256=None):
    """Replace target in one step, keeping its permissions."""
    fd, name = tempfile.mkstemp(prefix=".potklin-", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        mode = stat.S_IMODE(target.stat().st_mode) if target.exists() else None
        if expected_sha256 is not None and digest(target.read_bytes()) != expected_sha256:
            raise ValueError("stale revision")
        os.replace(name, target)
        # Applied last: a read-only temporary file could be neither renamed over nor removed on Windows.
        if mode is not None:
            os.chmod(target, mode)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def replace(workspace, path, expected_sha256, old, new):
    target = workspace.path(path)
    raw = workspace.load(path)
    if digest(raw) != expected_sha256:
        raise ValueError("stale revision")
    before = raw.decode("utf-8")
    # Models emit LF; keep CRLF files editable without rewriting their line endings.
    if old not in before and "\r\n" in before and "\r" not in old + new:
        old, new = old.replace("\n", "\r\n"), new.replace("\n", "\r\n")
    found = before.count(old) if old else 0
    if found != 1:
        advice = "include more surrounding lines" if found > 1 else "read the file again and copy it exactly, or use files.write"
        raise ValueError(f"`old` must occur exactly once but occurs {found} times; {advice}")
    after = before.replace(old, new, 1).encode("utf-8")
    if len(after) > MAX_FILE:
        raise ValueError("size limit")
    write_atomic(target, after, expected_sha256)
    return {"path": path, "sha256": digest(after)}


def overwrite(workspace, path, expected_sha256, text):
    """Rewrite a whole file, only if it still has the revision that was read."""
    target = workspace.path(path)
    before = workspace.load(path)
    if digest(before) != expected_sha256:
        raise ValueError("stale revision")
    if b"\r\n" in before and "\r" not in text:
        text = text.replace("\n", "\r\n")
    after = text.encode("utf-8")
    if len(after) > MAX_FILE:
        raise ValueError("size limit")
    write_atomic(target, after, expected_sha256)
    return {"path": path, "sha256": digest(after)}
