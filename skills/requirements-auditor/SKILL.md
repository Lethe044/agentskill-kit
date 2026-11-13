---
name: requirements-auditor
description: Audits a Python requirements.txt for unpinned packages, open version ranges, duplicate entries, installs from URLs or VCS and extra package indexes that invite dependency confusion. Use when the user asks to review dependencies, make builds reproducible or check a requirements file before release.
license: MIT
metadata:
  version: 1.0.0
  author: Lethe044
  tags: [python, dependencies, pip, supply-chain]
---

# Requirements auditor

Checks the shape of a `requirements.txt`. It does not look up vulnerabilities, so pair it with a
vulnerability scanner when the user needs one.

## When to use

- The user asks whether dependencies are pinned or builds are reproducible.
- A requirements file grew over time and may contain duplicates.
- A project installs from a private index and the user wants to know the risks.

## How to run

```bash
python scripts/audit_requirements.py requirements.txt
```

## Rules

| Rule | Level | Meaning |
| --- | --- | --- |
| `RQ001` | warning | package has no version specifier |
| `RQ002` | info | only a lower bound (`>=`) or a wildcard, the upper bound is open |
| `RQ003` | warning | package is listed twice (names are compared after normalizing `-`, `_` and `.`) |
| `RQ004` | warning | installed from a URL or VCS without a pinned commit or tag |
| `RQ005` | warning | `--extra-index-url` lets a public package replace a private one with the same name |
| `RQ006` | warning | `--trusted-host` disables TLS verification for a host |

Lines that start with `-r` or `-c`, comments, blank lines, extras (`pkg[extra]`) and environment markers
(`; python_version < "3.12"`) are handled.

## Output

JSON with `requirements` (count) and `findings`, each `{"line", "rule", "severity", "name", "message"}`.
The exit code is 1 when there is at least one warning.

## After running

Suggest `pip-compile` or `uv pip compile` to produce a fully pinned lock file with hashes, keep the loose file as
the input, and use `--index-url` with a single trusted index when possible.

## Errors

A missing file exits with code 2.
