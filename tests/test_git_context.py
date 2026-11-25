import unittest
from potklin.git_actions import branch_name
from potklin.context_policy import pack
class GitContext(unittest.TestCase):
    def test_branch(self):
        self.assertEqual(branch_name("feature/test"),"feature/test")
        for b in ("-x","a..b","a//b","a/","a b"):
            with self.assertRaises(ValueError):
                branch_name(b)
    def test_pack(self):
        rows=[{"tool":"x","data":"a"*3000,"verified":True} for _ in range(8)]
        result=pack(rows,1000)
        self.assertTrue(all(o["truncated"] for o in result))
        self.assertTrue(all(o["verified"] for o in result))
        self.assertLessEqual(sum(len(o["data"]) for o in result),1000)
