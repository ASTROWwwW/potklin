"""End-to-end mission tests on disposable local fixtures."""
import argparse
import json
import tempfile
from pathlib import Path
from potklin.core import Journal
from potklin.mods import build_registry
from potklin.mission import MissionRunner
from potklin.ollama import Ollama

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--model",required=True)
    p.add_argument("--repeats",type=int,default=5)
    a=p.parse_args()
    passed=total=0
    for i in range(a.repeats):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"notes.txt").write_text(f"fixture identifier K{i:04d}",encoding="utf8")
            (root/"sample.py").write_text("import hashlib\nhashlib.md5(b'fixture')\n",encoding="utf8")
            j=Journal(":memory:")
            try:
                runner=MissionRunner(build_registry(root),j,Ollama(a.model))
                for think in (False,True):
                    result=runner.run("First list directory ., then read notes.txt, then use cyber.ast_review on directory .; finally summarize the identifier and the static finding.",{"filesystem","cyber"},6,think)
                    observed={o["tool"] for o in result["observations"] if o.get("verified")}
                    ok=observed.issuperset({"files.list","files.read","cyber.ast_review"}) and result["status"]=="model_finished_unverified" and f"K{i:04d}" in (result["answer"] or "") and "CWE-327" in (result["answer"] or "")
                    total+=1
                    passed+=int(ok)
                    print(json.dumps({"run":i,"think":think,"oracle_pass":ok,"result":result},ensure_ascii=False),flush=True)
            finally:
                j.close()
    print(json.dumps({"summary":"v7_missions","passed":passed,"total":total}),flush=True)
    return int(passed!=total)
if __name__=="__main__":
    raise SystemExit(main())
