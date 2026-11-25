"""Deterministic randomized DAG and boundary tests."""
import argparse
import json
import random
import tempfile
import time
from pathlib import Path
from potklin.mods import build_registry
from potklin.workflows import Task,execute,order
from potklin.core import Journal,Executor

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--cases",type=int,default=1000)
    a=p.parse_args()
    rng=random.Random(17391)
    failures=[]
    start=time.perf_counter()
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)
        (root/"ok.txt").write_text("fixture",encoding="utf8")
        r=build_registry(root)
        j=Journal(":memory:")
        try:
            ex=Executor(r,j)
            for i in range(a.cases):
                try:
                    n=rng.randint(2,12)
                    tasks=[]
                    for k in range(n):
                        deps=tuple(str(v) for v in range(k) if rng.random()<.2)
                        tasks.append(Task(str(k),"files.read",{"path":"ok.txt"},deps))
                    rng.shuffle(tasks)
                    result=execute(tasks,r,{"filesystem"})
                    assert len(result)==n and all(x["status"]=="pass" and x["result"]["text"]=="fixture" for x in result.values())
                    for path in ("../outside","C:\\Windows","file:stream"):
                        try:
                            ex.run("files.read",{"path":path},{"filesystem"})
                        except PermissionError:
                            pass
                        else:
                            raise AssertionError("boundary accepted")
                    try:
                        order([Task("a","x",{},("b",)),Task("b","x",{},("a",))])
                    except ValueError:
                        pass
                    else:
                        raise AssertionError("cycle accepted")
                except Exception as e:
                    failures.append({"case":i,"error":type(e).__name__})
        finally:
            j.close()
    print(json.dumps({"suite":"stress","total":a.cases,"passed":a.cases-len(failures),"failures":failures,"seconds":time.perf_counter()-start}))
    return int(bool(failures))
if __name__=="__main__":
    raise SystemExit(main())
