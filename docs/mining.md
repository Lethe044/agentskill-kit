# Mining shell history

`askit mine` looks through your shell history for command sequences you keep repeating and proposes them as skills.
Everything happens on your machine.

```bash
askit mine                                   # auto-detect history files
askit mine --file ~/.bash_history --min-count 3
askit mine --draft 1                         # write candidate 1 as a skill, no model needed
askit mine --forge 1 --provider ollama       # let a model improve candidate 1
history | askit mine --stdin                 # when your shell keeps history in memory
```

## Supported history

bash (including timestamp lines), zsh (extended history), fish and PowerShell (`ConsoleHost_history.txt`).
Use `--file` for any other location.

## How it works

1. Trivial commands (`cd`, `ls`, `clear`, ...) are dropped.
2. Commands are normalised: URLs, paths, file names, numbers, hashes and quoted text become placeholders such as
   `<path>` and `<str>`, so `git commit -m "fix"` and `git commit -m "feat"` count as the same step.
3. Sequences of two to four consecutive steps that repeat at least `--min-count` times are ranked by frequency and length.
   Shorter sequences that are part of a longer one with the same count are hidden, and repeated cycles are reported once.
4. Single commands that you run very often are listed too.

## Privacy

Secrets are masked before anything is printed or written: provider API keys, tokens, `--password` style flags,
`KEY=value` assignments for names that look secret, `Authorization` headers and passwords inside URLs.
Always read the output before you share a generated skill. `--forge` sends the normalised steps and a redacted
example to your model provider.

## Drafts

`--draft` writes a SKILL.md with the steps, a parameter list for each placeholder and a redacted example from your
history. It passes `askit lint` and `askit scan`. It is a starting point: check that the steps make sense for other
targets and tell the agent when to stop.
