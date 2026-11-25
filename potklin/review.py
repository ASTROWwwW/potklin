"""Bounded AST review of local Python source; findings are static leads."""
import ast
import os
from pathlib import Path

def review(workspace, path):
    root=workspace.path(path)
    if not root.is_dir():
        raise ValueError("review requires directory")
    findings=[]
    parsed=skipped=visited=0
    for base,dirs,names in os.walk(root,followlinks=False):
        dirs[:]=sorted(d for d in dirs if not d.startswith(".") and d not in {"venv","node_modules","__pycache__"} and not Path(base,d).is_symlink() and not getattr(Path(base,d),"is_junction",lambda:False)())
        for name in sorted(names):
            visited+=1
            if visited>2000 or parsed>=200:
                return {"parsed":parsed,"skipped":skipped,"findings":findings,"truncated":True}
            if not name.endswith(".py"):
                continue
            rel=str(Path(base,name).relative_to(workspace.root))
            try:
                tree=ast.parse(workspace.read(rel)["text"])
            except (OSError,ValueError,PermissionError,UnicodeError,SyntaxError,RecursionError):
                skipped+=1
                continue
            parsed+=1
            for node in ast.walk(tree):
                if not isinstance(node,ast.Call):
                    continue
                fn=node.func
                name=fn.id if isinstance(fn,ast.Name) else fn.attr if isinstance(fn,ast.Attribute) else ""
                rule=None
                if name in {"eval","exec"}:
                    rule="CWE-95"
                elif name in {"md5","sha1"}:
                    rule="CWE-327"
                elif name in {"run","Popen","call","check_call","check_output"} and any(k.arg=="shell" and isinstance(k.value,ast.Constant) and k.value.value is True for k in node.keywords):
                    rule="CWE-78"
                elif name in {"execute","executemany"} and node.args and isinstance(node.args[0],ast.JoinedStr):
                    rule="CWE-89"
                if rule and len(findings)<500:
                    findings.append({"path":rel,"line":node.lineno,"rule":rule,"status":"unverified","method":"ast"})
    return {"parsed":parsed,"skipped":skipped,"findings":sorted(findings,key=lambda x:(x["path"],x["line"],x["rule"])),"truncated":False}
