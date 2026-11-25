"""Constrained code-repair tests: evaluate model expressions with a safe AST interpreter.
No eval, exec, imports, calls, attributes or model-generated process execution.
"""
import argparse
import ast
import json
import operator
import random
import time
from collections import defaultdict
from potklin.ollama import Ollama

BIN={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.FloorDiv:operator.floordiv,ast.Mod:operator.mod}
CMP={ast.Lt:operator.lt,ast.LtE:operator.le,ast.Gt:operator.gt,ast.GtE:operator.ge,ast.Eq:operator.eq,ast.NotEq:operator.ne}

def expression(text):
    if not isinstance(text,str) or not 1<=len(text)<=256:
        raise ValueError("invalid expression")
    root=ast.parse(text,mode="eval")
    if len(list(ast.walk(root)))>64:
        raise ValueError("expression too complex")
    def check(n):
        if isinstance(n,ast.Constant) and type(n.value) is int and abs(n.value)<=100000:
            return
        if isinstance(n,ast.Name) and n.id in {"x","y","n"}:
            return
        if isinstance(n,ast.BinOp) and type(n.op) in BIN:
            check(n.left);check(n.right);return
        if isinstance(n,ast.UnaryOp) and isinstance(n.op,ast.USub):
            check(n.operand);return
        if isinstance(n,ast.Compare) and len(n.ops)==1 and type(n.ops[0]) in CMP:
            check(n.left);check(n.comparators[0]);return
        if isinstance(n,ast.IfExp):
            check(n.test);check(n.body);check(n.orelse);return
        raise ValueError("unsupported expression")
    check(root.body)
    def calc(n,env):
        if isinstance(n,ast.Constant):return n.value
        if isinstance(n,ast.Name):return env[n.id]
        if isinstance(n,ast.BinOp):
            v=BIN[type(n.op)](calc(n.left,env),calc(n.right,env))
            if abs(v)>10**12:raise ValueError("numeric limit")
            return v
        if isinstance(n,ast.UnaryOp):return -calc(n.operand,env)
        if isinstance(n,ast.Compare):return CMP[type(n.ops[0])](calc(n.left,env),calc(n.comparators[0],env))
        if isinstance(n,ast.IfExp):return calc(n.body if calc(n.test,env) else n.orelse,env)
        raise ValueError("invalid expression")
    return lambda env:calc(root.body,env)

def case(i,rng):
    threshold=rng.randint(3,80)
    kind=i%5
    if kind==0:
        return "ceil_div","Return the corrected expression for ceil(x/y), x>=0, y>0. Bug: x//y. Use only x,y,n and arithmetic/conditionals.",lambda x,y,n:(x+y-1)//y
    if kind==1:
        return "clamp",f"Return the corrected expression clamping x to inclusive [0,{threshold}]. Bug: x if x < {threshold} else {threshold}.",lambda x,y,n:max(0,min(x,threshold))
    if kind==2:
        return "discount",f"Apply a {threshold}% discount to nonnegative integer x, rounding final price down. Bug: x-x*{threshold}//100.",lambda x,y,n:x*(100-threshold)//100
    if kind==3:
        return "pagination","Return zero-based last page index for n items, y items per page. Return 0 when n=0. Bug: n//y.",lambda x,y,n:max(0,(n-1)//y)
    return "bounded_subtract",f"Subtract y from x but never return less than {threshold}. Bug: x-y.",lambda x,y,n:max(threshold,x-y)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--model",required=True)
    p.add_argument("--cases",type=int,default=100)
    p.add_argument("--seed",type=int,default=615781)
    a=p.parse_args()
    if not 1<=a.cases<=2000:p.error("invalid cases")
    rng=random.Random(a.seed)
    model=Ollama(a.model)
    rows=defaultdict(list)
    for i in range(a.cases):
        kind,prompt,oracle=case(i,rng)
        inputs=[(x,y,n) for x in (0,1,2,99,100,101) for y in (1,2,7,100) for n in (0,1,7,8,100)]
        inputs += [(rng.randint(0,10000),rng.randint(1,100),rng.randint(0,10000)) for _ in range(100)]
        if kind in {"clamp","bounded_subtract"}:inputs += [(-x,y,n) for x,y,n in inputs[:100]]
        for think in (False,True):
            t=time.perf_counter()
            row={"case":i,"kind":kind,"think":think,"property_cases":len(inputs)}
            try:
                response=model.chat([{"role":"user","content":prompt+" Return JSON {expression:string}. No function calls, only Python arithmetic, comparisons and conditional expressions."}],think=think,tokens=4096 if think else 256,structured=True)
                text=json.loads(response["message"]["content"])["expression"]
                fn=expression(text)
                passed=sum(fn({"x":x,"y":y,"n":n})==oracle(x,y,n) for x,y,n in inputs)
                row.update(expression=text,property_passed=passed,passed=passed==len(inputs))
            except Exception as e:
                row.update(passed=False,error=type(e).__name__)
            row["seconds"]=time.perf_counter()-t
            rows[(kind,think)].append(row)
            print(json.dumps(row),flush=True)
    for (kind,think),data in rows.items():
        print(json.dumps({"summary":kind,"think":think,"passed":sum(r["passed"] for r in data),"total":len(data),"property_checks":sum(r["property_cases"] for r in data),"property_passed":sum(r.get("property_passed",0) for r in data)}),flush=True)
    return int(not all(r["passed"] for data in rows.values() for r in data))
if __name__=="__main__":
    raise SystemExit(main())
