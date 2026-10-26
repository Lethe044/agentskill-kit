import unittest

import helpers  # noqa: F401
from helpers import TempDirTest
from agentskill_kit import export


class ExportTests(TempDirTest):
    def setUp(self):
        super().setUp()
        self.skill = self.make_skill("demo-skill", files={"scripts/run.py": "print(1)"})
        self.proj = self.tmp / "proj"
        self.proj.mkdir()

    def test_claude_and_hermes_copy_the_folder(self):
        for target, folder in (("claude", ".claude/skills"), ("hermes", ".hermes/skills")):
            export.export_skill(self.skill, target, self.proj)
            self.assertTrue((self.proj / folder / "demo-skill" / "SKILL.md").exists())
            self.assertTrue((self.proj / folder / "demo-skill" / "scripts" / "run.py").exists())

    def test_cursor_rule(self):
        export.export_skill(self.skill, "cursor", self.proj)
        text = (self.proj / ".cursor/rules/demo-skill.mdc").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\ndescription:"))
        self.assertIn("alwaysApply: false", text)
        self.assertIn("## When to use", text)
        self.assertIn(".agent-skills/demo-skill", text)
        self.assertTrue((self.proj / ".agent-skills/demo-skill/scripts/run.py").exists())

    def test_windsurf_and_copilot(self):
        export.export_skill(self.skill, "windsurf", self.proj)
        self.assertIn("trigger: model_decision", (self.proj / ".windsurf/rules/demo-skill.md").read_text(encoding="utf-8"))
        export.export_skill(self.skill, "copilot", self.proj)
        text = (self.proj / ".github/instructions/demo-skill.instructions.md").read_text(encoding="utf-8")
        self.assertIn('applyTo: "**"', text)

    def test_block_targets_are_idempotent(self):
        agents = self.proj / "AGENTS.md"
        agents.write_text("# Existing notes\n\nKeep this.\n", encoding="utf-8")
        export.export_skill(self.skill, "codex", self.proj)
        first = agents.read_text(encoding="utf-8")
        export.export_skill(self.skill, "codex", self.proj)
        self.assertEqual(first, agents.read_text(encoding="utf-8"))
        self.assertEqual(first.count("agentskill-kit:begin demo-skill"), 1)
        self.assertIn("Keep this.", first)

    def test_block_update_replaces_content(self):
        export.export_skill(self.skill, "gemini", self.proj)
        (self.skill / "SKILL.md").write_text(
            (self.skill / "SKILL.md").read_text(encoding="utf-8").replace("Do the first thing.", "Do the NEW thing."),
            encoding="utf-8")
        export.export_skill(self.skill, "gemini", self.proj)
        text = (self.proj / "GEMINI.md").read_text(encoding="utf-8")
        self.assertIn("NEW thing", text)
        self.assertNotIn("first thing", text)

    def test_two_skills_share_one_file(self):
        other = self.make_skill("other-skill")
        export.export_skill(self.skill, "codex", self.proj)
        export.export_skill(other, "codex", self.proj)
        text = (self.proj / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("begin demo-skill", text)
        self.assertIn("begin other-skill", text)

    def test_dry_run_changes_nothing(self):
        actions = export.export_skill(self.skill, "claude", self.proj, dry_run=True)
        self.assertTrue(actions)
        self.assertFalse((self.proj / ".claude").exists())

    def test_remove(self):
        export.export_skill(self.skill, "claude", self.proj)
        export.export_skill(self.skill, "codex", self.proj)
        self.assertTrue(export.remove_skill("demo-skill", "claude", self.proj))
        self.assertFalse((self.proj / ".claude/skills/demo-skill").exists())
        export.remove_skill("demo-skill", "codex", self.proj)
        self.assertNotIn("demo-skill", (self.proj / "AGENTS.md").read_text(encoding="utf-8"))

    def test_errors(self):
        with self.assertRaises(export.ExportError):
            export.export_skill(self.skill, "nope", self.proj)
        with self.assertRaises(export.ExportError):
            export.export_skill(self.skill, "cursor", self.proj, global_=True)
        with self.assertRaises(export.ExportError):
            export.export_skill(self.tmp / "missing", "claude", self.proj)


if __name__ == "__main__":
    unittest.main()
