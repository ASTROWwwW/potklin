"""Pre-images of every file a mission writes, persisted before the write.

Covers the file tools only: changes made by a command are not recorded.
"""
import difflib
import hashlib
import json
import os
import stat
from pathlib import Path
from .edits import MAX_FILE, digest, write_atomic
from .mods import Workspace


def state(workspace, path):
    """What is on disk now: None, "directory", "unreadable" or the SHA-256 of the file, whatever its size."""
    try:
        target = workspace.path(path)
        if not target.exists():
            return None
        if not target.is_file():
            return "directory"
        with target.open("rb") as handle:
            return hashlib.file_digest(handle, "sha256").hexdigest()
    except (OSError, PermissionError):
        return "unreadable"


UNRESTORABLE = {"directory", "unreadable"}


class Checkpoints:
    def __init__(self, db):
        self.db = db
        db.execute("CREATE TABLE IF NOT EXISTS checkpoints (seq INTEGER PRIMARY KEY, mission TEXT, root TEXT, path TEXT, before BLOB, mode INTEGER, new_dirs TEXT, after TEXT, done INTEGER)")
        if "mode" not in {row[1] for row in db.execute("PRAGMA table_info(checkpoints)")}:
            db.execute("ALTER TABLE checkpoints ADD COLUMN mode INTEGER")
        db.commit()

    def snapshot(self, workspace, mission, path):
        target = workspace.path(path)
        if target.is_dir():
            raise ValueError("target is a directory")
        before = workspace.load(path) if target.is_file() else None
        mode = stat.S_IMODE(target.stat().st_mode) if before is not None else None
        new_dirs = [p.relative_to(workspace.root).as_posix() for p in target.parents
                    if p != workspace.root and p.is_relative_to(workspace.root) and not p.exists()]
        cursor = self.db.execute("INSERT INTO checkpoints(mission,root,path,before,mode,new_dirs,after,done) VALUES(?,?,?,?,?,?,NULL,0)",
                                 (mission, str(workspace.root), target.relative_to(workspace.root).as_posix(), before, mode, json.dumps(new_dirs)))
        self.db.commit()
        return cursor.lastrowid

    def seal(self, workspace, seq, path):
        after = state(workspace, path)
        before, new_dirs = self.db.execute("SELECT before,new_dirs FROM checkpoints WHERE seq=?", (seq,)).fetchone()
        untouched = after == (None if before is None else digest(before))
        if untouched and not any((workspace.root / name).exists() for name in json.loads(new_dirs)):
            # A write that changed nothing must not make a later edit by the user look like ours.
            self.db.execute("DELETE FROM checkpoints WHERE seq=?", (seq,))
        else:
            self.db.execute("UPDATE checkpoints SET after=?, done=1 WHERE seq=?", (after, seq))
        self.db.commit()

    def known(self, mission):
        return self.db.execute("SELECT 1 FROM checkpoints WHERE mission=? LIMIT 1", (mission,)).fetchone() is not None

    def paths(self, mission):
        """Files whose content now differs from what it was before the mission."""
        return sorted(item["path"] for item in self._pending(mission)[1] if item["current"] != item["original"])

    def diff(self, mission, limit=40000):
        """Unified diff from the pre-mission content to what is on disk now, for human review."""
        workspace, items, _ = self._pending(mission)
        chunks = []
        for item in sorted(items, key=lambda i: i["path"]):
            current = item["current"]
            if current == item["original"]:
                continue
            old = "/dev/null" if item["before"] is None else "a/" + item["path"]
            new = "/dev/null" if current is None else "b/" + item["path"]
            after = []
            if current is not None:
                try:
                    after = workspace.load(item["path"], MAX_FILE).decode("utf-8", errors="replace").splitlines()
                except (OSError, ValueError, PermissionError):
                    chunks.append(f"--- {old}\n+++ {new}\n[current content is too large or unreadable to diff]")
                    continue
            before = (item["before"] or b"").decode("utf-8", errors="replace").splitlines()
            body = list(difflib.unified_diff(before, after, old, new, lineterm=""))
            chunks.append("\n".join(body or [f"--- {old}", f"+++ {new}"]))
        text = "\n".join(chunks)
        return text if len(text) <= limit else text[:limit] + "\n[diff truncated]"

    def _pending(self, mission):
        rows = self.db.execute("SELECT root,path,before,mode,new_dirs,after,done FROM checkpoints WHERE mission=? ORDER BY seq", (mission,)).fetchall()
        if not rows:
            return None, [], set()
        workspace = Workspace(rows[0][0])
        items, new_dirs = {}, set()
        for _, path, before, mode, dirs, after, done in rows:
            # Where the disk ignores case, two spellings are one file: its first record holds the original.
            item = items.setdefault(os.path.normcase(path), {"path": path, "paths": set(), "before": before, "mode": mode,
                                                             "original": None if before is None else digest(before)})
            item["paths"].add(path)
            item["after"], item["done"] = after, done
            new_dirs.update(json.loads(dirs))
        for item in items.values():
            item["current"] = state(workspace, item["path"])
        return workspace, list(items.values()), new_dirs

    def rollback(self, mission, force=False):
        """All or nothing unless forced: a file edited after the mission blocks the whole rollback."""
        workspace, items, new_dirs = self._pending(mission)
        if workspace is None:
            raise ValueError("no checkpoint for this mission")
        created = {os.path.normcase(i["path"]) for i in items if i["before"] is None}

        def ours(item):
            """A directory the mission made, holding nothing but files the mission made."""
            if item["current"] != "directory" or item["path"] not in new_dirs:
                return False
            return all(f.is_dir() or os.path.normcase(f.relative_to(workspace.root).as_posix()) in created
                       for f in (workspace.root / item["path"]).rglob("*"))

        def prune():
            for name in sorted(new_dirs, key=len, reverse=True):
                try:
                    folder = workspace.path(name)
                    if folder.is_dir() and not any(folder.iterdir()):
                        folder.rmdir()
                except (OSError, PermissionError):
                    pass

        changed = [i for i in items if i["current"] != i["original"]]
        conflicts = sorted(i["path"] for i in changed
                           if not ours(i) and (i["current"] in UNRESTORABLE or not i["done"] or i["current"] != i["after"]))
        if conflicts and not force:
            return {"restored": [], "conflicts": conflicts, "unrestored": sorted(i["path"] for i in changed)}
        restored, unrestored = set(), set()
        # New files go first. On a case-insensitive disk two recorded names can be one file, so the
        # old contents are written afterwards, from a fresh look at what is left.
        for item in items:
            if item["before"] is None and item["current"] != item["original"]:
                if item["current"] in UNRESTORABLE:
                    if not ours(item):
                        unrestored.add(item["path"])
                    continue
                try:
                    workspace.path(item["path"]).unlink(missing_ok=True)
                except OSError:
                    unrestored.add(item["path"])
                    continue
                restored.add(item["path"])
        # A directory we created may sit where an old file has to come back.
        prune()
        for item in items:
            if item["before"] is None:
                continue
            now = state(workspace, item["path"])
            if now in UNRESTORABLE:
                unrestored.add(item["path"])
                continue
            try:
                if now != item["original"]:
                    target = workspace.path(item["path"])
                    target.parent.mkdir(parents=True, exist_ok=True)
                    write_atomic(target, item["before"])
                    if item["mode"] is not None:
                        os.chmod(target, item["mode"])
                    restored.add(item["path"])
                # Give back the original spelling after a case-only rename.
                actual, wanted = workspace.path(item["path"]), Path(item["path"]).name
                if actual.name != wanted:
                    actual.rename(actual.with_name(wanted))
                    restored.add(item["path"])
            except OSError:
                unrestored.add(item["path"])
        prune()
        # Keep the pre-images of whatever could not be restored: they may be the only copy.
        for item in items:
            if item["path"] not in unrestored:
                self.db.executemany("DELETE FROM checkpoints WHERE mission=? AND path=?",
                                    [(mission, path) for path in item["paths"]])
        self.db.commit()
        return {"restored": sorted(restored), "conflicts": conflicts, "unrestored": sorted(unrestored)}
