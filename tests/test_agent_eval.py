"""The evaluation is only worth its oracles: each must reject the starting state and accept a real solution."""
import tempfile
import unittest
from pathlib import Path
from potklin.checks import matches
from scripts.agent_eval import RUNNER, TASKS, grade, prepare, run_python, solve


class Oracles(unittest.TestCase):
    def test_controls(self):
        for name, build in TASKS.items():
            for variant in (7, 31):
                with self.subTest(task=name, variant=variant), tempfile.TemporaryDirectory() as workdir:
                    root = Path(workdir, "workspace")
                    root.mkdir()
                    task = build(variant)
                    prepare(task, root)
                    self.assertNotEqual(run_python(root, "-c", RUNNER, task["test"]).returncode, 0, "visible test starts green")
                    if task["solution"] is None:
                        continue
                    self.assertFalse(grade(task, root, workdir), "oracle accepts the starting state")
                    solve(task, root)
                    result = run_python(root, "-c", RUNNER, task["test"])
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertTrue(grade(task, root, workdir), "oracle rejects the reference solution")
                    self.assertTrue(all(matches(path, task["scope"]) for path, _, _ in task["solution"]))


if __name__ == "__main__":
    unittest.main()
