"""User-declared commands. The model picks a name; it never writes a command line.

This is not a sandbox: a command that runs workspace code runs whatever the mission wrote.
"""
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

NAME = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,39}")
SECRET = re.compile(r"TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|API_?KEY|PRIVATE_?KEY|ACCESS_?KEY|COOKIE|AUTH", re.I)
OUTPUT_TAIL = 4000


def clean_environment(source):
    env = {k: v for k, v in source.items() if not SECRET.search(k) and not k.upper().startswith("GIT_")}
    # Stale bytecode could make a test pass or fail against an older source.
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
    return env


def kill_tree(process):
    if sys.platform == "win32":
        taskkill = Path(os.environ["SystemRoot"]) / "System32" / "taskkill.exe"
        subprocess.run([str(taskkill), "/T", "/F", "/PID", str(process.pid)], capture_output=True, timeout=30)
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    process.kill()
    process.wait(timeout=30)


class CommandSet:
    def __init__(self, root, commands, timeout=120):
        self.root = Path(root).resolve(strict=True)
        if not 1 <= timeout <= 3600:
            raise ValueError("command timeout must be 1..3600 seconds")
        self.timeout = timeout
        if not isinstance(commands, dict) or not 1 <= len(commands) <= 32:
            raise ValueError("commands must be an object with 1..32 entries")
        self._commands = {name: self._resolve(name, argv) for name, argv in commands.items()}

    def _resolve(self, name, argv):
        if not NAME.fullmatch(name):
            raise ValueError("invalid command name: " + name)
        if not isinstance(argv, list) or not argv or any(not isinstance(a, str) or not a or "\x00" in a for a in argv):
            raise ValueError("command must be a non-empty list of strings: " + name)
        program = argv[0]
        if Path(program).is_absolute():
            found = program if Path(program).is_file() else None
        elif Path(program).name != program:
            raise ValueError("use a bare program name or an absolute path: " + name)
        else:
            found = shutil.which(program)
            # Windows searches the current directory first; a mission must not plant the program.
            if found and Path(found).resolve().is_relative_to(self.root):
                raise PermissionError("program resolves inside the workspace: " + program)
        if not found:
            raise ValueError("program not found: " + program)
        return (str(Path(found).absolute()), *argv[1:])

    @classmethod
    def load(cls, file, root, timeout=120):
        return cls(root, json.loads(Path(file).read_text(encoding="utf-8-sig")), timeout)

    @property
    def names(self):
        return sorted(self._commands)

    def run(self, name):
        if name not in self._commands:
            raise ValueError("unknown command; available: " + ", ".join(self.names))
        with tempfile.TemporaryFile() as sink:
            process = subprocess.Popen(self._commands[name], cwd=self.root, shell=False, stdin=subprocess.DEVNULL,
                                       stdout=sink, stderr=subprocess.STDOUT, env=clean_environment(os.environ),
                                       start_new_session=sys.platform != "win32")
            timed_out = False
            try:
                process.wait(timeout=self.timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                kill_tree(process)
            except BaseException:
                kill_tree(process)
                raise
            size = sink.seek(0, os.SEEK_END)
            sink.seek(max(0, size - OUTPUT_TAIL))
            output = sink.read().decode("utf-8", errors="replace")
        return {"name": name, "exit_code": -1 if timed_out else process.returncode, "timed_out": timed_out,
                "output": output, "output_truncated": size > OUTPUT_TAIL}
