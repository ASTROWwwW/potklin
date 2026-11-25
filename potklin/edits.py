"""Explicit, compare-and-swap text edits in a trusted local workspace."""
import hashlib
import os
import tempfile

def digest(data):
    return hashlib.sha256(data).hexdigest()

def replace(workspace,path,expected_sha256,old,new):
    target=workspace.path(path)
    before=workspace.read(path)["text"]
    raw=target.read_bytes()
    if digest(raw)!=expected_sha256 or raw.decode("utf-8")!=before:
        raise ValueError("stale revision")
    if not old or before.count(old)!=1:
        raise ValueError("replacement must match once")
    after=before.replace(old,new,1).encode("utf-8")
    if len(after)>65536:
        raise ValueError("size limit")
    fd,name=tempfile.mkstemp(prefix=".potklin-",dir=target.parent)
    try:
        with os.fdopen(fd,"wb") as f:
            f.write(after)
            f.flush()
            os.fsync(f.fileno())
        if digest(target.read_bytes())!=expected_sha256:
            raise ValueError("stale revision")
        os.replace(name,target)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    return {"path":path,"sha256":digest(after)}
