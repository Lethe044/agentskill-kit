---
name: dockerfile-linter
description: Checks a Dockerfile for common problems such as unpinned base images, running as root, ADD instead of COPY, secrets in ENV or ARG and apt-get without cleanup. Use when the user asks to review, harden or slim down a Dockerfile.
license: MIT
metadata:
  version: 1.0.0
  author: Lethe044
  tags: [docker, devops, security, linting]
---

# Dockerfile linter

A small rule set that catches the problems seen most often in real Dockerfiles, with line numbers.

## When to use

- The user asks for a review of a Dockerfile, or says an image is too big or insecure.
- Before a pull request that adds or changes a Dockerfile.
- When hardening a container that runs in production.

## How to run

```bash
python scripts/lint_dockerfile.py Dockerfile
```

## Rules

| Rule | Meaning |
| --- | --- |
| `DF001` | base image uses `latest` or has no tag, so builds are not reproducible |
| `DF002` | no `USER` instruction, the container runs as root |
| `DF003` | `ADD` used where `COPY` is enough (ADD is only needed for archives and URLs) |
| `DF004` | `apt-get install` without `--no-install-recommends` |
| `DF005` | `apt-get update` without removing `/var/lib/apt/lists` in the same layer |
| `DF006` | a secret-looking name (password, token, secret, api key) is set with `ENV` or `ARG` |
| `DF007` | `sudo` is used inside the image |
| `DF008` | no `HEALTHCHECK` (informational) |

## Output

JSON with `instructions` (count) and `findings`, a list of `{"line", "rule", "severity", "message"}`.
Severity is `warning` or `info`. The exit code is 1 when there is at least one warning.

## After running

Fix `DF006` first, a secret baked into an image layer is exposed to anyone who can pull the image. Then `DF002`
and `DF001`. Suggest multi-stage builds when the image installs compilers.

## Errors

A missing file exits with code 2.
