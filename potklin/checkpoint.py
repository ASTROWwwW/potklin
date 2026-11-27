"""Pre-images of every file a mission writes, persisted before the write.

Covers the file tools only: changes made by a command are not recorded.
"""
import difflib
import json
from .edits import digest, write_atomic
from .mods import Workspace


def state(workspace, path):
    target = workspace.path(path)
    if not target.exists():
        return None
    return digest(workspace.load(path)) if target.is_file() else "directory"


class Checkpoints:
    def __init__(self, db):
        self.db = db
        db.execute("CREATE TABLE IF NOT EXISTS checkpoints (seq INTEGER PRIMARY KEY, mission TEXT, root TEXT, path TEXT, before BLOB, new_dirs TEXT, after TEXT, done INTEGER)")
        db.commit()

    def snapshot(self, workspace, mission, path):
        target = workspace.path(path)
        if target.is_dir():
            raise ValueError("target is a directory")
        before = workspace.load(path) if target.is_file() else None
        new_dirs = [p.relative_to(workspace.root).as_posix() for p in target.parents
                    if p != workspace.root and p.is_relative_to(workspace.root) and not p.exists()]
        cursor = self.db.execute("INSERT INTO checkpoints(mission,root,path,before,new_dirs,after,done) VALUES(?,?,?,?,?,NULL,0)",
                                 (mission, str(workspace.root), target.relative_to(workspace.root).as_posix(), before, json.dumps(new_dirs)))
        self.db.commit()
        return cursor.lastrowid

    def seal(self, workspace, seq, path):
        self.db.execute("UPDATE checkpoints SET after=?, done=1 WHERE seq=?", (state(workspace, path), seq))
        self.db.commit()

    def paths(self, mission):
        """Files whose content now differs from what it was before the mission."""
        return sorted(item["path"] for item in self._pending(mission)[1] if item["current"] != item["original"])

    def diff(self, mission, limit=40000):
        """Unified diff from the pre-mission content to what is on disk now, for human review."""
        workspace, items, _ = self._pending(mission)
        chunks = []
        for item in sorted(items, key=lambda i: i["path"]):
            if item["current"] == item["original"] or item["current"] == "directory":
                continue
            before = (item["before"] or b"").decode("utf-8", errors="replace").splitlines()
            after = [] if item["current"] is None else workspace.load(item["path"]).decode("utf-8", errors="replace").splitlines()
            old = "/dev/null" if item["before"] is None else "a/" + item["path"]
            new = "/dev/null" if item["current"] is None else "b/" + item["path"]
            body = list(difflib.unified_diff(before, after, old, new, lineterm=""))
            chunks.append("\n".join(body or [f"--- {old}", f"+++ {new}"]))
        text = "\n".join(chunks)
        return text if len(text) <= limit else text[:limit] + "\n[diff truncated]"

    def _pending(self, mission):
        rows = self.db.execute("SELECT root,path,before,new_dirs,after,done FROM checkpoints WHERE mission=? ORDER BY seq", (mission,)).fetchall()
        if not rows:
            return None, [], set()
        workspace = Workspace(rows[0][0])
        items, new_dirs = {}, set()
        for _, path, before, dirs, after, done in rows:
            item = items.setdefault(path, {"path": path, "before": before, "original": None if before is None else digest(before)})
            item["after"], item["done"] = after, done
            new_dirs.update(json.loads(dirs))
        for item in items.values():
            item["current"] = state(workspace, item["path"])
        return workspace, list(items.values()), new_dirs

    def rollback(self, mission, force=False):
        """All or nothing: a file edited after the mission blocks the whole rollback unless forced."""
        workspace, items, new_dirs = self._pending(mission)
        if workspace is None:
            raise ValueError("no checkpoint for this mission")
        changed = [i for i in items if i["current"] != i["original"]]
        conflicts = sorted(i["path"] for i in changed
                           if i["current"] == "directory" or not i["done"] or i["current"] != i["after"])
        if conflicts and not force:
            return {"restored": [], "conflicts": conflicts}
        restored = []
        for item in changed:
            if item["current"] == "directory":
                continue
            target = workspace.path(item["path"])
            if item["before"] is None:
                target.unlink()
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                write_atomic(target, item["before"])
            restored.append(item["path"])
        for name in sorted(new_dirs, key=len, reverse=True):
            folder = workspace.path(name)
            if folder.is_dir() and not any(folder.iterdir()):
                folder.rmdir()
        self.db.execute("DELETE FROM checkpoints WHERE mission=?", (mission,))
        self.db.commit()
        return {"restored": sorted(restored), "conflicts": conflicts}
