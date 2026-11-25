import json
import tempfile
import unittest
from pathlib import Path
from potklin.mods import build_registry
from potklin.core import Executor,Journal
from potklin.edits import digest
from potklin.hierarchical import run
class Capabilities(unittest.TestCase):
    def test_file_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=build_registry(tmp);j=Journal(":memory:")
            try:
                ex=Executor(r,j)
                def call(name,args,allow=True):return ex.run(name,args,{"filesystem"},allow)
                with self.assertRaises(PermissionError):
                    call("files.create",{"path":"a.txt","text":"fixture"},False)
                x=call("files.create",{"path":"a.txt","text":"fixture"})
                self.assertTrue(x["verified"])
                key=digest(b"fixture")
                with self.assertRaises(FileExistsError):
                    call("files.create",{"path":"a.txt","text":"overwrite"})
                self.assertTrue(call("files.move",{"source":"a.txt","destination":"b.txt","expected_sha256":key})["verified"])
                with self.assertRaises(ValueError):
                    call("files.remove",{"path":"b.txt","expected_sha256":"bad"})
                self.assertTrue(call("files.remove",{"path":"b.txt","expected_sha256":key})["verified"])
                self.assertEqual(list(Path(tmp).iterdir()),[])
            finally:j.close()
    def test_hierarchy(self):
        class M:
            def chat(self,*a,**kw):return {"message":{"content":json.dumps({"children":["first","second"]})}}
        class Runner:
            def run(self,task,mods,steps,think):return {"answer":task}
        r=run(M(),Runner(),"root",{"filesystem"},lambda rows:[x["result"]["answer"] for x in rows]==["first","second"],depth=1,nodes=3)
        self.assertTrue(r["verified"])
