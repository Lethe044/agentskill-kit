---
name: skill-author
description: Guides an agent through writing a good SKILL.md, covering the name, a description that triggers at the right time, concise instructions, bundled scripts and tests. Use when the user asks to create, improve or review an agent skill, or wants to turn a repeated task into a reusable skill.
license: MIT
metadata:
  version: 1.0.0
  author: Lethe044
  tags: [skills, authoring, prompt-engineering, agents]
---

# Skill author

A skill is a folder with a `SKILL.md` file. The agent reads the name and description of every installed skill
and loads the full instructions only when a task matches. The description is therefore the most important line.

## When to use

- The user keeps repeating the same kind of task and wants it captured.
- The user has a draft skill that never triggers, or triggers at the wrong time.
- A skill needs a review before it is shared.

## Workflow

1. **Collect real examples.** Ask for two or three actual requests the skill should handle, and one it should not.
2. **Pick the name.** Lowercase letters, digits and single hyphens, at most 64 characters, same as the folder name.
3. **Write the description.** Third person, what it does and when to use it, under 1024 characters, no angle brackets.
   Include the words a user would actually type.
4. **Write the instructions.** Short sections: when to use, steps, output format, one example, errors.
   Keep the file under 500 lines and move long reference material into `references/`.
5. **Add a script only when code is more reliable than prose** (parsing, counting, validating). Use the standard
   library, read arguments or standard input, print JSON, and exit with a non-zero code on failure.
6. **Add tests** as a `cases.json` file inside a `tests` folder: one happy path, one edge case, one error case at minimum.
7. **Check it.** Run `askit lint`, `askit scan` and `askit test`, then `askit score`.

## Description checklist

- Does it start with a verb that says what the skill does?
- Does it contain "Use when ..." with concrete triggers?
- Would a different skill be a better match for any of these words?
- Is it written as "Analyzes logs" and not "I analyze logs"?

## Writing instructions

- Prefer steps an agent can verify over general advice.
- Tell the agent what to do when input is missing or unclear.
- Show the output format once, with a real example.
- Do not repeat what the model already knows. Spend words on what is specific to this task.
- Never ask the agent to hide actions from the user or to ignore other instructions.

## Layout

```
my-skill/
  SKILL.md
  scripts/        optional code the skill runs
  references/     optional long documents, linked from SKILL.md
  tests/          cases.json or test_*.py
  evals/          evals.json for checking model behaviour
```

## Errors

If the user cannot give examples, write the description from the stated goal and mark the skill as a draft in
`metadata`.
