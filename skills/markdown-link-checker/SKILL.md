---
name: markdown-link-checker
description: Checks relative links, image paths and heading anchors in Markdown files without using the network, and lists every broken one with its line number. Use when the user asks to verify README or docs links, after moving or renaming files, or before publishing documentation.
license: MIT
metadata:
  version: 1.0.0
  author: Lethe044
  tags: [markdown, documentation, links, quality]
---

# Markdown link checker

Finds links that point nowhere inside a repository. External `http` and `https` links are skipped on purpose,
so the check is fast, repeatable and works offline.

## When to use

- Files or folders were renamed or moved and docs may now point to the old paths.
- A README has a table of contents with `#anchors`.
- Before a release, to make sure the docs have no dead internal links.

## How to run

```bash
python scripts/check_links.py README.md docs/
```

Directories are searched recursively for `.md` files. Hidden folders and `node_modules` are skipped.

## What is checked

- `[text](path/to/file.md)` and image links: the target must exist, relative to the file that contains the link.
- `[text](#section)`: the heading must exist in the same file.
- `[text](other.md#section)`: the file must exist and contain the heading.
- Heading anchors use the GitHub style: lowercase, punctuation removed, spaces become hyphens, repeated headings
  get `-1`, `-2` and so on.
- Fenced code blocks and inline code are ignored.

## Output

JSON with `files`, `links_checked` and `broken`, a list of `{"file", "line", "target", "reason"}`.
Reasons are `file not found` and `anchor not found`. The exit code is 1 when anything is broken.

## After running

Group the broken links by file, fix the target when the file moved, and remove the link when the content is gone.
For anchors, check whether the heading was reworded.

## Errors

A path that does not exist exits with code 2.
