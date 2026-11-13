---
name: unit-test-writer
description: Writes focused unit tests for a function or module, covering the normal case, edge cases and failures, in the test framework the project already uses. Use when the user asks for tests, wants coverage for new code, or needs a regression test that reproduces a bug.
license: MIT
metadata:
  version: 1.0.0
  author: Lethe044
  tags: [testing, unit-tests, pytest, quality]
---

# Unit test writer

Good tests describe behavior. They fail for one reason and say what broke.

## When to use

- New code has no tests.
- A bug was fixed and needs a test that would have caught it.
- The user asks to raise coverage on a module.

## Steps

1. **Find the conventions.** Look at existing tests for the framework (pytest, unittest, Jest, JUnit, Go test), file
   layout, naming and fixtures. Follow them. Do not introduce a new framework.
2. **Read the code under test.** List its inputs, outputs, side effects and the errors it can raise.
3. **Plan the cases** before writing code:
   - the normal case with realistic input,
   - boundaries: empty, one item, maximum, zero, negative, unicode,
   - invalid input and the exact error expected,
   - one case per branch that has different behavior.
4. **Write each test small.** One behavior per test, a name that states it (`test_returns_empty_list_for_empty_input`),
   arrange, act, assert in that order.
5. **Isolate.** Replace network, clock, randomness and the file system with fakes or temporary directories. Tests must
   not depend on the order they run in.
6. **Run them.** Show the command and the result. Make sure a new test fails when the behavior is broken (change the
   code or the expectation briefly and check).

## For a bug fix

Write the failing test first, from the report. Confirm that it fails for the right reason, then fix the code.

## Rules

- Assert on behavior, not on implementation details such as private function calls.
- Do not copy the implementation into the test to compute the expected value. Use a literal.
- Avoid sleeping, real network calls and shared global state.
- Keep test data inline unless it is large.

## Example

For `parse_duration("1h30m")` the plan is: `"1h30m"` gives 5400, `"90s"` gives 90, `""` raises `ValueError`,
`"1x"` raises `ValueError`, and `"0s"` gives 0.

## Errors

If the code cannot be tested without a refactor (for example it reads a global), say so and propose the smallest change
that makes it testable.
