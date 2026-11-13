---
name: cron-explainer
description: Explains a five field cron expression in plain English, validates every field and warns about schedules that can never run, such as February 30. Use when the user pastes a crontab line or a schedule string and asks when it runs, or wants to check a schedule before adding it.
license: MIT
metadata:
  version: 1.0.0
  author: Lethe044
  tags: [cron, scheduling, devops, explain]
---

# Cron explainer

Cron expressions are short and easy to misread. This skill translates them and checks that they are valid.

## When to use

- The user pastes a line from a crontab, a CI schedule or a Kubernetes CronJob.
- A job runs at an unexpected time and the user wants to know why.
- Before adding a schedule, to confirm that it says what the user means.

## How to run

```bash
python scripts/explain_cron.py "30 2 * * 1-5"
python scripts/explain_cron.py @daily
```

Pass the five fields in one quoted argument (or as separate arguments). The macros `@yearly`, `@annually`,
`@monthly`, `@weekly`, `@daily`, `@midnight` and `@hourly` are expanded first.

## Field format

Minute `0-59`, hour `0-23`, day of month `1-31`, month `1-12` or `jan-dec`, day of week `0-7` or `sun-sat`
(0 and 7 are Sunday). Each field accepts `*`, a value, a range `a-b`, a step `*/n` or `a-b/n`, and comma lists.

## Output

JSON with `expression`, `expanded` (the five fields), `description` (English) and `warnings`.
Invalid expressions exit with code 2 and a message on stderr.

## Notes for the answer

- When both day of month and day of week are restricted, classic cron runs the job when either one matches.
  Mention this when the expression has both.
- Cron uses the time zone of the machine or scheduler, not the user's. Ask if it matters.
- Say what the next one or two runs would be only if the user gives the current time. This script does not guess it.

## Errors

A wrong number of fields, an unknown name, a value out of range or a zero step exits with code 2.
