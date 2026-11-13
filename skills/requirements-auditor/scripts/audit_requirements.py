#!/usr/bin/env python3
"""Audit a requirements.txt file for reproducibility and supply chain problems."""
import argparse
import json
import re
import sys

NAME_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[[^\]]*\])?\s*(.*)$")


def normalize(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def audit(text):
    findings = []
    seen = {}
    count = 0

    def add(line, rule, severity, name, message):
        findings.append({"line": line, "rule": rule, "severity": severity, "name": name, "message": message})

    for number, raw in enumerate(text.splitlines(), 1):
        line = re.sub(r"\s+#.*$", "", raw.strip())
        if not line or line.startswith("#"):
            continue
        if line.startswith(("-r", "-c", "--requirement", "--constraint")):
            continue
        if line.startswith("--extra-index-url"):
            add(number, "RQ005", "warning", "--extra-index-url", "extra index can shadow private package names")
            continue
        if line.startswith("--trusted-host"):
            add(number, "RQ006", "warning", "--trusted-host", "TLS verification is disabled for this host")
            continue
        if line.startswith("-") and not line.startswith(("-e", "--editable")):
            continue
        count += 1
        if line.startswith(("-e", "--editable")) or re.match(r"^(git\+|hg\+|svn\+|https?://)", line) or " @ " in line:
            if "@" not in line.replace(" @ ", "", 1) and not re.search(r"@[0-9a-fA-F]{7,40}\b", line):
                add(number, "RQ004", "warning", line[:60], "URL or VCS install is not pinned to a commit or tag")
            continue
        spec_line = line.split(";", 1)[0].strip()
        match = NAME_RE.match(spec_line)
        if not match:
            continue
        name, spec = match.group(1), match.group(2).strip()
        key = normalize(name)
        if key in seen:
            add(number, "RQ003", "warning", name, "already listed on line %d" % seen[key])
        else:
            seen[key] = number
        if not spec:
            add(number, "RQ001", "warning", name, "no version specifier")
        elif "==" in spec and not spec.endswith(".*"):
            continue
        elif not re.search(r"(~=|<=|<|!=)", spec):
            add(number, "RQ002", "info", name, "upper bound is open (%s)" % spec)
    findings.sort(key=lambda f: (f["line"], f["rule"]))
    return count, findings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", help="path to requirements.txt")
    args = parser.parse_args(argv)
    try:
        with open(args.file, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        print("file not found: %s" % args.file, file=sys.stderr)
        return 2
    count, findings = audit(text)
    print(json.dumps({"requirements": count, "findings": findings}))
    return 1 if any(f["severity"] == "warning" for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
