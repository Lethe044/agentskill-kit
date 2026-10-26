import unittest

import helpers  # noqa: F401
from helpers import TempDirTest, VALID_SKILL
from agentskill_kit.lint import lint_skill


def codes(result):
    return {i.code for i in result.issues}


class LintTests(TempDirTest):
    def test_valid_skill_is_clean(self):
        r = lint_skill(self.make_skill("good-skill"))
        self.assertEqual([i for i in r.issues if i.severity != "info"], [])
        self.assertEqual(r.score, 100)

    def test_missing_directory(self):
        self.assertIn("E001", codes(lint_skill(self.tmp / "nope")))

    def test_no_frontmatter(self):
        r = lint_skill(self.make_skill("x", text="# Only a heading\n"))
        self.assertIn("E002", codes(r))

    def test_name_rules(self):
        bad = VALID_SKILL.format(name="Bad_Name", title="t")
        d = self.make_skill("Bad_Name", text=bad)
        self.assertIn("E005", codes(lint_skill(d)))
        mismatch = self.make_skill("folder", text=VALID_SKILL.format(name="other", title="t"))
        self.assertIn("E006", codes(lint_skill(mismatch)))
        long_name = "a" * 65
        d3 = self.make_skill(long_name, text=VALID_SKILL.format(name=long_name, title="t"))
        self.assertIn("E004", codes(lint_skill(d3)))

    def test_reserved_word_warning(self):
        d = self.make_skill("claude-helper")
        self.assertIn("W011", codes(lint_skill(d)))

    def test_description_rules(self):
        base = "---\nname: {n}\ndescription: {d}\n---\n# Title\n\n## Use\n\nstep one\nstep two\nstep three\n"
        d = self.make_skill("no-desc", text="---\nname: no-desc\n---\n# T\n\nline\nline\nline\n")
        self.assertIn("E007", codes(lint_skill(d)))
        d = self.make_skill("long-desc", text=base.format(n="long-desc", d="x" * 1100))
        self.assertIn("E008", codes(lint_skill(d)))
        d = self.make_skill("xml-desc", text=base.format(n="xml-desc", d="Does <b>things</b> for the user always"))
        self.assertIn("E009", codes(lint_skill(d)))
        d = self.make_skill("short", text=base.format(n="short", d="Short."))
        self.assertIn("W001", codes(lint_skill(d)))
        d = self.make_skill("no-when", text=base.format(n="no-when", d="Computes totals for the quarterly sales report."))
        self.assertIn("W002", codes(lint_skill(d)))
        d = self.make_skill("first", text=base.format(n="first", d="I analyze logs and tell you when they look wrong."))
        self.assertIn("W012", codes(lint_skill(d)))

    def test_body_rules(self):
        text = VALID_SKILL.format(name="b", title="b").split("---\n")[1]
        empty = "---\n" + text + "---\n"
        self.assertIn("W003", codes(lint_skill(self.make_skill("b", text=empty))))
        big = VALID_SKILL.format(name="big", title="big") + "\nline\n" * 520
        self.assertIn("W004", codes(lint_skill(self.make_skill("big", text=big))))
        todo = VALID_SKILL.format(name="todo", title="todo") + "\nTODO: write this\n"
        self.assertIn("W007", codes(lint_skill(self.make_skill("todo", text=todo))))

    def test_broken_reference(self):
        text = VALID_SKILL.format(name="ref", title="ref") + "\nRun `scripts/run.py` first.\n"
        self.assertIn("W006", codes(lint_skill(self.make_skill("ref", text=text))))
        ok = self.make_skill("ref2", text=text.replace("name: ref", "name: ref2"), files={"scripts/run.py": "x"})
        self.assertNotIn("W006", codes(lint_skill(ok)))

    def test_legacy_and_unknown_keys_are_info(self):
        text = VALID_SKILL.format(name="legacy", title="t").replace("license: MIT", "license: MIT\nversion: 1\nweird: yes")
        r = lint_skill(self.make_skill("legacy", text=text))
        self.assertEqual({"I002", "I003"} & codes(r), {"I002", "I003"})
        self.assertEqual(r.errors, [])

    def test_to_dict(self):
        d = lint_skill(self.make_skill("dict-skill")).to_dict()
        self.assertEqual(d["skill"], "dict-skill")
        self.assertIn("issues", d)


if __name__ == "__main__":
    unittest.main()
