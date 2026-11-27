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
        self.assertEqual(store.rollback("m"), {"restored": [], "conflicts": ["b.txt"]})
        self.assertEqual((self.root / "a.txt").read_bytes(), b"a1")
        self.assertEqual(store.rollback("m", force=True)["restored"], ["a.txt", "b.txt"])
        self.assertEqual((self.root / "b.txt").read_bytes(), b"b0")

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
        self.assertEqual(sorted(k for k in env if not k.startswith("PYTHON")), ["PATH"])
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
        with patch("potklin.execution.shutil.which", return_value=str(planted)):
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
