#!/usr/bin/env python3
"""Lint a Dockerfile for common mistakes."""
import argparse
import json
import re
import sys

SECRET_NAME = re.compile(r"(PASSWORD|PASSWD|SECRET|TOKEN|API[_-]?KEY|PRIVATE[_-]?KEY)", re.I)


def logical_lines(text):
    """Join continuation lines. Yields (line_number, instruction_text)."""
    buf, start = "", 0
    for number, raw in enumerate(text.splitlines(), 1):
        stripped = raw.strip()
        if not buf and (not stripped or stripped.startswith("#")):
            continue
        if not buf:
            start = number
        if stripped.endswith("\\"):
            buf += stripped[:-1] + " "
            continue
        buf += stripped
        yield start, buf
        buf = ""
    if buf:
        yield start, buf


def lint(text):
    findings = []
    count = 0
    has_user = False
    has_health = False
    stages = []

    def add(line, rule, severity, message):
        findings.append({"line": line, "rule": rule, "severity": severity, "message": message})

    for number, line in logical_lines(text):
        count += 1
        keyword, _, rest = line.partition(" ")
        keyword = keyword.upper()
        rest = rest.strip()
        if keyword == "FROM":
            parts = [p for p in rest.split() if not p.startswith("--")]
            image = parts[0] if parts else ""
            is_stage_ref = image in stages
            if len(parts) >= 3 and parts[1].lower() == "as":
                stages.append(parts[2])
            if image != "scratch" and not is_stage_ref:
                tag = image.split("@")[0].rsplit(":", 1)[1] if ":" in image.split("@")[0].rsplit("/", 1)[-1] else ""
                if "@" not in image and (tag in ("", "latest")):
                    add(number, "DF001", "warning", "base image %s is not pinned to a version" % image)
        elif keyword == "USER":
            has_user = rest.lower() not in ("root", "0")
        elif keyword == "HEALTHCHECK":
            has_health = rest.upper() != "NONE"
        elif keyword == "ADD" and not re.search(r"https?://|\.(tar|tgz|gz|xz|bz2|zip)\b", rest):
            add(number, "DF003", "warning", "use COPY instead of ADD for plain files")
        elif keyword in ("ENV", "ARG"):
            name = re.split(r"[ =]", rest, 1)[0]
            if SECRET_NAME.search(name):
                add(number, "DF006", "warning", "%s %s may bake a secret into the image" % (keyword, name))
        elif keyword == "RUN":
            if "apt-get install" in rest and "--no-install-recommends" not in rest:
                add(number, "DF004", "warning", "apt-get install without --no-install-recommends")
            if "apt-get update" in rest and "/var/lib/apt/lists" not in rest:
                add(number, "DF005", "warning", "remove /var/lib/apt/lists in the same RUN to keep the layer small")
            if re.search(r"\bsudo\b", rest):
                add(number, "DF007", "warning", "sudo is not needed inside an image build")
    if count and not has_user:
        add(1, "DF002", "warning", "no USER instruction, the container runs as root")
    if count and not has_health:
        add(1, "DF008", "info", "no HEALTHCHECK defined")
    findings.sort(key=lambda f: (f["line"], f["rule"]))
    return count, findings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", help="path to a Dockerfile")
    args = parser.parse_args(argv)
    try:
        with open(args.file, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        print("file not found: %s" % args.file, file=sys.stderr)
        return 2
    count, findings = lint(text)
    print(json.dumps({"instructions": count, "findings": findings}))
    return 1 if any(f["severity"] == "warning" for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
