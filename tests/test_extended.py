import tempfile
import unittest
from pathlib import Path
from potklin.mods import Workspace
from potklin.edits import replace,digest
from potklin.semantic import SemanticMemory
from potklin.adaptive import solve
from potklin.dependencies import inventory

class Extended(unittest.TestCase):
    def test_edit(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"a.txt"
            p.write_bytes(b"old")
            w=Workspace(d)
            result=replace(w,"a.txt",digest(b"old"),"old","new")
            self.assertEqual(p.read_bytes(),b"new")
            self.assertEqual(result["sha256"],digest(b"new"))
            with self.assertRaises(ValueError):
                replace(w,"a.txt",digest(b"old"),"new","bad")
    def test_semantic(self):
        with tempfile.TemporaryDirectory() as d:
            m=SemanticMemory(Path(d)/"v.db",lambda t:[1.,0.] if "gpu" in t else [0.,1.],"fake")
            try:
                m.add("a","fixture","gpu compute")
                m.add("b","fixture","garden")
                self.assertEqual(m.search("gpu")[0]["id"],"a")
                m.delete("a")
                self.assertEqual(len(m.search("gpu")),1)
            finally:
                m.close()
    def test_adaptive(self):
        class Runner:
            def run(self,request,mods,steps,think):
                return {"success":think}
        result=solve(Runner(),"fixture",{"filesystem"},lambda r:r["success"])
        self.assertTrue(result["verified"])
        self.assertEqual(len(result["attempts"]),2)
    def test_dependencies(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/"package.json").write_text('{"dependencies":{"a":"1.0"}}',encoding="utf8")
            r=inventory(Workspace(d),"package.json")
            self.assertEqual(r["dependencies"],["a 1.0"])
            self.assertFalse(r["vulnerability_database_checked"])
