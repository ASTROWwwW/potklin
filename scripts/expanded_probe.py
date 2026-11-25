"""Offline regression campaign with independent oracles, synthetic data only."""
import json
import tempfile
import time
from pathlib import Path
from statistics import median
from potklin.mods import build_registry
from potklin.workflows import Task,execute
from potklin.memory import Memory
from potklin.scheduling import select,reference_samples

def main():
    times=[]
    failures=0
    for i in range(100):
        start=time.perf_counter()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"a.py").write_text("def example():\n    return 1\n",encoding="utf8")
            (root/"b.py").write_text("import hashlib\nhashlib.md5(b'test')\n",encoding="utf8")
            (root/"notes.txt").write_text(f"fixture-{i}",encoding="utf8")
            result=execute([Task("read","files.read",{"path":"notes.txt"}),Task("code","coding.symbols",{"path":"a.py"}),Task("audit","cyber.ast_review",{"path":"."}),Task("list","files.list",{"path":"."},("read","code","audit"))],build_registry(root),{"filesystem","cyber","coding"})
            ok=all(x["status"]=="pass" for x in result.values())
            ok=ok and result["read"]["result"]["text"]==f"fixture-{i}" and result["code"]["result"]["symbols"][0]["name"]=="example" and any(x["rule"]=="CWE-327" for x in result["audit"]["result"]["findings"]) and set(result["list"]["result"]["entries"])=={"a.py","b.py","notes.txt"}
            failures+=int(not ok)
        times.append(time.perf_counter()-start)
    print(json.dumps({"suite":"parallel_dag","total":100,"passed":100-failures,"median_ms":median(times)*1000}))
    print(json.dumps({"suite":"reference_scheduler","solo":select(reference_samples()),"concurrent":select(reference_samples(),True),"measured_here":False}))
    return int(failures!=0)
if __name__=="__main__":
    raise SystemExit(main())
