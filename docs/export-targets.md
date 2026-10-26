# Export targets

`askit export PATH --target NAME` converts a skill for another agent. Add `--dest DIR` to choose the project folder
(default: current directory), `--global` to install in your home directory, and `--dry-run` to preview.

| Target | Writes | Global |
| --- | --- | --- |
| `claude` | `.claude/skills/<name>/` (whole folder) | `~/.claude/skills/` |
| `hermes` | `.hermes/skills/<name>/` (whole folder) | `~/.hermes/skills/` |
| `cursor` | `.cursor/rules/<name>.mdc` | no |
| `windsurf` | `.windsurf/rules/<name>.md` | no |
| `copilot` | `.github/instructions/<name>.instructions.md` | no |
| `codex` | a managed block in `AGENTS.md` | `~/.codex/AGENTS.md` |
| `gemini` | a managed block in `GEMINI.md` | `~/.gemini/GEMINI.md` |
| `all` | every target above that supports the chosen scope | |

## How conversion works

- Folder targets copy the skill as it is, including scripts and references.
- Rule file targets keep the description in the rule header, inline the instructions and, when the skill has
  scripts or other files, copy the folder to `.agent-skills/<name>/` and add a line that points to it.
- Block targets add a section between `<!-- agentskill-kit:begin NAME -->` and `<!-- agentskill-kit:end NAME -->`
  markers. Exporting again replaces the block, so the command is safe to repeat, and the rest of the file is untouched.

`askit uninstall NAME --target X` removes what an export created.

## Compatibility note

Each agent defines its own conventions and they change over time. The paths and headers above follow the documented
conventions at the time of writing. If an agent changes its format, open an issue.
