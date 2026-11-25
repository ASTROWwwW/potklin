"""Bounded escalation with externally supplied objective verifier."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Attempt:
    think: bool
    steps: int

def solve(runner,request,mods,verify,attempts=(Attempt(False,6),Attempt(True,12))):
    if not 1<=len(attempts)<=3:
        raise ValueError("attempt budget")
    history=[]
    for a in attempts:
        result=runner.run(request,mods,a.steps,a.think)
        passed=bool(verify(result))
        history.append({"think":a.think,"steps":a.steps,"verified":passed,"result":result})
        if passed:
            break
    return {"verified":history[-1]["verified"],"attempts":history}
