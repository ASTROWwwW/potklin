import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from potklin.core import Executor, Journal, Registry, Tool
from potklin.mods import build_registry, Workspace
from potklin.ollama import Ollama

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "fixture.py").write_text("subprocess.run(cmd, shell=True)\n", encoding="utf-8")
        self.j = Journal(":memory:")
        self.r = build_registry(self.root)
        self.e = Executor(self.r, self.j)

    def tearDown(self):
        self.j.close()
        self.temp.cleanup()

    def test_read_verified(self):
        x = self.e.run("files.read", {"path":"fixture.py"}, {"filesystem"})
        self.assertTrue(x["verified"])
        self.assertIn("shell=True", x["result"]["text"])

    def test_list(self):
        self.assertEqual(self.e.run("files.list", {"path":"."}, {"filesystem"})["result"]["entries"], ["fixture.py"])

    def test_audit_unverified_finding(self):
        x = self.e.run("cyber.audit", {"path":"."}, {"cyber"})
        self.assertTrue(x["verified"])
        self.assertEqual(x["result"]["findings"][0]["status"], "unverified")

    def test_wrong_mod(self):
        with self.assertRaises(PermissionError):
            self.e.run("files.read", {"path":"fixture.py"}, {"cyber"})

    def test_traversal(self):
        with self.assertRaises(PermissionError):
            self.e.run("files.read", {"path":"../outside"}, {"filesystem"})

    def test_absolute_outside(self):
        with self.assertRaises(PermissionError):
            Workspace(self.root).path(str(self.root.parent))

    def test_schema(self):
        for args in ({}, {"path":4}, {"path":"x","extra":"y"}, {"path":"x"*8193}):
            with self.subTest(args=str(args)[:80]), self.assertRaises(ValueError):
                self.e.run("files.read", args, {"filesystem"})

    def test_side_effect_permission(self):
        with self.assertRaises(PermissionError):
            self.e.run("windows.launch", {"app":"discord"}, {"windows"})

    def test_unknown_tool(self):
        with self.assertRaises(PermissionError):
            self.e.run("shell.exec", {}, {"windows"})

    def test_duplicate(self):
        r = Registry()
        t = Tool("x","m","x",(),lambda:1,lambda v:True)
        r.register(t)
        with self.assertRaises(ValueError):
            r.register(t)

    def test_failure_journal(self):
        with self.assertRaises(ValueError):
            self.e.run("files.read", {"path":"missing"}, {"filesystem"})
        self.assertEqual([x[0] for x in self.j.db.execute("SELECT kind FROM events ORDER BY seq")], ["started","failed"])

    def test_journal_no_content(self):
        self.e.run("files.read", {"path":"fixture.py"}, {"filesystem"})
        self.assertNotIn("shell=True", str(self.j.db.execute("SELECT payload FROM events").fetchall()))

    def test_model_plan_no_execution(self):
        with patch.object(Ollama, "chat", return_value={"message":{"content":json.dumps({"name":"files.read","args":{"path":"fixture.py"}})}}):
            x = Ollama("fake").propose("read", self.r.select({"filesystem"}))
        self.assertEqual(x["name"], "files.read")
        self.assertEqual(self.j.db.execute("SELECT COUNT(*) FROM events").fetchone()[0], 0)

    def test_bad_model_plan(self):
        with patch.object(Ollama, "chat", return_value={"message":{"content":"[]"}}):
            with self.assertRaises(ValueError):
                Ollama("fake").propose("read", {})

    def test_large_file(self):
        (self.root/"large.txt").write_bytes(b"x"*65537)
        with self.assertRaises(ValueError):
            Workspace(self.root).read("large.txt")

if __name__ == "__main__":
    unittest.main()
