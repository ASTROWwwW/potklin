"""Independent exact-answer reasoning tasks with seeded parameters."""
import argparse
import json
import random
import time
from collections import defaultdict
from statistics import median
from potklin.ollama import Ollama

def generate(rng,i):
    kind=i%5
    if kind==0:
        a,b,c,d=[rng.randrange(2,40) for _ in range(4)]
        return "arithmetic",f"Compute ({a}*{b}+{c}) modulo {d}. Return the integer only.",str((a*b+c)%d)
    if kind==1:
        x=[rng.randrange(1,100) for _ in range(8)]
        return "algorithm",f"Sort {x} ascending, then return the sum of the second and sixth elements. Integer only.",str(sorted(x)[1]+sorted(x)[5])
    if kind==2:
        a,b,c=[rng.randrange(2,20) for _ in range(3)]
        return "code_trace",f"Python: x={a}; for i in range({b}): x=(x+i*{c})%97. What is final x? Integer only.",str((a+c*b*(b-1)//2)%97)
    if kind==3:
        a,b,c=[rng.randrange(1,50) for _ in range(3)]
        return "constraints",f"A has {a} units, B has {b}, C has {c}. Move all B units to A, then move half of A rounded down to C. How many units are in C? Integer only.",str(c+(a+b)//2)
    values=[rng.randrange(1,30) for _ in range(5)]
    return "state",f"Start with balance 100. Apply changes {values} in order: add at even zero-based indexes, subtract at odd indexes. Final balance? Integer only.",str(100+sum(v if j%2==0 else -v for j,v in enumerate(values)))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--model",required=True)
    p.add_argument("--cases",type=int,default=100)
    p.add_argument("--seed",type=int,default=928317)
    a=p.parse_args()
    if not 1<=a.cases<=2000:
        p.error("invalid case count")
    rng=random.Random(a.seed)
    client=Ollama(a.model)
    stats=defaultdict(list)
    for i in range(a.cases):
        kind,question,expected=generate(rng,i)
        for think in (False,True):
            t=time.perf_counter()
            row={"case":i,"kind":kind,"think":think,"expected":expected}
            try:
                r=client.chat([{"role":"user","content":question}],think=think,tokens=4096 if think else 256)
                answer=r["message"]["content"].strip()
                row.update(answer=answer,passed=answer==expected,tokens=r.get("eval_count"),done_reason=r.get("done_reason"))
            except Exception as e:
                row.update(passed=False,error=type(e).__name__)
            row["seconds"]=time.perf_counter()-t
            stats[(kind,think)].append(row)
            print(json.dumps(row),flush=True)
    for (kind,think),rows in stats.items():
        print(json.dumps({"summary":kind,"think":think,"passed":sum(r["passed"] for r in rows),"total":len(rows),"median_s":median(r["seconds"] for r in rows)}),flush=True)
    return int(not all(r["passed"] for rows in stats.values() for r in rows))
if __name__=="__main__":
    raise SystemExit(main())
