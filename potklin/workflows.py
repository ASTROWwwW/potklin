"""Developer-defined DAG execution, explicit operations, bounded scheduling."""
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from collections import deque
import time

@dataclass(frozen=True)
class Task:
    id: str
    tool: str
    args: dict
    depends: tuple[str,...]=()

def order(tasks):
    if len(tasks)>64:
        raise ValueError("too many tasks")
    by={t.id:t for t in tasks}
    if len(by)!=len(tasks) or any(not t.id for t in tasks):
        raise ValueError("duplicate or empty task id")
    if any(d not in by for t in tasks for d in t.depends):
        raise ValueError("unknown dependency")
    done=set()
    layers=[]
    while len(done)<len(by):
        ready=[t for t in tasks if t.id not in done and set(t.depends)<=done]
        if not ready:
            raise ValueError("cycle")
        layers.append(ready)
        done.update(t.id for t in ready)
    return layers

def execute(tasks,registry,mods,workers=4):
    """Parallel read-only calls; dependent work stops on failed verification."""
    if not 1<=workers<=8:
        raise ValueError("invalid worker count")
    allowed=registry.select(mods)
    layers=order(tasks)
    for t in tasks:
        tool=allowed.get(t.tool)
        if tool is None or tool.side_effect:
            raise PermissionError("workflow requires selected read-only tools")
        if not isinstance(t.args,dict) or set(t.args)!=set(tool.arguments) or any(not isinstance(v,str) or len(v)>8192 for v in t.args.values()):
            raise ValueError("invalid arguments")
    results={}
    def call(t):
        start=time.monotonic()
        try:
            tool=allowed[t.tool]
            value=tool.execute(**t.args)
            return {"status":"pass" if tool.verify(value,**t.args) else "unverified","result":value,"seconds":time.monotonic()-start}
        except Exception as e:
            return {"status":"failed","error":type(e).__name__}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for layer in layers:
            pending={}
            for t in layer:
                if any(results[d]["status"]!="pass" for d in t.depends):
                    results[t.id]={"status":"blocked"}
                else:
                    pending[t.id]=pool.submit(call,t)
            for key,future in pending.items():
                results[key]=future.result()
    return results
