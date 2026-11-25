"""Live recursive planning and verifier-driven retry on synthetic data."""
import argparse
import json
import tempfile
from pathlib import Path
from potklin.adaptive import solve
from potklin.decompose import decompose,leaves
from potklin.hierarchical import run as hierarchical
from potklin.core import Journal
from potklin.mods import build_registry
from potklin.mission import MissionRunner
from potklin.ollama import Ollama

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--model",required=True)
    a=p.parse_args()
    model=Ollama(a.model)
    goal="Find the identifier in the supplied workspace and report it exactly."
    plan=decompose(model,goal,1,4)
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp)/"record.txt").write_text("reference PK829471",encoding="utf8")
        j=Journal(":memory:")
        try:
            (Path(tmp)/"second.txt").write_text("second reference PK593248",encoding="utf8")
            result=solve(MissionRunner(build_registry(tmp),j,model),goal,{"filesystem"},lambda r:r["status"]=="model_finished_unverified" and "PK829471" in (r["answer"] or "") and any(o["tool"]=="files.read" and o.get("verified") and o.get("args",{}).get("path")=="record.txt" for o in r["observations"]))
            print(json.dumps({"suite":"adaptive","decomposition":plan,"leaf_count":len(leaves(plan)),"decomposition_executed":False,"result":result},ensure_ascii=False))
            h=hierarchical(model,MissionRunner(build_registry(tmp),j,model),"Read record.txt and second.txt and report both exact references.",{"filesystem"},lambda rows:all(any(marker in (x["result"].get("answer") or "") and any(o.get("args",{}).get("path")==path and o.get("verified") for o in x["result"].get("observations",[])) for x in rows) for marker,path in [("PK829471","record.txt"),("PK593248","second.txt")]),depth=1,nodes=4,steps_per_leaf=8)
            print(json.dumps({"suite":"hierarchical","result":h},ensure_ascii=False),flush=True)
            return int(not result["verified"] or not h["verified"])
        finally:
            j.close()
if __name__=="__main__":
    raise SystemExit(main())
