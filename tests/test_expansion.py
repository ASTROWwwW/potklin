import tempfile
import unittest
from pathlib import Path
from potklin.mods import build_registry,Workspace
from potklin.workflows import Task,order,execute
from potklin.memory import Memory
from potklin.scheduling import select,reference_samples,Sample
from potklin.codeinspect import symbols

class Expansion(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.root=Path(self.t.name)
        (self.root/"a.py").write_text("def f():\n    return 1\n",encoding="utf8")
        self.r=build_registry(self.root)
    def tearDown(self):
        self.t.cleanup()
    def test_dag(self):
        t=[Task("a","files.list",{"path":"."}),Task("b","files.read",{"path":"a.py"},("a",))]
        self.assertEqual([x[0].id for x in order(t)],["a","b"])
        self.assertTrue(all(x["status"]=="pass" for x in execute(t,self.r,{"filesystem"}).values()))
    def test_cycle(self):
        with self.assertRaises(ValueError):
            order([Task("a","x",{},("b",)),Task("b","x",{},("a",))])
    def test_unknown_dependency(self):
        with self.assertRaises(ValueError):
            order([Task("a","x",{},("b",))])
    def test_duplicate(self):
        with self.assertRaises(ValueError):
            order([Task("a","x",{}),Task("a","x",{})])
    def test_blocked(self):
        result=execute([Task("a","files.read",{"path":"missing"}),Task("b","files.list",{"path":"."},("a",))],self.r,{"filesystem"})
        self.assertEqual(result["b"]["status"],"blocked")
    def test_side_effect(self):
        with self.assertRaises(PermissionError):
            execute([Task("a","windows.launch",{"app":"discord"})],self.r,{"windows"})
    def test_memory(self):
        m=Memory(self.root/"notes.db")
        try:
            k=m.add("fixture","GPU scheduling")
            self.assertEqual(k,m.add("fixture","GPU scheduling"))
            self.assertEqual(m.search("GPU")[0]["id"],k)
            m.delete(k)
            self.assertEqual(m.search("GPU"),[])
        finally:
            m.close()
    def test_scheduler(self):
        self.assertEqual(select(reference_samples()),"CPU")
        self.assertEqual(select(reference_samples(),True),"iGPU")
        self.assertIsNone(select([Sample("NPU",1,0,False)]))
    def test_symbols(self):
        self.assertEqual(symbols(Workspace(self.root),"a.py")["symbols"][0]["name"],"f")
