# Getting started

## Install

```bash
pip install agentskill-kit
```

This installs two commands that do the same thing: `askit` and `agentskill`. Python 3.9 or newer is required.
There are no runtime dependencies.

To work from a clone instead:

```bash
git clone https://github.com/Lethe044/agentskill-kit
cd agentskill-kit
python -m pip install -e ".[dev]"
```

## Check a skill you already have

These three commands need no API key and no network:

```bash
askit lint path/to/skill       # structure, name, description
askit scan path/to/skill       # prompt injection, secrets, dangerous commands
askit test path/to/skill       # runs the tests bundled with the skill
askit score path/to/skill      # one number that combines all of the above
```

Pass a folder that holds several skills and every skill inside it is checked.
Without a path, `./skills` is used when it exists, otherwise the current folder.

## Create a skill by hand

```bash
askit init changelog-writer --script --tags git,release
```

This creates `skills/changelog-writer/` with a SKILL.md, a small Python script and a test file. Edit the text,
then run `askit lint` and `askit test`. The template contains lines that start with "Replace this"; lint warns
until you have rewritten them.

## Create a skill with a model

```bash
askit forge --task "turn meeting notes into action items with owners"
```

`forge` asks a model for a draft, checks it with the same lint, scan and test steps as above, and sends the
problems back to the model until the score reaches the threshold (0.8 by default) or the rounds run out.
Nothing is written when the result is below the threshold, unless you pass `--force`.

You can also feed it material to learn from:

```bash
askit forge --from-file examples/deploy-runbook.md --name deploy-billing
```

No model available? Try the offline demo model: `askit forge --task "anything" --provider mock`.
See [providers](providers.md) for free options.

## Use the skills

```bash
askit export skills/log-analyzer --target claude      # ./.claude/skills/
askit export skills/log-analyzer --target cursor      # ./.cursor/rules/
askit export skills/log-analyzer --target all         # every supported agent
askit export skills/log-analyzer --target claude --global
```

See [export targets](export-targets.md) for what each target writes.

## Find and install community skills

```bash
askit search docker
askit install dockerfile-linter
askit install github:owner/repo/path/to/skill
```

See [registry](registry.md).

## Settings

```bash
askit config set provider groq
askit config set threshold 0.85
askit config show
```

Settings live in `~/.agentskill-kit/config.json`. Set `ASKIT_HOME` to use another folder.
A `.env` file in the current directory is loaded automatically, which is a convenient place for API keys.
Use `--lang tr` (or `ASKIT_LANG=tr`) for a Turkish interface.
