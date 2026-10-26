"""Create a new skill from a template."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from .skillfile import dump_frontmatter, slugify

SCRIPT = '''#!/usr/bin/env python3
"""%(summary)s"""
import argparse
import json
import sys


def run(text):
    """Return a result for the given text."""
    words = text.split()
    return {"words": len(words), "characters": len(text)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", nargs="?", help="input file (reads stdin when omitted)")
    args = parser.parse_args(argv)
    if args.file:
        try:
            with open(args.file, encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            print("file not found: %%s" %% args.file, file=sys.stderr)
            return 2
    else:
        text = sys.stdin.read()
    print(json.dumps(run(text)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''

CASES = '''{
  "entry": "scripts/main.py",
  "cases": [
    {"name": "counts words", "kind": "happy", "stdin": "one two three",
     "stdout_json": {"words": 3, "characters": 13}},
    {"name": "empty input", "kind": "edge", "stdin": "",
     "stdout_json": {"words": 0, "characters": 0}},
    {"name": "missing file", "kind": "error", "args": ["missing.txt"],
     "expect_exit": 2, "stderr_contains": "file not found"}
  ]
}
'''


def create_skill(name: str, parent: Path, description: str = "", with_script: bool = False,
                 author: str = "", tags: Optional[List[str]] = None, force: bool = False) -> Path:
    slug = slugify(name)
    dest = Path(parent) / slug
    if dest.exists() and any(dest.iterdir()) and not force:
        raise FileExistsError(str(dest))
    dest.mkdir(parents=True, exist_ok=True)
    desc = description.strip() or ("Describe what this skill does in one sentence. Use when the user asks "
                                   "for the task this skill covers.")
    meta = {"version": "0.1.0"}
    if author:
        meta["author"] = author
    meta["tags"] = tags or ["general"]
    fm = dump_frontmatter({"name": slug, "description": desc, "license": "MIT", "metadata": meta})
    title = slug.replace("-", " ").capitalize()
    lines = [fm, "# %s\n" % title,
             "## When to use\n",
             "- Replace this line with the situations where an agent should pick this skill.\n",
             "## Steps\n",
             "1. Replace this step with the first thing the agent should do.",
             "2. Add the next step. Keep every step concrete and checkable.\n"]
    if with_script:
        lines += ["## Script\n", "```bash", "python scripts/main.py path/to/input.txt", "```\n",
                  "The script prints JSON with the word and character count. Replace it with your own logic.\n"]
    lines += ["## Examples\n", "Input: describe a typical request.\n", "Output: describe the expected result.\n",
              "## Errors\n", "- Say what the agent should do when the input is missing or invalid.\n"]
    (dest / "SKILL.md").write_text("\n".join(lines), encoding="utf-8")
    if with_script:
        (dest / "scripts").mkdir(exist_ok=True)
        (dest / "scripts" / "main.py").write_text(SCRIPT % {"summary": desc.split(".")[0] + "."}, encoding="utf-8")
        (dest / "tests").mkdir(exist_ok=True)
        (dest / "tests" / "cases.json").write_text(CASES, encoding="utf-8")
    return dest
