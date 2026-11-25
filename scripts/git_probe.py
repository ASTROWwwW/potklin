"""Git mutations only in a freshly created disposable repository."""
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from potklin.git_actions import LocalGit

def main():
    git=shutil.which("git")
    if not git:
        raise FileNotFoundError("git")
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)
        def run(*a):
            subprocess.run([git,"-C",d,*a],check=True,capture_output=True,timeout=30)
        run("init")
        run("config","user.email","fixture@example.invalid")
        run("config","user.name","Potklin Fixture")
        run("config","commit.gpgsign","false")
        (p/"a.txt").write_text("before",encoding="utf8")
        run("add","a.txt")
        run("commit","-m","initial")
        g=LocalGit(p)
        old=g.status()["head"]
        g.branch("fixture/update",True)
        (p/"a.txt").write_text("after",encoding="utf8")
        result=g.commit(["a.txt"],"fixture update",True)
        passed=result["head"]!=old and result["branch"]=="fixture/update" and not result["changes"]
        print(json.dumps({"suite":"git_fixture","passed":passed,"result":result}))
        return int(not passed)
if __name__=="__main__":
    raise SystemExit(main())
