"""Offline dependency inventory; no network or package installation."""
import json
import tomllib

def inventory(workspace,path):
    text=workspace.read(path)["text"]
    if path.endswith("pyproject.toml"):
        data=tomllib.loads(text)
        items=data.get("project",{}).get("dependencies",[])
    elif path.endswith("package.json"):
        data=json.loads(text)
        items=[k+" "+str(v) for k,v in data.get("dependencies",{}).items()]
        items += [k+" "+str(v) for k,v in data.get("devDependencies",{}).items()]
    elif path.endswith(".txt"):
        items=[x.strip() for x in text.splitlines() if x.strip() and not x.lstrip().startswith("#")]
    else:
        raise ValueError("unsupported manifest")
    if not isinstance(items,list) or any(not isinstance(x,str) for x in items):
        raise ValueError("invalid dependency list")
    return {"path":path,"dependencies":sorted(items)[:500],"truncated":len(items)>500,"vulnerability_database_checked":False}
