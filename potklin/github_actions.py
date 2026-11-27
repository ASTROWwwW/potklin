"""Explicit GitHub CLI pull request creation. Uses existing user authentication."""
import re
import subprocess
from .git_actions import branch_name
from .programs import find_program

def create_pr(repository,head,base,title,body,confirmed=False):
    if not confirmed:
        raise PermissionError("explicit confirmation required")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",repository) or repository.startswith("-"):
        raise ValueError("invalid repository")
    head=branch_name(head)
    base=branch_name(base)
    if head==base or not title.strip() or len(title)>200 or len(body)>12000:
        raise ValueError("invalid pull request")
    gh=find_program("gh")
    # No shell, no push, no merge, no token retrieval.
    result=subprocess.run([gh,"pr","create","--repo",repository,"--head",head,"--base",base,"--title",title,"--body",body],capture_output=True,timeout=60,check=True,text=True)
    return {"output":result.stdout.strip(),"verified":False,"status":"PR creation requested; inspect returned URL"}
