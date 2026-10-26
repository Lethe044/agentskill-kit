---
name: sql-query-reviewer
description: Reviews SQL queries for correctness, performance and safety problems such as SELECT star, missing indexes, unbounded updates, implicit casts and injection risks. Use when the user asks to optimize a query, explain why a query is slow, or check SQL before it runs on production data.
license: MIT
metadata:
  version: 1.0.0
  author: Lethe044
  tags: [sql, database, performance, review]
---

# SQL query reviewer

## When to use

- A query is slow or times out.
- The user is about to run an `UPDATE` or `DELETE` on real data.
- SQL is built from user input in application code.

## Checklist

**Safety first**

1. `UPDATE` or `DELETE` without a `WHERE` clause. Ask for confirmation and suggest running a `SELECT COUNT(*)` with the same condition first.
2. Wrap destructive statements in a transaction and show how to roll back.
3. String concatenation of user input into SQL. Replace it with bound parameters.

**Correctness**

4. `NULL` comparisons written with `=` instead of `IS NULL`.
5. `LEFT JOIN` followed by a `WHERE` condition on the right table, which silently turns it into an inner join.
6. `GROUP BY` that does not match the selected columns, and `COUNT(column)` used where `COUNT(*)` was meant.
7. `NOT IN` with a subquery that can return `NULL`. Prefer `NOT EXISTS`.

**Performance**

8. `SELECT *` on wide tables. List the columns that are used.
9. Functions on indexed columns in `WHERE` (`WHERE LOWER(email) = ...`). Suggest an expression index or a different predicate.
10. Leading wildcards (`LIKE '%term'`) that cannot use an index.
11. Missing indexes on join and filter columns. Ask for `EXPLAIN` output instead of guessing.
12. `OFFSET` pagination on large tables. Suggest keyset pagination.
13. `ORDER BY` without `LIMIT` on large results, and `DISTINCT` used to hide a bad join.

## Steps

1. Identify the database engine. Advice differs between PostgreSQL, MySQL, SQLite and SQL Server.
2. Go through the checklist and list only real findings, most serious first.
3. Show the rewritten query next to each finding.
4. If performance is the question and no `EXPLAIN` output was given, ask for it and say what to look for (sequential scans, row estimates far from actual rows).

## Example

Input: `DELETE FROM sessions WHERE created_at < now() - interval '30 days'`

Review: valid, but deletes an unknown number of rows. Run `SELECT COUNT(*)` with the same condition first, delete
in batches if the count is large, and keep it inside a transaction until the result looks right.

## Errors

If the schema is unknown, say which assumptions the review makes about indexes and types.
