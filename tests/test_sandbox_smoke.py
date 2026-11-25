import tempfile
import unittest
from pathlib import Path
from xml.etree.ElementTree import fromstring
from potklin.sandbox import smoke_config
class SandboxSmoke(unittest.TestCase):
    def test_smoke_xml(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=Path(tmp)/"input";b=Path(tmp)/"output"
            a.mkdir();b.mkdir()
            root=fromstring(smoke_config(a,b))
            self.assertEqual(root.findtext("Networking"),"Disable")
            self.assertEqual([x.findtext("ReadOnly") for x in root.findall("MappedFolders/MappedFolder")],["true","false"])
            self.assertIn("check.ps1",root.findtext("LogonCommand/Command"))
    def test_same_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                smoke_config(tmp,tmp)
