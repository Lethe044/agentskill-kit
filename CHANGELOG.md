# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.2.0]

### Added

- `askit audit`: scan the skills already installed for Claude Code and Hermes (project and user folders), or any folder with `--path`.
- `askit update`: update skills that were installed from a registry when the registry has newer files.
- `askit eval --judge`: grade open ended eval cases with the model, using a `judge` criterion next to the plain string checks.
- Look-alike check in `askit lint`: warns when two skills in one set have very similar descriptions (W020) or the same name (W021). Disable with `--no-compare`.
- Scanner rules: chat template markers (SC008), links and images that can carry data out in the URL (SC009) and long encoded blobs (SC112). Rule SC101 now also catches downloads piped into python, node, perl, ruby or php, and `eval "$(curl ...)"` style commands.
- Export targets for Aider (`CONVENTIONS.md`), Cline (`.clinerules/`) and Roo Code (`.roo/rules/`).
- 11 new starter skills: `docker-compose-reviewer`, `requirements-auditor`, `markdown-link-checker`, `openapi-summarizer`, `cron-explainer`, `jwt-inspector`, `git-conflict-resolver`, `unit-test-writer`, `release-checklist`, `incident-postmortem-writer` and `regex-explainer`.
- The README demo is now an animated terminal session.

### Changed

- Rule SC003 no longer fires on prohibitions such as "do not force push without telling the user".
- Lint no longer checks links that sit inside code spans or fenced code blocks.
- File lists in the registry index are sorted by path on every operating system.

## [0.1.0]

First release of agentskill-kit. The project started as a hackathon prototype for Hermes Agent and was rebuilt
as a model independent toolkit for agent skills.

### Added

- `askit lint`: structural checks for SKILL.md files, offline and without a model.
- `askit scan`: security scanner for prompt injection, hidden unicode, dangerous commands, secrets and exfiltration patterns.
- `askit test` and `askit score`: run bundled tests in an isolated working directory and combine lint, scan and test results into a quality score.
- `askit forge`: generate a skill from a task description or from notes, check it with the same tools and refine it until it passes.
- `askit eval`: compare how a model follows a skill with and without it.
- `askit mine`: find repeated workflows in shell history and draft skills from them.
- `askit export`: convert one skill for Claude Code, Hermes, Cursor, Windsurf, GitHub Copilot, Codex (AGENTS.md) and Gemini CLI.
- `askit registry`, `search`, `install`, `uninstall`, `list`, `pack`, `publish`: a static, checksum verified skill registry and static website.
- `askit serve`: local web interface for the skills on your machine.
- Providers: Ollama, LM Studio, Groq, Gemini, OpenRouter, any OpenAI compatible endpoint, plus optional OpenAI and Anthropic keys.
- Turkish and English interface (`--lang tr`).
- 16 starter skills, a GitHub Action, a pre-commit hook and a Hermes integration.
- The package is published on PyPI as `agentskill-toolkit`.

### Changed

- The old simulated publish step was removed. Quality scores now come from real checks.
