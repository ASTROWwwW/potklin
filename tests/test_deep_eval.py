import random
import tempfile
import unittest
from pathlib import Path
from scripts.deep_eval import fixture
from potklin.mods import Workspace
from potklin.review import review

class DeepFixtures(unittest.TestCase):
    def test_fixtures(self):
        for kind in ("cross_file","document","search","injection","recovery"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)
                request,mods,required,expected,forbidden=fixture(root,random.Random(42),kind)
                self.assertTrue(request and mods and required and expected)
                self.assertFalse((root/"missing.txt").exists())
                result=review(Workspace(root),"src")
                self.assertEqual([f["rule"] for f in result["findings"]],["CWE-327"])
