"""Bounded lexical search in user-selected trusted workspace."""
import os
from pathlib import Path
def search(workspace,path,query):
    if not query.strip() or len(query)>256:
        raise ValueError("invalid query")
    root=workspace.path(path)
    if not root.exists():
        raise ValueError("path does not exist")
    matches=[]
    visited=0
    scanned=0
    skipped=0
    def result(truncated):
        # skipped counts unreadable, protected or oversized files: no match there proves nothing.
        return {"matches":matches,"scanned":scanned,"skipped":skipped,"truncated":truncated}
    walk=[(str(root.parent),[],[root.name])] if root.is_file() else os.walk(root,followlinks=False)
    for base,dirs,names in walk:
        dirs[:]=sorted(d for d in dirs if not d.startswith(".") and d not in {"node_modules","venv","__pycache__"} and not Path(base,d).is_symlink() and not getattr(Path(base,d),"is_junction",lambda:False)())
        for name in sorted(names):
            visited+=1
            if visited>2000 or scanned>=200 or len(matches)>=100:
                return result(True)
            rel=str(Path(base,name).relative_to(workspace.root))
            try:
                body=workspace.load(rel).decode("utf-8")
                if "\x00" in body:
                    raise ValueError("binary file")
            except (OSError,ValueError,UnicodeError,PermissionError):
                skipped+=1
                continue
            scanned+=1
            for i,line in enumerate(body.splitlines(),1):
                if query.casefold() in line.casefold():
                    matches.append({"path":rel,"line":i,"text":line[:500]})
                    if len(matches)>=100:
                        return result(True)
    return result(False)
