"""Quality gates, packaging and contribution helpers for sharing skills."""

from __future__ import annotations

import json
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import registry
from .scoring import Quality, evaluate_skill
from .skillfile import iter_skill_files, load_skill


class PublishError(Exception):
    pass


def check_gate(quality: Quality, threshold: float) -> List[str]:
    """Return the reasons a skill may not be published (empty when it can)."""
    reasons: List[str] = []
    if quality.lint and quality.lint.errors:
        reasons.append("%d lint error(s)" % len(quality.lint.errors))
    if quality.scan and quality.scan.count("high"):
        reasons.append("%d high severity security finding(s)" % quality.scan.count("high"))
    if quality.tests and quality.tests.refused:
        reasons.append(quality.tests.refused)
    elif quality.tests and quality.tests.has_tests and quality.tests.rate < 1.0:
        reasons.append("tests failing (%d/%d)" % (quality.tests.passed, quality.tests.total))
    if quality.score < threshold:
        reasons.append("score %.2f is below %.2f" % (quality.score, threshold))
    return reasons


def pack(skill_dir: Any, out_dir: Any = ".") -> Path:
    """Create <name>-<version>.zip with a checksum manifest."""
    skill = load_skill(skill_dir)
    files = iter_skill_files(skill.path)
    manifest = {"name": skill.name, "version": skill.version or "0.0.0",
                "files": [{"path": f.as_posix(), "sha256": registry.sha256_file(skill.path / f)} for f in files]}
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    archive = out / ("%s-%s.zip" % (skill.name, skill.version or "0.0.0"))
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            zf.write(skill.path / f, "%s/%s" % (skill.name, f.as_posix()))
        zf.writestr("%s/MANIFEST.json" % skill.name, json.dumps(manifest, indent=2) + "\n")
    return archive


def publish_to_registry(skill_dir: Any, registry_root: Any, threshold: float = 0.8, force: bool = False,
                        dry_run: bool = False) -> Dict[str, Any]:
    """Copy a skill into a registry checkout (skills/<name>) and refresh its index."""
    skill = load_skill(skill_dir)
    quality = evaluate_skill(skill.path)
    reasons = check_gate(quality, threshold)
    if reasons and not force:
        raise PublishError("; ".join(reasons))
    root = Path(registry_root).expanduser()
    skills_dir = root / "skills"
    if not skills_dir.is_dir():
        raise PublishError("%s does not look like a registry checkout (no skills/ folder)" % root)
    dest = skills_dir / skill.name
    steps = ["copy %s -> %s" % (skill.path, dest), "rebuild %s" % (root / "registry" / "index.json")]
    if not dry_run:
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(skill.path, dest, ignore=shutil.ignore_patterns("__pycache__", ".git", "*.pyc"))
        index = registry.build_index([skills_dir], relative_to=root)
        registry.write_index(index, root / "registry" / "index.json")
    return {"name": skill.name, "quality": quality, "steps": steps, "dest": dest, "forced": bool(reasons)}


def pr_commands(name: str, registry_root: Any = ".") -> List[str]:
    """Git and GitHub CLI commands that open a pull request for a skill."""
    return [
        "git checkout -b add-skill-%s" % name,
        "git add skills/%s registry/index.json" % name,
        'git commit -m "Add %s skill"' % name,
        "git push -u origin add-skill-%s" % name,
        'gh pr create --title "Add %s skill" --body "New skill: %s. Lint, scan and tests pass."' % (name, name),
    ]


def run_pr(name: str, registry_root: Any) -> Tuple[bool, str]:
    """Run the commands from pr_commands inside the registry checkout. Needs git and gh."""
    root = str(Path(registry_root).expanduser())
    if not shutil.which("git") or not shutil.which("gh"):
        return False, "git and the GitHub CLI (gh) must be installed"
    for cmd in pr_commands(name):
        proc = subprocess.run(cmd, shell=True, cwd=root, capture_output=True, text=True)
        if proc.returncode != 0:
            return False, "%s\n%s" % (cmd, (proc.stderr or proc.stdout).strip())
    return True, "pull request created"
