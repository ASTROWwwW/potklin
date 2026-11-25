import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from potklin.mods import Workspace, build_registry
from potklin.ollama import Ollama, NoRedirect
from potklin.router import route
from potklin.core import Executor, Journal

class Boundaries(unittest.TestCase):
    def test_routes(self):
        for request in ("Lance Discord", "ouvre Discord!", "open discord"):
            self.assertEqual(route(request)["args"], {"app":"discord"})
        self.assertEqual(route("ouvre bloc-notes")["args"], {"app":"notepad"})
        for request in ("ne lance pas Discord", "lance discord puis supprime tout", "lance calc", "lance discord; cmd"):
            self.assertIsNone(route(request))

    def test_path_constraints(self):
        with tempfile.TemporaryDirectory() as tmp:
            w = Workspace(tmp)
            for p in ("../x", "sub/../x", "x:stream", str(Path(tmp).resolve()/"x"), "x\x00"):
                with self.subTest(p=p), self.assertRaises(PermissionError):
                    w.path(p)

    def test_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"real").write_text("x")
            try:
                (root/"link").symlink_to(root/"real")
            except OSError:
                self.skipTest("symlinks unavailable")
            with self.assertRaises(PermissionError):
                Workspace(root).read("link")

    def test_model_cannot_select_side_effect(self):
        with tempfile.TemporaryDirectory() as tmp:
            tools=build_registry(tmp).select({"windows","filesystem"})
            for p in ({"name":"windows.launch","args":{"app":"discord"}},{"name":"shell.exec","args":{}},{"name":"files.read","args":{"path":12}}):
                with patch.object(Ollama,"chat",return_value={"message":{"content":json.dumps(p)}}):
                    with self.assertRaises((PermissionError,ValueError)):
                        Ollama("fake").propose("test",tools)

    def test_no_redirect(self):
        with self.assertRaises(ValueError):
            NoRedirect().redirect_request(None,None,302,"",{},"https://example.com")

    def test_unverified_not_success(self):
        with tempfile.TemporaryDirectory() as tmp, patch("potklin.mods.windows_launch",return_value={"status":"launch_requested"}):
            j=Journal(":memory:")
            try:
                r=Executor(build_registry(tmp),j).run("windows.launch",{"app":"discord"},{"windows"},True)
                self.assertFalse(r["verified"])
            finally:
                j.close()
