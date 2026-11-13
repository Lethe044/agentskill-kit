#!/usr/bin/env python3
"""Check relative links and heading anchors in Markdown files."""
import argparse
import json
import os
import re
import sys
from urllib.parse import unquote

LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
HEADING_RE = re.compile(r"^#{1,6}\s+(.*?)\s*#*\s*$")
SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:|^//")
SKIP_DIRS = {"node_modules", "venv", "dist", "build", "__pycache__"}


def slugify(heading):
    text = re.sub(r"[`*_~]", "", heading).strip().lower()
    text = re.sub(r"[^\w\- ]", "", text, flags=re.UNICODE)
    return text.replace(" ", "-")


def strip_code(text):
    """Return (lines without code, headings) with fenced blocks and inline code blanked."""
    lines, in_fence = [], False
    for raw in text.splitlines():
        if raw.lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
            lines.append("")
        elif in_fence:
            lines.append("")
        else:
            lines.append(re.sub(r"`[^`]*`", "", raw))
    return lines


def anchors_of(lines):
    seen, out = {}, set()
    for raw in lines:
        m = HEADING_RE.match(raw)
        if not m:
            continue
        slug = slugify(m.group(1))
        count = seen.get(slug, 0)
        out.add(slug if count == 0 else "%s-%d" % (slug, count))
        seen[slug] = count + 1
    return out


def collect(paths):
    for path in paths:
        if os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in SKIP_DIRS)
                for name in sorted(files):
                    if name.lower().endswith(".md"):
                        yield os.path.join(root, name)
        else:
            yield path


def check(paths):
    cache = {}

    def load(path):
        if path not in cache:
            with open(path, encoding="utf-8", errors="replace") as fh:
                lines = strip_code(fh.read())
            cache[path] = (lines, anchors_of(lines))
        return cache[path]

    broken, checked, files = [], 0, 0
    for path in collect(paths):
        files += 1
        shown = os.path.relpath(path).replace(os.sep, "/")
        lines, own_anchors = load(path)
        for number, line in enumerate(lines, 1):
            for target in LINK_RE.findall(line):
                if SCHEME_RE.match(target):
                    continue
                checked += 1
                file_part, _, anchor = target.partition("#")
                file_part = unquote(file_part.split("?", 1)[0])
                anchor = unquote(anchor).lower()
                if file_part:
                    full = os.path.normpath(os.path.join(os.path.dirname(path), file_part))
                    if not os.path.exists(full):
                        broken.append({"file": shown, "line": number, "target": target, "reason": "file not found"})
                        continue
                    anchors = load(full)[1] if anchor and full.lower().endswith(".md") and os.path.isfile(full) else None
                else:
                    anchors = own_anchors if anchor else None
                if anchor and anchors is not None and anchor not in anchors:
                    broken.append({"file": shown, "line": number, "target": target, "reason": "anchor not found"})
    return files, checked, broken


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="Markdown files or directories")
    args = parser.parse_args(argv)
    for p in args.paths:
        if not os.path.exists(p):
            print("path not found: %s" % p, file=sys.stderr)
            return 2
    files, checked, broken = check(args.paths)
    print(json.dumps({"files": files, "links_checked": checked, "broken": broken}))
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
