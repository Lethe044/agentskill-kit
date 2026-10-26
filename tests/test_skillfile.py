import unittest

import helpers  # noqa: F401
from helpers import TempDirTest
from agentskill_kit import skillfile as sf


class ParseTests(unittest.TestCase):
    def test_scalars_lists_and_maps(self):
        text = ("---\nname: demo\ndescription: \"Quoted: value\"\nmetadata:\n  version: 1.0\n  tags: [a, 'b c', d]\n"
                "allowed-tools: Bash Read # trailing comment\nflag: true\nempty: null\n---\nbody\n")
        s = sf.parse_skill_text(text)
        self.assertEqual(s.meta["description"], "Quoted: value")
        self.assertEqual(s.metadata["tags"], ["a", "b c", "d"])
        self.assertEqual(s.meta["allowed-tools"], "Bash Read")
        self.assertIs(s.meta["flag"], True)
        self.assertIsNone(s.meta["empty"])
        self.assertEqual(s.version, "1.0")
        self.assertEqual(s.body.strip(), "body")
        self.assertEqual(s.fm_errors, [])

    def test_folded_and_literal_blocks(self):
        text = "---\nname: x\ndescription: >\n  first line\n  second line\n\n  new paragraph\nnotes: |\n  keep\n  lines\n---\n"
        s = sf.parse_skill_text(text)
        self.assertEqual(s.meta["description"], "first line second line\n\nnew paragraph")
        self.assertEqual(s.meta["notes"], "keep\nlines")

    def test_block_list_and_nested_map(self):
        text = "---\nname: x\ntags:\n  - one\n  - two\nmetadata:\n  author: me\n  deep:\n    k: v\n---\n"
        s = sf.parse_skill_text(text)
        self.assertEqual(s.meta["tags"], ["one", "two"])
        self.assertEqual(s.metadata["deep"], {"k": "v"})

    def test_missing_frontmatter(self):
        s = sf.parse_skill_text("# just markdown\n")
        self.assertFalse(s.has_frontmatter)
        self.assertEqual(s.meta, {})

    def test_unclosed_frontmatter(self):
        self.assertFalse(sf.parse_skill_text("---\nname: x\nno end\n").has_frontmatter)

    def test_bad_line_is_reported(self):
        s = sf.parse_skill_text("---\nname: x\nthis is not yaml\n---\n")
        self.assertTrue(s.fm_errors)

    def test_bom_is_ignored(self):
        self.assertTrue(sf.parse_skill_text("\ufeff---\nname: x\n---\n").has_frontmatter)

    def test_dump_roundtrip(self):
        data = {"name": "demo", "description": "Does: things # really", "license": "MIT",
                "metadata": {"version": "1.0.0", "tags": ["a", "b"]}}
        out = sf.dump_frontmatter(data)
        back = sf.parse_skill_text(out + "body")
        self.assertEqual(back.meta["description"], data["description"])
        self.assertEqual(back.metadata["tags"], ["a", "b"])

    def test_slugify(self):
        self.assertEqual(sf.slugify("Hello, World!!"), "hello-world")
        self.assertEqual(sf.slugify("***"), "new-skill")
        self.assertLessEqual(len(sf.slugify("a" * 200)), 64)


class DiscoveryTests(TempDirTest):
    def test_discover_and_load(self):
        self.make_skill("one")
        self.make_skill("two")
        (self.tmp / "skills" / "node_modules" / "x").mkdir(parents=True)
        (self.tmp / "skills" / "node_modules" / "x" / "SKILL.md").write_text("---\nname: x\n---\n")
        found = sf.discover_skills(self.tmp / "skills")
        self.assertEqual([p.name for p in found], ["one", "two"])
        self.assertEqual(sf.load_skill(found[0]).name, "one")

    def test_load_errors(self):
        with self.assertRaises(sf.SkillError):
            sf.load_skill(self.tmp / "missing")
        (self.tmp / "empty").mkdir()
        with self.assertRaises(sf.SkillError):
            sf.load_skill(self.tmp / "empty")

    def test_iter_skill_files_skips_caches(self):
        d = self.make_skill("one", files={"scripts/a.py": "x=1", "scripts/__pycache__/a.pyc": "x"})
        names = [p.as_posix() for p in sf.iter_skill_files(d)]
        self.assertEqual(names, ["SKILL.md", "scripts/a.py"])


if __name__ == "__main__":
    unittest.main()
