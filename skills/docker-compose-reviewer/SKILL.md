---
name: docker-compose-reviewer
description: Reviews a docker-compose.yml for risky or fragile settings such as unpinned images, privileged containers, secrets in environment values, a mounted Docker socket and host networking. Use when the user asks to check, harden or clean up a compose file before deploying a stack.
license: MIT
metadata:
  version: 1.0.0
  author: Lethe044
  tags: [docker, docker-compose, devops, security]
---

# Docker Compose reviewer

A line based review of a compose file. It needs no YAML library and no Docker installation.

## When to use

- The user asks for a review of `docker-compose.yml` or `compose.yaml`.
- A stack is about to move from a laptop to a server.
- A compose file contains passwords or tokens and the user is unsure whether that is a problem.

## How to run

```bash
python scripts/review_compose.py docker-compose.yml
```

## Rules

| Rule | Level | Meaning |
| --- | --- | --- |
| `DC001` | warning | image has no tag or uses `latest` |
| `DC002` | warning | `privileged: true` gives the container almost full host access |
| `DC003` | warning | a secret-looking variable (password, token, secret, API key) has a literal value |
| `DC004` | info | a port is published on all interfaces |
| `DC005` | warning | the Docker socket is mounted, which gives the container control over the host |
| `DC006` | info | no `restart` policy |
| `DC007` | info | no `healthcheck` |
| `DC008` | warning | `network_mode: host` removes network isolation |

## Output

JSON with `services` (count) and `findings`, a list of `{"service", "line", "rule", "severity", "message"}`.
The exit code is 1 when there is at least one warning.

## After running

1. Fix `DC003` first. Move secrets to an `.env` file that is not committed, or to Docker secrets, and reference them as `${NAME}`.
2. Pin images to a version. Use a digest (`image@sha256:...`) for production.
3. Bind local-only services to `127.0.0.1:PORT:PORT`.
4. Treat `DC002` and `DC005` as requiring a written reason, not a quick fix.

## Limits

The parser reads the common layout (services at two spaces, keys at four). Anchors, merge keys and
`extends` are not followed.

## Errors

A missing file exits with code 2.
