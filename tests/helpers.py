"""Shared test helpers. Importing this module makes `agentskill_kit` importable from src/."""
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

VALID_SKILL = """---
name: {name}
description: Summarizes example data for tests. Use when the user asks for the example summary of a thing.
license: MIT
metadata:
  version: 1.0.0
  tags: [test, example]
---

# {title}

## When to use

- A test needs a valid skill.

## Steps

1. Do the first thing.
2. Do the second thing.

## Example

Input: something. Output: something else.
"""


class TempDirTest(unittest.TestCase):
    """Gives every test a fresh directory and an isolated askit home."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="askit-test-"))
        self.home = self.tmp / "home"
        self.home.mkdir()
        self._old_home = os.environ.get("ASKIT_HOME")
        os.environ["ASKIT_HOME"] = str(self.home)
        self.addCleanup(self._restore)

    def _restore(self):
        if self._old_home is None:
            os.environ.pop("ASKIT_HOME", None)
        else:
            os.environ["ASKIT_HOME"] = self._old_home
        shutil.rmtree(self.tmp, ignore_errors=True)

    def make_skill(self, name="demo-skill", parent=None, text=None, files=None):
        parent = Path(parent) if parent else self.tmp / "skills"
        d = parent / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(text if text is not None else VALID_SKILL.format(name=name, title=name),
                                    encoding="utf-8")
        for rel, content in (files or {}).items():
            p = d / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
        return d
