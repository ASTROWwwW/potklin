import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from potklin.core import Journal
from potklin.mods import build_registry,Workspace
from potklin.manifests import validate
from potklin.mission import MissionRunner
from potklin.review import review

class Fake:
    def __init__(self,actions):
        self.actions=iter(actions)
    def chat(self,*a,**kw):
        return {"message":{"content":json.dumps(next(self.actions))}}

class V7(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        (self.root/"a.py").write_text("# eval(x)\nimport hashlib\nhashlib.md5(b'x')\n",encoding="utf8")
        self.j=Journal(":memory:")
        self.r=build_registry(self.root)
    def tearDown(self):
        self.j.close()
        self.tmp.cleanup()
    def run_actions(self,actions,steps=6):
        return MissionRunner(self.r,self.j,Fake(actions)).run("review fixture",{"filesystem","cyber"},steps)
    def test_manifest(self):
        validate(self.r)
    def test_ast_ignores_comment(self):
        result=review(Workspace(self.root),".")
        self.assertEqual([f["rule"] for f in result["findings"]],["CWE-327"])
    def test_two_steps(self):
        result=self.run_actions([{"name":"files.list","args":{"path":"."}},{"name":"cyber.ast_review","args":{"path":"."}},{"finish":"done"}])
        self.assertEqual(len(result["observations"]),2)
        self.assertEqual(result["status"],"model_finished_unverified")
        self.assertFalse(result["verified"])
    def test_disallowed(self):
        self.assertEqual(self.run_actions([{"name":"windows.launch","args":{"app":"discord"}}])["status"],"invalid_action")
    def test_repeat(self):
        a={"name":"files.list","args":{"path":"."}}
        self.assertEqual(self.run_actions([a,a])["status"],"repeated_action")
    def test_budget(self):
        self.assertEqual(self.run_actions([{"name":"files.list","args":{"path":"."}}],1)["status"],"budget_exhausted")
    def test_path_failure(self):
        x=self.run_actions([{"name":"files.read","args":{"path":"../secret"}},{"finish":"cannot read"}])
        self.assertEqual(x["observations"][0]["error"],"PermissionError")
    def test_invalid_json_shape(self):
        self.assertEqual(self.run_actions([[]])["status"],"invalid_action")
    def test_invalid_budget(self):
        with self.assertRaises(ValueError):
            self.run_actions([],13)
    def test_no_secrets_in_journal(self):
        self.run_actions([{"name":"files.read","args":{"path":"a.py"}},{"finish":"done"}])
        self.assertNotIn("hashlib",str(self.j.db.execute("SELECT payload FROM events").fetchall()))
