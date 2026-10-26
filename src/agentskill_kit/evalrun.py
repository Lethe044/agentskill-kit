"""Behaviour evals: does a model follow a skill better than it does without it?

A skill may ship ``evals/evals.json``:

    {"cases": [{"name": "...", "prompt": "...", "must_include": ["..."],
                "must_not_include": ["..."], "regex": ["..."]}]}

The prompt is sent to a model twice, once with the skill instructions in the
system message and once without (``--baseline``). Checks are plain string
and regex assertions, so results are reproducible and need no judge model.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .providers import LLM
from .skillfile import SkillError, load_skill


@dataclass
class EvalCase:
    name: str
    passed: bool
    detail: str = ""
    baseline_passed: Optional[bool] = None
    output: str = ""


@dataclass
class EvalReport:
    skill: str
    cases: List[EvalCase] = field(default_factory=list)
    has_evals: bool = False

    @property
    def passed(self) -> int:
        return sum(1 for c in self.cases if c.passed)

    @property
    def baseline_passed(self) -> Optional[int]:
        vals = [c.baseline_passed for c in self.cases if c.baseline_passed is not None]
        return sum(1 for v in vals if v) if vals else None


def skill_system_prompt(name: str, description: str, body: str) -> str:
    return ("You are a coding assistant. You have access to the following skill. Apply it when the request "
            "matches its description.\n\nSkill name: %s\nDescription: %s\n\nInstructions:\n%s" % (name, description, body))


def check_output(case: Dict[str, Any], output: str) -> str:
    low = output.lower()
    for s in case.get("must_include", []) or []:
        if str(s).lower() not in low:
            return "missing %r" % s
    for s in case.get("must_not_include", []) or []:
        if str(s).lower() in low:
            return "contains forbidden %r" % s
    for rx in case.get("regex", []) or []:
        if not re.search(rx, output, re.M | re.I):
            return "does not match /%s/" % rx
    return ""


def run_evals(skill_dir: Any, llm: LLM, baseline: bool = False, limit: int = 0) -> EvalReport:
    skill = load_skill(skill_dir)
    path = skill.path / "evals" / "evals.json"
    report = EvalReport(skill=skill.name)
    if not path.exists():
        return report
    report.has_evals = True
    try:
        spec = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise SkillError("evals/evals.json is not valid JSON: %s" % exc)
    cases = spec.get("cases", [])
    if limit:
        cases = cases[:limit]
    system = skill_system_prompt(skill.name, skill.description, skill.body)
    for idx, case in enumerate(cases):
        name = str(case.get("name") or "case %d" % (idx + 1))
        prompt = str(case.get("prompt", ""))
        out = llm.chat([{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                       temperature=0.0, max_tokens=1500).content
        reason = check_output(case, out)
        item = EvalCase(name, not reason, reason, output=out)
        if baseline:
            base_out = llm.chat([{"role": "user", "content": prompt}], temperature=0.0, max_tokens=1500).content
            item.baseline_passed = not check_output(case, base_out)
        report.cases.append(item)
    return report
