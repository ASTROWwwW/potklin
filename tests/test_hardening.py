import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from potklin import checks
from potklin.checkpoint import Checkpoints
from potklin.context_policy import pack
from potklin.core import Executor, Journal
from potklin.execution import CommandSet, clean_environment
from potklin.git_actions import LocalGit
from potklin.mods import Workspace, build_registry
from potklin.search import search


class Temp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.journal = Journal(":memory:")

    def tearDown(self):
        self.journal.close()
        self.tmp.cleanup()

    def put(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data.encode() if isinstance(data, str) else data)
        return path

    def tool(self, name, args):
        return Executor(build_registry(self.root), self.journal).run(name, args, {"filesystem", "coding", "cyber"}, True)


class ProtectedPaths(Temp):
    def test_sensitive_paths_are_refused(self):
        (self.root / ".git" / "hooks").mkdir(parents=True)
        workspace = Workspace(self.root)
        for name in (".git/hooks/pre-commit", ".GIT/config", ".git./config", ".git /config", "sub/.git/config",
                     ".env", ".ENV.local", ".vscode/tasks.json", ".idea/x", ".potklin/journal"):
            with self.subTest(name=name), self.assertRaises(PermissionError):
                workspace.path(name)
        for name in (".env.example", ".github/workflows/ci.yml", "git/config", ".gitignore"):
            with self.subTest(name=name):
                workspace.path(name)

    def test_model_cannot_create_a_git_hook(self):
        (self.root / ".git").mkdir()
        with self.assertRaises(PermissionError):
            self.tool("files.create", {"path": ".git/hooks/pre-commit", "text": "#!/bin/sh\n"})
        self.assertFalse((self.root / ".git" / "hooks").exists())

    @unittest.skipUnless(os.name == "nt", "Windows short names")
    def test_short_name_alias_is_refused(self):
        import ctypes
        (self.root / ".git").mkdir()
        buffer = ctypes.create_unicode_buffer(1024)
        ctypes.windll.kernel32.GetShortPathNameW(str(self.root / ".git"), buffer, 1024)
        alias = Path(buffer.value).name
        if alias.casefold() == ".git":
            self.skipTest("short names disabled on this volume")
        for name in (alias + "/config", alias + "/hooks/new"):
            with self.subTest(name=name), self.assertRaises(PermissionError):
                Workspace(self.root).path(name)


class RedTeam(Temp):
    def test_planted_git_is_never_started(self):
        self.put(".git/HEAD", "ref: refs/heads/main\n")
        marker = self.root / "owned.txt"
        if os.name == "nt":
            self.put("git.cmd", f"@echo off\r\necho owned> \"{marker}\"\r\n")
        else:
            self.put("git", f"#!/bin/sh\necho owned > '{marker}'\n").chmod(0o755)
        previous = os.getcwd()
        environment = {k: v for k, v in os.environ.items() if k != "NoDefaultCurrentDirectoryInExePath"}
        environment["PATH"] = "." + os.pathsep + environment["PATH"]
        try:
            os.chdir(self.root)
            with patch.dict(os.environ, environment, clear=True):
                try:
                    self.tool("coding.git", {"path": "."})
                except subprocess.CalledProcessError:
                    pass
        finally:
            os.chdir(previous)
        self.assertFalse(marker.exists())

    def test_device_names_and_odd_characters_are_refused(self):
        self.put("data.txt", "precious")
        key = hashlib.sha256(b"precious").hexdigest()
        for destination in ("n/NUL", "nul.txt", "CON", "sub/aux .log", "COM1", "lpt9.md", "a|b", "q?.txt", "x\ny"):
            with self.subTest(destination=destination), self.assertRaises(PermissionError):
                self.tool("files.move", {"source": "data.txt", "destination": destination, "expected_sha256": key})
        self.assertEqual((self.root / "data.txt").read_bytes(), b"precious")
        for name in ("console.py", "null.txt", "com10.log", "auxiliary/x"):
            Workspace(self.root).path(name)

    def test_git_hides_everything_the_file_tools_refuse(self):
        subprocess.run(["git", "-C", str(self.root), "init", "-q"], check=True)
        hidden = [".vscode/s.json", ".idea/w.xml", ".potklin/j", ".env.d/prod", "sub/.env/keys", "a/.VSCode/t"]
        for name in hidden:
            self.put(name, "old\n")
        self.put("seen.txt", "old\n")

        def git(*args):
            subprocess.run(["git", "-C", str(self.root), "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                           check=True, capture_output=True)

        git("add", "-A", "-f")
        git("commit", "-q", "-m", "x")
        for name in hidden:
            self.put(name, "SECRETVALUE\n")
        self.put("seen.txt", "new\n")
        result = self.tool("coding.git", {"path": "."})["result"]
        self.assertIn("seen.txt", result["diff"])
        self.assertNotIn("SECRETVALUE", result["diff"])
        for name in hidden:
            self.assertNotIn(name, result["status"] + result["diff"])

    def test_allow_patterns_are_strict_and_deny_patterns_broad(self):
        for relative, pattern in (("\u017frc/evil.py", "src"), ("stra\u00dfe.py", "strasse.py"),
                                  ("tas\u212as/x", "tasks"), ("app/i.tsx", "app/[id].tsx")):
            with self.subTest(relative=relative):
                self.assertFalse(checks.matches(relative, [pattern], allow=True))
        self.assertTrue(checks.matches("app/[id].tsx", ["app/[id].tsx"], allow=True))
        self.assertTrue(checks.matches("src/deep/m.py", ["src/*.py"], allow=True))

    def test_protection_reaches_dependency_folders_inside_protected_trees(self):
        self.put("tests/venv/helper.py", "h")
        self.put("tests/node_modules/m.js", "m")
        self.put("node_modules/other.js", "o")
        self.assertEqual(sorted(checks.fingerprint(self.root, ["tests"])), ["tests/node_modules/m.js", "tests/venv/helper.py"])
        self.assertEqual(sorted(checks.fingerprint(self.root, ["node_modules/other.js"])), ["node_modules/other.js"])

    def test_module_shadowing_from_the_workspace_is_ignored(self):
        marker = self.root / "shadowed.txt"
        for module in ("argparse", "sqlite3", "json"):
            self.put(module + ".py", f"open({str(marker)!r}, 'w').write('x')\nraise SystemExit(7)\n")
        repository = str(Path(__import__("potklin").__file__).resolve().parents[1])
        run = subprocess.run([sys.executable, "-m", "potklin", "--version"], cwd=self.root, capture_output=True,
                             env={**os.environ, "PYTHONPATH": repository}, timeout=60)
        self.assertEqual((run.returncode, marker.exists()), (0, False), run.stderr)


class SecondPass(Temp):
    def test_read_only_files_leave_no_debris_and_do_not_block_rollback(self):
        locked = self.put("vendor.txt", "v")
        self.put("app.py", "good")
        locked.chmod(0o444)
        key = hashlib.sha256(b"v").hexdigest()
        store = Checkpoints(self.journal.db)
        workspace = Workspace(self.root)
        try:
            for name, args in (("files.move", {"source": "vendor.txt", "destination": "copy.txt", "expected_sha256": key}),
                               ("files.write", {"path": "vendor.txt", "expected_sha256": key, "text": "model text"})):
                seqs = [(store.snapshot(workspace, "m", args[a]), args[a]) for a in ("source", "destination", "path") if a in args]
                try:
                    self.tool(name, args)
                except (OSError, ValueError):
                    pass
                for seq, path in seqs:
                    store.seal(workspace, seq, path)
            self.write_file(store, "app.py", "EVIL")
            result = store.rollback("m", force=True)
            self.assertEqual((self.root / "app.py").read_bytes(), b"good")
            self.assertEqual((self.root / "vendor.txt").read_bytes(), b"v")
            self.assertEqual([p.name for p in self.root.glob(".potklin-*")], [])
            self.assertIsInstance(result["unrestored"], list)
        finally:
            for file in self.root.iterdir():
                file.chmod(0o644)

    def write_file(self, store, name, text):
        workspace = Workspace(self.root)
        seq = store.snapshot(workspace, "m", name)
        self.put(name, text)
        store.seal(workspace, seq, name)

    def test_old_journal_gains_the_new_column(self):
        self.journal.db.execute("CREATE TABLE checkpoints (seq INTEGER PRIMARY KEY, mission TEXT, root TEXT, path TEXT, before BLOB, new_dirs TEXT, after TEXT, done INTEGER)")
        self.put("a.txt", "a0")
        store = Checkpoints(self.journal.db)
        self.write_file(store, "a.txt", "a1")
        self.assertEqual(store.rollback("m")["restored"], ["a.txt"])

    def test_globs_reaching_dependency_folders_are_fingerprinted(self):
        self.put("tests/node_modules/helper.js", "h")
        self.put("tests/a.js", "a")
        self.put("node_modules/x.js", "x")
        self.assertEqual(sorted(checks.fingerprint(self.root, ["tests/*.js"])), ["tests/a.js", "tests/node_modules/helper.js"])


class SlowAndBrokenResponses(unittest.TestCase):
    def serve(self, reply):
        import socket
        import threading
        listener = socket.create_server(("127.0.0.1", 0))

        def run():
            client, _ = listener.accept()
            with client:
                client.recv(4096)
                try:
                    reply(client)
                except OSError:
                    pass

        threading.Thread(target=run, daemon=True).start()
        self.addCleanup(listener.close)
        return f"http://127.0.0.1:{listener.getsockname()[1]}/"

    def test_endless_stream_hits_the_total_deadline(self):
        import time
        from potklin import browser_session

        def trickle(client):
            client.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\n\r\n")
            for _ in range(100):
                client.sendall(b"data: x\n\n")
                time.sleep(0.1)

        url = self.serve(trickle)
        with patch.object(browser_session, "FETCH_DEADLINE", 1), self.assertRaisesRegex(ValueError, "too slow"):
            browser_session.fetch(url, "GET", {})

    def test_malformed_replies_raise_handled_errors(self):
        import http.client
        from potklin.browser_session import fetch
        for payload in (b"NOT-HTTP\r\n\r\n", b"HTTP/1.1 200 OK\r\nContent-Length: 50\r\n\r\nshort",
                        b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n10\r\nabc"):
            url = self.serve(lambda client, data=payload: client.sendall(data))
            with self.subTest(payload=payload[:20]), self.assertRaises((OSError, ValueError, http.client.HTTPException)):
                fetch(url, "GET", {})


class FileTools(Temp):
    def test_read_exposes_hash_and_line_ranges(self):
        self.put("a.txt", "one\ntwo\nthree\n")
        whole = self.tool("files.read", {"path": "a.txt"})["result"]
        self.assertEqual(whole["sha256"], hashlib.sha256(b"one\ntwo\nthree\n").hexdigest())
        part = self.tool("files.read_lines", {"path": "a.txt", "start": "2", "count": "1"})["result"]
        self.assertEqual((part["text"], part["total_lines"], part["sha256"]), ("two", 3, whole["sha256"]))
        for start, count in (("0", "1"), ("1", "401"), ("x", "1")):
            with self.assertRaises(ValueError):
                Workspace(self.root).read_lines("a.txt", start, count)

    def test_create_makes_parent_directories(self):
        self.assertTrue(self.tool("files.create", {"path": "pkg/sub/m.py", "text": "x = 1\n"})["verified"])
        self.assertEqual((self.root / "pkg/sub/m.py").read_bytes(), b"x = 1\n")

    def test_replace_keeps_crlf(self):
        path = self.put("w.txt", b"a\r\nb\r\nc\r\n")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        self.tool("files.replace", {"path": "w.txt", "expected_sha256": digest, "old": "a\nb", "new": "A\nB"})
        self.assertEqual(path.read_bytes(), b"A\r\nB\r\nc\r\n")

    @unittest.skipIf(os.name == "nt", "POSIX permissions")
    def test_replace_keeps_permissions(self):
        path = self.put("run.sh", "echo a\n")
        path.chmod(0o755)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        self.tool("files.replace", {"path": "run.sh", "expected_sha256": digest, "old": "a", "new": "b"})
        self.assertEqual(path.stat().st_mode & 0o777, 0o755)

    def test_search_accepts_a_single_file(self):
        self.put("pkg/a.py", "x\nneedle\n")
        self.put("pkg/b.py", "needle\n")
        found = search(Workspace(self.root), "pkg/a.py", "needle")["matches"]
        self.assertEqual([(m["line"], Path(m["path"]).name) for m in found], [(2, "a.py")])
        with self.assertRaises(ValueError):
            search(Workspace(self.root), "pkg/none.py", "needle")

    def test_whole_file_write_needs_the_read_revision(self):
        path = self.put("w.txt", b"a\r\n")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        with self.assertRaises(ValueError):
            self.tool("files.write", {"path": "w.txt", "expected_sha256": "0" * 64, "text": "x"})
        self.assertTrue(self.tool("files.write", {"path": "w.txt", "expected_sha256": digest, "text": "b\nc\n"})["verified"])
        self.assertEqual(path.read_bytes(), b"b\r\nc\r\n")

    def test_replace_error_says_how_to_recover(self):
        path = self.put("d.txt", "x\nx\n")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        for old, expected in (("x", "occurs 2 times"), ("missing", "occurs 0 times")):
            with self.assertRaisesRegex(ValueError, expected):
                self.tool("files.replace", {"path": "d.txt", "expected_sha256": digest, "old": old, "new": "y"})

    def test_search_and_audit_report_skipped_files(self):
        self.put("big.py", "needle\n" * 200000)
        self.put("ok.py", "needle\n")
        found = search(Workspace(self.root), ".", "needle")
        self.assertEqual((found["scanned"], found["skipped"], len(found["matches"])), (1, 1, 1))
        self.assertEqual(Workspace(self.root).audit(".")["skipped"], 1)

    def test_pack_favours_the_latest_observation(self):
        rows = [{"data": "a" * 5000} for _ in range(5)] + [{"data": "z" * 8000}]
        packed = pack(rows, 12000)
        self.assertEqual(len(packed[-1]["data"]), 8000)
        self.assertLessEqual(sum(len(r["data"]) for r in packed), 12000)
        self.assertTrue(all(len(r["data"]) >= 200 for r in packed))


class CheckpointTests(Temp):
    def write(self, store, mission, name, text):
        workspace = Workspace(self.root)
        seq = store.snapshot(workspace, mission, name)
        self.put(name, text)
        store.seal(workspace, seq, name)

    def test_rollback_restores_edits_and_removes_new_files(self):
        self.put("keep.txt", "original")
        store = Checkpoints(self.journal.db)
        self.write(store, "m", "keep.txt", "first")
        self.write(store, "m", "keep.txt", "second")
        self.write(store, "m", "new/dir/file.txt", "created")
        self.assertEqual(store.paths("m"), ["keep.txt", "new/dir/file.txt"])
        result = store.rollback("m")
        self.assertEqual(result["conflicts"], [])
        self.assertEqual((self.root / "keep.txt").read_bytes(), b"original")
        self.assertFalse((self.root / "new").exists())
        with self.assertRaises(ValueError):
            store.rollback("m")

    def test_later_user_edit_blocks_the_whole_rollback(self):
        self.put("a.txt", "a0")
        self.put("b.txt", "b0")
        store = Checkpoints(self.journal.db)
        self.write(store, "m", "a.txt", "a1")
        self.write(store, "m", "b.txt", "b1")
        self.put("b.txt", "user work")
        self.assertEqual(store.rollback("m"), {"restored": [], "conflicts": ["b.txt"], "unrestored": ["a.txt", "b.txt"]})
        self.assertEqual((self.root / "a.txt").read_bytes(), b"a1")
        self.assertEqual(store.rollback("m", force=True)["restored"], ["a.txt", "b.txt"])
        self.assertEqual((self.root / "b.txt").read_bytes(), b"b0")

    def test_case_only_renames_never_destroy_the_file(self):
        self.put("Readme.md", "the only copy")
        store = Checkpoints(self.journal.db)
        workspace = Workspace(self.root)

        def move(source, destination):
            seqs = [(store.snapshot(workspace, "m", n), n) for n in (source, destination)]
            (self.root / source).rename(self.root / destination)
            for seq, name in seqs:
                store.seal(workspace, seq, name)

        move("Readme.md", "tmp.md")
        move("tmp.md", "readme.md")
        result = store.rollback("m")
        self.assertEqual(result["unrestored"], [])
        self.assertEqual([p.read_bytes() for p in self.root.iterdir()], [b"the only copy"])

    def test_write_that_changed_nothing_leaves_no_checkpoint(self):
        self.put("a.txt", "a0")
        self.put("b.txt", "b0")
        store = Checkpoints(self.journal.db)
        workspace = Workspace(self.root)
        store.seal(workspace, store.snapshot(workspace, "m", "b.txt"), "b.txt")
        self.write(store, "m", "a.txt", "a1")
        self.put("b.txt", "user work")
        self.assertEqual(store.rollback("m"), {"restored": ["a.txt"], "conflicts": [], "unrestored": []})
        self.assertEqual((self.root / "b.txt").read_bytes(), b"user work")

    def test_oversized_file_can_still_be_diffed_and_rolled_back(self):
        self.put("a.txt", "small")
        store = Checkpoints(self.journal.db)
        self.write(store, "m", "a.txt", "edited")
        self.put("a.txt", "x" * 2_000_000)
        self.assertEqual(store.paths("m"), ["a.txt"])
        self.assertIn("too large", store.diff("m"))
        self.assertEqual(store.rollback("m", force=True)["restored"], ["a.txt"])
        self.assertEqual((self.root / "a.txt").read_bytes(), b"small")

    def test_unrestorable_path_keeps_its_pre_image(self):
        self.put("a.txt", "a0")
        store = Checkpoints(self.journal.db)
        self.write(store, "m", "a.txt", "a1")
        (self.root / "a.txt").unlink()
        (self.root / "a.txt").mkdir()
        self.assertEqual(store.rollback("m", force=True)["unrestored"], ["a.txt"])
        (self.root / "a.txt").rmdir()
        self.assertEqual(store.rollback("m", force=True)["restored"], ["a.txt"])
        self.assertEqual((self.root / "a.txt").read_bytes(), b"a0")

    @unittest.skipIf(os.name == "nt", "POSIX permissions")
    def test_move_and_restore_keep_permissions(self):
        path = self.put("run.sh", "echo\n")
        path.chmod(0o755)
        key = hashlib.sha256(path.read_bytes()).hexdigest()
        store = Checkpoints(self.journal.db)
        workspace = Workspace(self.root)
        seqs = [(store.snapshot(workspace, "m", n), n) for n in ("run.sh", "moved.sh")]
        self.tool("files.move", {"source": "run.sh", "destination": "moved.sh", "expected_sha256": key})
        for seq, name in seqs:
            store.seal(workspace, seq, name)
        self.assertEqual((self.root / "moved.sh").stat().st_mode & 0o777, 0o755)
        store.rollback("m")
        self.assertEqual(path.stat().st_mode & 0o777, 0o755)

    def test_search_does_not_depend_on_the_suffix_and_skips_binaries(self):
        self.put("run.sh", "needle\n")
        self.put("blob.bin", b"needle\x00")
        found = search(Workspace(self.root), ".", "needle")
        self.assertEqual(([m["path"] for m in found["matches"]], found["skipped"]), (["run.sh"], 1))

    def test_file_replaced_by_our_own_directory_is_restored(self):
        self.put("notes", "the only copy")
        store = Checkpoints(self.journal.db)
        workspace = Workspace(self.root)
        seqs = [(store.snapshot(workspace, "m", n), n) for n in ("notes", "y")]
        (self.root / "notes").rename(self.root / "y")
        for seq, name in seqs:
            store.seal(workspace, seq, name)
        seq = store.snapshot(workspace, "m", "notes/z")
        self.put("notes/z", "z")
        store.seal(workspace, seq, "notes/z")
        self.assertEqual(store.rollback("m")["unrestored"], [])
        self.assertEqual([(p.name, p.read_bytes()) for p in self.root.iterdir()], [("notes", b"the only copy")])

    def test_interrupted_write_needs_force(self):
        self.put("a.txt", "a0")
        store = Checkpoints(self.journal.db)
        store.snapshot(Workspace(self.root), "m", "a.txt")
        self.put("a.txt", "half")
        self.assertEqual(store.rollback("m")["conflicts"], ["a.txt"])
        store.rollback("m", force=True)
        self.assertEqual((self.root / "a.txt").read_bytes(), b"a0")


class Commands(Temp):
    def commands(self, code, timeout=60):
        return CommandSet(self.root, {"probe": [sys.executable, "-c", code]}, timeout)

    def test_exit_code_and_output(self):
        result = self.commands("print('hello'); raise SystemExit(3)").run("probe")
        self.assertEqual((result["exit_code"], result["output"].strip(), result["timed_out"]), (3, "hello", False))

    def test_secrets_are_not_inherited(self):
        env = clean_environment({"PATH": "p", "GITHUB_TOKEN": "t", "OPENAI_API_KEY": "k", "DB_PASSWORD": "d", "GIT_DIR": "g"})
        self.assertEqual(sorted(k for k in env if not k.startswith(("PYTHON", "NoDefault"))), ["PATH"])
        leaked = {n: "x" for n in ("DB_PASS", "GITHUB_PAT", "OPENAI_KEY", "STRIPE_KEY", "SSH_PASSPHRASE")}
        leaked["DATABASE_URL"] = "postgres://user:hunter2@localhost/db"
        self.assertEqual([k for k in clean_environment(leaked) if k in leaked], [])
        self.assertIn("PATHEXT", clean_environment({"PATHEXT": ".EXE"}))
        with patch.dict(os.environ, {"POTKLIN_TEST_TOKEN": "leak"}):
            out = self.commands("import os; print(os.environ.get('POTKLIN_TEST_TOKEN'))").run("probe")["output"]
        self.assertEqual(out.strip(), "None")

    def test_timeout_kills_the_process_tree(self):
        marker = self.root / "survivor.txt"
        child = f"import time,pathlib; time.sleep(4); pathlib.Path({str(marker)!r}).write_text('alive')"
        parent = f"import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',{child!r}]); time.sleep(30)"
        result = self.commands(parent, timeout=1).run("probe")
        self.assertEqual((result["exit_code"], result["timed_out"]), (-1, True))
        import time
        time.sleep(5)
        self.assertFalse(marker.exists())

    def test_output_is_bounded(self):
        result = self.commands("print('x' * 100000)").run("probe")
        self.assertTrue(result["output_truncated"])
        self.assertLessEqual(len(result["output"]), 4000)

    def test_declarations_are_validated(self):
        for bad in ({}, {"a b": ["x"]}, {"a": "python -c 1"}, {"a": []}, {"a": ["./tool"]}, {"a": ["no-such-program-potklin"]}):
            with self.subTest(bad=bad), self.assertRaises((ValueError, PermissionError)):
                CommandSet(self.root, bad)
        with self.assertRaises(ValueError):
            self.commands("pass").run("other")

    def test_program_planted_in_workspace_is_refused(self):
        planted = self.put("planted-tool.cmd" if os.name == "nt" else "planted-tool", "@echo off\n")
        planted.chmod(0o755)
        with patch.dict(os.environ, {"PATH": str(self.root)}):
            with self.assertRaises(PermissionError):
                CommandSet(self.root, {"a": ["planted-tool"]})


class Acceptance(Temp):
    def test_each_kind(self):
        self.put("a.txt", "alpha\r\nbeta\r\n")
        digest = hashlib.sha256((self.root / "a.txt").read_bytes()).hexdigest()
        specs = ["exists:a.txt", "absent:b.txt", "contains:a.txt::alpha\nbeta", "sha256:a.txt::" + digest.upper()]
        rows = checks.evaluate([checks.parse(s) for s in specs], Workspace(self.root))
        self.assertTrue(all(r["passed"] for r in rows), rows)
        rows = checks.evaluate([checks.parse(s) for s in ("exists:b.txt", "contains:b.txt::x", "contains:a.txt::gamma")], Workspace(self.root))
        self.assertFalse(any(r["passed"] for r in rows))

    def test_expected_value_stays_hidden(self):
        self.assertEqual(checks.parse("contains:a.txt::secret answer").label, "contains:a.txt")

    def test_invalid_specs_fail_before_the_mission(self):
        for spec in ("nope:x", "exists:", "contains:a.txt"):
            with self.subTest(spec=spec), self.assertRaises(ValueError):
                checks.parse(spec)
        with self.assertRaises(ValueError):
            checks.validate([checks.parse("command:missing")], Workspace(self.root), None)
        with self.assertRaises(PermissionError):
            checks.validate([checks.parse("exists:../x")], Workspace(self.root), None)

    def test_fingerprint_matches_directories_and_globs(self):
        self.put("tests/test_a.py", "a")
        self.put("tests/__pycache__/x.pyc", "x")
        self.put("setup.cfg", "s")
        self.put("src/m.py", "m")
        self.assertEqual(sorted(checks.fingerprint(self.root, ["tests/", "*.cfg"])), ["setup.cfg", "tests/test_a.py"])


@unittest.skipUnless(shutil.which("git"), "git required")
class GitCommit(Temp):
    def git(self, *args, **env):
        return subprocess.run(["git", "-C", str(self.root), *args], check=True, capture_output=True, text=True,
                              env={**os.environ, **env}).stdout

    def isolated(self, content):
        """Point git's global configuration at a fixture, never at the developer's own."""
        config = Path(self.home.name) / "gitconfig"
        config.write_text(content, encoding="utf-8")
        return patch.dict(os.environ, {"HOME": self.home.name, "USERPROFILE": self.home.name,
                                       "XDG_CONFIG_HOME": self.home.name, "GIT_CONFIG_NOSYSTEM": "1"})

    def setUp(self):
        super().setUp()
        self.home = tempfile.TemporaryDirectory()
        self.git("init", "-q")
        self.git("-c", "user.name=s", "-c", "user.email=s@example.invalid", "commit", "-q", "--allow-empty", "-m", "seed")
        self.put("note.txt", "x\n")

    def tearDown(self):
        super().tearDown()
        self.home.cleanup()

    def test_uses_the_global_identity(self):
        with self.isolated("[user]\n\tname = Global Person\n\temail = global@example.invalid\n"):
            (Path(self.home.name) / ".gitconfig").write_text("[user]\n\tname = Global Person\n\temail = global@example.invalid\n", encoding="utf-8")
            LocalGit(self.root).commit(["note.txt"], "add note", True)
        self.assertIn("Global Person", self.git("log", "-1", "--format=%an"))

    def test_missing_identity_leaves_the_index_untouched(self):
        with self.isolated(""):
            with self.assertRaises(ValueError):
                LocalGit(self.root).commit(["note.txt"], "add note", True)
        self.assertEqual(self.git("diff", "--cached", "--name-only"), "")

    def test_failed_commit_unstages_so_a_retry_works(self):
        self.git("config", "user.name", "L")
        self.git("config", "user.email", "l@example.invalid")
        repo = LocalGit(self.root)
        original = repo._run

        def failing(*args, **kw):
            if args[0] == "commit":
                raise subprocess.CalledProcessError(1, "git commit")
            return original(*args, **kw)

        with patch.object(repo, "_run", side_effect=failing), self.assertRaises(subprocess.CalledProcessError):
            repo.commit(["note.txt"], "add note", True)
        self.assertEqual(self.git("diff", "--cached", "--name-only"), "")
        repo.commit(["note.txt"], "add note", True)

    def test_root_path_is_rejected_cleanly(self):
        self.git("config", "user.name", "L")
        self.git("config", "user.email", "l@example.invalid")
        with self.assertRaises(ValueError):
            LocalGit(self.root).commit(["."], "all", True)

    def test_diff_hides_tracked_secrets(self):
        self.git("config", "user.name", "L")
        self.git("config", "user.email", "l@example.invalid")
        self.put(".env", "KEY=old\n")
        self.put("sub/.env.local", "KEY=old\n")
        self.git("add", "-f", ".env", "sub/.env.local", "note.txt")
        self.git("commit", "-q", "-m", "tracked")
        self.put(".env", "KEY=SECRETVALUE\n")
        self.put("sub/.env.local", "KEY=SECRETVALUE\n")
        self.put("note.txt", "changed\n")
        result = self.tool("coding.git", {"path": "."})["result"]
        self.assertIn("changed", result["diff"])
        self.assertNotIn("SECRETVALUE", result["diff"] + result["status"])


if __name__ == "__main__":
    unittest.main()
