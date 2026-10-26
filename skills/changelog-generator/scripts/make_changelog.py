#!/usr/bin/env python3
"""Build a markdown changelog from `git log --pretty=format:'%h|%s'` lines."""
import argparse
import re
import sys

SECTIONS = [
    ("breaking", "Breaking changes"), ("feat", "Features"), ("fix", "Fixes"), ("perf", "Performance"),
    ("docs", "Documentation"), ("refactor", "Refactoring"), ("test", "Tests"), ("build", "Build and CI"),
    ("other", "Other"),
]
ALIASES = {"feature": "feat", "bugfix": "fix", "doc": "docs", "tests": "test", "ci": "build", "chore": "other",
           "style": "other", "revert": "other"}
LINE_RE = re.compile(r"^(?P<type>[a-zA-Z]+)(?:\((?P<scope>[^)]+)\))?(?P<bang>!)?:\s*(?P<subject>.+)$")


def classify(subject):
    m = LINE_RE.match(subject)
    if not m:
        return "other", "", subject.strip(), "BREAKING CHANGE" in subject
    kind = m.group("type").lower()
    kind = ALIASES.get(kind, kind)
    if kind not in dict(SECTIONS):
        kind = "other"
    return kind, m.group("scope") or "", m.group("subject").strip(), bool(m.group("bang")) or "BREAKING CHANGE" in subject


def build(lines, title="Changelog"):
    groups = {key: [] for key, _ in SECTIONS}
    count = 0
    for raw in lines:
        if "|" not in raw:
            continue
        sha, _, subject = raw.strip().partition("|")
        if not subject.strip():
            continue
        count += 1
        kind, scope, text, breaking = classify(subject.strip())
        entry = "- %s%s (%s)" % ("**%s:** " % scope if scope else "", text, sha.strip())
        groups["breaking" if breaking else kind].append(entry)
    out = ["# %s" % title, ""]
    if not count:
        out.append("No commits found.")
        return "\n".join(out) + "\n"
    for key, heading in SECTIONS:
        if groups[key]:
            out.append("## %s" % heading)
            out.extend(groups[key])
            out.append("")
    return "\n".join(out).rstrip() + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title", default="Changelog")
    args = parser.parse_args(argv)
    sys.stdout.write(build(sys.stdin.read().splitlines(), args.title))
    return 0


if __name__ == "__main__":
    sys.exit(main())
