"""Bounded hierarchical read-only mission execution with independent verification."""
from .decompose import decompose,leaves
def run(model,runner,request,mods,verify,depth=2,nodes=12,steps_per_leaf=6):
    if not 1<=steps_per_leaf<=12:raise ValueError("invalid leaf budget")
    plan=decompose(model,request,depth,nodes)
    tasks=leaves(plan)
    results=[]
    for task in tasks:
        value=runner.run(task,mods,steps_per_leaf,True)
        results.append({"task":task,"result":value})
    return {"plan":plan,"results":results,"verified":bool(verify(results))}
