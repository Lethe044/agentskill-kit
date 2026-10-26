#!/usr/bin/env python3
"""Summarize a log file: severity counts, time range and frequent errors."""
import argparse
import json
import re
import sys
from collections import Counter

LEVELS = ["CRITICAL", "FATAL", "ERROR", "WARNING", "WARN", "INFO", "DEBUG", "TRACE"]
LEVEL_RE = re.compile(r"\b(" + "|".join(LEVELS) + r")\b")
TS_RE = re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?")
CANONICAL = {"FATAL": "CRITICAL", "WARNING": "WARN", "TRACE": "DEBUG"}


def normalize(message):
    message = re.sub(r"0x[0-9a-fA-F]+", "<hex>", message)
    message = re.sub(r"\b[0-9a-f]{8}-[0-9a-f-]{27}\b", "<uuid>", message)
    message = re.sub(r"\"[^\"]*\"|'[^']*'", "<str>", message)
    message = re.sub(r"\d+", "<n>", message)
    return message.strip()


def analyze(text, top=5):
    levels = Counter()
    errors = Counter()
    stamps = []
    lines = text.splitlines()
    for line in lines:
        ts = TS_RE.search(line)
        if ts:
            stamps.append(ts.group(0).replace(",", "."))
        m = LEVEL_RE.search(line)
        if not m:
            continue
        level = CANONICAL.get(m.group(1), m.group(1))
        levels[level] += 1
        if level in ("ERROR", "CRITICAL"):
            message = line[m.end():].lstrip(" :-]|")
            if message:
                errors[normalize(message)] += 1
    stamps.sort()
    return {
        "total_lines": len(lines),
        "levels": dict(levels),
        "first_timestamp": stamps[0] if stamps else None,
        "last_timestamp": stamps[-1] if stamps else None,
        "top_errors": [{"message": m, "count": c} for m, c in errors.most_common(top)],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", nargs="?", help="log file (reads stdin when omitted)")
    parser.add_argument("--top", type=int, default=5, help="number of frequent errors to list")
    args = parser.parse_args(argv)
    if args.file:
        try:
            with open(args.file, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            print("file not found: %s" % args.file, file=sys.stderr)
            return 2
    else:
        text = sys.stdin.read()
    print(json.dumps(analyze(text, args.top)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
