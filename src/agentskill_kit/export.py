"""Install a skill into the format used by different coding agents.

Skill directories (Claude Code, Hermes) are copied as they are. Agents that
use rule files or a single instructions file (Cursor, Windsurf, Copilot,
Codex, Gemini CLI) get the skill converted: frontmatter is rewritten and the
instructions are inlined. Managed blocks are marked so re-exporting updates
them instead of duplicating them.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from .skillfile import Skill, SkillError, _dump_scalar, iter_skill_files, load_skill

BUNDLE_DIR = ".agent-skills"


@dataclass
class Target:
    name: str
    label: str
    kind: str  # dir | file | block
    project: str
    global_: str = ""


TARGETS: Dict[str, Target] = {
    "claude": Target("claude", "Claude Code skills", "dir", ".claude/skills", "~/.claude/skills"),
    "hermes": Target("hermes", "Hermes Agent skills", "dir", ".hermes/skills", "~/.hermes/skills"),
    "cursor": Target("cursor", "Cursor project rules", "file", ".cursor/rules"),
    "windsurf": Target("windsurf", "Windsurf rules", "file", ".windsurf/rules"),
    "copilot": Target("copilot", "GitHub Copilot instructions", "file", ".github/instructions"),
    "codex": Target("codex", "AGENTS.md (Codex and others)", "block", "AGENTS.md", "~/.codex/AGENTS.md"),
    "gemini": Target("gemini", "Gemini CLI GEMINI.md", "block", "GEMINI.md", "~/.gemini/GEMINI.md"),
}


class ExportError(Exception):
    pass


def _begin(name: str) -> str:
    return "<!-- agentskill-kit:begin %s -->" % name


def _end(name: str) -> str:
    return "<!-- agentskill-kit:end %s -->" % name


def _extra_files(skill: Skill) -> List[Path]:
    return [p for p in iter_skill_files(skill.path) if p.as_posix() != "SKILL.md"]


def _footer(skill: Skill, extras: bool) -> str:
    if not extras:
        return ""
    return "\n\nBundled files for this skill are in `%s/%s/`." % (BUNDLE_DIR, skill.name)


def _copy_tree(skill: Skill, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(skill.path, dest, ignore=shutil.ignore_patterns("__pycache__", ".git", "*.pyc"))


def render_rule(skill: Skill, target: str, extras: bool) -> str:
    body = skill.body.strip() + _footer(skill, extras)
    desc = _dump_scalar(skill.description)
    if target == "cursor":
        return "---\ndescription: %s\nglobs:\nalwaysApply: false\n---\n\n%s\n" % (desc, body)
    if target == "windsurf":
        return "---\ntrigger: model_decision\ndescription: %s\n---\n\n%s\n" % (desc, body)
    if target == "copilot":
        return '---\napplyTo: "**"\n---\n\n# %s\n\n%s\n\n%s\n' % (skill.name, skill.description, body)
    raise ExportError("no rule renderer for %s" % target)


def render_block(skill: Skill, extras: bool) -> str:
    body = skill.body.strip() + _footer(skill, extras)
    return "%s\n## Skill: %s\n\n%s\n\n%s\n%s\n" % (_begin(skill.name), skill.name, skill.description, body,
                                                    _end(skill.name))


def _upsert_block(path: Path, skill: Skill, block: str) -> str:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    pattern = re.compile(re.escape(_begin(skill.name)) + r".*?" + re.escape(_end(skill.name)) + r"\n?", re.S)
    if pattern.search(text):
        new = pattern.sub(lambda _m: block, text)
        action = "updated"
    else:
        sep = "" if not text or text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n")
        new = text + sep + block
        action = "added"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new, encoding="utf-8")
    return action


def destination(target: str, base: Optional[Path] = None, global_: bool = False) -> Path:
    if target not in TARGETS:
        raise ExportError("unknown target %r. Choose from: %s" % (target, ", ".join(TARGETS)))
    t = TARGETS[target]
    if global_:
        if not t.global_:
            raise ExportError("%s has no global location; export it into a project instead" % t.label)
        return Path(t.global_).expanduser()
    return (base or Path.cwd()) / t.project


def export_skill(skill_path: Path, target: str, base: Optional[Path] = None, global_: bool = False,
                 dry_run: bool = False) -> List[str]:
    """Export one skill. Returns a list of human readable actions."""
    try:
        skill = load_skill(skill_path)
    except SkillError as exc:
        raise ExportError(str(exc))
    t = TARGETS.get(target)
    if t is None:
        raise ExportError("unknown target %r. Choose from: %s" % (target, ", ".join(TARGETS)))
    dest = destination(target, base, global_)
    extras = bool(_extra_files(skill))
    actions: List[str] = []

    if t.kind == "dir":
        out = dest / skill.name
        actions.append("copy %s -> %s" % (skill.path, out))
        if not dry_run:
            dest.mkdir(parents=True, exist_ok=True)
            _copy_tree(skill, out)
    elif t.kind == "file":
        ext = ".mdc" if target == "cursor" else (".instructions.md" if target == "copilot" else ".md")
        out = dest / (skill.name + ext)
        actions.append("write %s" % out)
        if extras:
            bundle = (base or Path.cwd()) / BUNDLE_DIR / skill.name
            actions.append("copy bundled files -> %s" % bundle)
        if not dry_run:
            dest.mkdir(parents=True, exist_ok=True)
            out.write_text(render_rule(skill, target, extras), encoding="utf-8")
            if extras:
                _copy_tree(skill, (base or Path.cwd()) / BUNDLE_DIR / skill.name)
    else:
        actions.append("%s block for %s in %s" % ("write", skill.name, dest))
        if extras:
            bundle = (base or Path.cwd()) / BUNDLE_DIR / skill.name
            actions.append("copy bundled files -> %s" % bundle)
        if not dry_run:
            action = _upsert_block(dest, skill, render_block(skill, extras))
            actions[0] = "%s block for %s in %s" % (action, skill.name, dest)
            if extras:
                _copy_tree(skill, (base or Path.cwd()) / BUNDLE_DIR / skill.name)
    return actions


def remove_skill(name: str, target: str, base: Optional[Path] = None, global_: bool = False) -> List[str]:
    t = TARGETS.get(target)
    if t is None:
        raise ExportError("unknown target %r" % target)
    dest = destination(target, base, global_)
    done: List[str] = []
    if t.kind == "dir":
        out = dest / name
        if out.exists():
            shutil.rmtree(out)
            done.append("removed %s" % out)
    elif t.kind == "file":
        for ext in (".mdc", ".instructions.md", ".md"):
            out = dest / (name + ext)
            if out.exists():
                out.unlink()
                done.append("removed %s" % out)
    else:
        if dest.exists():
            text = dest.read_text(encoding="utf-8")
            pat = re.compile(r"\n?" + re.escape(_begin(name)) + r".*?" + re.escape(_end(name)) + r"\n?", re.S)
            if pat.search(text):
                dest.write_text(pat.sub("\n", text).lstrip("\n"), encoding="utf-8")
                done.append("removed block %s from %s" % (name, dest))
    bundle = (base or Path.cwd()) / BUNDLE_DIR / name
    if bundle.exists():
        shutil.rmtree(bundle)
        done.append("removed %s" % bundle)
    return done
