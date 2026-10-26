---
name: pr-description-writer
description: Drafts a pull request description with a summary, motivation, a change list, test notes and risks from a diff or commit list. Use when the user opens a pull request, asks for a PR description, or wants reviewers to understand a change quickly.
license: MIT
metadata:
  version: 1.0.0
  author: Lethe044
  tags: [git, pull-request, code-review, writing]
---

# Pull request description writer

## When to use

- The user is about to open a pull request and has a diff or a commit list.
- A pull request description is empty or says only "see commits".
- The change is large and reviewers need a reading order.

## Template

```markdown
## Summary
One or two sentences: what changes and why it matters.

## Motivation
The problem or ticket behind this change. Link the issue.

## Changes
- Grouped by area, one line each. Mention renamed or moved files once.

## How it was tested
- Commands run, cases covered, and what was not covered.

## Risks and rollout
- Migrations, config changes, performance effects, how to roll back.

## Review notes
- Where to start reading and what deserves the most attention.
```

## Rules

1. Lead with the user visible effect, not the file list.
2. Be honest about gaps. "Not tested on Windows" helps the reviewer more than silence.
3. Call out anything that needs action at deploy time (new environment variable, migration, feature flag).
4. Keep it under about 300 words unless the change is very large.
5. Do not invent test results. If the user did not say what was tested, ask or write "Not yet tested".

## Steps

1. Read the diff and the commit messages and find the main purpose.
2. Group the changes by area (API, UI, tests, build) instead of by file.
3. Fill the template and drop sections that have nothing to say.
4. Suggest a title in the form `<type>: <summary>`.

## Errors

If the diff is empty or only whitespace, say that there is nothing to describe.
