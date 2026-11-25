"""Bounded lexical search in user-selected trusted workspace."""
import os
from pathlib import Path
def search(workspace,path,query):
    if not query.strip() or len(query)>256:
        raise ValueError("invalid query")
    root=workspace.path(path)
    if not root.is_dir():
        raise ValueError("directory required")
    matches=[]
    visited=0
    scanned=0
    for base,dirs,names in os.walk(root,followlinks=False):
        dirs[:]=sorted(d for d in dirs if not d.startswith(".") and d not in {"node_modules","venv","__pycache__"} and not Path(base,d).is_symlink() and not getattr(Path(base,d),"is_junction",lambda:False)())
        for name in sorted(names):
            visited+=1
            if visited>2000 or scanned>=200 or len(matches)>=100:
                return {"matches":matches,"scanned":scanned,"truncated":True}
            if Path(name).suffix.lower() not in {".py",".txt",".md",".json",".html",".csv",".js",".ts",".lua",".c",".cpp",".h"}:
                continue
            rel=str(Path(base,name).relative_to(workspace.root))
            try:
                body=workspace.read(rel)["text"]
            except (OSError,ValueError,UnicodeError,PermissionError):
                continue
            scanned+=1
            for i,line in enumerate(body.splitlines(),1):
                if query.casefold() in line.casefold():
                    matches.append({"path":rel,"line":i,"text":line[:500]})
                    if len(matches)>=100:
                        return {"matches":matches,"scanned":scanned,"truncated":True}
    return {"matches":matches,"scanned":scanned,"truncated":False}
