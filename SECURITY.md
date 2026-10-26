# Security policy

## Reporting a vulnerability

Please report security problems privately through
[GitHub security advisories](https://github.com/Lethe044/agentskill-kit/security/advisories/new)
instead of a public issue. Include the version, a short description and steps to reproduce. You will get a reply
within a few days.

## Scope

agentskill-kit installs and runs text and code that other people wrote. These parts matter most:

- the scanner (`askit scan`) and its rules,
- the sandbox that runs bundled tests (`askit test`),
- registry installs (checksum verification, path handling),
- the exporters that write into your project and home directory.

## What the tools do not promise

- The scanner is a heuristic filter. A clean result is not proof that a skill is safe.
- The test sandbox limits time, memory, output size and environment variables. It is not a security boundary.
  Use a container or a virtual machine when you test skills from sources you do not trust.
- Registry checksums protect against corrupted or modified downloads, not against a malicious author.

Read a skill before you let an agent act on it.
