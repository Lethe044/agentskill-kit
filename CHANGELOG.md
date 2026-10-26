# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

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
