---
name: json-diff
description: Compares two JSON files structurally and lists added, removed and changed values with their full paths. Use when the user asks what changed between two API responses, config files, fixtures or package manifests.
license: MIT
metadata:
  version: 1.0.0
  author: Lethe044
  tags: [json, diff, config, api]
---

# JSON diff

A structural comparison that ignores key order and formatting, which a plain text diff cannot do.

## When to use

- Two API responses should be the same but a test fails.
- A config or lock file changed and the user wants to know exactly which values moved.
- Comparing a fixture with the output of the code that is supposed to produce it.

## How to run

```bash
python scripts/json_diff.py old.json new.json
```

## Output

JSON with `identical` (boolean), `count` and `changes`. Every change has a `path`
(for example `users[1].email`), a `change` of `added`, `removed` or `changed`, and the `old` and `new` values
where they apply. The exit code is 1 when the files differ, 0 when they match.

## Reading the result

1. If `identical` is true, say so and stop.
2. Group the changes by the first path segment so the user sees which area moved.
3. Call out type changes (for example a number that became a string), they cause the subtle bugs.
4. Arrays are compared by position. If order is not meaningful, tell the user the diff may be noisy.

## Errors

A missing file exits with code 2. Invalid JSON exits with code 3 and names the file.
