import tempfile
import unittest
from pathlib import Path
from potklin.core import Journal, Executor
from potklin.mods import build_registry
from potklin.router import route

class PersistenceTests(unittest.TestCase):
    def test_reopen_journal(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"journal.sqlite3"
            j=Journal(path)
            j.append("mission","started",{"tool":"fixture"})
            j.close()
            j=Journal(path)
            try:
                self.assertEqual(j.db.execute("SELECT mission,kind FROM events").fetchall(), [("mission","started")])
            finally:
                j.close()

    def test_no_unapproved_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            j=Journal(":memory:")
            try:
                action=route("lance Discord")
                with self.assertRaises(PermissionError):
                    Executor(build_registry(tmp),j).run(action["name"],action["args"],{action["mod"]})
            finally:
                j.close()
