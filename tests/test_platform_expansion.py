import tempfile
import unittest
from xml.etree.ElementTree import fromstring
from potklin.browser_session import Scope,origin
from potklin.sandbox import config
from potklin.advanced_lab import review_source,authorization_oracle
from potklin.desktop_actions import control

class PlatformExpansion(unittest.TestCase):
    def test_browser_origin(self):
        s=Scope.from_urls(["https://example.test"])
        for u in ("https://example.test/a","https://example.test:443/a"):
            self.assertTrue(s.allows(u))
        for u in ("https://example.test.evil/a","https://evil.test","https://user@example.test","file:///etc/passwd","https://example.test:444/a"):
            self.assertFalse(s.allows(u))
    def test_no_plain_remote(self):
        with self.assertRaises(ValueError):
            origin("http://example.test")
    def test_sandbox(self):
        with tempfile.TemporaryDirectory() as tmp:
            xml=fromstring(config(tmp))
            self.assertEqual(xml.findtext("Networking"),"Disable")
            self.assertEqual(xml.findtext("MappedFolders/MappedFolder/ReadOnly"),"true")
            self.assertIsNone(xml.find("LogonCommand"))
    def test_desktop_requires_permission(self):
        with self.assertRaises(PermissionError):
            control("notepad","x","Edit","set_text","x")
    def test_review(self):
        s="# eval(x)\nimport pickle\npickle.loads(data)\nconn.execute(f'SELECT {x}')\nconn.execute('SELECT ?', (x,))"
        self.assertEqual([x.rule for x in review_source(s)],["CWE-502","CWE-89"])
    def test_authorization(self):
        good=lambda role,owner,action:action=="read" or role=="admin" or (action=="write" and role=="editor" and owner)
        self.assertTrue(all(x["passed"] for x in authorization_oracle(good)))
        self.assertTrue(any(not x["passed"] for x in authorization_oracle(lambda *a:True)))
