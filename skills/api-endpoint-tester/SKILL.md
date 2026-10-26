---
name: api-endpoint-tester
description: Runs a list of HTTP checks against a base URL from a JSON file and reports status codes, response time and body assertions. Use when the user asks whether an API is up, wants a smoke test after a deploy, or needs to verify that endpoints return what the docs promise.
license: MIT
metadata:
  version: 1.0.0
  author: Lethe044
  tags: [api, http, testing, smoke-test]
---

# API endpoint tester

A tiny smoke test runner with no dependencies. It sends real HTTP requests, so only point it at services
the user owns or has permission to test.

## When to use

- After a deploy, to confirm the main endpoints respond.
- When the user suspects an endpoint changed shape or status code.
- To turn a list of curl commands into a repeatable check.

## How to run

```bash
python scripts/check_api.py checks.json --base-url https://staging.example.com
```

The checks file is a JSON list:

```json
[
  {"name": "health", "method": "GET", "path": "/health", "expect_status": 200, "expect_body_contains": "ok"},
  {"name": "create", "method": "POST", "path": "/items", "json": {"name": "demo"}, "expect_status": 201}
]
```

Optional fields: `headers` (object), `json` (request body), `expect_status` (default 200),
`expect_body_contains` (string) and `timeout` (seconds, default 10).

## Output

JSON with `base_url`, `passed`, `failed` and `results`. Each result has `name`, `ok`, `status`,
`elapsed_ms` and, when it failed, a `reason`. The exit code is 1 when any check fails.

## After running

Report failures first with the reason and status code. Mention slow endpoints (over one second). Do not retry
failing POST requests automatically, they may create duplicates.

## Errors

A missing checks file exits with code 2. Invalid JSON or a malformed check exits with code 3.
Connection errors are reported as failed checks, not crashes.
