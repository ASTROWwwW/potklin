"""Long-context retrieval with exact randomized identifiers and distractors."""
import argparse
import json
import random
import time
from potklin.ollama import Ollama

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--model",required=True)
    p.add_argument("--repeats",type=int,default=3)
    a=p.parse_args()
    if not 1<=a.repeats<=20:p.error("invalid repeat count")
    rng=random.Random(78129)
    failures=0
    for ctx in (4096,8192,16384,32768):
        for position in (.1,.5,.9):
            for i in range(a.repeats):
                marker="PK"+str(rng.randrange(100000000,999999999))
                target="case-"+str(rng.randrange(100000,999999))
                # Character-based budget, report actual token count from Ollama.
                ids=rng.sample([x for x in range(100000,105000) if "case-"+str(x)!=target],max(20,ctx//25))
                lines=[f"record case-{v} status normal value PK{rng.randrange(100000000,999999999)}" for v in ids]
                lines.insert(int(len(lines)*position),f"record {target} status confirmed value {marker}")
                prompt="Find the value for exact record "+target+". Return only its value.\n"+"\n".join(lines)
                t=time.perf_counter()
                try:
                    r=Ollama(a.model,context=ctx).chat([{"role":"user","content":prompt}],tokens=64)
                    answer=r["message"]["content"].strip()
                    row={"ctx":ctx,"position":position,"run":i,"characters":len(prompt),"prompt_tokens":r.get("prompt_eval_count"),"passed":answer==marker,"expected":marker,"answer":answer,"seconds":time.perf_counter()-t}
                except Exception as e:
                    row={"ctx":ctx,"position":position,"run":i,"passed":False,"error":type(e).__name__}
                failures+=int(not row["passed"])
                print(json.dumps(row),flush=True)
    return int(bool(failures))
if __name__=="__main__":
    raise SystemExit(main())
