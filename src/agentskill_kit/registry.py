"""Build, search and publish a static skill registry.

A registry is a folder of skills plus a generated ``index.json``. Hosting it
needs nothing but static files, so GitHub (raw files and Pages) is enough.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from . import __version__
from .config import RAW_BASE
from .runner import has_tests
from .scoring import evaluate_skill
from .skillfile import SkillError, discover_skills, iter_skill_files, load_skill

SCHEMA = 1
USER_AGENT = "agentskill-kit/%s" % __version__


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def skill_entry(skill_dir: Path, root: Path, include_body: bool = True, run_tests: bool = True) -> Dict[str, Any]:
    """Describe one skill for the index (lint, scan and, optionally, tests are run)."""
    skill = load_skill(skill_dir)
    q = evaluate_skill(skill_dir, run_tests=run_tests)
    lint, scan = q.lint, q.scan
    assert lint is not None and scan is not None
    try:
        rel = skill_dir.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        rel = skill_dir.name
    files = [{"path": f.as_posix(), "sha256": sha256_file(skill_dir / f), "size": (skill_dir / f).stat().st_size}
             for f in iter_skill_files(skill_dir)]
    entry: Dict[str, Any] = {
        "name": skill.name,
        "description": skill.description,
        "version": skill.version or "0.0.0",
        "tags": skill.tags,
        "author": skill.author,
        "license": skill.license,
        "path": rel,
        "files": files,
        "score": round(q.score, 3),
        "grade": q.grade,
        "safety": scan.safety,
        "lint_errors": len(lint.errors),
        "lint_warnings": len(lint.warnings),
        "scan": {"high": scan.count("high"), "medium": scan.count("medium"), "low": scan.count("low")},
        "tested": has_tests(skill_dir),
        "tests_passed": q.tests.passed if q.tests else 0,
        "tests_total": q.tests.total if q.tests else 0,
        "has_scripts": any(f["path"].startswith("scripts/") for f in files),
    }
    if include_body:
        entry["body"] = skill.body.strip()
    return entry


def build_index(roots: Iterable[Any], base_url: str = RAW_BASE, name: str = "agentskill-kit registry",
                include_body: bool = True, relative_to: Optional[Path] = None,
                run_tests: bool = True) -> Dict[str, Any]:
    """Create the registry index for every skill under the given roots."""
    root_paths = [Path(r) for r in roots]
    base = Path(relative_to) if relative_to else (root_paths[0].parent if root_paths else Path.cwd())
    entries: List[Dict[str, Any]] = []
    seen = set()
    for r in root_paths:
        for d in discover_skills(r):
            try:
                e = skill_entry(d, base, include_body, run_tests)
            except SkillError:
                continue
            if e["name"] in seen:
                continue
            seen.add(e["name"])
            entries.append(e)
    entries.sort(key=lambda e: e["name"])
    return {"schema": SCHEMA, "name": name, "generator": "agentskill-kit %s" % __version__,
            "base_url": base_url, "count": len(entries), "skills": entries}


def write_index(index: Dict[str, Any], dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(index, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def index_is_current(index: Dict[str, Any], dest: Path) -> bool:
    if not dest.exists():
        return False
    try:
        current = json.loads(dest.read_text(encoding="utf-8"))
    except ValueError:
        return False
    return json.dumps(current, sort_keys=True) == json.dumps(index, sort_keys=True)


# ---------------------------------------------------------------------------
# Loading and search
# ---------------------------------------------------------------------------

def fetch_bytes(url: str, timeout: float = 30.0) -> bytes:
    if re.match(r"^[a-z][a-z0-9+.-]*://", url, re.I):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    return Path(url).expanduser().read_bytes()


def load_index(source: str) -> Dict[str, Any]:
    try:
        data = json.loads(fetch_bytes(source).decode("utf-8"))
    except Exception as exc:
        raise SkillError("could not load registry %s: %s" % (source, exc))
    if not isinstance(data, dict) or "skills" not in data:
        raise SkillError("%s is not a valid registry index" % source)
    return data


def _tokens(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def search(index: Dict[str, Any], query: str, tag: str = "", limit: int = 20) -> List[Dict[str, Any]]:
    """Rank skills with a small BM25-style score over name, tags and description."""
    skills = index.get("skills", [])
    if tag:
        skills = [s for s in skills if tag.lower() in [t.lower() for t in s.get("tags", [])]]
    q = _tokens(query)
    if not q:
        return sorted(skills, key=lambda s: -s.get("score", 0))[:limit]
    docs = []
    for s in skills:
        fields = {"name": _tokens(s["name"].replace("-", " ")), "tags": _tokens(" ".join(s.get("tags", []))),
                  "desc": _tokens(s.get("description", ""))}
        docs.append((s, fields))
    n = max(1, len(docs))
    df: Dict[str, int] = {}
    for _, f in docs:
        for term in set(f["name"] + f["tags"] + f["desc"]):
            df[term] = df.get(term, 0) + 1
    scored = []
    for s, f in docs:
        total = 0.0
        for term in q:
            idf = math.log(1 + (n - df.get(term, 0) + 0.5) / (df.get(term, 0) + 0.5))
            tf = 3.0 * (term in f["name"]) + 2.0 * (term in f["tags"]) + min(2, f["desc"].count(term)) * 0.8
            if not tf:
                # prefix match so "summar" finds "summarizer"
                tf = 1.5 * any(w.startswith(term) for w in f["name"] + f["tags"]) + \
                     0.5 * any(w.startswith(term) for w in f["desc"])
            total += idf * tf
        if total > 0:
            scored.append((total + s.get("score", 0) * 0.3, s))
    scored.sort(key=lambda x: -x[0])
    return [s for _, s in scored[:limit]]


def find(index: Dict[str, Any], name: str) -> Optional[Dict[str, Any]]:
    for s in index.get("skills", []):
        if s["name"] == name:
            return s
    return None
