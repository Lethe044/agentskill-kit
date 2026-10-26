<p align="center">
  <img src="docs/assets/banner.svg" alt="agentskill-kit" width="100%">
</p>

<p align="center">
  <a href="https://github.com/Lethe044/agentskill-kit/actions/workflows/ci.yml"><img src="https://github.com/Lethe044/agentskill-kit/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/agentskill-kit/"><img src="https://img.shields.io/pypi/v/agentskill-kit" alt="PyPI"></a>
  <a href="https://pypi.org/project/agentskill-kit/"><img src="https://img.shields.io/pypi/pyversions/agentskill-kit" alt="Python versions"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/Lethe044/agentskill-kit" alt="License"></a>
</p>

**agentskill-kit** is a command line toolkit for agent skills, the `SKILL.md` folders that coding agents such as
Claude Code, Cursor, Codex, Gemini CLI and Hermes load when a task matches. It checks a skill before you trust it,
generates new ones, and installs the same skill into every agent you use.

- **Lint** a skill: name, description, structure. Works offline.
- **Scan** it for prompt injection, hidden unicode, secrets and dangerous commands.
- **Test** it: run the tests that ship with the skill in an isolated folder.
- **Forge** a new skill from a task description with any model, including free and local ones.
- **Mine** your shell history for routines that should be skills.
- **Export** one skill to Claude Code, Cursor, Windsurf, Copilot, Codex and Gemini CLI.
- **Share** skills through a static registry with checksums and a searchable website.

No runtime dependencies. No paid service required. Python 3.9 or newer on Linux, macOS and Windows.

<p align="center">
  <img src="docs/assets/demo.svg" alt="Terminal session: lint, scan, test and forge" width="100%">
</p>

## Install

```bash
pip install agentskill-kit
```

The package installs `askit` (and the longer alias `agentskill`).

## Quick start

Check a skill without any API key:

```bash
askit lint skills/my-skill
askit scan skills/my-skill
askit test skills/my-skill
askit score skills/my-skill
```

Create one with a free model (a local Ollama model, or a Groq or Gemini key on the free tier):

```bash
askit forge --task "turn meeting notes into action items with owners and due dates"
```

Use it in your agents:

```bash
askit export skills/meeting-notes-to-actions --target claude
askit export skills/meeting-notes-to-actions --target cursor
askit export skills/meeting-notes-to-actions --target all
```

Install something from the community registry:

```bash
askit search docker
askit install dockerfile-linter
```

Try everything offline with the built-in demo model: `askit forge --task "anything" --provider mock`.

## Why this exists

Skills are plain text that an agent obeys, so they deserve the same care as code you run: a review, a linter, a
test and a look at what they do. At the same time every agent wants a slightly different file layout, and writing
good skills by hand is slow. agentskill-kit covers both: quality gates for skills, and tools that do the tedious
parts.

## Commands

| Command | What it does |
| --- | --- |
| `askit init NAME` | Create a skill from a template, optionally with a script and tests |
| `askit lint [PATH]` | Check SKILL.md structure (`--strict`, `--format json\|github`) |
| `askit scan [PATH]` | Security scan (`--fail-on high\|medium\|low\|never`) |
| `askit test [PATH]` | Run `tests/cases.json` and `tests/test_*.py` of each skill |
| `askit score [PATH]` | Combine lint, scan and tests into one score and a pass or fail gate |
| `askit forge` | Generate a skill with a model, verify it and refine it until it passes |
| `askit eval PATH` | Check how well a model follows a skill, with an optional baseline run |
| `askit mine` | Find repeated workflows in shell history and draft skills |
| `askit export PATH` | Convert and install a skill for another agent |
| `askit search`, `install`, `uninstall`, `list` | Work with the registry, GitHub folders and local folders |
| `askit pack`, `publish` | Bundle a skill, run the quality gate, prepare a pull request |
| `askit registry build\|site` | Build a registry index or a static website |
| `askit serve` | Browse the skills on your machine in a local web page |
| `askit providers`, `config`, `doctor` | Models, settings and environment checks |

Every command has `--help`. Add `--lang tr` for a Turkish interface.

## Free first, paid optional

| Provider | Cost | How |
| --- | --- | --- |
| Ollama, LM Studio | free, local | run a local model, no key |
| Groq | free tier | `GROQ_API_KEY` |
| Google Gemini | free tier | `GEMINI_API_KEY` |
| OpenRouter | free models | `OPENROUTER_API_KEY`, pick a `:free` model |
| Any OpenAI compatible server | yours | `ASKIT_BASE_URL`, `ASKIT_MODEL` |
| OpenAI, Anthropic | paid, optional | `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` |

`askit providers` shows what is ready. Details in [docs/providers.md](docs/providers.md).

`forge` does not rely on tool calling. The loop is controlled by code, so small local models work. The model only
writes files; lint, scan and tests decide whether they are good enough.

## How forge decides

```
task or notes
      |
      v
  model drafts SKILL.md, scripts and tests/cases.json
      |
      v
  lint + scan + run tests in a clean folder  ->  score
      |                                           |
      |  below threshold: failures go back        |  at or above threshold,
      |  to the model (up to 3 rounds)            |  no high findings
      v                                           v
  best attempt kept                          written to skills/<name>/
```

The score is not the model's opinion. It comes from [real checks](docs/skill-format.md#quality-score).
Nothing is written when the best attempt misses the threshold, unless you pass `--force`.

## Mine your history

```bash
$ askit mine --file examples/shell-history-sample.txt
-- read 20 commands
Found 1 repeated workflow(s)

#1  git-status-add-commit  (4x)
     git status
     git add -A
     git commit -m <str>
     git push origin main

$ askit mine --file examples/shell-history-sample.txt --draft 1
```

Secrets are masked before anything is shown. See [docs/mining.md](docs/mining.md).

## Export targets

| Target | Result |
| --- | --- |
| `claude` | `.claude/skills/<name>/` or `~/.claude/skills/` with `--global` |
| `hermes` | `.hermes/skills/<name>/` or `~/.hermes/skills/` |
| `cursor` | `.cursor/rules/<name>.mdc` |
| `windsurf` | `.windsurf/rules/<name>.md` |
| `copilot` | `.github/instructions/<name>.instructions.md` |
| `codex` | managed block in `AGENTS.md` |
| `gemini` | managed block in `GEMINI.md` |

Exports are repeatable: managed blocks are replaced, not duplicated. More in [docs/export-targets.md](docs/export-targets.md).

## Starter skills

The registry ships 16 skills that pass every check. Nine of them include scripts with tests, so you can read how a
tested skill is built.

| Skill | What it does |
| --- | --- |
| `log-analyzer` | severity counts, time range and frequent errors of a log |
| `python-code-smells` | bare except, mutable defaults, missing docstrings and long functions |
| `csv-profiler` | column types, missing values and ranges for a CSV |
| `json-diff` | structural diff of two JSON files |
| `dockerfile-linter` | unpinned images, root user, ADD vs COPY, secrets in ENV |
| `env-file-auditor` | `.env` against `.env.example`, without printing values |
| `todo-extractor` | TODO, FIXME and HACK inventory of a source tree |
| `changelog-generator` | conventional commits to grouped release notes |
| `api-endpoint-tester` | smoke test an API from a JSON file |
| `commit-message-writer` | clear conventional commit messages |
| `pr-description-writer` | pull request descriptions reviewers can use |
| `sql-query-reviewer` | safety, correctness and performance review of SQL |
| `meeting-notes-to-actions` | decisions, owners and open questions from notes |
| `readme-doctor` | what to fix in a README to get people to try a project |
| `secure-code-review` | a security checklist with a report format |
| `skill-author` | how to write a skill that triggers and works |

Browse them on the registry website, or run `askit search` and `askit install NAME`.

## Use it in CI

```yaml
- uses: Lethe044/agentskill-kit@main
  with:
    path: skills
    strict: "true"
    scan-fail-on: medium
```

Also available as a pre-commit hook. See [docs/github-action.md](docs/github-action.md).

## Use it from Python

```python
from agentskill_kit.lint import lint_skill
from agentskill_kit.scan import scan_skill
from agentskill_kit.scoring import evaluate_skill

quality = evaluate_skill("skills/log-analyzer")
print(quality.score, quality.grade, quality.passes_gate)

for issue in lint_skill("skills/log-analyzer").issues:
    print(issue.code, issue.message)

print(scan_skill("skills/log-analyzer").verdict)
```

## Security notes

- The scanner is a heuristic filter, not a guarantee. Read skills from sources you do not trust.
- `askit test` isolates the working directory and environment and limits time and memory, but it is not a sandbox.
  Use a container for untrusted skills.
- Registry downloads are verified against checksums, linted and scanned before installation.

Details in [docs/security.md](docs/security.md) and [SECURITY.md](SECURITY.md).

## Hermes Agent

This project began as a Hermes Agent hackathon prototype. Hermes remains a first class target
(`askit export --target hermes`) and `integrations/hermes/` holds the skill-forge playbook and an Atropos
training environment whose reward can use verified scores. See [integrations/hermes](integrations/hermes/README.md).

## Documentation

- [Getting started](docs/getting-started.md)
- [Skill format, tests and scoring](docs/skill-format.md)
- [Providers](docs/providers.md)
- [Security model](docs/security.md)
- [Export targets](docs/export-targets.md)
- [Registry and publishing](docs/registry.md)
- [Mining shell history](docs/mining.md)
- [GitHub Action and pre-commit](docs/github-action.md)

## Roadmap

- More scanner rules and a community rule pack.
- Translated rule messages (the interface is already available in Turkish and English).
- `askit eval` with a judge model for open ended checks.
- Skill dependencies and version constraints in the registry.
- Export targets for more agents.

Ideas and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add a skill in a few minutes.

## License

[MIT](LICENSE)
