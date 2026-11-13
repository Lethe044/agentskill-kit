---
name: regex-explainer
description: Explains regular expressions in plain language, builds new patterns from examples and tests them against matching and non-matching samples. Use when the user pastes a regex they do not understand, needs a pattern for a text format, or wants to find out why a pattern does not match.
license: MIT
metadata:
  version: 1.0.0
  author: Lethe044
  tags: [regex, text, parsing, explain]
---

# Regex explainer

Regular expressions are dense. Read them in pieces and prove the result with examples.

## When to use

- The user pastes a pattern and asks what it does.
- The user describes a format (dates, ids, log lines) and needs a pattern.
- A pattern matches too much, too little, or is very slow.

## Explaining a pattern

1. Name the flavor (Python `re`, JavaScript, PCRE, POSIX). Behavior differs for lookbehind, named groups and flags.
2. Split the pattern into tokens: anchors, groups, character classes, quantifiers, alternations.
3. Explain each token in order, in a short list, then give the whole meaning in one sentence.
4. Show two strings that match and two that do not, and say why.

## Building a pattern

1. Ask for at least three strings that must match and three that must not, unless they are given.
2. Start from the simplest pattern that matches the positives, then tighten it with anchors (`^`, `$`, `\b`) until the
   negatives fail.
3. Prefer explicit character classes (`[0-9]`, `[A-Za-z]`) over `.` and avoid `.*` in the middle of a pattern.
4. Use non-capturing groups `(?:...)` when you do not need the text, and named groups when you do.
5. Test the pattern against every example and show a table of results. If a code runner is available, run it.

## Common problems

- Greedy quantifiers swallow too much. Use a lazy quantifier (`.*?`) or a negated class (`[^"]*`).
- Missing anchors make a pattern match inside longer text. Add `^...$` or `\b`.
- Unescaped special characters (`.`, `?`, `+`, `(`) inside literal text.
- Nested quantifiers such as `(a+)+` can take exponential time on long input. Rewrite them.
- Do not use a regex to parse nested or recursive formats (HTML, JSON, source code). Use a parser.

## Example

Pattern: `^(\d{4})-(\d{2})-(\d{2})$`

Matches a date like `2024-05-17` and captures year, month and day. It rejects `2024-5-17` (month has one digit)
and `x2024-05-17` (anchored). It does not check that the month is 1 to 12.

## Errors

If the flavor is unknown and the pattern uses flavor specific syntax, say which flavors support it.
