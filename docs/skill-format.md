# Skill format

A skill is a folder with a `SKILL.md` file. The file starts with a YAML block, then markdown instructions.

```markdown
---
name: log-analyzer
description: Summarizes application log files by severity and frequent errors. Use when the user shares a log and asks what went wrong.
license: MIT
metadata:
  version: 1.0.0
  author: your-name
  tags: [logs, debugging]
---

# Log analyzer

## When to use
...
```

## Frontmatter

| Field | Required | Rules |
| --- | --- | --- |
| `name` | yes | lowercase letters, digits and single hyphens, at most 64 characters, equal to the folder name |
| `description` | yes | at most 1024 characters, no XML or HTML tags, third person, says what it does and when to use it |
| `license` | no | for example `MIT` |
| `compatibility` | no | at most 500 characters, environment requirements |
| `metadata` | no | a mapping: `version`, `author`, `tags` and anything else you like |
| `allowed-tools` | no | tools the skill may use, if your agent supports it |

Top-level `version`, `author` and `tags` are accepted but lint suggests moving them under `metadata`.

## The description matters most

Agents read only the name and description of every skill and load the rest when a task matches.
A good description names concrete triggers:

- Weak: `Helps with logs.`
- Better: `Summarizes application log files by severity and frequent errors. Use when the user shares a log and asks what went wrong.`

## Optional folders

```
my-skill/
  SKILL.md
  scripts/       code the skill runs (Python scripts are testable with askit)
  references/    longer documents that SKILL.md links to
  assets/        templates and other static files
  tests/         cases.json and/or test_*.py
  evals/         evals.json for model behaviour checks
```

Keep SKILL.md under 500 lines. Put long reference material in `references/`.

## Lint rules

| Code | Level | Meaning |
| --- | --- | --- |
| E001 | error | skill folder or SKILL.md not found |
| E002 | error | no frontmatter block |
| E003 to E006 | error | missing, too long, badly formed or mismatched `name` |
| E007 to E009 | error | missing, too long, or tagged `description` |
| E010 to E012 | error | frontmatter does not parse, bad `compatibility` or `metadata` |
| W001, W002, W012 | warning | description too short, no "when to use", written in first person |
| W003 to W005 | warning | empty body, body over 500 lines, no headings |
| W006 | warning | the instructions mention a file that does not exist |
| W007 | warning | leftover template or placeholder text |
| W010, W011 | warning | tabs in frontmatter, reserved word in name |
| I001 to I003 | info | no license, legacy top-level key, unknown key |

Errors fail `askit lint`. Add `--strict` to fail on warnings too.

## Tests

`tests/cases.json` describes command line cases for a script:

```json
{
  "entry": "scripts/tool.py",
  "cases": [
    {"name": "counts", "kind": "happy", "stdin": "a b c", "stdout_json": {"words": 3}},
    {"name": "missing file", "kind": "error", "args": ["nope.txt"],
     "expect_exit": 2, "stderr_contains": "file not found"}
  ]
}
```

| Key | Meaning |
| --- | --- |
| `name`, `kind` | label and one of `happy`, `edge`, `error` |
| `args`, `stdin` | command line arguments and standard input |
| `files` | `{path: content}` created in the working directory first |
| `expect_exit` | exit code (default 0) |
| `stdout_contains`, `stdout_not_contains`, `stderr_contains` | string or list of strings |
| `stdout_regex` | regular expression or list |
| `stdout_json` | the output is JSON and contains at least these keys and values (lists must match in length) |
| `timeout` | seconds (default 20) |
| `entry` | script for this case, overrides the file level `entry` |

Every case runs in its own empty temporary directory, with a clean environment (no API keys, `HOME` pointing at
the temp folder). The `entry` path is relative to the skill folder, so scripts that read their own bundled files
should locate them with `__file__`.

`tests/test_*.py` files are run with `python -m unittest discover` from the skill root.

## Evals

`evals/evals.json` checks how a model behaves when it has the skill:

```json
{"cases": [{"name": "uses conventional commits", "prompt": "Write a commit message for ...",
            "must_include": ["fix"], "must_not_include": ["wip"], "regex": ["^fix(\\(.+\\))?:"]}]}
```

Run `askit eval path/to/skill --provider groq --baseline` to compare the answers with and without the skill.
Checks are plain strings and regular expressions, so results are repeatable.

## Quality score

| Part | With tests | Without tests |
| --- | --- | --- |
| lint (100 minus 25 per error, 6 per warning) | 30% | 45% |
| safety (100 minus risk from scan findings) | 25% | 35% |
| tests passed | 35% | not counted |
| documentation (description, headings, example, size, metadata) | 10% | 20% |

Lint errors cap the score at 0.59 and high severity scan findings cap it at 0.49. Grades: A from 0.9, B from 0.8,
C from 0.7, D from 0.5. The default gate for `forge` and `publish` is 0.8, no lint errors, no high severity findings
and all bundled tests passing.
