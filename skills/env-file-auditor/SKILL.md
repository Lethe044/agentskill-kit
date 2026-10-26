---
name: env-file-auditor
description: Compares a .env file with its .env.example template and reports missing keys, undocumented extra keys, empty values and example files that contain real looking secrets. Use when the user asks why an app fails on startup with missing configuration, or wants to check environment files before committing.
license: MIT
metadata:
  version: 1.0.0
  author: Lethe044
  tags: [env, configuration, security, devops]
---

# Env file auditor

Keeps `.env` and `.env.example` in step and stops secrets from leaking into the example file.

## When to use

- An app crashes with "missing environment variable" and the user is not sure which one.
- Before committing, to make sure `.env.example` has no real credentials.
- After adding configuration, to check that the template documents every key.

## How to run

```bash
python scripts/audit_env.py .env .env.example
```

The first argument is the real file, the second is the template.

## Output

JSON with:

- `missing`: keys in the template that the real file does not define.
- `extra`: keys in the real file that the template does not document.
- `empty`: keys that are defined but have no value in the real file.
- `suspicious_example_keys`: keys in the template whose value looks like a real secret (long, mixed characters, on a name that contains KEY, SECRET, TOKEN or PASSWORD).

The exit code is 1 when anything is reported. Values are never printed, only key names.

## After running

Fix `suspicious_example_keys` first: replace the value with a placeholder such as `changeme`, and rotate the
secret if the file was ever committed. Then add `extra` keys to the template and ask the user for `missing` values.

## Errors

A missing file exits with code 2.
