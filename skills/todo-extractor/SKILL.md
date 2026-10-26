---
name: todo-extractor
description: Finds TODO, FIXME, HACK and XXX comments across a source tree and groups them by tag and file. Use when the user asks for a list of open tasks in the code, wants to plan cleanup work, or needs an inventory of technical debt.
license: MIT
metadata:
  version: 1.0.0
  author: Lethe044
  tags: [todo, technical-debt, code-search, planning]
---

# TODO extractor

Turns scattered comments into a planning list.

## When to use

- The user asks "what is left to do in this repo?".
- Planning a cleanup sprint or a release, where known shortcuts must be reviewed.
- Before archiving or handing over a project.

## How to run

```bash
python scripts/find_todos.py src/
python scripts/find_todos.py . --tags TODO,FIXME
```

Hidden folders, `node_modules`, `venv`, `dist`, `build` and binary files are skipped.

## Output

JSON with `total`, `by_tag` (counts) and `items`, a list of `{"file", "line", "tag", "text"}`
sorted by file and line. The exit code is always 0 when the path exists.

## After running

1. Lead with the counts per tag. `FIXME` and `HACK` usually matter more than `TODO`.
2. Group items by file or folder and point out hot spots.
3. Propose an order of work, and mark items that look stale (they mention past dates or removed code).

## Errors

A path that does not exist exits with code 2.
