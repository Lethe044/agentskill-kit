---
name: changelog-generator
description: Turns git log output into a grouped markdown changelog using conventional commit prefixes such as feat, fix and docs. Use when the user prepares a release, asks for release notes, or wants a summary of what changed between two tags.
license: MIT
metadata:
  version: 1.0.0
  author: Lethe044
  tags: [git, changelog, release, documentation]
---

# Changelog generator

Groups commit subjects by type so release notes can be written in minutes.

## When to use

- The user is cutting a release and needs notes.
- The user asks what changed since the last tag.
- A pull request needs a summary of its commits.

## How to run

Pipe `git log` with the `%h|%s` format into the script:

```bash
git log v1.0.0..HEAD --pretty=format:"%h|%s" | python scripts/make_changelog.py --title "v1.1.0"
```

Without a title, the heading is `Changelog`.

## Output

Markdown on standard output. Sections appear in a fixed order: Breaking changes, Features, Fixes,
Performance, Documentation, Refactoring, Tests, Build and CI, Other. Empty sections are left out.
A `!` after the type (`feat!:`) or a `BREAKING CHANGE` marker puts the commit under Breaking changes.
Each line shows the scope in bold, the subject and the short hash.

## After running

Read the draft once, merge duplicate lines, and rewrite subjects that only make sense to the author.
Add a short summary paragraph on top for releases with user visible changes.

## Errors

Empty input prints a heading and the line `No commits found.`. Lines without a `|` separator are ignored.
