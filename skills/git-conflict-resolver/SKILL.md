---
name: git-conflict-resolver
description: Resolves git merge and rebase conflicts by reading both sides, keeping the intent of each change and verifying the result with tests. Use when a merge, rebase or cherry-pick stops with conflict markers, or when the user asks how to fix conflicts safely.
license: MIT
metadata:
  version: 1.0.0
  author: Lethe044
  tags: [git, merge, rebase, conflicts]
---

# Git conflict resolver

A conflict means two people changed the same lines. The goal is to keep what both wanted, not to make the
markers disappear.

## When to use

- `git merge`, `git rebase` or `git cherry-pick` stops with "CONFLICT".
- A file contains `<<<<<<<`, `=======` and `>>>>>>>` markers.
- The user is unsure whether to keep "ours" or "theirs".

## Steps

1. **See the scope.** Run `git status` and list the files marked as both modified. Note whether this is a merge or a
   rebase, because "ours" and "theirs" swap meaning during a rebase.
2. **Understand both changes.** For each file, run `git log --merge -p -- <file>` or compare the two branches, and write
   one sentence for what each side was trying to do.
3. **Resolve by intent.** Combine the changes when both are needed. Pick one side only when the other is obsolete,
   and say why. Never delete a side silently.
4. **Handle special files.**
   - Lock files and generated files: do not edit by hand. Take one side, then regenerate with the package manager.
   - Renames and deletes: check `git status` for "deleted by us" or "deleted by them" and decide on purpose.
   - Whitespace-only conflicts: keep the project's formatter output.
5. **Remove every marker.** Run `git grep -n -E '^(<<<<<<<|=======|>>>>>>>)'` and expect no output.
6. **Verify.** Run the build and the tests. A conflict that compiles can still be wrong.
7. **Finish.** `git add <files>`, then `git merge --continue` or `git rebase --continue`. If it went badly,
   `git merge --abort` or `git rebase --abort` returns to the starting point.

## Rules

- Do not use `git checkout --theirs .` or `--ours .` on the whole tree.
- Do not force push after a rebase on a shared branch without telling the user.
- Show the user the resolved hunks for any file where behavior changed.

## Example

Both branches edited a function. One added a timeout parameter, the other renamed a variable. The resolution keeps
the rename and the new parameter, and the test that covers the function is run before `git add`.

## Errors

If the intent of one side is unclear, ask the user or the author of the change instead of guessing.
