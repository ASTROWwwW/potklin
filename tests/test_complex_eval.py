import json
import random
import unittest
from scripts.complex_eval import generate,shortest
from scripts.security_eval import CASES,metrics
from potklin.advanced_lab import review_source
from potklin.decompose import decompose,leaves
from potklin.browser_agent import browse
class Fake:
    def __init__(self,rows):
        self.rows=iter(rows)
    def chat(self,*a,**kw):
        return {"message":{"content":json.dumps(next(self.rows))}}
class Complex(unittest.TestCase):
    def test_graph(self):
        self.assertEqual(shortest([(0,1,9),(0,2,1),(2,1,1),(1,3,1)],4),3)
    def test_seed(self):
        self.assertEqual(generate(random.Random(42),2),generate(random.Random(42),2))
    def test_static_precision(self):
        rows=[{"expected":expected,"actual":[f.rule for f in review_source(source)]} for source,expected in CASES]
        self.assertEqual(metrics(rows)["exact"],len(rows))
    def test_decompose(self):
        tree=decompose(Fake([{"children":["a","b"]}]),"root",1,3)
        self.assertEqual(leaves(tree),["a","b"])
    def test_decompose_budget(self):
        tree=decompose(Fake([{"children":["a","b"]}]),"root",2,2)
        self.assertEqual(leaves(tree),["a"])
    def test_browser_loop(self):
        class Session:
            def navigate(self,url):
                return {"url":url,"text":"x","links":[{"url":url}]}
        self.assertEqual(browse(Session(),Fake([{"link":0}]),"test","https://example.test")["status"],"repeated_link")
