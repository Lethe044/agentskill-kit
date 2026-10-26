---
name: log-analyzer
description: Summarizes application log files by severity, time range and the most frequent error messages. Use when the user shares a log file or pasted log output and asks what went wrong, which errors repeat, or how noisy the log is.
license: MIT
metadata:
  version: 1.0.0
  author: Lethe044
  tags: [logs, debugging, devops, analysis]
---

# Log analyzer

Reads plain text logs and produces a structured summary so the agent can reason about the
incident instead of scrolling through thousands of lines.

## When to use

- The user pastes a stack trace or log excerpt and asks for the root cause.
- The user asks which errors happen most often, or when problems started.
- A deploy or test run failed and a log file is available.

## How to run

```bash
python scripts/analyze_log.py --top 5 app.log
cat app.log | python scripts/analyze_log.py
```

The script reads the file given as the last argument, or standard input when no file is given.

## Output

A JSON object:

- `total_lines` and `levels`: a count per severity (`CRITICAL`, `ERROR`, `WARN`, `INFO`, `DEBUG`).
- `first_timestamp` and `last_timestamp`: the earliest and latest ISO style timestamps found, or `null`.
- `top_errors`: the most frequent error messages as `{"message", "count"}`. Numbers, hex ids and quoted
  values are replaced with placeholders so that similar errors group together.

## Reading the result

1. Start with `levels`. A high ratio of `ERROR` to `INFO` points to a sustained failure, not a one-off.
2. Compare `first_timestamp` with the time the user reports the problem.
3. Take the first entry of `top_errors` and search the original log for its raw form to get the stack trace.
4. Report the cause, the evidence (counts and timestamps), and one concrete next step.

## Example

Input line: `2024-05-01 10:00:02 ERROR db timeout after 30s on host 10.0.0.5`

The message is grouped as `db timeout after <n>s on host <n>.<n>.<n>.<n>`.

## Errors

A missing file exits with code 2 and `file not found` on stderr. Empty input returns zero counts.
