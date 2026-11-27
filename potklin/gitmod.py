"""Local repository inspection only. No hooks, network, credentials or writes."""
import os
import subprocess
from .programs import find_program

# Everything the file tools refuse to read must stay out of diffs too.
HIDDEN = (".env", ".env.*", ".vscode", ".idea", ".potklin")


def inspect(workspace, path):
    p = workspace.path(path)
    if not p.is_dir() or not (p / ".git").is_dir():
        raise ValueError("expected an ordinary local repository")
    # Avoid repository-controlled external diff, fsmonitor and optional index locks.
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
    git = find_program("git", workspace.root)

    def run(args):
        result = subprocess.run([git, "--no-pager", "-c", "core.fsmonitor=false", "-c", "core.hooksPath=" + os.devnull,
                                 "-c", "core.autocrlf=" + ("true" if os.name == "nt" else "false"), "-C", str(p), *args],
                                env=env, capture_output=True, timeout=15, check=True)
        return result.stdout[:16384].decode("utf-8", errors="replace")

    # Tracked secret files must not reach the model through a diff.
    visible = ["--", "."] + [f":(exclude,icase,glob)**/{name}{below}" for name in HIDDEN for below in ("", "/**")]
    return {"head": run(["rev-parse", "HEAD"]).strip(),
            "branch": run(["rev-parse", "--abbrev-ref", "HEAD"]).strip(),
            "status": run(["status", "--porcelain=v1", "--no-renames", "--untracked-files=normal", *visible]),
            "diff": run(["diff", "--no-ext-diff", "--no-textconv", "--no-renames", "HEAD", *visible])}
