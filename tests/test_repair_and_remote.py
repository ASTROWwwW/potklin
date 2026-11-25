import unittest
from unittest.mock import patch
from scripts.repair_eval import expression
from potklin.github_actions import create_pr

class RepairRemote(unittest.TestCase):
    def test_expr(self):
        f=expression("(x+y-1)//y")
        self.assertEqual(f({"x":8,"y":3,"n":0}),3)
    def test_condition(self):
        self.assertEqual(expression("0 if x<0 else x")({"x":-3,"y":1,"n":0}),0)
    def test_no_execution(self):
        for x in ("__import__('os')","x.__class__","[x][0]","2**100","(lambda: 1)()"):
            with self.subTest(x=x),self.assertRaises(ValueError):
                expression(x)
    def test_remote_confirmation(self):
        with self.assertRaises(PermissionError):
            create_pr("owner/repo","feature","main","title","body")
    def test_remote_args(self):
        with patch("potklin.github_actions.shutil.which",return_value="gh"),patch("potklin.github_actions.subprocess.run") as run:
            run.return_value.stdout="https://github.com/owner/repo/pull/1"
            result=create_pr("owner/repo","feature","main","title","body",True)
            self.assertFalse(result["verified"])
            self.assertEqual(run.call_args.args[0][:3],["gh","pr","create"])
