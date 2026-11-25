"""Defensive security validation: deterministic isolated Python fixtures.
No network, target execution or exploit payloads.
"""
import ast
from dataclasses import dataclass

@dataclass(frozen=True)
class Finding:
    rule:str
    line:int
    evidence:str

def review_source(source):
    if len(source)>65536:
        raise ValueError("source exceeds budget")
    tree=ast.parse(source)
    out=[]
    for node in ast.walk(tree):
        if not isinstance(node,ast.Call):
            continue
        fn=node.func
        name=fn.attr if isinstance(fn,ast.Attribute) else fn.id if isinstance(fn,ast.Name) else ""
        if name in {"execute","executemany"} and node.args and isinstance(node.args[0],ast.JoinedStr):
            out.append(Finding("CWE-89",node.lineno,"formatted SQL expression; review parameterization"))
        if name in {"loads","load"} and isinstance(fn,ast.Attribute) and isinstance(fn.value,ast.Name) and fn.value.id=="pickle":
            out.append(Finding("CWE-502",node.lineno,"pickle deserialization; review data trust"))
        if name in {"md5","sha1"}:
            out.append(Finding("CWE-327",node.lineno,"weak hash; review security context"))
        if name in {"run","Popen","call"} and any(k.arg=="shell" and isinstance(k.value,ast.Constant) and k.value.value is True for k in node.keywords):
            out.append(Finding("CWE-78",node.lineno,"shell execution; review input handling"))
        if name in {"eval","exec"}:
            out.append(Finding("CWE-95",node.lineno,"dynamic evaluation; review trust"))
    return sorted(out,key=lambda x:(x.line,x.rule))

def authorization_oracle(policy):
    """Exercise a developer-supplied pure authorization function against a reference matrix."""
    cases=[]
    for role in ("viewer","editor","admin"):
        for owner in (False,True):
            for action in ("read","write","delete"):
                expected=action=="read" or role=="admin" or (action=="write" and role=="editor" and owner)
                actual=bool(policy(role,owner,action))
                cases.append({"role":role,"owner":owner,"action":action,"expected":expected,"actual":actual,"passed":actual==expected})
    return cases
