"""Observe a selected existing window without reading its text values."""
import argparse
import json
from potklin.desktop import tree

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--app",choices=["discord","notepad"],default="discord")
    a=p.parse_args()
    r=tree(a.app)
    print(json.dumps({"suite":"desktop_uia","observed":bool(r["windows"]),"result":r}))
    raise SystemExit(int(not r["windows"]))
