"""Real fixture-based integration tests plus local-model planning. No personal files."""
import argparse
import json
import tempfile
import time
from pathlib import Path
from potklin.core import Executor, Journal
from potklin.mods import build_registry
from potklin.ollama import Ollama
from potklin.router import route

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--model",required=True)
    p.add_argument("--repeats",type=int,default=5)
    args=p.parse_args()
    with tempfile.TemporaryDirectory(prefix="potklin-fixture-") as tmp:
        root=Path(tmp)
        (root/"sample.py").write_text("import hashlib\nvalue=hashlib.md5(b'fixture')\n",encoding="utf-8")
        (root/"notes.txt").write_text("POTKLIN_TEST_37",encoding="utf-8")
        j=Journal(":memory:")
        try:
            registry=build_registry(root)
            ex=Executor(registry,j)
            client=Ollama(args.model)
            cases=[("Read notes.txt","files.read",{"path":"notes.txt"},{"filesystem"}),("List directory .","files.list",{"path":"."},{"filesystem"}),("Review Python source in directory . for risky patterns","cyber.audit",{"path":"."},{"cyber"})]
            total = passed = 0
            for i in range(args.repeats):
                for request,name,expected,mods in cases:
                    t=time.perf_counter()
                    row={"run":i,"case":name}
                    try:
                        plan=client.propose(request,registry.select(mods))
                        row["plan"]=plan
                        row["exact"]=plan=={"name":name,"args":expected}
                        if row["exact"]:
                            result=ex.run(name,expected,mods)
                            value=result["result"]
                            oracle=(value.get("text")=="POTKLIN_TEST_37" if name=="files.read" else set(value.get("entries",[]))=={"sample.py","notes.txt"} if name=="files.list" else any(f["rule"]=="CWE-327" for f in value["findings"]))
                            row["verified"]=result["verified"] and oracle
                        else:
                            row["verified"]=False
                    except Exception as e:
                        row.update(error=type(e).__name__,verified=False)
                    row["seconds"]=time.perf_counter()-t
                    total += 1
                    passed += int(row['verified'])
                    print(json.dumps(row),flush=True)
            start=time.perf_counter_ns()
            for _ in range(10000):
                assert route("Lance Discord")["args"]["app"]=="discord"
            print(json.dumps({"benchmark":"native_route","iterations":10000,"mean_us":(time.perf_counter_ns()-start)/10000/1000}),flush=True)
            print(json.dumps({'summary':'fixture_tasks','passed':passed,'total':total}),flush=True)
            return 0 if passed == total else 1
        finally:
            j.close()
if __name__=="__main__":
    raise SystemExit(main())
