import sys
import unittest

import helpers  # noqa: F401
from helpers import ROOT, TempDirTest

sys.path.insert(0, str(ROOT / "integrations" / "hermes"))
from skill_forge_env import ForgeScenario, SCENARIOS, SkillForgeEnv, compute_skill_reward, verified_quality  # noqa: E402


def trajectory(search=True, write=True, code_runs=3, quality=0.93, publish=True):
    calls = []
    if search:
        calls += [{"name": "search_memory", "input": {"query": "x"}}, {"name": "search_skills", "input": {"query": "x"}}]
    if write:
        calls.append({"name": "write_file", "input": {
            "path": "~/.hermes/skills/demo/SKILL.md",
            "content": "---\nname: demo\ndescription: Demo\ninputs:\n  - name: text\nexamples:\n  - input: a\n"}})
    calls += [{"name": "execute_code", "input": {"code": "print(1)"}} for _ in range(code_runs)]
    if publish:
        calls.append({"name": "publish_skill", "input": {"skill_name": "demo", "quality_score": quality}})
    return {"output": "quality_score: %s" % quality, "tool_calls": calls}


class ScenarioTests(unittest.TestCase):
    def test_scenarios(self):
        self.assertGreaterEqual(len(SCENARIOS), 5)
        for s in SCENARIOS:
            self.assertTrue(s.id and s.title and s.expected_skill_name and s.expected_tags)
            self.assertIn(s.difficulty, ("easy", "medium", "hard"))
            self.assertGreaterEqual(len(s.prompt), 50)

    def test_env_cycles_and_formats(self):
        env = SkillForgeEnv()
        ids = [env.get_next_item().id for _ in range(len(SCENARIOS) * 2)]
        self.assertEqual(len(set(ids)), len(SCENARIOS))
        prompt = env.format_prompt(SCENARIOS[0])
        self.assertIn(SCENARIOS[0].expected_skill_name, prompt)


class RewardTests(TempDirTest):
    def test_perfect_run(self):
        r = compute_skill_reward(trajectory(), SCENARIOS[0])
        self.assertGreaterEqual(r["total"], 0.9)
        self.assertEqual((r["skill_written"], r["tests_executed"], r["published"], r["searched_first"]),
                         (0.30, 0.25, 0.10, 0.10))

    def test_components(self):
        self.assertEqual(compute_skill_reward(trajectory(code_runs=0), SCENARIOS[0])["tests_executed"], 0.0)
        self.assertEqual(compute_skill_reward(trajectory(code_runs=1), SCENARIOS[0])["tests_executed"], 0.12)
        self.assertEqual(compute_skill_reward(trajectory(search=False), SCENARIOS[0])["searched_first"], 0.0)
        self.assertEqual(compute_skill_reward(trajectory(publish=False), SCENARIOS[0])["published"], 0.0)
        self.assertEqual(compute_skill_reward(trajectory(write=False), SCENARIOS[0])["skill_written"], 0.0)

    def test_search_after_write_does_not_count(self):
        t = trajectory(search=False)
        t["tool_calls"].append({"name": "search_skills", "input": {}})
        self.assertEqual(compute_skill_reward(t, SCENARIOS[0])["searched_first"], 0.0)

    def test_total_is_bounded(self):
        for kwargs in ({}, {"quality": 5.0}, {"quality": -1.0}, {"write": False, "search": False, "publish": False}):
            self.assertTrue(0.0 <= compute_skill_reward(trajectory(**kwargs), SCENARIOS[0])["total"] <= 1.0)

    def test_verified_score_replaces_self_report(self):
        low = compute_skill_reward(trajectory(quality=1.0), SCENARIOS[0], verified_score=0.0)
        high = compute_skill_reward(trajectory(quality=0.0), SCENARIOS[0], verified_score=1.0)
        self.assertEqual(low["quality_score"], 0.0)
        self.assertEqual(high["quality_score"], 0.2)

    def test_verified_quality_uses_the_real_checks(self):
        good = self.make_skill("real-skill")
        self.assertGreaterEqual(verified_quality(good), 0.9)
        self.assertEqual(verified_quality(self.tmp / "nothing"), 0.0)
        env = SkillForgeEnv()
        out = env.evaluate(trajectory(quality=0.0), SCENARIOS[0], skill_dir=good)
        self.assertGreater(out["rewards"]["quality_score"], 0.15)


if __name__ == "__main__":
    unittest.main()
