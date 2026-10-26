---
name: skill-forge
description: Lets a Hermes agent turn a task it keeps repeating into a tested, reusable skill, using askit to lint, scan, test and score the result before sharing it. Use when the same kind of request comes up more than twice, or when the user asks the agent to save a workflow as a skill.
license: MIT
metadata:
  version: 2.0.0
  author: Lethe044
  tags: [hermes, skills, self-improvement, automation]
---

# Skill forge for Hermes

A playbook for an agent that notices repeated work and captures it as a skill, with checks that do not depend on
the agent's own opinion of its work.

## When to use

- The same request, or the same sequence of steps, has come up three times.
- The user says "remember how to do this" or "make this a skill".
- A workflow took many tool calls and would be much shorter with a script.

## Loop

1. **Search first.** Look through installed skills and memory for something that already covers the task.
   Extend an existing skill instead of writing a near copy.
2. **Abstract.** Remove details that belong to one run: names, paths, dates. Decide the inputs, the output
   and what should happen on bad input.
3. **Write.** Create `~/.hermes/skills/<name>/SKILL.md` with frontmatter (name, description, license, metadata)
   and short instructions. Add `scripts/` when code is more reliable than prose.
4. **Test.** Add a `cases.json` file inside a `tests` folder with a happy path, an edge case and an error case, then run the checks:

   ```bash
   askit lint ~/.hermes/skills/<name>
   askit scan ~/.hermes/skills/<name>
   askit test ~/.hermes/skills/<name>
   askit score ~/.hermes/skills/<name>
   ```

5. **Refine.** If the score is below 0.8, read the failing checks, fix the skill and run them again.
6. **Share.** When the gate passes, run `askit publish ~/.hermes/skills/<name>` and tell the user where the package is.
7. **Remember.** Store one line in memory: skill name, score and what it is for, so step 1 finds it next time.

## Rules

- Never report a score you did not get from `askit score`.
- Never put secrets or personal data into a skill or into its test cases.
- Tell the user before running a script from a skill you did not write.

## Errors

If `askit` is not installed, install it with `pip install agentskill-toolkit` and continue. If the checks cannot run,
say so and do not claim the skill is tested.
