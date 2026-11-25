"""Recursive read-only task decomposition with total node/depth limits."""
import json

def decompose(model,request,max_depth=2,max_nodes=12):
    if not 0<=max_depth<=3 or not 1<=max_nodes<=32 or not isinstance(request,str) or not request.strip() or len(request)>4000:
        raise ValueError("invalid decomposition budget")
    remaining=max_nodes
    seen=set()
    def walk(task,depth):
        nonlocal remaining
        remaining-=1
        seen.add(task.strip().casefold())
        if depth>=max_depth or remaining<=0:
            return {"task":task,"children":[]}
        r=model.chat([{"role":"system","content":"Decompose a read-only goal into at most three independent subgoals. Return JSON {children:[strings]} or empty list. Do not execute any actions."},{"role":"user","content":task}],structured=True,tokens=512)
        value=json.loads(r["message"]["content"])
        children=value.get("children") if isinstance(value,dict) and set(value)=={"children"} else None
        if not isinstance(children,list) or len(children)>3 or any(not isinstance(x,str) or not x.strip() or len(x)>1000 for x in children):
            raise ValueError("invalid decomposition")
        result=[]
        for child in children:
            if remaining<=0:
                break
            if child.strip().casefold() not in seen:
                result.append(walk(child,depth+1))
        return {"task":task,"children":result}
    return walk(request,0)

def leaves(tree):
    if not tree["children"]:
        return [tree["task"]]
    return [x for child in tree["children"] for x in leaves(child)]
