"""Combine lint, scan and test results into a single quality score."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from . import runner
from .lint import LintResult, lint_skill
from .scan import ScanResult, scan_skill
from .skillfile import SkillError, load_skill

WEIGHTS_TESTED = {"lint": 0.30, "safety": 0.25, "tests": 0.35, "docs": 0.10}
WEIGHTS_UNTESTED = {"lint": 0.45, "safety": 0.35, "docs": 0.20}


@dataclass
class Quality:
    skill: str
    score: float
    grade: str
    tested: bool
    breakdown: Dict[str, float] = field(default_factory=dict)
    lint: Optional[LintResult] = None
    scan: Optional[ScanResult] = None
    tests: Optional[runner.TestReport] = None

    @property
    def passes_gate(self) -> bool:
        return bool(self.lint and not self.lint.errors and self.scan and self.scan.count("high") == 0
                    and not (self.tests and self.tests.has_tests and self.tests.rate < 1.0))

    def to_dict(self) -> Dict[str, Any]:
        return {"skill": self.skill, "score": round(self.score, 3), "grade": self.grade,
                "tested": self.tested, "breakdown": {k: round(v, 3) for k, v in self.breakdown.items()},
                "lint": self.lint.to_dict() if self.lint else None,
                "scan": self.scan.to_dict() if self.scan else None,
                "tests": self.tests.to_dict() if self.tests else None}


def grade_for(score: float) -> str:
    for cutoff, letter in ((0.9, "A"), (0.8, "B"), (0.7, "C"), (0.5, "D")):
        if score >= cutoff:
            return letter
    return "F"


def docs_score(skill_dir: Path) -> float:
    try:
        skill = load_skill(skill_dir)
    except SkillError:
        return 0.0
    body = skill.body
    lines = [ln for ln in body.splitlines() if ln.strip()]
    pts = 0.0
    if len(skill.description) >= 60:
        pts += 0.3
    if re.search(r"^#{1,3}\s+\S", body, re.M):
        pts += 0.2
    if re.search(r"\bexamples?\b", body, re.I) or "```" in body:
        pts += 0.2
    if 12 <= len(lines) <= 500:
        pts += 0.2
    if skill.license or skill.version or skill.tags:
        pts += 0.1
    return min(1.0, pts)


def evaluate_skill(skill_dir: Any, run_tests: bool = True, timeout: float = 20.0) -> Quality:
    base = Path(skill_dir).resolve()
    lint = lint_skill(base)
    scan = scan_skill(base) if base.is_dir() else None
    tests = runner.run_skill_tests(base, timeout=timeout) if (run_tests and base.is_dir()) else None
    tested = bool(tests and tests.has_tests)
    parts: Dict[str, float] = {
        "lint": lint.score / 100.0,
        "safety": (scan.safety / 100.0) if scan else 0.0,
        "docs": docs_score(base) if base.is_dir() else 0.0,
    }
    if tested and tests is not None:
        parts["tests"] = tests.rate
        weights = WEIGHTS_TESTED
    else:
        weights = WEIGHTS_UNTESTED
    score = sum(parts[k] * w for k, w in weights.items())
    if lint.errors:
        score = min(score, 0.59)
    if scan and scan.count("high"):
        score = min(score, 0.49)
    return Quality(skill=lint.skill, score=score, grade=grade_for(score), tested=tested,
                   breakdown=parts, lint=lint, scan=scan, tests=tests)
