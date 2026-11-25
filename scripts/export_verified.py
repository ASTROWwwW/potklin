"""Export reviewed synthetic evaluation trajectories; never train automatically."""
import argparse
import json
from pathlib import Path

def export(source,destination):
    count=0
    with open(source,encoding="utf-8-sig") as src,open(destination,"x",encoding="utf-8") as dst:
        for line in src:
            try:
                r=json.loads(line)
            except ValueError:
                continue
            if r.get("pass") is not True or not r.get("checks") or not all(r["checks"].values()):
                continue
            if not isinstance(r.get("answer"),str) or not isinstance(r.get("observations"),list):
                continue
            # Not a training-ready chat transcript: preserve evidence and case metadata for review.
            dst.write(json.dumps({"case":r["case"],"kind":r["kind"],"answer":r["answer"],"observations":r["observations"],"review_required":True},ensure_ascii=False)+"\n")
            count+=1
    return count
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("source")
    p.add_argument("destination")
    a=p.parse_args()
    print(json.dumps({"exported":export(a.source,a.destination),"training_started":False}))
