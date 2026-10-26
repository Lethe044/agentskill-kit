"""Built-in offline model used by ``--provider mock``.

It always answers with the same small, working skill. That makes the full
forge loop (draft, lint, scan, test, score, write) demonstrable without
network access, and keeps the test suite deterministic.
"""

from __future__ import annotations

from typing import Dict, List

_SKILL_MD = """---
name: text-stats
description: Computes word, sentence and line counts, average word length and the most frequent words of a text. Use when the user asks for statistics, a quick readability overview or word frequency of plain text or a file.
license: MIT
metadata:
  version: 0.1.0
  tags: [text, analysis, statistics]
---

# Text statistics

Summarizes a piece of text with a small Python script that has no dependencies.

## When to use

- The user pastes text or points to a file and wants counts or word frequency.
- The user wants a quick sense of length before editing or summarizing.

## How to run

```bash
python scripts/text_stats.py --top 5 notes.txt
cat notes.txt | python scripts/text_stats.py
```

The script reads the file given as the last argument, or standard input when no file is given.

## Output

A JSON object with `words`, `sentences`, `lines`, `avg_word_length` and `top_words`
(a list of `[word, count]` pairs). Words shorter than three letters are ignored in `top_words`.

## Example

Input: `The cat sat. The cat ran.`

Output: `{"words": 6, "sentences": 2, "lines": 1, "avg_word_length": 3.0, "top_words": [["the", 2], ["cat", 2], ["sat", 1], ["ran", 1]]}`

## Errors

A missing file exits with code 2 and a message on stderr. Empty input returns zero counts.
"""

_SCRIPT = '''#!/usr/bin/env python3
"""Print word, sentence and line statistics for text."""
import argparse
import json
import re
import sys
from collections import Counter


def analyze(text, top=5):
    words = re.findall(r"[A-Za-z0-9']+", text)
    sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    lines = [ln for ln in text.splitlines() if ln.strip()]
    counts = Counter(w.lower() for w in words if len(w) >= 3)
    avg = round(sum(len(w) for w in words) / len(words), 2) if words else 0.0
    return {
        "words": len(words),
        "sentences": len(sentences),
        "lines": len(lines),
        "avg_word_length": avg,
        "top_words": [[w, c] for w, c in counts.most_common(top)],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", nargs="?", help="text file (reads stdin when omitted)")
    parser.add_argument("--top", type=int, default=5, help="number of frequent words to list")
    args = parser.parse_args(argv)
    if args.file:
        try:
            with open(args.file, encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            print("file not found: %s" % args.file, file=sys.stderr)
            return 2
    else:
        text = sys.stdin.read()
    print(json.dumps(analyze(text, args.top)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''

_CASES = """{
  "entry": "scripts/text_stats.py",
  "cases": [
    {"name": "counts words and sentences", "kind": "happy",
     "stdin": "The cat sat. The cat ran.",
     "stdout_json": {"words": 6, "sentences": 2, "top_words": [["the", 2], ["cat", 2], ["sat", 1], ["ran", 1]]}},
    {"name": "empty input", "kind": "edge", "stdin": "",
     "stdout_json": {"words": 0, "sentences": 0, "lines": 0}},
    {"name": "missing file", "kind": "error", "args": ["nope.txt"],
     "expect_exit": 2, "stderr_contains": "file not found"}
  ]
}
"""


def draft_files() -> Dict[str, str]:
    return {"SKILL.md": _SKILL_MD, "scripts/text_stats.py": _SCRIPT, "tests/cases.json": _CASES}


def mock_reply(messages: List[Dict[str, str]]) -> str:
    parts = []
    for path, content in draft_files().items():
        parts.append("=== FILE: %s ===\n%s\n=== END FILE ===" % (path, content.rstrip("\n")))
    return "\n\n".join(parts)
