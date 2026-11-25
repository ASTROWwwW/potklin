"""Paired local Ollama inference configuration measurements, no hardware changes."""
import argparse
import json
import random
import time
from statistics import median
from potklin.ollama import Ollama

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--model",required=True)
    p.add_argument("--repeats",type=int,default=3)
    p.add_argument("--contexts",nargs="+",type=int,default=[4096,8192,16384])
    p.add_argument("--threads",nargs="+",type=int,default=[4,8,16])
    a=p.parse_args()
    if not 1<=a.repeats<=20 or any(c not in {2048,4096,8192,16384,32768} for c in a.contexts) or any(not 1<=t<=32 for t in a.threads):
        p.error("configuration outside test bounds")
    configs=[(c,t) for c in a.contexts for t in a.threads]
    random.Random(42).shuffle(configs)
    prompt="Write a technical explanation of why regression tests matter. Use at least 300 words, no code."
    for c,t in configs:
        rows=[]
        client=Ollama(a.model,context=c,threads=t)
        for i in range(a.repeats+1):
            start=time.perf_counter()
            try:
                r=client.chat([{"role":"user","content":prompt}],think=False,tokens=512)
                n=r.get("eval_count",0)
                d=r.get("eval_duration",0)
                row={"ctx":c,"threads":t,"run":i,"warmup":i==0,"seconds":time.perf_counter()-start,"tokens":n,"tps":n*1e9/d if d else None,"load_s":r.get("load_duration",0)/1e9,"prompt_tokens":r.get("prompt_eval_count"),"valid":n>=128 and d>0}
            except Exception as e:
                row={"ctx":c,"threads":t,"run":i,"warmup":i==0,"valid":False,"error":type(e).__name__}
            print(json.dumps(row),flush=True)
            if i and row["valid"]:
                rows.append(row["tps"])
        print(json.dumps({"summary":"inference_matrix","ctx":c,"threads":t,"valid_repeats":len(rows),"median_tps":median(rows) if rows else None}),flush=True)
    return 0
if __name__=="__main__":
    raise SystemExit(main())
