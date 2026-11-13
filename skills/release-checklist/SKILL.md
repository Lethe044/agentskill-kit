---
name: release-checklist
description: Walks through a software release step by step, from version bump and changelog to tagging, publishing and post-release checks. Use when the user is about to cut a release, asks what to verify before shipping, or wants a repeatable release process for a library or service.
license: MIT
metadata:
  version: 1.0.0
  author: Lethe044
  tags: [release, versioning, ci, process]
---

# Release checklist

A release is a sequence of small checks. Do them in order and stop at the first failure.

## When to use

- The user says "let's release" or asks what is left before shipping.
- A project has no written release process.
- A release went wrong and the user wants a safer routine.

## Before you start

Ask or find out: what is being released (library, service, app), where it is published (PyPI, npm, a registry, a store,
a server), and whether versions follow semantic versioning.

## Checklist

1. **Branch is clean.** Releasing from the default branch, no uncommitted changes, up to date with the remote.
2. **CI is green** on the commit to be released. Do not release on a red or unknown build.
3. **Decide the version.** Breaking change: major. New feature: minor. Fix only: patch. For `0.x` projects, say what
   the project treats as breaking.
4. **Update the version** in every place it lives (package metadata, a `__version__` constant, docs, lock files).
   Search the repository for the old number.
5. **Update the changelog.** Group entries (added, changed, fixed, removed), mention breaking changes first, date the
   section.
6. **Run the full test suite** and a fresh install test: build the package, install it in a clean environment and run
   the main command or import.
7. **Commit and tag.** Use an annotated or signed tag that matches the version (`v1.4.0`). Push the commit, then the tag.
8. **Publish.** Prefer automated publishing from CI with trusted credentials over publishing from a laptop.
9. **Create the release notes** from the changelog section.
10. **Verify after release.** Install the published version, run it, check that the docs and the package page show the
    new version.
11. **Announce** only after step 10 passes.

## If something goes wrong

- Do not delete or re-use a published version number. Publish a new patch version.
- Yank or deprecate the bad version if the registry supports it, and say why in the notes.
- Write down what failed and add a check to this list.

## Errors

If the publish target or version rules are unknown, ask before running any command that pushes tags or uploads files.
