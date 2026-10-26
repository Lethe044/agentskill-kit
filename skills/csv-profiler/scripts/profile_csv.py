#!/usr/bin/env python3
"""Profile the columns of a CSV file."""
import argparse
import csv
import json
import re
import sys

MISSING = {"", "na", "n/a", "nan", "null", "none", "-"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?)?$|^\d{1,2}/\d{1,2}/\d{2,4}$")


def classify(value):
    low = value.strip().lower()
    if low in ("true", "false", "yes", "no"):
        return "boolean"
    try:
        int(value)
        return "integer"
    except ValueError:
        pass
    try:
        float(value)
        return "float"
    except ValueError:
        pass
    return "date" if DATE_RE.match(value.strip()) else "string"


def profile(rows, header):
    result = []
    for idx, name in enumerate(header):
        values = [r[idx] if idx < len(r) else "" for r in rows]
        present = [v for v in values if v.strip().lower() not in MISSING]
        kinds = {classify(v) for v in present}
        if not present:
            kind = "empty"
        elif kinds <= {"integer"}:
            kind = "integer"
        elif kinds <= {"integer", "float"}:
            kind = "float"
        elif len(kinds) == 1:
            kind = next(iter(kinds))
        else:
            kind = "string"
        entry = {"name": name, "type": kind, "missing": len(values) - len(present),
                 "unique": len(set(present)), "sample": present[:3]}
        if kind in ("integer", "float"):
            nums = [float(v) for v in present]
            entry.update({"min": min(nums), "max": max(nums), "mean": round(sum(nums) / len(nums), 4)})
        result.append(entry)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file")
    parser.add_argument("--delimiter", help="field delimiter, or the word 'tab' (auto detected by default)")
    args = parser.parse_args(argv)
    try:
        with open(args.file, newline="", encoding="utf-8-sig", errors="replace") as fh:
            text = fh.read()
    except OSError:
        print("file not found: %s" % args.file, file=sys.stderr)
        return 2
    delimiter = None
    if args.delimiter:
        delimiter = "\t" if args.delimiter == "tab" else args.delimiter
    elif text.strip():
        try:
            delimiter = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|").delimiter
        except csv.Error:
            delimiter = ","
    parsed = list(csv.reader(text.splitlines(), delimiter=delimiter or ","))
    if not parsed:
        print(json.dumps({"rows": 0, "columns": 0, "profile": []}))
        return 0
    header, rows = parsed[0], parsed[1:]
    print(json.dumps({"rows": len(rows), "columns": len(header), "profile": profile(rows, header)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
