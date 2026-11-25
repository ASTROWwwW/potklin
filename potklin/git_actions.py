"""Explicit trusted-checkout Git actions, no model-generated command strings."""
import os
import re
import shutil
import subprocess
from pathlib import Path

def branch_name(value):
    if not isinstance(value,str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9/_-]{0,79}",value) or ".." in value or "//" in value or value.endswith("/"):
        raise ValueError("invalid branch")
    return value

class LocalGit:
    def __init__(self,root):
        self.root=Path(root).resolve(strict=True)
        if not (self.root/".git").is_dir():
            raise ValueError("trusted ordinary checkout required")
        self.git=shutil.which("git")
        if not self.git:
            raise FileNotFoundError("git")
        self.env={k:v for k,v in os.environ.items() if not k.upper().startswith("GIT_")}
        self.env.update(GIT_CONFIG_NOSYSTEM="1",GIT_CONFIG_GLOBAL=os.devnull,GIT_TERMINAL_PROMPT="0")
    def _run(self,*args):
        proc=subprocess.run([self.git,"--no-pager","-c","core.hooksPath="+os.devnull,"-c","core.fsmonitor=false","-c","commit.gpgsign=false","-C",str(self.root),*args],env=self.env,capture_output=True,timeout=30,check=True)
        return proc.stdout.decode("utf-8",errors="replace").strip()
    def status(self):
        return {"head":self._run("rev-parse","HEAD"),"branch":self._run("branch","--show-current"),"changes":self._run("status","--porcelain=v1","--untracked-files=no")}
    def branch(self,name,confirmed=False):
        if not confirmed:
            raise PermissionError("explicit confirmation required")
        name=branch_name(name)
        if self._run("status","--porcelain=v1"):
            raise ValueError("checkout not clean")
        self._run("switch","-c",name)
        return self.status()
    def commit(self,paths,message,confirmed=False):
        if not confirmed:
            raise PermissionError("explicit confirmation required")
        if not paths or len(paths)>32 or not message.strip() or len(message)>300:
            raise ValueError("invalid commit")
        if self._run("diff","--cached","--name-only"):
            raise ValueError("preexisting staged changes")
        safe=[]
        for value in paths:
            p=Path(value)
            if p.is_absolute() or p.anchor or ".." in p.parts or ":" in value or p.parts[0]==".git" or value.startswith("-"):
                raise ValueError("invalid path")
            target=(self.root/p).resolve(strict=True)
            if not target.is_file() or not target.is_relative_to(self.root):
                raise ValueError("outside checkout")
            safe.append(str(p))
        self._run("--literal-pathspecs","add","--",*safe)
        self._run("commit","-m",message)
        return self.status()
