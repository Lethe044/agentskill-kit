import json
import unittest

import helpers  # noqa: F401
from helpers import TempDirTest
from agentskill_kit import evalrun
from agentskill_kit.providers import PROVIDERS, LLM


class EvalTests(TempDirTest):
    def skill(self, cases):
        return self.make_skill("eval-skill", files={"evals/evals.json": json.dumps({"cases": cases})})

    def test_check_output(self):
        case = {"must_include": ["alpha"], "must_not_include": ["beta"], "regex": ["^a\\w+"]}
        self.assertEqual(evalrun.check_output(case, "Alpha ok"), "")
        self.assertIn("missing", evalrun.check_output(case, "gamma"))
        self.assertIn("forbidden", evalrun.check_output(case, "alpha beta"))
        self.assertIn("match", evalrun.check_output({"regex": ["^z"]}, "alpha"))

    def test_run_with_and_without_skill(self):
        d = self.skill([{"name": "one", "prompt": "p", "must_include": ["fix:"]}])
        # reply 1: with skill, reply 2: baseline
        llm = LLM(PROVIDERS["mock"], "mock", scripted=["fix: done", "something else"])
        rep = evalrun.run_evals(d, llm, baseline=True)
        self.assertTrue(rep.has_evals)
        self.assertEqual(rep.passed, 1)
        self.assertEqual(rep.baseline_passed, 0)

    def test_system_prompt_contains_skill(self):
        seen = []

        class Spy(LLM):
            def chat(self, messages, **kw):
                seen.append(messages)
                return super().chat(messages, **kw)

        d = self.skill([{"name": "one", "prompt": "question"}])
        evalrun.run_evals(d, Spy(PROVIDERS["mock"], "mock", scripted=["x"]))
        self.assertIn("eval-skill", seen[0][0]["content"])
        self.assertEqual(seen[0][1]["content"], "question")

    def test_skill_without_evals(self):
        rep = evalrun.run_evals(self.make_skill("plain"), LLM(PROVIDERS["mock"], "mock", scripted=[]))
        self.assertFalse(rep.has_evals)


if __name__ == "__main__":
    unittest.main()
