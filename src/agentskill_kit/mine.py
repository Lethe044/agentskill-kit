"""Find repeated workflows in shell history and suggest skills.

Everything runs locally. Commands are normalised (paths, numbers, quoted
strings and hashes become placeholders) and secrets are masked before
anything is shown or written.
"""

from __future__ import annotations

import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from .scan import redact
from .skillfile import dump_frontmatter, slugify

TRIVIAL = {
    "cd", "ls", "ll", "la", "dir", "pwd", "clear", "cls", "exit", "logout", "history", "echo", "man", "help",
    "which", "where", "whoami", "date", "top", "htop", "vim", "vi", "nano", "code", "type", "cat", "less",
    "more", "head", "tail", "mkdir", "touch", "source", "export", "set", "alias", "sleep", "true", "false",
    "pushd", "popd", "tree", "open", "start", "tldr", "z", "j",
}

_PATHISH = re.compile(r"[\\/]")
_NUM = re.compile(r"^\d+(?:[.:_-]\d+)*$")
_HASH = re.compile(r"^[0-9a-f]{7,40}$")
_FILE = re.compile(r"^[\w.-]+\.(?:py|js|ts|tsx|json|ya?ml|md|txt|csv|log|toml|sh|ini|cfg|xml|html|sql|zip|tar|gz)$", re.I)
_URL = re.compile(r"^[a-z]+://", re.I)


@dataclass
class Candidate:
    kind: str  # sequence | command
    template: List[str]
    count: int
    examples: List[str]
    score: float = 0.0

    @property
    def tools(self) -> List[str]:
        seen: List[str] = []
        for line in self.template:
            tool = line.split()[0] if line.split() else ""
            if tool and tool not in seen:
                seen.append(tool)
        return seen

    @property
    def name(self) -> str:
        tools = self.tools
        if self.kind == "command" and self.template:
            toks = [t for t in self.template[0].split() if re.match(r"^[a-z][a-z0-9-]*$", t)][:2]
            return slugify("-".join(toks) or "command")
        if len(tools) == 1:
            subs: List[str] = []
            for line in self.template:
                parts = line.split()
                if len(parts) > 1 and re.match(r"^[a-z][a-z0-9-]*$", parts[1]) and parts[1] not in subs:
                    subs.append(parts[1])
            return slugify("-".join([tools[0]] + subs[:3]))
        return slugify("-".join(tools[:3]) + "-workflow")


# ---------------------------------------------------------------------------
# Reading history
# ---------------------------------------------------------------------------

def default_history_files() -> List[Path]:
    home = Path.home()
    cands = [home / ".bash_history", home / ".zsh_history", home / ".local/share/fish/fish_history"]
    appdata = os.environ.get("APPDATA")
    if appdata:
        cands.append(Path(appdata) / "Microsoft/Windows/PowerShell/PSReadLine/ConsoleHost_history.txt")
    cands.append(home / ".local/share/powershell/PSReadLine/ConsoleHost_history.txt")
    histfile = os.environ.get("HISTFILE")
    if histfile:
        cands.insert(0, Path(histfile).expanduser())
    out, seen = [], set()
    for c in cands:
        if c.is_file() and str(c) not in seen:
            out.append(c)
            seen.add(str(c))
    return out


def parse_history(text: str, hint: str = "") -> List[str]:
    """Parse bash, zsh, fish or PowerShell history text into a list of commands."""
    cmds: List[str] = []
    lines = text.splitlines()
    is_fish = hint == "fish" or any(ln.startswith("- cmd: ") for ln in lines[:20])
    if is_fish:
        for ln in lines:
            if ln.startswith("- cmd: "):
                cmds.append(ln[7:].strip())
        return cmds
    buf = ""
    for ln in lines:
        if re.match(r"^#\d{9,}$", ln):  # bash timestamps
            continue
        m = re.match(r"^: \d+:\d+;(.*)$", ln)  # zsh extended history
        if m:
            ln = m.group(1)
        if buf:
            ln = buf + "\n" + ln
            buf = ""
        if ln.endswith("\\") or ln.endswith("`"):
            buf = ln[:-1].rstrip()
            continue
        if ln.strip():
            cmds.append(ln.strip())
    if buf:
        cmds.append(buf.strip())
    return cmds


def read_history(paths: Optional[Iterable[Path]] = None) -> List[str]:
    files = list(paths) if paths else default_history_files()
    cmds: List[str] = []
    for p in files:
        try:
            text = Path(p).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        hint = "fish" if "fish" in str(p).lower() else ""
        cmds.extend(parse_history(text, hint))
    return cmds


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

def normalize(cmd: str) -> str:
    c = re.sub(r'"[^"]*"|\'[^\']*\'', "<str>", cmd.strip())
    c = redact(c)
    out: List[str] = []
    for i, tok in enumerate(c.split()):
        if tok == "<str>" or tok.startswith("<redacted"):
            out.append("<str>" if tok == "<str>" else tok)
        elif i == 0:
            out.append(tok)
        elif _URL.match(tok):
            out.append("<url>")
        elif tok.startswith("-"):
            out.append(tok)
        elif i == 1 and re.match(r"^[a-z][a-z0-9:-]*$", tok):
            out.append(tok)  # keep the subcommand (git commit, docker build)
        elif _PATHISH.search(tok) or tok in (".", "..", "~"):
            out.append("<path>")
        elif _FILE.match(tok):
            out.append("<file>")
        elif _HASH.match(tok) and re.search(r"\d", tok):
            out.append("<hash>")
        elif _NUM.match(tok):
            out.append("<n>")
        else:
            out.append(tok)
    return " ".join(out)


def _is_trivial(cmd: str) -> bool:
    toks = cmd.split()
    if not toks:
        return True
    base = Path(toks[0]).name.lower()
    return base in TRIVIAL or toks[0].startswith("#")


# ---------------------------------------------------------------------------
# Mining
# ---------------------------------------------------------------------------

def find_candidates(commands: List[str], min_count: int = 3, max_len: int = 4, limit: int = 15) -> List[Candidate]:
    pairs = [(c, normalize(c)) for c in commands if not _is_trivial(c)]
    norms = [n for _, n in pairs]
    originals = [redact(o) for o, _ in pairs]

    seq_counts: Counter = Counter()
    seq_positions: Dict[Tuple[str, ...], int] = {}
    for length in range(2, max_len + 1):
        for i in range(0, len(norms) - length + 1):
            window = tuple(norms[i:i + length])
            if len(set(window)) == 1:
                continue
            seq_counts[window] += 1
            seq_positions[window] = i
    seqs = {w: c for w, c in seq_counts.items() if c >= min_count}

    maximal: Dict[Tuple[str, ...], int] = {}
    for w, c in sorted(seqs.items(), key=lambda kv: -len(kv[0])):
        covered = any(len(o) > len(w) and oc >= c and _contains(o, w) for o, oc in maximal.items())
        if not covered:
            maximal[w] = c

    # A workflow repeated back to back shows up as several rotations of itself.
    # Keep one candidate per set of commands: the most frequent, then the longest.
    best_by_set: Dict[frozenset, Tuple[Tuple[str, ...], int]] = {}
    for w, c in maximal.items():
        key = frozenset(w)
        cur = best_by_set.get(key)
        if cur is None or (c, len(w)) > (cur[1], len(cur[0])):
            best_by_set[key] = (w, c)

    out: List[Candidate] = []
    for w, c in best_by_set.values():
        pos = seq_positions[w]
        out.append(Candidate("sequence", list(w), c, originals[pos:pos + len(w)],
                             score=c * (len(w) ** 1.5)))

    cmd_counts = Counter(norms)
    for n, c in cmd_counts.items():
        if c >= max(min_count * 2, 4) and len(n.split()) >= 3:
            if any(n in cand.template for cand in out):
                continue
            idx = max(i for i, x in enumerate(norms) if x == n)
            out.append(Candidate("command", [n], c, [originals[idx]], score=c * 1.2))
    out.sort(key=lambda cand: -cand.score)
    return out[:limit]


def _contains(big: Tuple[str, ...], small: Tuple[str, ...]) -> bool:
    n = len(small)
    return any(big[i:i + n] == small for i in range(len(big) - n + 1))


# ---------------------------------------------------------------------------
# Drafting
# ---------------------------------------------------------------------------

def placeholders(candidate: Candidate) -> List[str]:
    found: List[str] = []
    for line in candidate.template:
        for ph in re.findall(r"<(?:str|path|file|url|n|hash|redacted)>", line):
            if ph not in found:
                found.append(ph)
    return found


_PLACEHOLDER_HELP = {
    "<str>": "a quoted text value such as a message or name",
    "<path>": "a file or directory path",
    "<file>": "a file name",
    "<url>": "a URL",
    "<n>": "a number such as a version, port or count",
    "<hash>": "a commit hash or other identifier",
    "<redacted>": "a secret; read it from the environment, never inline it",
}


def draft_skill_files(candidate: Candidate, name: Optional[str] = None) -> Dict[str, str]:
    """Write a deterministic SKILL.md for a mined workflow (no model needed)."""
    name = slugify(name or candidate.name)
    tools = ", ".join(candidate.tools[:4])
    first = candidate.template[0]
    plain = [re.sub(r"<[^>]*>", "...", t) for t in candidate.template[:3]]
    steps = "; ".join(t if len(t) <= 50 else t[:47] + "..." for t in plain)
    desc = ("Runs a recurring %s workflow: %s. Use when the user asks to repeat this sequence "
            "of commands or to automate the same routine." % (tools, steps))
    if len(desc) > 600:
        desc = desc[:597] + "..."
    fm = dump_frontmatter({
        "name": name,
        "description": desc,
        "license": "MIT",
        "metadata": {"version": "0.1.0", "tags": [slugify(t) for t in candidate.tools[:4]] + ["workflow"],
                     "source": "askit mine"},
    })
    lines = [fm, "# %s\n" % name.replace("-", " ").capitalize(),
             "This workflow was found %d times in shell history. Review the steps and fill in the "
             "parameters before running them.\n" % candidate.count,
             "## When to use\n",
             "- The user wants to repeat the routine below on a different target.",
             "- The user describes the same goal in different words.\n",
             "## Steps\n"]
    for i, tmpl in enumerate(candidate.template, 1):
        lines.append("%d. Run:\n\n   ```bash\n   %s\n   ```" % (i, tmpl))
    phs = placeholders(candidate)
    if phs:
        lines.append("\n## Parameters\n")
        for ph in phs:
            lines.append("- `%s`: %s" % (ph, _PLACEHOLDER_HELP.get(ph, "a value that changes between runs")))
    lines.append("\n## Example from history\n")
    lines.append("```bash\n%s\n```" % "\n".join(candidate.examples))
    lines.append("\n## Notes\n")
    lines.append("- Stop and report the error if a step fails; do not continue with the remaining steps.")
    lines.append("- Ask the user to confirm any step that deletes or overwrites data.")
    return {"SKILL.md": "\n".join(lines) + "\n"}
