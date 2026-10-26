"""Turn a task description into a tested skill with a language model.

The loop is driven by this module, not by the model, so it works with small
local models that cannot call tools reliably:

    draft -> lint + scan + run tests -> score -> (feedback -> redraft) -> write

Every candidate is judged by the same checks used by ``askit lint``, ``scan``
and ``test``, so the score reflects real results, not the model's opinion.
"""

from __future__ import annotations

import json
import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .config import memory_path
from .providers import LLM
from .scoring import Quality, evaluate_skill
from .skillfile import discover_skills, load_skill, parse_skill_text, slugify, SkillError

ALLOWED_TOP = {"SKILL.md"}
ALLOWED_DIRS = {"scripts", "references", "assets", "tests", "evals"}
MAX_FILES = 12
MAX_FILE_BYTES = 120_000

SYSTEM_PROMPT = """You write agent skills. A skill is a directory with a SKILL.md file that an AI coding agent reads when a task matches. You are precise, concise and you only write things that work.

SKILL.md format:
- It starts with YAML frontmatter between --- lines.
- Required: name (lowercase letters, digits and single hyphens, max 64 characters, same as the directory name) and description (max 1024 characters).
- The description is written in the third person. It states what the skill does AND when an agent should use it ("Use when the user asks to ...").
- Optional: license, compatibility, metadata (version, author, tags as a list).
- After the frontmatter: short markdown instructions with headings (when to use, how to run, output, examples, error handling). Keep it under 150 lines.

If the task is best served by code, add scripts:
- Python 3 standard library only, no network access, no file writes outside the working directory.
- The script reads arguments or stdin and prints a result (JSON when the output is structured).
- Add tests/cases.json so the skill can be verified. Schema:
{
  "entry": "scripts/tool.py",
  "cases": [
    {"name": "short name", "kind": "happy|edge|error", "args": ["--flag"], "stdin": "text",
     "files": {"input.txt": "file content"}, "expect_exit": 0,
     "stdout_contains": ["text"], "stdout_regex": "pattern", "stdout_json": {"key": "value"},
     "stderr_contains": ["text"]}
  ]
}
- Include at least three cases: one happy path, one edge case, one error case.
- Only assert on output you are certain the script produces.
If the task is only about process or judgment (for example writing commit messages), write instructions only: no scripts, no tests.

Output format. Return every file in exactly this form and nothing else outside the blocks:
=== FILE: SKILL.md ===
(file content)
=== END FILE ===
=== FILE: scripts/tool.py ===
(file content)
=== END FILE ===
Do not wrap file content in code fences. Allowed paths: SKILL.md, scripts/, references/, assets/, tests/, evals/."""


class ForgeError(Exception):
    pass


@dataclass
class Candidate:
    round: int
    files: Dict[str, str]
    name: str
    quality: Optional[Quality] = None
    notes: List[str] = field(default_factory=list)


@dataclass
class ForgeResult:
    name: str = ""
    path: Optional[Path] = None
    quality: Optional[Quality] = None
    rounds: int = 0
    accepted: bool = False
    written: bool = False
    files: Dict[str, str] = field(default_factory=dict)
    provider: str = ""
    model: str = ""
    notes: List[str] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0


# ---------------------------------------------------------------------------
# Parsing model output
# ---------------------------------------------------------------------------

_BLOCK_RE = re.compile(r"^=== FILE:\s*(.+?)\s*===[ \t]*\r?\n(.*?)\r?\n=== END FILE ===", re.S | re.M)
_FENCE_RE = re.compile(r"```[ \t]*(?:file:|path:)?[ \t]*([\w./-]+\.[A-Za-z0-9]+|SKILL\.md)[ \t]*\r?\n(.*?)\r?\n```", re.S)


def _unwrap_fence(content: str) -> str:
    m = re.match(r"^\s*```[\w-]*[ \t]*\r?\n(.*?)\r?\n```\s*$", content, re.S)
    return m.group(1) if m else content


def _safe_path(path: str) -> Optional[str]:
    p = path.strip().strip("`").replace("\\", "/").lstrip("./")
    if not p or p.startswith("/") or ".." in p.split("/") or re.match(r"^[A-Za-z]:", p):
        return None
    if p in ALLOWED_TOP:
        return p
    parts = p.split("/")
    if parts[0] in ALLOWED_DIRS and len(parts) >= 2 and len(parts) <= 4:
        return p
    return None


def parse_files(reply: str) -> Tuple[Dict[str, str], List[str]]:
    """Extract files from a model reply. Returns (files, notes)."""
    notes: List[str] = []
    raw: List[Tuple[str, str]] = [(m.group(1), m.group(2)) for m in _BLOCK_RE.finditer(reply)]
    if not raw:
        raw = [(m.group(1), m.group(2)) for m in _FENCE_RE.finditer(reply)]
    if not raw:
        stripped = reply.strip()
        fence = re.search(r"```(?:markdown|md)?\s*\r?\n(---\r?\n.*?)\r?\n```", stripped, re.S)
        if fence:
            raw = [("SKILL.md", fence.group(1))]
        elif stripped.startswith("---"):
            raw = [("SKILL.md", stripped)]
    if not raw:
        return {}, ["no files found in the reply"]
    prefix = ""
    for path, _ in raw:
        norm = path.strip().strip("`").replace("\\", "/")
        if norm.endswith("/SKILL.md"):
            prefix = norm[: -len("SKILL.md")]
            break
    files: Dict[str, str] = {}
    for path, content in raw:
        norm = path.strip().strip("`").replace("\\", "/")
        if prefix and norm.startswith(prefix):
            norm = norm[len(prefix):]
        safe = _safe_path(norm)
        if not safe:
            notes.append("ignored file with unsupported path: %s" % path.strip())
            continue
        body = _unwrap_fence(content)
        if len(body.encode("utf-8")) > MAX_FILE_BYTES:
            notes.append("ignored oversized file: %s" % safe)
            continue
        files[safe] = body.rstrip("\n") + "\n"
        if len(files) >= MAX_FILES:
            notes.append("too many files; extra files ignored")
            break
    return files, notes


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

def build_task_prompt(task: str, context: str = "", name_hint: str = "", similar: Optional[List[str]] = None) -> str:
    parts = ["Create a skill for this task:\n%s" % task.strip()]
    if name_hint:
        parts.append("Use this skill name: %s" % name_hint)
    if context.strip():
        parts.append("Source material to learn from (notes, transcript or runbook):\n---\n%s\n---" % context.strip()[:12000])
    if similar:
        parts.append("Skills that already exist locally (do not duplicate them, be clearly different):\n- "
                     + "\n- ".join(similar))
    parts.append("Return the files now, using the exact === FILE: path === format.")
    return "\n\n".join(parts)


def build_feedback(candidate: Candidate, threshold: float) -> str:
    q = candidate.quality
    lines = ["The skill scored %.2f; the required score is %.2f. Fix these problems and return ALL files again "
             "in the same === FILE: path === format." % (q.score if q else 0.0, threshold)]
    if candidate.notes:
        lines.append("Format notes: " + "; ".join(candidate.notes))
    if q and q.lint:
        issues = [i for i in q.lint.issues if i.severity in ("error", "warning")]
        if issues:
            lines.append("Lint issues:")
            lines.extend("- [%s] %s (line %d)" % (i.code, i.message, i.line) for i in issues[:12])
    if q and q.scan and q.scan.findings:
        lines.append("Security findings (remove these patterns):")
        lines.extend("- [%s] %s in %s line %d" % (f.rule, f.message, f.file, f.line)
                     for f in q.scan.findings[:8] if f.severity in ("high", "medium"))
    if q and q.tests:
        if q.tests.refused:
            lines.append("Tests were not run: " + q.tests.refused)
        failed = [c for c in q.tests.cases if not c.passed]
        if failed:
            lines.append("Failing tests:")
            lines.extend("- %s: %s" % (c.name, c.detail) for c in failed[:8])
        elif not q.tests.has_tests and any(p.startswith("scripts/") for p in candidate.files):
            lines.append("The skill has scripts but no tests/cases.json. Add at least three cases.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Writing candidates
# ---------------------------------------------------------------------------

def _skill_name(files: Dict[str, str], fallback: str) -> str:
    if "SKILL.md" in files:
        parsed = parse_skill_text(files["SKILL.md"])
        n = parsed.meta.get("name")
        if isinstance(n, str) and n.strip():
            return n.strip()
    return slugify(fallback)


def write_files(base: Path, files: Dict[str, str]) -> None:
    for rel, content in files.items():
        target = base / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def _similar_local(task: str, dirs: List[Path]) -> List[str]:
    words = {w for w in re.findall(r"[a-z]{4,}", task.lower())}
    hits: List[Tuple[int, str]] = []
    for d in dirs:
        for sd in discover_skills(d, max_depth=3):
            try:
                s = load_skill(sd)
            except SkillError:
                continue
            blob = (s.name + " " + s.description).lower()
            overlap = sum(1 for w in words if w in blob)
            if overlap >= 2:
                hits.append((overlap, "%s: %s" % (s.name, s.description[:100])))
    hits.sort(reverse=True)
    return [h[1] for h in hits[:5]]


def remember(entry: Dict[str, Any]) -> None:
    try:
        with open(memory_path(), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def forge(task: str, llm: LLM, out_dir: Any, threshold: float = 0.8, max_rounds: int = 3,
          force: bool = False, dry_run: bool = False, context: str = "", name_hint: str = "",
          check_duplicates: bool = True, log: Optional[Callable[[str], None]] = None,
          work_dir: Optional[Path] = None) -> ForgeResult:
    import tempfile

    say = log or (lambda msg: None)
    if not task.strip() and not context.strip():
        raise ForgeError("describe the task with --task or provide --from-file")
    out = Path(out_dir).expanduser()
    similar = _similar_local(task + " " + context[:400], [out]) if check_duplicates else []
    if similar:
        say("Similar skills already exist: " + "; ".join(s.split(":")[0] for s in similar))

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_task_prompt(task, context, name_hint, similar)},
    ]
    result = ForgeResult(provider=llm.name, model=llm.model)
    best: Optional[Candidate] = None
    tmp_root = Path(tempfile.mkdtemp(prefix="askit-forge-")) if work_dir is None else Path(work_dir)

    try:
        for rnd in range(1, max(1, max_rounds) + 1):
            say("round %d/%d: asking %s" % (rnd, max_rounds, llm.describe()))
            reply = llm.chat(messages)
            result.prompt_tokens += reply.prompt_tokens
            result.completion_tokens += reply.completion_tokens
            files, notes = parse_files(reply.content)
            messages.append({"role": "assistant", "content": reply.content})
            if "SKILL.md" not in files:
                cand = Candidate(rnd, files, name_hint or slugify(task[:40]), None, notes + ["SKILL.md is missing"])
                messages.append({"role": "user", "content":
                                 "Your reply did not contain a SKILL.md file in the required format. "
                                 "Return all files using === FILE: path === and === END FILE === markers."})
                say("round %d: no SKILL.md in the reply" % rnd)
                result.rounds = rnd
                continue
            name = _skill_name(files, name_hint or task[:40])
            cdir = tmp_root / ("r%d" % rnd) / name
            if cdir.exists():
                shutil.rmtree(cdir)
            cdir.mkdir(parents=True)
            write_files(cdir, files)
            quality = evaluate_skill(cdir)
            cand = Candidate(rnd, files, name, quality, notes)
            result.rounds = rnd
            say("round %d: %s score %.2f (%s), lint %d errors %d warnings, safety %d, tests %s" % (
                rnd, name, quality.score, quality.grade, len(quality.lint.errors), len(quality.lint.warnings),
                quality.scan.safety if quality.scan else 0,
                "%d/%d" % (quality.tests.passed, quality.tests.total) if quality.tests and quality.tests.has_tests
                else "none"))
            if best is None or (cand.quality and best.quality and cand.quality.score > best.quality.score):
                best = cand
            if quality.score >= threshold and quality.passes_gate:
                result.accepted = True
                break
            if rnd < max_rounds:
                messages.append({"role": "user", "content": build_feedback(cand, threshold)})

        if best is None or best.quality is None:
            raise ForgeError("the model did not produce a usable skill. Try another model with --model")
        result.name = best.name
        result.quality = best.quality
        result.files = best.files
        result.notes = best.notes

        if not result.accepted and not force:
            remember({"event": "rejected", "name": best.name, "score": round(best.quality.score, 3),
                      "rounds": result.rounds, "provider": llm.name, "model": llm.model,
                      "task": task[:200], "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
            return result
        if dry_run:
            return result

        dest = out / best.name
        if dest.exists():
            if not force:
                raise ForgeError("%s already exists. Use --force to overwrite or choose another --name" % dest)
            shutil.rmtree(dest)
        dest.mkdir(parents=True, exist_ok=True)
        write_files(dest, best.files)
        result.path = dest
        result.written = True
        remember({"event": "created", "name": best.name, "score": round(best.quality.score, 3),
                  "rounds": result.rounds, "provider": llm.name, "model": llm.model, "task": task[:200],
                  "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
        return result
    finally:
        if work_dir is None:
            shutil.rmtree(tmp_root, ignore_errors=True)
