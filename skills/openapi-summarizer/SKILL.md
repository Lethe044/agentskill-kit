---
name: openapi-summarizer
description: Summarizes an OpenAPI 3 or Swagger 2 JSON file into title, servers, endpoint counts per tag, unsecured operations, deprecated operations and a compact endpoint list. Use when the user shares an API spec and asks what it contains, wants an overview before integrating, or needs to find endpoints without authentication.
license: MIT
metadata:
  version: 1.0.0
  author: Lethe044
  tags: [openapi, swagger, api, documentation]
---

# OpenAPI summarizer

Turns a large spec into a short, structured overview that an agent can reason about.

## When to use

- The user pastes or points to an `openapi.json` or `swagger.json`.
- Before writing a client, to see how big the API is and how it is organized.
- During a review, to list the operations that have no security requirement.

## How to run

```bash
python scripts/summarize_openapi.py openapi.json
```

YAML specs must be converted to JSON first.

## Output

JSON with:

- `title`, `version` (the API version) and `spec` (the OpenAPI or Swagger version).
- `servers`: server URLs (for Swagger 2, built from `schemes`, `host` and `basePath`).
- `operations`, `deprecated`, `unsecured`: counts. An operation is secured when it has its own `security` list,
  or when it has none and the document defines a global `security` list. An empty list means no security.
- `by_tag`: operations per tag (`untagged` when missing).
- `schemas`: number of schema definitions.
- `endpoints`: a list of `{"method", "path", "summary", "tags", "secured", "deprecated"}`.

## Reading the result

1. Start with the title, version and the size (operations and schemas).
2. Name the biggest tags and what they seem to cover.
3. Point out `unsecured` operations and ask whether they are meant to be public.
4. Mention deprecated operations so they are not used in new code.

## Errors

A missing file exits with code 2. Invalid JSON, or a document that is not OpenAPI or Swagger, exits with code 3.
