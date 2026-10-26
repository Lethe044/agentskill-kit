---
name: secure-code-review
description: Reviews code for common security flaws such as injection, broken authentication, unsafe deserialization, hardcoded secrets, path traversal and weak cryptography, and reports findings with severity and fixes. Use when the user asks for a security review, a pre-release audit or a check of code that handles user input, files or credentials.
license: MIT
metadata:
  version: 1.0.0
  author: Lethe044
  tags: [security, code-review, appsec, owasp]
---

# Secure code review

## When to use

- Code parses user input, builds queries or commands, handles uploads or sessions.
- Before a release, or when code from an unknown source is about to be merged.
- The user asks "is this safe?" about a function or a service.

## What to look for

1. **Injection.** User input concatenated into SQL, shell commands, templates, LDAP or file paths.
2. **Authentication and sessions.** Missing checks on endpoints, weak password storage, tokens in URLs, predictable ids.
3. **Authorization.** Object access that trusts an id from the client without an ownership check.
4. **Secrets.** Keys, tokens and passwords in code, config files, logs or error messages.
5. **Unsafe deserialization.** `pickle`, `yaml.load` without a safe loader, Java object streams, `eval` on data.
6. **Path traversal and uploads.** User controlled file names, missing type and size limits, files saved under the web root.
7. **Cryptography.** Home made schemes, MD5 or SHA-1 for passwords, fixed IVs, `random` used for tokens.
8. **Network.** Disabled TLS verification, permissive CORS, server side requests to user supplied URLs.
9. **Dependencies.** Pinned versions with known advisories, install scripts that fetch code at run time.
10. **Error handling.** Stack traces returned to clients, verbose logs with personal data.

## Report format

For every finding give: severity (critical, high, medium, low), the file and line, one sentence on how it can be
abused, and a corrected snippet. Order by severity. Finish with what was not reviewed.

## Rules

- Only report issues you can point to in the code. Mark guesses as "possible" and say what would confirm them.
- Do not run or test against systems the user does not own.
- Do not paste real secrets into the report. Show the first and last two characters at most.
- Prefer the framework's built-in protection over custom code in fixes.

## Errors

If only a snippet is available, state which parts of the application (auth, config, deployment) were out of view.
