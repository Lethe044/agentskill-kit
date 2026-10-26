"""Atropos reinforcement learning environment for skill authoring.

The environment rewards an agent that writes a SKILL.md, tests it with real code
and checks quality before it shares the result. It is the training side of the
agentskill-kit workflow: the same lint, scan and test steps that ``askit`` runs
can be used to verify what the agent claims (see ``verified_quality``).

Atropos is optional. Without it the environment falls back to a plain base class
so the reward function can be developed and tested anywhere.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from atropos.environments.base import HermesAgentBaseEnv
except ImportError:
    class HermesAgentBaseEnv:  # type: ignore[no-redef]
        """Stand-in used when Atropos is not installed."""


@dataclass
class ForgeScenario:
    id: str
    title: str
    prompt: str
    expected_skill_name: str
    expected_tags: List[str]
    min_test_cases: int = 3
    difficulty: str = "medium"  # easy, medium or hard


SCENARIOS: List[ForgeScenario] = [
    ForgeScenario(
        id="forge-web-summarizer",
        title="Forge a web content summarizer skill",
        prompt="I keep summarizing web content manually. Fetch text, return 3 bullets. Build a reusable skill for this.",
        expected_skill_name="web-summarizer",
        expected_tags=["nlp", "summarization", "web"],
        difficulty="easy",
    ),
    ForgeScenario(
        id="forge-log-analyzer",
        title="Forge a log pattern analyzer skill",
        prompt="Team keeps manually grepping logs every week. Build a skill that counts errors by type from log text.",
        expected_skill_name="log-analyzer",
        expected_tags=["devops", "logs", "monitoring"],
        difficulty="medium",
    ),
    ForgeScenario(
        id="forge-code-reviewer",
        title="Forge an automated code reviewer skill",
        prompt="Devs keep asking reviews on simple functions. Same feedback repeats. Build a skill that detects missing docstrings, bare excepts, magic numbers.",
        expected_skill_name="code-reviewer",
        expected_tags=["code", "review", "quality"],
        difficulty="medium",
    ),
    ForgeScenario(
        id="forge-data-validator",
        title="Forge a data validation skill",
        prompt="We keep writing the same validation logic: check required fields, validate types, report errors. Make it a skill.",
        expected_skill_name="data-validator",
        expected_tags=["data", "validation", "quality"],
        difficulty="hard",
    ),
    ForgeScenario(
        id="forge-api-tester",
        title="Forge an API endpoint tester skill",
        prompt="QA team manually tests every endpoint after deploys. Build a skill that sends test requests and validates responses.",
        expected_skill_name="api-tester",
        expected_tags=["testing", "api", "qa"],
        difficulty="hard",
    ),
]


def verified_quality(skill_dir: Any) -> float:
    """Score a finished skill with agentskill-kit (0.0 to 1.0).

    Returns 0.0 when agentskill-kit is not installed or the directory is not a skill.
    Use it to replace the quality number the agent reports about itself.
    """
    try:
        from agentskill_kit.scoring import evaluate_skill
    except ImportError:
        return 0.0
    path = Path(skill_dir).expanduser()
    if not (path / "SKILL.md").exists():
        return 0.0
    return float(evaluate_skill(path).score)


def compute_skill_reward(
    trajectory: Dict[str, Any],
    scenario: ForgeScenario,
    verified_score: Optional[float] = None,
) -> Dict[str, float]:
    """Reward for one episode.

    Components and weights:
        skill_written   0.30  a SKILL.md was written
        tests_executed  0.25  real code was executed (three or more runs earn the full amount)
        quality_score   0.20  quality reached, from ``verified_score`` when given
        published       0.10  the skill was published
        searched_first  0.10  existing skills or memory were searched before writing
        documentation   0.05  description, examples and inputs are present
    """
    output = trajectory.get("output", "")
    tool_calls = trajectory.get("tool_calls", [])
    tool_names = [tc.get("name", "") for tc in tool_calls]
    rewards: Dict[str, float] = {}

    wrote_skill = any(
        tc.get("name") == "write_file" and "SKILL.md" in tc.get("input", {}).get("path", "")
        for tc in tool_calls
    )
    rewards["skill_written"] = 0.30 if wrote_skill else 0.0

    code_executions = sum(1 for n in tool_names if n == "execute_code")
    if code_executions >= 3:
        rewards["tests_executed"] = 0.25
    elif code_executions >= 1:
        rewards["tests_executed"] = 0.12
    else:
        rewards["tests_executed"] = 0.0

    if verified_score is not None:
        quality = max(0.0, min(1.0, float(verified_score)))
    else:
        quality = 0.0
        for tc in tool_calls:
            if tc.get("name") == "publish_skill":
                q = tc.get("input", {}).get("quality_score", 0.0)
                if isinstance(q, (int, float)):
                    quality = max(quality, float(q))
        match = re.search(r"quality[_\s]*score[:\s]+([0-9.]+)", output, re.IGNORECASE)
        if match and quality == 0:
            try:
                quality = float(match.group(1))
            except ValueError:
                quality = 0.0
    rewards["quality_score"] = min(0.20, quality * 0.20)

    rewards["published"] = 0.10 if any(n == "publish_skill" for n in tool_names) else 0.0

    first_write_idx = next((i for i, n in enumerate(tool_names) if n == "write_file"), len(tool_names))
    searched_before = any(
        tool_names[i] in ("search_skills", "search_memory") for i in range(first_write_idx)
    )
    rewards["searched_first"] = 0.10 if searched_before else 0.0

    skill_content = ""
    for tc in tool_calls:
        if tc.get("name") == "write_file" and "SKILL.md" in tc.get("input", {}).get("path", ""):
            skill_content = tc.get("input", {}).get("content", "")
    has_description = bool(re.search(r"description:", skill_content))
    has_examples = "example" in skill_content.lower()
    has_inputs = "inputs:" in skill_content
    rewards["documentation"] = round(0.05 * sum([has_description, has_examples, has_inputs]) / 3, 4)

    rewards["total"] = round(sum(rewards.values()), 4)
    return rewards


class SkillForgeEnv(HermesAgentBaseEnv):
    """Environment that cycles through skill authoring scenarios."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._scenarios = SCENARIOS * 3
        self._idx = 0

    def get_next_item(self) -> ForgeScenario:
        scenario = self._scenarios[self._idx % len(self._scenarios)]
        self._idx += 1
        return scenario

    def format_prompt(self, scenario: ForgeScenario) -> str:
        return (
            f"Task: {scenario.title}\n\n"
            f"{scenario.prompt}\n\n"
            f"Expected skill name: {scenario.expected_skill_name}\n"
            f"Expected tags: {', '.join(scenario.expected_tags)}\n"
            f"Required test cases: {scenario.min_test_cases}\n\n"
            "Complete the full loop: observe, abstract, write, test, refine, publish."
        )

    def evaluate(self, trajectory: Dict[str, Any], scenario: ForgeScenario,
                 skill_dir: Optional[Any] = None) -> Dict[str, Any]:
        verified = verified_quality(skill_dir) if skill_dir else None
        rewards = compute_skill_reward(trajectory, scenario, verified)
        return {
            "rewards": rewards,
            "total_reward": rewards["total"],
            "scenario_id": scenario.id,
            "difficulty": scenario.difficulty,
        }


def smoke_test() -> None:
    env = SkillForgeEnv()
    for _ in range(len(SCENARIOS)):
        scenario = env.get_next_item()
        assert len(env.format_prompt(scenario)) > 50
        print("ok  %s" % scenario.id)


if __name__ == "__main__":
    smoke_test()
