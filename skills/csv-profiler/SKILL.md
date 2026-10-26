---
name: csv-profiler
description: Profiles a CSV file column by column, reporting inferred type, missing values, unique counts and min, max and mean for numeric columns. Use when the user hands over a CSV and asks what is in it, whether the data is clean, or what to check before analysis.
license: MIT
metadata:
  version: 1.0.0
  author: Lethe044
  tags: [csv, data, profiling, analysis]
---

# CSV profiler

Gives an agent a reliable picture of a CSV file before it writes any analysis code.

## When to use

- The user uploads or points to a CSV and asks "what is in this file?".
- Before cleaning, joining or plotting data, to find empty columns and mixed types.
- When a script fails on a column and the user suspects bad values.

## How to run

```bash
python scripts/profile_csv.py data.csv
python scripts/profile_csv.py data.tsv --delimiter tab
```

The delimiter is detected automatically when it is not given. Use `--delimiter tab` for tab separated files.

## Output

JSON with `rows`, `columns` and a `profile` list. Each column has `name`, `type`
(`integer`, `float`, `boolean`, `date`, `string` or `empty`), `missing`, `unique`, `sample`
and, for numeric columns, `min`, `max` and `mean`.

## Reading the result

- A column with a large `missing` count needs a decision: drop it, fill it, or ask the user.
- A `string` column whose `unique` count is close to `rows` is probably an identifier.
- A `string` column with few unique values is a good candidate for a categorical type.
- Report surprises first: mixed types, empty columns, duplicated headers.

## Errors

A missing file exits with code 2. A file with no rows returns `rows: 0`.
