"""Measure defensive static-review precision/recall on labeled synthetic snippets."""
import argparse
import json
import random
from potklin.advanced_lab import review_source
from potklin.ollama import Ollama
CASES=[
 ("import hashlib\ndef f(x): return hashlib.md5(x)",["CWE-327"]),
 ("import hashlib\ndef f(x): return hashlib.sha256(x)",[]),
 ("def f(db,x): return db.execute(f'SELECT {x}')",["CWE-89"]),
 ("def f(db,x): return db.execute('SELECT ?', (x,))",[]),
 ("import pickle\ndef f(x): return pickle.loads(x)",["CWE-502"]),
 ("import json\ndef f(x): return json.loads(x)",[]),
 ("# eval(user_input)\ndef f(x): return x",[]),
 ("def f(x): return eval(x)",["CWE-95"]),
 ("import subprocess\ndef f(x): return subprocess.run(x,shell=True)",["CWE-78"]),
 ("import subprocess\ndef f(x): return subprocess.run(['echo',x],shell=False)",[]),
 ("import hashlib\nimport pickle\ndef f(x): return hashlib.md5(pickle.loads(x))",["CWE-327","CWE-502"])
]
def metrics(rows):
    tp=sum(len(set(r["expected"])&set(r["actual"])) for r in rows)
    fp=sum(len(set(r["actual"])-set(r["expected"])) for r in rows)
    fn=sum(len(set(r["expected"])-set(r["actual"])) for r in rows)
    return {"tp":tp,"fp":fp,"fn":fn,"precision":tp/(tp+fp) if tp+fp else None,"recall":tp/(tp+fn) if tp+fn else None,"exact":sum(set(r["expected"])==set(r["actual"]) and not r.get("error") for r in rows),"total":len(rows)}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--model",default="")
    p.add_argument("--repeats",type=int,default=5)
    a=p.parse_args()
    if not 1<=a.repeats<=50:
        p.error("invalid repeats")
    rng=random.Random(2481)
    client=Ollama(a.model) if a.model else None
    rows={"static":[],"fast":[],"think":[]}
    for i in range(a.repeats):
        cases=list(CASES)
        rng.shuffle(cases)
        for source,expected in cases:
            source="\n"*rng.randrange(5)+source
            row={"expected":expected,"actual":[f.rule for f in review_source(source)]}
            rows["static"].append(row)
            if client:
                for think in (False,True):
                    try:
                        r=client.chat([{"role":"user","content":"Defensive source review: identify only the following static leads if present: CWE-327 weak hash, CWE-89 formatted SQL, CWE-502 pickle, CWE-95 eval, CWE-78 shell=True. Do not infer exploitability. JSON {rules:[CWE strings]}. Source:\n"+source}],think=think,tokens=4096 if think else 256,structured=True)
                        result=json.loads(r["message"]["content"])["rules"]
                        if not isinstance(result,list) or any(not isinstance(x,str) for x in result):
                            raise ValueError("invalid rules")
                        row={"expected":expected,"actual":result}
                    except Exception as e:
                        row={"expected":expected,"actual":[],"error":type(e).__name__}
                    rows["think" if think else "fast"].append(row)
                    print(json.dumps({"mode":"think" if think else "fast",**row}),flush=True)
    for mode,data in rows.items():
        if data:
            print(json.dumps({"summary":mode,**metrics(data)}),flush=True)
    return int(any(metrics(data)["exact"]!=len(data) for data in rows.values() if data))
if __name__=="__main__":
    raise SystemExit(main())
