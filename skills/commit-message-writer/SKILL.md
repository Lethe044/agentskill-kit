---
name: commit-message-writer
description: Writes clear git commit messages in the conventional commits style from a diff or a description of the change. Use when the user asks for a commit message, wants to tidy up a message before pushing, or has staged changes and no wording yet.
license: MIT
metadata:
  version: 1.0.0
  author: Lethe044
  tags: [git, commit, conventional-commits, writing]
---

# Commit message writer

## When to use

- The user pastes a diff, or says "write a commit message for this".
- The user shows a vague message ("fix stuff", "wip") and wants it improved.
- A change touches several areas and should be split into more than one commit.

## Format

```
<type>(<optional scope>): <summary>

<optional body>

<optional footer>
```

Types: `feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`. Add `!` after the type or a
`BREAKING CHANGE:` footer for incompatible changes.

## Rules

1. The summary is at most 72 characters, in the imperative mood ("add", not "added"), with no trailing period.
2. Say what changed and why, not how. The diff already shows how.
3. Use the body for the reason, the trade-off or the side effects. Wrap lines at 72 characters.
4. Reference issues in the footer, for example `Closes #42`.
5. If the diff mixes unrelated changes, say so and propose one message per change.

## Steps

1. Read the diff and find the single main intent.
2. Pick the type and a scope that matches a folder or module name used in the repo.
3. Write the summary, then the body only if the reason is not obvious.
4. Return the message in a code block, and mention any suggested split.

## Example

Change: a retry loop was added around an HTTP call and the timeout was raised from 5 to 15 seconds.

```
fix(client): retry failed requests and raise timeout

The upstream API drops about 2% of connections under load. Retry up to
three times with backoff and use a 15 second timeout so slow responses
are not cut off.
```

## Errors

If there is no diff and no description, ask what changed instead of guessing.
