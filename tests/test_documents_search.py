import unittest
import tempfile
from pathlib import Path
from potklin.mods import Workspace,build_registry
from potklin.documents import inspect
from potklin.search import search

class DocumentsSearch(unittest.TestCase):
    def test_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp)/"x.html").write_text('<h1>Report</h1><script>secret</script><a href="https://example.invalid">Read</a>',encoding="utf8")
            result=inspect(Workspace(tmp),"x.html")
            self.assertEqual(result["text"],"Report Read")
            self.assertEqual(result["links"],["https://example.invalid"])
            self.assertIn("documents.html",build_registry(tmp).select({"documents"}))
    def test_search(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp)/"a.txt").write_text("alpha\nBeta\n",encoding="utf8")
            self.assertEqual(search(Workspace(tmp),".","beta")["matches"],[{"path":"a.txt","line":2,"text":"Beta"}])
    def test_search_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                search(Workspace(tmp),".","")
