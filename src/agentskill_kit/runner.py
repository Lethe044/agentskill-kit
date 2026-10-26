"""Run the tests that ship with a skill.

Two formats are supported and can be combined:

* ``tests/cases.json``: declarative command line cases for a script.
* ``tests/test_*.py``: standard unittest modules, run from the skill root.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import sandbox
from .scan import scan_text, SEVERITY_RANK


@dataclass
class CaseResult:
    name: str
    kind: str
    passed: bool
    detail: str = ""
    duration: float = 0.0
    n_passed: Optional[int] = None
    n_total: int = 1

    def __post_init__(self) -> None:
        if self.n_passed is None:
            self.n_passed = 1 if self.passed else 0


@dataclass
class TestReport:
    __test__ = False  # keep pytest from collecting this class

    skill: str
    has_tests: bool = False
    cases: List[CaseResult] = field(default_factory=list)
    refused: str = ""

    @property
    def passed(self) -> int:
        return sum(int(c.n_passed or 0) for c in self.cases)

    @property
    def total(self) -> int:
        return sum(c.n_total for c in self.cases)

    @property
    def rate(self) -> float:
        if self.refused:
            return 0.0
        return (self.passed / self.total) if self.total else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {"skill": self.skill, "has_tests": self.has_tests, "passed": self.passed,
                "total": self.total, "refused": self.refused,
                "cases": [{"name": c.name, "kind": c.kind, "passed": c.passed, "detail": c.detail}
                          for c in self.cases]}


def has_tests(skill_dir: Path) -> bool:
    t = skill_dir / "tests"
    return t.is_dir() and ((t / "cases.json").exists() or any(t.glob("test_*.py")))


def _safe_rel(rel: str) -> bool:
    p = Path(rel)
    return not p.is_absolute() and ".." not in p.parts and bool(rel)


def _as_list(v: Any) -> List[str]:
    if v is None:
        return []
    return [str(x) for x in v] if isinstance(v, list) else [str(v)]


def _subset(expected: Any, actual: Any) -> bool:
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(k in actual and _subset(v, actual[k]) for k, v in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(expected) == len(actual) and all(
            _subset(e, a) for e, a in zip(expected, actual))
    return expected == actual


def _check_case(case: Dict[str, Any], res: sandbox.RunResult) -> str:
    """Return an empty string when the case passes, otherwise a reason."""
    if res.error:
        return "could not start: " + res.error
    if res.timed_out:
        return "timed out"
    want_exit = case.get("expect_exit", 0)
    if want_exit is not None and res.exit_code != want_exit:
        tail = (res.stderr or res.stdout).strip().splitlines()[-1:] or [""]
        return "exit code %s, expected %s (%s)" % (res.exit_code, want_exit, tail[0][:120])
    for s in _as_list(case.get("stdout_contains")):
        if s not in res.stdout:
            return "stdout does not contain %r" % s
    for s in _as_list(case.get("stdout_not_contains")):
        if s in res.stdout:
            return "stdout unexpectedly contains %r" % s
    for s in _as_list(case.get("stderr_contains")):
        if s not in res.stderr:
            return "stderr does not contain %r" % s
    for rx in _as_list(case.get("stdout_regex")):
        if not re.search(rx, res.stdout, re.M):
            return "stdout does not match /%s/" % rx
    if "stdout_json" in case:
        try:
            actual = json.loads(res.stdout)
        except ValueError:
            return "stdout is not valid JSON"
        if not _subset(case["stdout_json"], actual):
            return "JSON output differs from expected"
    return ""


def _run_cases(root: Path, spec: Dict[str, Any], timeout: float) -> List[CaseResult]:
    """Run declarative cases. Each case gets its own empty working directory."""
    import shutil
    import tempfile

    entry = spec.get("entry")
    out: List[CaseResult] = []
    for idx, case in enumerate(spec.get("cases", [])):
        name = str(case.get("name") or "case %d" % (idx + 1))
        kind = str(case.get("kind") or "case")
        script = case.get("entry") or entry
        if not script or not _safe_rel(str(script)) or not (root / script).is_file():
            out.append(CaseResult(name, kind, False, "entry script not found: %s" % script))
            continue
        bad = next((f for f in (case.get("files") or {}) if not _safe_rel(f)), None)
        if bad:
            out.append(CaseResult(name, kind, False, "unsafe file path in case: %s" % bad))
            continue
        workdir = Path(tempfile.mkdtemp(prefix="askit-case-"))
        try:
            for rel, content in (case.get("files") or {}).items():
                p = workdir / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(str(content), encoding="utf-8")
            args = [str((root / script).resolve())] + [str(a) for a in case.get("args", [])]
            res = sandbox.run_python(args, workdir, stdin=str(case.get("stdin", "")),
                                     timeout=float(case.get("timeout", timeout)))
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
        reason = _check_case(case, res)
        out.append(CaseResult(name, kind, not reason, reason, res.duration))
    return out


def _run_unittests(root: Path, timeout: float) -> Optional[CaseResult]:
    tests_dir = root / "tests"
    if not any(tests_dir.glob("test_*.py")):
        return None
    res = sandbox.run_python(["-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
                             root, timeout=timeout * 3)
    text = res.stderr + "\n" + res.stdout
    m = re.search(r"Ran (\d+) tests?", text)
    if not m:
        return CaseResult("unittest", "unittest", False, "could not run: " + text.strip()[-200:], res.duration, 0, 1)
    total = int(m.group(1))
    failures = int(next(iter(re.findall(r"failures=(\d+)", text)), 0))
    errors = int(next(iter(re.findall(r"errors=(\d+)", text)), 0))
    skipped = int(next(iter(re.findall(r"skipped=(\d+)", text)), 0))
    passed = max(0, total - failures - errors)
    ok = failures == 0 and errors == 0
    detail = "" if ok else "%d failure(s), %d error(s)" % (failures, errors)
    return CaseResult("unittest (%d tests%s)" % (total, ", %d skipped" % skipped if skipped else ""),
                      "unittest", ok, detail, res.duration, passed, max(total, 1))


def run_skill_tests(skill_dir: Any, timeout: float = 20.0, allow_unsafe: bool = False) -> TestReport:
    base = Path(skill_dir).resolve()
    report = TestReport(skill=base.name)
    if not has_tests(base):
        return report
    report.has_tests = True

    if not allow_unsafe:
        for py in sorted(base.rglob("*.py")):
            if "__pycache__" in py.parts:
                continue
            try:
                findings = scan_text(py.read_text(encoding="utf-8", errors="replace"), py.name)
            except OSError:
                continue
            high = [f for f in findings if SEVERITY_RANK[f.severity] >= 3]
            if high:
                report.refused = "%s has high severity findings (%s); refusing to execute" % (
                    py.relative_to(base).as_posix(), ", ".join(sorted({f.rule for f in high})))
                return report

    with sandbox.scratch_copy(base) as root:
        spec_path = root / "tests" / "cases.json"
        if spec_path.exists():
            try:
                spec = json.loads(spec_path.read_text(encoding="utf-8"))
            except ValueError as exc:
                report.cases.append(CaseResult("cases.json", "spec", False, "invalid JSON: %s" % exc))
                spec = {}
            if isinstance(spec, dict) and spec.get("cases"):
                report.cases.extend(_run_cases(root, spec, timeout))
            elif isinstance(spec, dict) and not report.cases:
                report.cases.append(CaseResult("cases.json", "spec", False, "no cases defined"))
        ut = _run_unittests(root, timeout)
        if ut:
            report.cases.append(ut)
    return report
