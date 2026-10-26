# Security model

Skills are instructions that an agent follows, often with access to a shell and your files. A bad skill can
steer an agent to leak data or run harmful commands. agentskill-kit helps you notice that, but it is not a guarantee.

## `askit scan`

The scanner reads every text file in a skill and reports findings with a rule id, a severity and the line.

| Rule | Severity | What it looks for |
| --- | --- | --- |
| SC001 to SC005 | high, medium | phrases that override instructions, hide actions from the user, jailbreak wording, requests to reveal the system prompt |
| SC006 | high | invisible and bidirectional unicode characters |
| SC007 | medium | instructions hidden in HTML comments |
| SC101 to SC111 | high to low | `curl | sh`, recursive deletes of broad paths, sudo, `chmod 777`, decode and run, reverse shells, eval and exec, destructive disk commands, force push, installs from URLs |
| SC201 to SC206 | high, medium | AWS, GitHub, LLM provider, Slack, npm and PyPI tokens, private keys, hardcoded credentials |
| SC301, SC302, SC310 | medium to high | reading credential files, sending data over the network, and both in one file |
| SC303 | medium | raw IP URLs, link shorteners, request catchers and webhook endpoints |
| SC401 | medium | persistence through shell rc files, cron, ssh keys |
| SC601, SC602 | medium, low | bundled binaries and very large files |

Severity decides the exit code: `askit scan --fail-on high` (the default) fails on any high finding.

### Silencing a deliberate match

Put `askit-ignore` on the same line, optionally with rule ids:

```markdown
Run `sudo apt install jq` once.   <!-- askit-ignore: SC103 -->
```

### Limits

Pattern matching can be evaded, and prose that talks about attacks (like this page) can trigger rules. Treat the
scanner as a first filter. Read skills from sources you do not trust before installing them.

## Running tests safely

`askit test` copies the skill to a temporary folder and runs every case in a fresh empty working directory with:

- a minimal environment (no API keys, `HOME` set to the temp folder),
- a time limit per case, and on Linux and macOS CPU, memory, file size and open file limits,
- truncated output.

Before running anything, the runner scans the skill's Python files and refuses to execute code with high severity
findings. This is a seat belt, not a sandbox. For skills you do not trust, run `askit test` inside a container
or a virtual machine.

## Installing

`askit install` verifies SHA-256 checksums from the registry index, rejects unsafe paths, runs lint and scan on the
download and refuses to install when there are lint errors or high severity findings (override with `--force`).
Checksums detect corruption and tampering after the index was built. They do not make a malicious author trustworthy.

## Reporting problems

See [SECURITY.md](../SECURITY.md).
