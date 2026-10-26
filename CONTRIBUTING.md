# Contributing

Thanks for helping. There are three easy ways in: add a skill, fix a bug, or improve the docs.

## Set up

```bash
git clone https://github.com/Lethe044/agentskill-kit
cd agentskill-kit
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install -e ".[dev]"
python -m pytest -q
```

The package has no runtime dependencies, and new ones need a strong reason.
Code must run on Python 3.9 and newer, on Linux, macOS and Windows.

## Add a skill

Skills live in `skills/<name>/`. Start from the template:

```bash
askit init my-skill --script --tags text,example
```

A skill is accepted when:

1. `askit lint skills/my-skill --strict` passes. The name matches the folder, and the description says what the skill does and when to use it.
2. `askit scan skills/my-skill` finds nothing at medium severity or above.
3. If it has a script, it uses only the standard library and has `tests/cases.json` with a happy path, an edge case and an error case (or `tests/test_*.py`).
4. `askit score skills/my-skill` reports a score of 0.9 or higher.
5. Content is original or properly licensed. Do not copy other people's skills.

Then refresh the registry index and run the whole suite:

```bash
askit registry build skills
python -m pytest -q
```

Commit `registry/index.json` together with the skill. CI fails when the index is stale.

### Test case format

```json
{
  "entry": "scripts/tool.py",
  "cases": [
    {"name": "happy path", "kind": "happy", "args": ["input.txt"],
     "files": {"input.txt": "content"}, "stdout_json": {"count": 1}},
    {"name": "missing file", "kind": "error", "args": ["nope.txt"],
     "expect_exit": 2, "stderr_contains": "file not found"}
  ]
}
```

Each case runs in an empty temporary directory. `files` are created there before the script runs.
Supported checks: `expect_exit`, `stdout_contains`, `stdout_not_contains`, `stdout_regex`, `stdout_json` (subset match),
`stderr_contains`. Optional keys: `args`, `stdin`, `files`, `timeout`.

## Fix a bug or add a feature

1. Open an issue first for anything larger than a small fix, so we can agree on the approach.
2. Add a test that fails without your change. Tests use `unittest` style classes and run with pytest.
3. Keep functions small and error messages actionable (say what to do, not only what went wrong).
4. Update `docs/` and `CHANGELOG.md` when behaviour changes.

## Scanner rules

New rules in `src/agentskill_kit/scan.py` need a test for a match and a test for a near miss.
Prefer precise patterns. A rule that fires on normal prose teaches people to ignore the scanner.

## Style

- Plain, direct English in code, comments and docs. No marketing language.
- Use a normal hyphen, not an em dash.
- Standard library only in `src/`.

## Releases (maintainers)

1. Update `version` in `pyproject.toml` and `__version__` in `src/agentskill_kit/__init__.py`.
2. Move the unreleased notes in `CHANGELOG.md` under the new version.
3. Run `askit registry build skills` and the tests.
4. Tag and publish a GitHub release. The `Publish to PyPI` workflow uploads the package through trusted publishing.
