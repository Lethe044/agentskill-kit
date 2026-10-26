---
name: readme-doctor
description: Reviews a README for the things that make people try a project, covering the opening line, install steps, a runnable example, proof that it works and contribution info, then proposes concrete edits. Use when the user asks to improve a README, wants more stars or users for an open source project, or is preparing a launch.
license: MIT
metadata:
  version: 1.0.0
  author: Lethe044
  tags: [readme, documentation, open-source, growth]
---

# README doctor

Most visitors decide in under a minute. The README has to answer three questions fast: what is this, does it
solve my problem, and how do I try it.

## When to use

- The user shares a README and asks for feedback.
- A project is about to be announced on a forum or social media.
- The repository has traffic but few stars or issues.

## Review order

1. **Opening line.** One sentence naming the problem and the audience. Reject slogans and buzzwords.
2. **Proof above the fold.** A terminal recording, screenshot or short output sample within the first screen.
3. **Install.** One command that works on a clean machine. State supported platforms and versions.
4. **First success.** A minimal example whose output is shown, so the reader sees the result without running it.
5. **Why this exists.** Two or three sentences on how it differs from the alternatives, with honest limits.
6. **Features.** A short list of things the tool does, written as capabilities, not adjectives.
7. **Reference.** Commands, options and configuration in tables or short sections.
8. **Project health.** Badges for CI and version, license, contributing guide, roadmap, how to report bugs.

## Rules

- Check every command and link before recommending them. Do not suggest claims that cannot be shown.
- Cut anything that sounds like marketing and does not carry information.
- Prefer showing a real output to describing it.
- Suggest a repository description and topics that match what people search for.

## Output

Return a prioritized list: the three changes with the most impact first, each with a before and after snippet.
End with a short checklist of what is still missing.

## Errors

If the README is empty, ask what the project does and who it is for, then draft only the opening line and the
install section.
