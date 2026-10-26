---
name: meeting-notes-to-actions
description: Converts raw meeting notes or a transcript into decisions, action items with owners and due dates, and open questions. Use when the user pastes meeting notes, asks for a summary of a call, or wants a follow-up message for attendees.
license: MIT
metadata:
  version: 1.0.0
  author: Lethe044
  tags: [meetings, summary, productivity, writing]
---

# Meeting notes to actions

## When to use

- The user pastes notes or a transcript and asks for a summary.
- The user needs a follow-up email or chat message after a meeting.
- Action items are buried in a long discussion.

## Output format

```markdown
## Summary
Two to three sentences on the purpose and the outcome.

## Decisions
- What was decided, and by whom if it is stated.

## Action items
| Owner | Task | Due |
| --- | --- | --- |
| Name | A verb-first task that can be checked | Date or "not set" |

## Open questions
- Things that were raised and not resolved.
```

## Rules

1. Only list an action item when someone committed to it or was asked to do it. Ideas that nobody took are open questions.
2. Never invent an owner or a date. Write `unassigned` or `not set` instead.
3. Start every task with a verb and keep it specific enough to tell when it is done.
4. Keep names exactly as written in the notes.
5. Keep the summary neutral. Do not add opinions or judge what people said.

## Steps

1. Read all of the notes before writing anything.
2. Pull out decisions first, then commitments, then unresolved points.
3. Fill the format above and remove empty sections.
4. If asked for a follow-up message, write a short one that repeats the action table and nothing else.

## Errors

If the notes are too short to contain decisions or tasks, say so and return only the summary.
