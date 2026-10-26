---
name: python-code-smells
description: Finds common Python code smells with the ast module, such as bare except clauses, mutable default arguments, missing docstrings, very long functions and long argument lists. Use when the user asks for a quick review of Python code, a cleanup pass or a pre-commit style check.
license: MIT
metadata:
  version: 1.0.0
  author: Lethe044
  tags: [python, code-review, quality, static-analysis]
---

# Python code smells

A fast, dependency-free first pass over Python files. It does not replace a linter, it gives an
agent concrete line numbers to start a review from.

## When to use

- The user asks to review, clean up or "look over" Python code.
- Before a commit or pull request, to catch the obvious problems.
- When a project has no linter configured yet.

## How to run

```bash
python scripts/smells.py src/
python scripts/smells.py app.py utils.py --max-lines 40
```

Directories are searched recursively for `.py` files. Hidden folders and `__pycache__` are skipped.

## Rules

| Rule | Meaning |
| --- | --- |
| `bare-except` | `except:` without an exception type hides real errors |
| `mutable-default` | a list, dict or set used as a default argument value is shared between calls |
| `missing-docstring` | a public function or class (no leading underscore) has no docstring |
| `long-function` | a function is longer than `--max-lines` (default 50) |
| `too-many-args` | a function takes more than `--max-args` parameters (default 6) |
| `syntax-error` | the file could not be parsed |

## Output

JSON with `files` (number of files checked) and `findings`, a list of
`{"file", "line", "rule", "message"}`. The exit code is 1 when there are findings and 0 otherwise.

## After running

Group the findings by rule, fix the bugs first (`bare-except`, `mutable-default`), then the readability
items. Do not add docstrings that only repeat the function name.

## Errors

A path that does not exist exits with code 2.
