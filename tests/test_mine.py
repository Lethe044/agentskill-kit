import unittest

import helpers  # noqa: F401
from helpers import TempDirTest
from agentskill_kit import mine
from agentskill_kit.lint import lint_skill
from agentskill_kit.scan import scan_skill

HISTORY = """git status
git add -A
git commit -m "fix a"
git push origin main
ls
docker build -t app .
git status
git add -A
git commit -m "feat b"
git push origin main
cd ..
git status
git add -A
git commit -m "docs c"
git push origin main
export API_KEY=sk-abcdefghijklmnopqrstuvwxyz0123456789
""".splitlines()


class ParseTests(unittest.TestCase):
    def test_bash_with_timestamps(self):
        self.assertEqual(mine.parse_history("#1700000000\nls -la\n#1700000001\ngit status\n"), ["ls -la", "git status"])

    def test_zsh_extended(self):
        self.assertEqual(mine.parse_history(": 1700000000:0;git pull\n: 1700000005:2;make test\n"), ["git pull", "make test"])

    def test_fish(self):
        text = "- cmd: git pull\n  when: 1700000000\n- cmd: make test\n  when: 1700000001\n"
        self.assertEqual(mine.parse_history(text), ["git pull", "make test"])

    def test_line_continuation(self):
        self.assertEqual(mine.parse_history("docker run \\\n  -p 80:80 app\n"), ["docker run\n  -p 80:80 app"])


class NormalizeTests(unittest.TestCase):
    def test_placeholders(self):
        self.assertEqual(mine.normalize('git commit -m "hello world"'), "git commit -m <str>")
        self.assertEqual(mine.normalize("python tools/run.py data/in.csv 42"), "python <path> <path> <n>")
        self.assertEqual(mine.normalize("git checkout 3f2a9bc"), "git checkout <hash>")
        self.assertEqual(mine.normalize("curl https://x.io/a"), "curl <url>")

    def test_secrets_never_survive(self):
        for cmd in ("curl --token=abc123", "mysql -u root -phunter2 --password hunter2", "export DB_PASSWORD=hunter2"):
            self.assertNotIn("hunter2", mine.normalize(cmd))
            self.assertNotIn("abc123", mine.normalize(cmd))


class MiningTests(TempDirTest):
    def test_finds_the_repeated_sequence(self):
        cands = mine.find_candidates(HISTORY, min_count=3)
        self.assertTrue(cands)
        top = cands[0]
        self.assertEqual(top.kind, "sequence")
        self.assertEqual(top.count, 3)
        self.assertEqual(top.template, ["git status", "git add -A", "git commit -m <str>", "git push origin main"])
        self.assertEqual(top.name, "git-status-add-commit")

    def test_subsequences_are_not_repeated(self):
        cands = mine.find_candidates(HISTORY, min_count=3)
        self.assertEqual(len([c for c in cands if c.kind == "sequence"]), 1)

    def test_trivial_commands_are_ignored(self):
        self.assertEqual(mine.find_candidates(["ls", "cd x", "ls", "cd y"] * 10, min_count=2), [])

    def test_min_count(self):
        self.assertEqual(mine.find_candidates(HISTORY, min_count=4), [])

    def test_examples_are_redacted(self):
        hist = ["curl -H 'X: 1' --token=SECRETVALUE1 https://a.io/x", "make deploy"] * 3
        cands = mine.find_candidates(hist, min_count=3)
        blob = " ".join(" ".join(c.examples) for c in cands)
        self.assertNotIn("SECRETVALUE1", blob)

    def test_draft_is_a_valid_clean_skill(self):
        cand = mine.find_candidates(HISTORY, min_count=3)[0]
        files = mine.draft_skill_files(cand)
        d = self.make_skill(cand.name, text=files["SKILL.md"])
        lint = lint_skill(d)
        self.assertEqual(lint.errors, [], [i.message for i in lint.issues])
        self.assertEqual(scan_skill(d).findings, [])
        self.assertIn("git push origin main", files["SKILL.md"])
        self.assertIn("<str>", files["SKILL.md"])


if __name__ == "__main__":
    unittest.main()
