"""Regression tests: every skill that ships in this repository must stay healthy."""
import unittest

import helpers  # noqa: F401
from helpers import ROOT
from agentskill_kit import registry, runner
from agentskill_kit.lint import lint_skill
from agentskill_kit.scan import scan_skill
from agentskill_kit.skillfile import discover_skills, load_skill

SKILL_DIRS = discover_skills(ROOT / "skills") + discover_skills(ROOT / "integrations" / "hermes" / "skills")


class StarterSkillTests(unittest.TestCase):
    def test_there_are_enough_skills(self):
        self.assertGreaterEqual(len(discover_skills(ROOT / "skills")), 15)

    def test_lint_is_clean(self):
        for d in SKILL_DIRS:
            with self.subTest(skill=d.name):
                res = lint_skill(d)
                self.assertEqual([(i.code, i.message) for i in res.issues if i.severity != "info"], [])

    def test_scan_has_no_high_or_medium_findings(self):
        for d in SKILL_DIRS:
            with self.subTest(skill=d.name):
                res = scan_skill(d)
                self.assertEqual([f.rule for f in res.findings if f.severity in ("high", "medium")], [])

    def test_bundled_tests_pass(self):
        for d in SKILL_DIRS:
            if not runner.has_tests(d):
                continue
            with self.subTest(skill=d.name):
                rep = runner.run_skill_tests(d)
                failed = [(c.name, c.detail) for c in rep.cases if not c.passed]
                self.assertEqual(failed, [])
                self.assertGreaterEqual(rep.total, 3)

    def test_scripts_come_with_tests(self):
        for d in SKILL_DIRS:
            if (d / "scripts").is_dir():
                with self.subTest(skill=d.name):
                    self.assertTrue(runner.has_tests(d))

    def test_metadata_is_complete(self):
        for d in SKILL_DIRS:
            with self.subTest(skill=d.name):
                s = load_skill(d)
                self.assertTrue(s.license)
                self.assertTrue(s.version)
                self.assertTrue(s.tags)

    def test_committed_index_is_current(self):
        index = registry.build_index([ROOT / "skills"], relative_to=ROOT)
        self.assertTrue(registry.index_is_current(index, ROOT / "registry" / "index.json"),
                        "registry/index.json is stale. Run: askit registry build")


if __name__ == "__main__":
    unittest.main()
