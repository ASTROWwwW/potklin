"""Harder exact-oracle tasks: graph paths, transaction replay, code diagnosis, security review.
Seeded synthetic tasks, not a public benchmark. No generated code is executed.
"""
import argparse
import json
import random
import time
import heapq
from collections import defaultdict
from statistics import median
from potklin.ollama import Ollama

def shortest(edges,n):
    dist=[float("inf")]*n
    dist[0]=0
    q=[(0,0)]
    while q:
        d,u=heapq.heappop(q)
        if d!=dist[u]:
            continue
        for a,b,w in edges:
            if a==u and d+w<dist[b]:
                dist[b]=d+w
                heapq.heappush(q,(d+w,b))
    return dist[-1]

def generate(rng,i):
    kind=i%5
    if kind==0:
        n=rng.randrange(7,11)
        edges=[(k,k+1,rng.randrange(1,15)) for k in range(n-1)]
        edges.extend((a,b,rng.randrange(1,30)) for a in range(n) for b in range(n) if a!=b and rng.random()<.22)
        rng.shuffle(edges)
        return "graph",f"Directed weighted edges (source,target,cost): {edges}. Compute shortest distance from 0 to {n-1}. Return JSON {{answer:integer}}.",shortest(edges,n)
    if kind==1:
        balance=100
        seen=set()
        ops=[]
        for _ in range(20):
            key=rng.randrange(1,14)
            delta=rng.randrange(-30,31)
            ops.append((key,delta))
            if key not in seen:
                seen.add(key)
                if balance+delta>=0:
                    balance+=delta
        return "ledger",f"Initial balance 100. Process events {ops} in order. Every first-seen ID is permanently recorded even if rejected. Reject duplicates and any delta making balance negative. Return JSON {{answer:integer}} with final balance.",balance
    if kind==2:
        x=[rng.randrange(-8,10) for _ in range(10)]
        limit=rng.randrange(1,12)
        expected=sum(v for v in x if v>0 and v%2==0 and v<limit)
        return "code_repair",f"Function should sum positive even values strictly below {limit}. Buggy code: sum(v for v in values if v>=0 and v%2==0 and v<={limit}). Which two comparisons must be corrected? Choose exact option A: >= to > and <= to <; B: >= to > only; C: <= to < only; D: %2==0 to %2!=0. Then compute corrected result on {x}. Return JSON {{answer:[option,integer]}}.",["A",expected]
    if kind==3:
        rows=[(rng.choice(["viewer","editor","admin"]),rng.choice([True,False]),rng.choice(["read","write","delete"])) for _ in range(15)]
        expected=[j for j,(role,owner,act) in enumerate(rows) if act=="read" or role=="admin" or (act=="write" and role=="editor" and owner)]
        return "authorization",f"Policy: read all; admin all; editor may write only owned resources; no other permissions. Indexed requests starting at 0: {rows}. Return JSON {{answer:[allowed indexes ascending]}}.",expected
    rows=[(k,rng.randrange(10,90),rng.randrange(1,8)) for k in range(8)]
    stock=[(k,rng.randrange(0,10)) for k in range(8)]
    rng.shuffle(stock)
    expected=sum(price*min(q,dict(stock)[k]) for k,price,q in rows)
    return "data_join",f"Orders (id,unit price,quantity): {rows}; stock (id,available): {stock}. Fulfill min(quantity,available) for each id. Compute total revenue. Return JSON {{answer:integer}}.",expected

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--model",required=True)
    p.add_argument("--cases",type=int,default=100)
    p.add_argument("--seed",type=int,default=873246)
    a=p.parse_args()
    if not 1<=a.cases<=2000:
        p.error("invalid cases")
    rng=random.Random(a.seed)
    client=Ollama(a.model)
    stats=defaultdict(list)
    for i in range(a.cases):
        kind,prompt,expected=generate(rng,i)
        for think in (False,True):
            t=time.perf_counter()
            row={"case":i,"kind":kind,"think":think,"expected":expected}
            try:
                result=client.chat([{"role":"user","content":prompt}],think=think,tokens=6144 if think else 512,structured=True)
                obj=json.loads(result["message"]["content"])
                answer=obj.get("answer") if isinstance(obj,dict) else None
                row.update(answer=answer,passed=type(answer)==type(expected) and answer==expected,tokens=result.get("eval_count"),done_reason=result.get("done_reason"))
            except Exception as e:
                row.update(passed=False,error=type(e).__name__)
            row["seconds"]=time.perf_counter()-t
            stats[(kind,think)].append(row)
            print(json.dumps(row),flush=True)
    for (kind,think),rows in stats.items():
        print(json.dumps({"summary":kind,"think":think,"total":len(rows),"passed":sum(r["passed"] for r in rows),"median_s":median(r["seconds"] for r in rows)}),flush=True)
    return int(not all(r["passed"] for rows in stats.values() for r in rows))
if __name__=="__main__":
    raise SystemExit(main())
