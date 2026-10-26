# GitHub Action and pre-commit

## GitHub Action

Check every skill in a repository on each push and pull request:

```yaml
name: Skills
on: [push, pull_request]
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: Lethe044/agentskill-kit@main
        with:
          path: skills
          strict: "true"
          scan-fail-on: medium
```

| Input | Default | Meaning |
| --- | --- | --- |
| `path` | `.` | folder with skills, or a single skill |
| `strict` | `false` | treat lint warnings as errors |
| `scan-fail-on` | `high` | lowest scan severity that fails the job (`high`, `medium`, `low`, `never`) |
| `run-tests` | `true` | run bundled skill tests |
| `python-version` | `3.12` | Python version |
| `version` | empty | install this PyPI version instead of the one bundled with the action |

Lint problems show up as annotations on the pull request.
Pin a tag or commit instead of `@main` once you rely on it.

## pre-commit

```yaml
repos:
  - repo: https://github.com/Lethe044/agentskill-kit
    rev: v0.1.0
    hooks:
      - id: askit-lint
      - id: askit-scan
```

## Plain CI

```yaml
- run: pip install agentskill-toolkit
- run: askit lint skills --strict
- run: askit scan skills --fail-on medium
- run: askit test skills
```
