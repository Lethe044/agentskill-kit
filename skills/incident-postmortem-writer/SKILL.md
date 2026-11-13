---
name: incident-postmortem-writer
description: Turns incident notes and timelines into a blameless postmortem with impact, root cause, timeline, what went well and action items. Use when the user needs to write up an outage, a failed deploy, a data problem or a security incident.
license: MIT
metadata:
  version: 1.0.0
  author: Lethe044
  tags: [incident, postmortem, sre, writing]
---

# Incident postmortem writer

A postmortem explains what happened and how to make it less likely, without blaming a person.

## When to use

- The user pastes chat logs, alerts or notes from an incident and wants a write-up.
- A review meeting is coming and the document is not started.
- The user asks how to structure a postmortem.

## Format

```markdown
# Postmortem: <short title>

**Date:** YYYY-MM-DD   **Duration:** Xh Ym   **Severity:** SEV-N   **Status:** draft

## Summary
Two or three sentences: what broke, who was affected, how it was fixed.

## Impact
Users or systems affected, for how long, with numbers when known (requests failed, orders lost).

## Timeline (UTC)
| Time | Event |
| --- | --- |
| 14:02 | Alert fired for elevated error rate |

## Root cause
The technical cause, then the contributing factors that let it happen or delayed detection.

## Detection and response
How it was noticed, how long it took, what slowed the response.

## What went well
## What went wrong
## Where we got lucky

## Action items
| Action | Owner | Due | Type (prevent, detect, mitigate) |
| --- | --- | --- | --- |
```

## Rules

1. **Blameless.** Describe actions and systems, not people. Write "the deploy script did not check the schema", not
   "Sam forgot to check".
2. **Facts before conclusions.** Build the timeline first from the sources. Mark gaps as unknown.
3. **Never invent.** Do not make up times, numbers, owners or causes. Write `unknown` or `to be confirmed`.
4. **Find the system cause.** Ask "why" until the answer is a missing check, a gap in monitoring or a weak default,
   not a human mistake.
5. **Action items must be checkable.** Each has an owner and a date, and fixes one cause. Prefer few strong items over a
   long list.
6. **Keep secrets out.** Remove tokens, customer data and internal hostnames that do not need to be shared.

## Errors

If the notes have no times, produce the format with the timeline marked "to be filled in" and list the questions that
would fill it.
