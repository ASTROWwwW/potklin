"""Explicit user-facing commands for the advanced capabilities."""
import argparse
import json

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--model",default="huihui_ai/Qwen3.6-abliterated:35b-a3b")
    sub=p.add_subparsers(dest="command",required=True)
    b=sub.add_parser("browse")
    b.add_argument("url")
    b.add_argument("request")
    b.add_argument("--origin",action="append",required=True)
    d=sub.add_parser("decompose")
    d.add_argument("request")
    d.add_argument("--depth",type=int,default=2)
    d.add_argument("--nodes",type=int,default=12)
    s=sub.add_parser("sandbox")
    s.add_argument("fixture")
    s.add_argument("output")
    g=sub.add_parser("git")
    g.add_argument("root")
    g.add_argument("action",choices=["status","branch","commit"])
    g.add_argument("--name",default="")
    g.add_argument("--path",action="append",default=[])
    g.add_argument("--confirm",action="store_true")
    pr=sub.add_parser("pr")
    pr.add_argument("repository")
    pr.add_argument("head")
    pr.add_argument("base")
    pr.add_argument("title")
    pr.add_argument("--body",default="")
    pr.add_argument("--confirm",action="store_true")
    u=sub.add_parser("uia")
    u.add_argument("app",choices=["discord","notepad"])
    u.add_argument("--action",choices=["observe","invoke","set_text","click","press"],default="observe")
    u.add_argument("--id",default="")
    u.add_argument("--kind",default="Button")
    u.add_argument("--text",default="")
    u.add_argument("--confirm",action="store_true")
    a=p.parse_args()
    if a.command=="browse":
        from .browser_session import BrowserSession,Scope
        from .browser_agent import browse
        from .ollama import Ollama
        with BrowserSession(Scope.from_urls(a.origin)) as session:
            result=browse(session,Ollama(a.model),a.request,a.url)
    elif a.command=="decompose":
        from .decompose import decompose
        from .ollama import Ollama
        result=decompose(Ollama(a.model),a.request,a.depth,a.nodes)
    elif a.command=="sandbox":
        from .sandbox import config
        with open(a.output,"x",encoding="utf-8") as f:
            f.write(config(a.fixture))
        result={"created":a.output,"launched":False}
    elif a.command=="git":
        from .git_actions import LocalGit
        git=LocalGit(a.root)
        if a.action=="status":
            result=git.status()
        elif a.action=="branch":
            result=git.branch(a.name,a.confirm)
        else:
            result=git.commit(a.path,a.name,a.confirm)
    elif a.command=="pr":
        from .github_actions import create_pr
        result=create_pr(a.repository,a.head,a.base,a.title,a.body,a.confirm)
    elif a.command=="uia":
        if a.action=="observe":
            from .desktop import tree
            result=tree(a.app)
        else:
            from .desktop_actions import control
            result=control(a.app,a.id,a.kind,a.action,a.text,a.confirm)
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=="__main__":
    main()
