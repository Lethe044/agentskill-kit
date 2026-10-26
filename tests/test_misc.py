import json
import os
import re
import threading
import unittest
import urllib.request
from pathlib import Path

import helpers  # noqa: F401
from helpers import ROOT, TempDirTest
from agentskill_kit import __version__, config, registry, server, ui
from agentskill_kit.scaffold import create_skill
from agentskill_kit.lint import lint_skill


class ConfigTests(TempDirTest):
    def test_set_get_unset(self):
        config.set_setting("provider", "groq")
        self.assertEqual(config.get_setting("provider"), "groq")
        config.set_setting("provider", None)
        self.assertIsNone(config.get_setting("provider"))
        with self.assertRaises(KeyError):
            config.set_setting("nonsense", "x")

    def test_environment_overrides_file(self):
        config.set_setting("model", "from-file")
        os.environ["ASKIT_MODEL"] = "from-env"
        self.addCleanup(os.environ.pop, "ASKIT_MODEL", None)
        self.assertEqual(config.get_setting("model"), "from-env")

    def test_corrupt_config_is_ignored(self):
        config.config_path().write_text("{broken", encoding="utf-8")
        self.assertEqual(config.load_config(), {})

    def test_dotenv(self):
        env = self.tmp / ".env"
        env.write_text('# comment\nASKIT_TEST_A=1\nexport ASKIT_TEST_B="two words"\nASKIT_TEST_C=\'x\'\nBAD LINE\n', encoding="utf-8")
        os.environ["ASKIT_TEST_A"] = "keep"
        for k in ("ASKIT_TEST_A", "ASKIT_TEST_B", "ASKIT_TEST_C"):
            self.addCleanup(os.environ.pop, k, None)
        loaded = config.load_dotenv(env)
        self.assertEqual(os.environ["ASKIT_TEST_A"], "keep")
        self.assertEqual(os.environ["ASKIT_TEST_B"], "two words")
        self.assertEqual(os.environ["ASKIT_TEST_C"], "x")
        self.assertEqual(loaded, 2)


class ScaffoldTests(TempDirTest):
    def test_scaffold_is_valid_and_testable(self):
        d = create_skill("My Cool Skill!", self.tmp, "Counts things. Use when the user asks for counts.", True, "me", ["a"])
        self.assertEqual(d.name, "my-cool-skill")
        self.assertEqual(lint_skill(d).errors, [])
        self.assertTrue((d / "tests" / "cases.json").exists())

    def test_no_overwrite(self):
        create_skill("x", self.tmp)
        with self.assertRaises(FileExistsError):
            create_skill("x", self.tmp)
        create_skill("x", self.tmp, force=True)


class ServerTests(TempDirTest):
    def test_serves_page_and_index(self):
        self.make_skill("served-skill")
        roots = [self.tmp / "skills"]
        handler = server.make_handler(lambda: registry.build_index(roots, run_tests=False, relative_to=self.tmp))
        httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        self.addCleanup(httpd.server_close)
        self.addCleanup(httpd.shutdown)
        base = "http://127.0.0.1:%d" % httpd.server_address[1]
        page = urllib.request.urlopen(base + "/").read().decode("utf-8")
        self.assertIn("served-skill", page)
        data = json.loads(urllib.request.urlopen(base + "/index.json").read())
        self.assertEqual(data["skills"][0]["name"], "served-skill")
        with self.assertRaises(Exception):
            urllib.request.urlopen(base + "/secret.txt")


class UiTests(unittest.TestCase):
    def test_table_ignores_color_codes(self):
        ui.set_no_color(True)
        self.addCleanup(ui.set_no_color, False)
        out = ui.table([("a", "1"), ("longer", "22")], ["name", "n"])
        self.assertIn("longer  22", out)

    def test_truncate(self):
        self.assertEqual(ui.truncate("a  b   c", 20), "a b c")
        self.assertEqual(len(ui.truncate("x" * 100, 10)), 10)


class RepositoryHygieneTests(unittest.TestCase):
    def test_version_matches_pyproject(self):
        text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertEqual(re.search(r'^version = "([^"]+)"', text, re.M).group(1), __version__)

    def test_no_em_dashes_in_tracked_text(self):
        bad = []
        for path in ROOT.rglob("*"):
            if not path.is_file() or any(p in {".git", "__pycache__", "dist", "node_modules"} for p in path.parts):
                continue
            if path.suffix.lower() not in {".py", ".md", ".json", ".yml", ".yaml", ".toml", ".html", ".txt", ".svg", ".cfg"}:
                continue
            if "\u2014" in path.read_text(encoding="utf-8", errors="replace"):
                bad.append(str(path.relative_to(ROOT)))
        self.assertEqual(bad, [])

    def test_required_project_files_exist(self):
        for name in ("README.md", "LICENSE", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "SECURITY.md", "CHANGELOG.md",
                     "pyproject.toml", "action.yml", ".github/workflows/ci.yml", ".github/workflows/publish.yml",
                     ".github/workflows/pages.yml"):
            self.assertTrue((ROOT / name).exists(), name)


if __name__ == "__main__":
    unittest.main()
