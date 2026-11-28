import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from potklin import profile
from potklin.__main__ import main


class Model:
    """Reads, fixes, then reports; ignores the connection settings the CLI passes."""
    def __init__(self, *args, **kwargs):
        self.replies = [{"name": "files.read", "args": {"path": "calc.py"}},
                        {"name": "files.create", "args": {"path": "extra.txt", "text": "x"}},
                        {"name": "files.replace", "args": {"path": "calc.py", "old": "a - b", "new": "a + b"}},
                        {"finish": "done"}]

    def chat(self, messages, **kwargs):
        return {"message": {"content": json.dumps(self.replies.pop(0))}}


class Profiles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name).resolve()
        self.workspace, self.outside = base / "project", base / "outside"
        self.workspace.mkdir()
        self.outside.mkdir()
        (self.workspace / "calc.py").write_bytes(b"def add(a, b):\n    return a - b\n")

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, data, folder=None):
        path = (folder or self.outside) / "profile.json"
        path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
        return str(path)

    def cli(self, *arguments):
        out, err = io.StringIO(), io.StringIO()
        argv = ["--workspace", str(self.workspace), "--journal", str(self.outside / "j.sqlite3"), "mission", "fix add", *arguments]
        with patch("potklin.__main__.Ollama", Model), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(argv)
        return code, out.getvalue(), err.getvalue()

    def scope(self, **extra):
        test = "import sys; sys.path.insert(0, '.'); from calc import add; assert add(2, 3) == 5"
        return {"only": ["calc.py"], "check": ["command:test"], "commands": {"test": [sys.executable, "-c", test]}, **extra}

    def test_profile_supplies_the_whole_scope(self):
        code, out, err = self.cli("--profile", self.write(self.scope()), "--allow-write", "--allow-exec")
        result = json.loads(out)
        self.assertEqual((code, result["status"], result["changes"]), (0, "verified", ["calc.py"]), err)
        self.assertFalse((self.workspace / "extra.txt").exists())

    def test_command_line_lists_add_to_the_profile(self):
        code, out, _ = self.cli("--profile", self.write(self.scope()), "--allow-write", "--allow-exec",
                                "--only", "extra.txt", "--check", "exists:extra.txt")
        result = json.loads(out)
        self.assertEqual((code, result["changes"]), (0, ["calc.py", "extra.txt"]))
        self.assertEqual([c["check"] for c in result["checks"]], ["command:test", "exists:extra.txt"])

    def test_a_profile_cannot_grant_permissions(self):
        for key in ("allow_write", "allow_exec", "allow_delete"):
            with self.subTest(key=key):
                code, _, err = self.cli("--profile", self.write({key: True}))
                self.assertEqual(code, 2)
                self.assertIn("command-line flags only", err)

    def test_commands_from_a_profile_still_need_allow_exec(self):
        code, _, err = self.cli("--profile", self.write(self.scope()), "--allow-write")
        self.assertEqual(code, 2)
        self.assertIn("--allow-exec", err)
        self.assertIn(b"a - b", (self.workspace / "calc.py").read_bytes())

    def test_profile_inside_the_workspace_is_refused(self):
        (self.workspace / ".potklin").mkdir()
        for folder in (self.workspace, self.workspace / ".potklin"):
            with self.subTest(folder=folder.name), self.assertRaises(PermissionError):
                profile.load(self.write(self.scope(), folder), self.workspace)

    def test_wrong_types_are_refused(self):
        for bad in ("[]", {"only": "calc.py"}, {"steps": "5"}, {"steps": True}, {"commands": []},
                    {"rollback_on_failure": 1}, {"check": [1]}, {"unknown": 1}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                profile.load(self.write(bad), self.workspace)

    def test_unknown_mod_in_a_profile_is_refused(self):
        code, _, err = self.cli("--profile", self.write({"mods": ["commands"]}))
        self.assertEqual(code, 2)
        self.assertIn("unknown mods", err)


if __name__ == "__main__":
    unittest.main()
