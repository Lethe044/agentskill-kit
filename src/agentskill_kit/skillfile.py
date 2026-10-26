"""Reading and writing SKILL.md files.

A skill is a directory that contains a SKILL.md file. The file starts with a
small YAML frontmatter block (name, description and a few optional keys) and
continues with markdown instructions. To keep the package free of runtime
dependencies, this module ships a small YAML reader that covers the subset
used by skill files: scalars, inline and block lists, nested maps and
folded or literal block scalars.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

SKILL_FILENAME = "SKILL.md"
SKIP_DIRS = {
    ".git", ".hg", ".svn", "__pycache__", "node_modules", ".venv", "venv",
    "dist", "build", ".mypy_cache", ".pytest_cache", ".idea", ".vscode",
    ".tox", ".eggs",
}
SKIP_SUFFIXES = {".pyc", ".pyo"}
FRONTMATTER_ORDER = [
    "name", "description", "license", "compatibility", "metadata", "allowed-tools",
]


class SkillError(Exception):
    """Raised when a skill cannot be located or read."""


# ---------------------------------------------------------------------------
# Minimal YAML subset
# ---------------------------------------------------------------------------

_KEY_RE = re.compile(r"^([A-Za-z0-9_][A-Za-z0-9_.\-]*)\s*:(?:\s+(.*))?$")


def _strip_comment(value: str) -> str:
    """Remove a trailing ' # comment' that is not inside quotes."""
    quote = ""
    for i, ch in enumerate(value):
        if quote:
            if ch == quote:
                quote = ""
        elif ch in "\"'":
            quote = ch
        elif ch == "#" and (i == 0 or value[i - 1] in " \t"):
            return value[:i].rstrip()
    return value


def _split_inline(text: str) -> List[str]:
    parts: List[str] = []
    buf: List[str] = []
    quote = ""
    for ch in text:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = ""
        elif ch in "\"'":
            quote = ch
            buf.append(ch)
        elif ch == ",":
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    tail = "".join(buf)
    if tail.strip() or parts:
        parts.append(tail)
    return parts


def parse_scalar(raw: str) -> Any:
    s = raw.strip()
    if s == "":
        return ""
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        inner = s[1:-1]
        if s[0] == '"':
            inner = (inner.replace('\\"', '"').replace("\\n", "\n")
                     .replace("\\t", "\t").replace("\\\\", "\\"))
        else:
            inner = inner.replace("''", "'")
        return inner
    if s.startswith("[") and s.endswith("]"):
        return [parse_scalar(p) for p in _split_inline(s[1:-1]) if p.strip()]
    low = s.lower()
    if low in ("true", "false"):
        return low == "true"
    if low in ("null", "~"):
        return None
    return s


def _fold_block(block: List[str], style: str) -> str:
    lines = [ln.rstrip("\r\n") for ln in block]
    indents = [len(ln) - len(ln.lstrip()) for ln in lines if ln.strip()]
    cut = min(indents) if indents else 0
    lines = [ln[cut:] if ln.strip() else "" for ln in lines]
    if style.startswith("|"):
        text = "\n".join(lines)
    else:
        out: List[str] = []
        para: List[str] = []
        for ln in lines:
            if ln == "":
                if para:
                    out.append(" ".join(para))
                    para = []
                out.append("")
            else:
                para.append(ln.strip())
        if para:
            out.append(" ".join(para))
        text = "\n".join(out)
    return text.strip()


def parse_yaml(lines: List[str], line_offset: int = 0) -> Tuple[Dict[str, Any], List[Tuple[int, str]]]:
    """Parse a YAML subset. Returns (mapping, [(line_number, message)])."""
    result: Dict[str, Any] = {}
    errors: List[Tuple[int, str]] = []
    i = 0
    n = len(lines)
    while i < n:
        raw = lines[i]
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        if raw[0] in " \t":
            errors.append((line_offset + i + 1, "unexpected indentation"))
            i += 1
            continue
        m = _KEY_RE.match(raw.rstrip())
        if not m:
            errors.append((line_offset + i + 1, "cannot parse line: %s" % stripped[:60]))
            i += 1
            continue
        key = m.group(1)
        value = _strip_comment(m.group(2) or "").strip()
        i += 1
        if value in (">", "|", ">-", "|-", ">+", "|+"):
            block: List[str] = []
            while i < n and (not lines[i].strip() or lines[i][0] in " \t"):
                block.append(lines[i])
                i += 1
            result[key] = _fold_block(block, value)
        elif value == "":
            block = []
            while i < n and (not lines[i].strip() or lines[i][0] in " \t" or lines[i].startswith("- ")):
                block.append(lines[i])
                i += 1
            first = next((b for b in block if b.strip()), "")
            if not first:
                result[key] = ""
            elif first.lstrip().startswith("- "):
                items = []
                for b in block:
                    bs = b.strip()
                    if bs.startswith("- "):
                        items.append(parse_scalar(_strip_comment(bs[2:])))
                result[key] = items
            else:
                cut = min(len(b) - len(b.lstrip()) for b in block if b.strip())
                nested, nested_errors = parse_yaml([b[cut:] for b in block], line_offset + i - len(block))
                errors.extend(nested_errors)
                result[key] = nested
        else:
            result[key] = parse_scalar(value)
    return result, errors


def _needs_quotes(s: str) -> bool:
    if s == "" or s != s.strip():
        return True
    if s[0] in "-?:,[]{}#&*!|>'\"%@`":
        return True
    if ": " in s or " #" in s or "\n" in s or s.endswith(":"):
        return True
    return s.lower() in ("true", "false", "null", "~", "yes", "no")


def _dump_scalar(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return "null"
    s = str(v)
    if _needs_quotes(s):
        return '"%s"' % s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return s


def dump_frontmatter(data: Dict[str, Any]) -> str:
    """Serialise a mapping to a frontmatter block (including the --- fences)."""
    keys = [k for k in FRONTMATTER_ORDER if k in data] + [k for k in data if k not in FRONTMATTER_ORDER]
    out = ["---"]
    for key in keys:
        val = data[key]
        if isinstance(val, dict):
            out.append("%s:" % key)
            for k2, v2 in val.items():
                if isinstance(v2, list):
                    out.append("  %s: [%s]" % (k2, ", ".join(_dump_scalar(x) for x in v2)))
                else:
                    out.append("  %s: %s" % (k2, _dump_scalar(v2)))
        elif isinstance(val, list):
            out.append("%s: [%s]" % (key, ", ".join(_dump_scalar(x) for x in val)))
        else:
            out.append("%s: %s" % (key, _dump_scalar(val)))
    out.append("---")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Skill model
# ---------------------------------------------------------------------------

@dataclass
class Skill:
    path: Path
    file: Path
    raw: str
    meta: Dict[str, Any] = field(default_factory=dict)
    body: str = ""
    body_line: int = 1
    has_frontmatter: bool = False
    fm_errors: List[Tuple[int, str]] = field(default_factory=list)
    fm_lines: List[str] = field(default_factory=list)

    @property
    def name(self) -> str:
        return str(self.meta.get("name") or self.path.name)

    @property
    def description(self) -> str:
        d = self.meta.get("description")
        return d if isinstance(d, str) else ""

    @property
    def metadata(self) -> Dict[str, Any]:
        m = self.meta.get("metadata")
        return m if isinstance(m, dict) else {}

    @property
    def version(self) -> str:
        v = self.metadata.get("version") or self.meta.get("version") or ""
        return str(v)

    @property
    def author(self) -> str:
        return str(self.metadata.get("author") or self.meta.get("author") or "")

    @property
    def license(self) -> str:
        return str(self.meta.get("license") or "")

    @property
    def tags(self) -> List[str]:
        raw = self.metadata.get("tags") or self.meta.get("tags") or []
        if isinstance(raw, str):
            raw = [p for p in re.split(r"[,\s]+", raw) if p]
        return [str(t).strip() for t in raw if str(t).strip()]


def split_frontmatter(text: str) -> Tuple[Optional[List[str]], str, int]:
    """Return (frontmatter_lines or None, body, body_start_line)."""
    if text.startswith("\ufeff"):
        text = text[1:]
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text, 1
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            body = "\n".join(lines[idx + 1:])
            return lines[1:idx], body, idx + 2
    return None, text, 1


def parse_skill_text(text: str, path: Optional[Path] = None) -> Skill:
    path = path or Path(".")
    fm_lines, body, body_line = split_frontmatter(text)
    skill = Skill(path=path, file=path / SKILL_FILENAME, raw=text, body=body, body_line=body_line)
    if fm_lines is None:
        return skill
    skill.has_frontmatter = True
    skill.fm_lines = fm_lines
    meta, errors = parse_yaml(fm_lines, line_offset=1)
    skill.meta = meta
    skill.fm_errors = errors
    return skill


def load_skill(target: Any) -> Skill:
    """Load a skill from a directory or a SKILL.md path."""
    p = Path(target).expanduser()
    if p.is_file():
        if p.name.lower() != SKILL_FILENAME.lower():
            raise SkillError("%s is not a SKILL.md file" % p)
        p = p.parent
    if not p.is_dir():
        raise SkillError("not found: %s" % target)
    skill_file = p / SKILL_FILENAME
    if not skill_file.exists():
        alt = next((c for c in p.iterdir() if c.name.lower() == "skill.md"), None) if p.exists() else None
        if alt is None:
            raise SkillError("no %s in %s" % (SKILL_FILENAME, p))
        skill_file = alt
    try:
        text = skill_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise SkillError("cannot read %s: %s" % (skill_file, exc))
    skill = parse_skill_text(text, p.resolve())
    skill.file = skill_file
    return skill


def discover_skills(root: Any, max_depth: int = 5) -> List[Path]:
    """Find every directory below root that holds a SKILL.md."""
    base = Path(root).expanduser()
    found: List[Path] = []
    if not base.exists():
        return found
    if base.is_file():
        return [base.parent] if base.name.lower() == "skill.md" else []

    def walk(d: Path, depth: int) -> None:
        try:
            entries = sorted(d.iterdir(), key=lambda e: e.name)
        except OSError:
            return
        if any(e.is_file() and e.name.lower() == "skill.md" for e in entries):
            found.append(d)
            return
        if depth >= max_depth:
            return
        for e in entries:
            if e.is_dir() and e.name not in SKIP_DIRS and not e.name.startswith("."):
                walk(e, depth + 1)

    walk(base, 0)
    return found


def iter_skill_files(skill_dir: Any) -> List[Path]:
    """All files of a skill (relative paths), excluding caches."""
    base = Path(skill_dir)
    out: List[Path] = []
    for p in sorted(base.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(base)
        if any(part in SKIP_DIRS for part in rel.parts[:-1]) or p.suffix in SKIP_SUFFIXES:
            continue
        out.append(rel)
    return out


def slugify(text: str, max_len: int = 64) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    s = re.sub(r"-{2,}", "-", s)
    return s[:max_len].strip("-") or "new-skill"


def as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    return [p for p in re.split(r"[,\s]+", str(value)) if p]
