"""Explicit opt-in launch plus independent visible-window observation."""
import argparse
import json
from potklin.windows import status,wait_visible
from potklin.mods import windows_launch

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--app",choices=["discord","notepad"],default="discord")
    p.add_argument("--launch",action="store_true")
    a=p.parse_args()
    before=status(a.app)
    requested=None
    if a.launch and not before["visible"]:
        requested=windows_launch(a.app)
    after=wait_visible(a.app) if requested else status(a.app)
    print(json.dumps({"before":before,"launch":requested,"after":after,"verified":after["visible"]}))
    return int(a.launch and not after["visible"])
if __name__=="__main__":
    raise SystemExit(main())
