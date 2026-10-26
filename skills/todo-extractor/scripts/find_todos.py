#!/usr/bin/env python3
"""List TODO style comments in a source tree."""
import argparse
import json
import os
import re
import sys

SKIP_DIRS = {"node_modules", "venv", "dist", "build", "__pycache__", "target", "vendor"}
BINARY_EXT = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".gz", ".tar", ".so", ".dll",
              ".exe", ".pyc", ".woff", ".woff2", ".ttf", ".mp4", ".mov", ".jar", ".lock"}


def scan_text(text, filename, tags):
    pattern = re.compile(r"(?:#|//|/\*|\*|--|<!--|;)\s*\b(%s)\b[:(\s-]*(.*)" % "|".join(map(re.escape, tags)))
    items = []
    for number, line in enumerate(text.splitlines(), 1):
        m = pattern.search(line)
        if m:
            note = re.sub(r"(\*/|-->)\s*$", "", m.group(2)).strip()
            items.append({"file": filename, "line": number, "tag": m.group(1), "text": note})
    return items


def walk(path):
    if os.path.isfile(path):
        yield path
        return
    for root, dirs, files in os.walk(path):
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in SKIP_DIRS)
        for name in sorted(files):
            if os.path.splitext(name)[1].lower() not in BINARY_EXT:
                yield os.path.join(root, name)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", default=".")
    parser.add_argument("--tags", default="TODO,FIXME,HACK,XXX", help="comma separated tags")
    args = parser.parse_args(argv)
    if not os.path.exists(args.path):
        print("path not found: %s" % args.path, file=sys.stderr)
        return 2
    tags = [t.strip().upper() for t in args.tags.split(",") if t.strip()]
    items = []
    for file_path in walk(args.path):
        try:
            with open(file_path, encoding="utf-8") as fh:
                text = fh.read()
        except (OSError, UnicodeDecodeError):
            continue
        items.extend(scan_text(text, file_path.replace(os.sep, "/"), tags))
    by_tag = {}
    for item in items:
        by_tag[item["tag"]] = by_tag.get(item["tag"], 0) + 1
    print(json.dumps({"total": len(items), "by_tag": by_tag, "items": items}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
