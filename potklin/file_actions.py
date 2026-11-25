"""Explicit filesystem actions in a trusted workspace, no implicit overwrite."""
import hashlib
def create(workspace,path,text):
    target=workspace.path(path)
    raw=text.encode("utf-8")
    if len(raw)>65536:raise ValueError("size limit")
    if not target.parent.is_dir():raise ValueError("parent directory missing")
    with target.open("xb") as out:
        out.write(raw)
    return {"path":path,"sha256":hashlib.sha256(raw).hexdigest()}
def move(workspace,source,destination,expected_sha256):
    a=workspace.path(source);b=workspace.path(destination)
    raw=workspace.read(source)["text"].encode("utf-8")
    if hashlib.sha256(raw).hexdigest()!=expected_sha256:raise ValueError("stale revision")
    if a==b or b.exists():raise ValueError("destination exists")
    # Exclusive destination creation; remove only the specific verified source.
    with b.open("xb") as out:out.write(raw)
    if hashlib.sha256(a.read_bytes()).hexdigest()!=expected_sha256:
        b.unlink()
        raise ValueError("source changed")
    try:a.unlink()
    except OSError:
        b.unlink()
        raise
    return {"source":source,"destination":destination,"sha256":expected_sha256}
def remove(workspace,path,expected_sha256):
    target=workspace.path(path)
    raw=workspace.read(path)["text"].encode("utf-8")
    if hashlib.sha256(raw).hexdigest()!=expected_sha256:raise ValueError("stale revision")
    target.unlink()
    return {"path":path,"removed":True}
