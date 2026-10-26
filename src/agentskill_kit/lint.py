"""Structural checks for SKILL.md files. Works offline and needs no model."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .skillfile import Skill, SkillError, load_skill

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
KNOWN_KEYS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
LEGACY_KEYS = {"version", "author", "tags"}
RESERVED_WORDS = ("anthropic", "claude")
TRIGGER_RE = re.compile(
    r"\b(use when|use this|use for|use it|when the user|when you|whenever|if the user|"
    r"trigger|invoke|asks? (?:to|for)|needs? to|when (?:asked|working|reviewing|writing|"
    r"creating|debugging|analy[sz]ing|you))\b", re.I)
FIRST_PERSON_RE = re.compile(r"^\s*(i|i'll|i can|i will|my|we|you can|you will)\b", re.I)
PLACEHOLDER_RE = re.compile(
    r"\b(?:TODO|FIXME|TBD):|[\[<](?:TODO|FIXME|TBD)[\]>]|\blorem ipsum\b|<your[ -][^>]*>|\[insert [^\]]*\]"
    r"|\bReplace this (?:line|step)\b|\bDescribe what this skill does\b", re.I)
REF_RE = re.compile(r"(?<![\w/.-])((?:scripts|references|assets|tests|evals)/[\w./-]+\.[A-Za-z0-9]+)")
LINK_RE = re.compile(r"\]\((?!https?:|mailto:|#)([^)\s#]+)")

SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}


@dataclass
class Issue:
    code: str
    severity: str
    message: str
    file: str = "SKILL.md"
    line: int = 0
    hint: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"code": self.code, "severity": self.severity, "message": self.message,
                "file": self.file, "line": self.line, "hint": self.hint}


@dataclass
class LintResult:
    skill: str
    path: str
    issues: List[Issue] = field(default_factory=list)

    @property
    def errors(self) -> List[Issue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> List[Issue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def score(self) -> int:
        return max(0, 100 - 25 * len(self.errors) - 6 * len(self.warnings))

    def to_dict(self) -> Dict[str, Any]:
        return {"skill": self.skill, "path": self.path, "score": self.score,
                "errors": len(self.errors), "warnings": len(self.warnings),
                "issues": [i.to_dict() for i in self.issues]}


def _find_line(skill: Skill, key: str) -> int:
    for idx, ln in enumerate(skill.fm_lines):
        if ln.startswith(key + ":"):
            return idx + 2
    return 1


def lint_skill(target: Any) -> LintResult:
    """Lint a skill directory (or SKILL.md path)."""
    try:
        skill = load_skill(target)
    except SkillError as exc:
        return LintResult(skill=Path(str(target)).name, path=str(target),
                          issues=[Issue("E001", "error", str(exc), file=str(target))])
    return lint_loaded(skill)


def lint_loaded(skill: Skill) -> LintResult:
    res = LintResult(skill=skill.name, path=str(skill.path))
    add = res.issues.append

    if not skill.has_frontmatter:
        add(Issue("E002", "error", "SKILL.md must start with a YAML frontmatter block between --- lines",
                  line=1, hint="Add name and description at the top of the file."))
        return res

    for line_no, msg in skill.fm_errors:
        add(Issue("E010", "error", "frontmatter: " + msg, line=line_no))
    for idx, ln in enumerate(skill.fm_lines):
        if "\t" in ln:
            add(Issue("W010", "warning", "tab character in frontmatter; use spaces", line=idx + 2))

    meta = skill.meta
    name = meta.get("name")
    if not name or not isinstance(name, str):
        add(Issue("E003", "error", "missing required field: name", line=1))
    else:
        line = _find_line(skill, "name")
        if len(name) > 64:
            add(Issue("E004", "error", "name is %d characters; the limit is 64" % len(name), line=line))
        if not NAME_RE.match(name):
            add(Issue("E005", "error",
                      "name must use lowercase letters, digits and single hyphens (got %r)" % name,
                      line=line, hint="Example: log-analyzer"))
        if name != skill.path.name:
            add(Issue("E006", "error",
                      "name %r does not match the directory name %r" % (name, skill.path.name),
                      line=line, hint="Rename the directory or the name field so both agree."))
        if any(w in name for w in RESERVED_WORDS):
            add(Issue("W011", "warning", "name contains a reserved word (%s)" % "/".join(RESERVED_WORDS),
                      line=line, hint="Some agents reject skill names that include these words."))

    desc = meta.get("description")
    dline = _find_line(skill, "description")
    if not desc or not isinstance(desc, str):
        add(Issue("E007", "error", "missing required field: description", line=1,
                  hint="Describe what the skill does and when an agent should use it."))
    else:
        if len(desc) > 1024:
            add(Issue("E008", "error", "description is %d characters; the limit is 1024" % len(desc), line=dline))
        if re.search(r"</?[A-Za-z][^>]*>", desc):
            add(Issue("E009", "error", "description must not contain XML or HTML tags", line=dline))
        if PLACEHOLDER_RE.search(desc):
            add(Issue("W007", "warning", "description still contains template text", line=dline))
        if len(desc) < 40:
            add(Issue("W001", "warning", "description is very short (%d characters)" % len(desc), line=dline,
                      hint="Agents pick skills by description. Say what it does and when to use it."))
        if not TRIGGER_RE.search(desc):
            add(Issue("W002", "warning", "description does not say when to use the skill", line=dline,
                      hint="Add a sentence such as 'Use when the user asks to ...'."))
        if FIRST_PERSON_RE.match(desc):
            add(Issue("W012", "warning", "description should be written in the third person", line=dline,
                      hint="Write 'Analyzes logs ...' instead of 'I analyze logs ...'."))

    comp = meta.get("compatibility")
    if isinstance(comp, str) and len(comp) > 500:
        add(Issue("E011", "error", "compatibility is %d characters; the limit is 500" % len(comp),
                  line=_find_line(skill, "compatibility")))

    if "metadata" in meta and not isinstance(meta["metadata"], dict):
        add(Issue("E012", "error", "metadata must be a mapping of keys to values",
                  line=_find_line(skill, "metadata")))

    for key in meta:
        if key in KNOWN_KEYS:
            continue
        if key in LEGACY_KEYS:
            add(Issue("I002", "info", "top-level key %r is accepted but belongs under metadata" % key,
                      line=_find_line(skill, key)))
        else:
            add(Issue("I003", "info", "unknown frontmatter key %r (ignored by most agents)" % key,
                      line=_find_line(skill, key)))
    if not meta.get("license"):
        add(Issue("I001", "info", "no license field", line=1,
                  hint="Add license: MIT (or similar) if you plan to share the skill."))

    body = skill.body
    nonblank = [ln for ln in body.splitlines() if ln.strip()]
    if len(nonblank) < 3:
        add(Issue("W003", "warning", "the instructions are empty or nearly empty", line=skill.body_line))
    total_lines = len(body.splitlines())
    if total_lines > 500:
        add(Issue("W004", "warning", "body has %d lines; keep SKILL.md under 500" % total_lines,
                  line=skill.body_line, hint="Move long reference material to references/*.md."))
    if nonblank and not re.search(r"^#{1,3}\s+\S", body, re.M):
        add(Issue("W005", "warning", "no markdown headings in the instructions", line=skill.body_line))
    for m in PLACEHOLDER_RE.finditer(body):
        line = skill.body_line + body.count("\n", 0, m.start())
        add(Issue("W007", "warning", "placeholder text found: %r" % m.group(0), line=line))
        break

    seen = set()
    for m in list(REF_RE.finditer(body)) + list(LINK_RE.finditer(body)):
        ref = m.group(1).strip("`.,;:")
        if ref in seen or not ref:
            continue
        seen.add(ref)
        if not (skill.path / ref).exists():
            line = skill.body_line + body.count("\n", 0, m.start())
            add(Issue("W006", "warning", "referenced file does not exist: %s" % ref, line=line))

    res.issues.sort(key=lambda i: (SEVERITY_ORDER.get(i.severity, 3), i.line, i.code))
    return res


def format_github(result: LintResult) -> List[str]:
    out = []
    for i in result.issues:
        if i.severity == "info":
            continue
        level = "error" if i.severity == "error" else "warning"
        path = Path(result.path) / i.file
        out.append("::%s file=%s,line=%d::[%s] %s" % (level, path.as_posix(), max(1, i.line), i.code, i.message))
    return out
