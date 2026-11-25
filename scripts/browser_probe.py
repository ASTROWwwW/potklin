import tempfile
from pathlib import Path
import json
from potklin.mods import Workspace
from potklin.browser import exercise

def main():
    with tempfile.TemporaryDirectory() as d:
        (Path(d)/"fixture.html").write_text('<button id="go" onclick="document.getElementById(\'out\').textContent=\'verified\'">Go</button><p id="out">initial</p>',encoding="utf8")
        r=exercise(Workspace(d),"fixture.html","go","out")
        passed=r=={"before":"initial","after":"verified"}
        print(json.dumps({"suite":"browser","passed":passed,"result":r}))
        return int(not passed)
if __name__=="__main__":
    raise SystemExit(main())
