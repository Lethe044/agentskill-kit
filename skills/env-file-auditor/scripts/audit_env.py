#!/usr/bin/env python3
"""Compare a .env file with .env.example without printing secret values."""
import argparse
import json
import re
import sys

SECRET_NAME = re.compile(r"(KEY|SECRET|TOKEN|PASSWORD|PASSWD|PRIVATE)", re.I)
PLACEHOLDER = re.compile(r"(changeme|change_me|your|example|placeholder|xxx|<.*>|replace|dummy|sample)", re.I)


def parse_env(text):
    values = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[7:]
        key, _, value = line.partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].strip()
        values[key.strip()] = value
    return values


def looks_secret(key, value):
    if not SECRET_NAME.search(key) or len(value) < 16 or PLACEHOLDER.search(value):
        return False
    classes = sum(bool(re.search(p, value)) for p in (r"[a-z]", r"[A-Z]", r"\d"))
    return classes >= 2


def audit(real, template):
    return {
        "missing": sorted(k for k in template if k not in real),
        "extra": sorted(k for k in real if k not in template),
        "empty": sorted(k for k, v in real.items() if v == ""),
        "suspicious_example_keys": sorted(k for k, v in template.items() if looks_secret(k, v)),
    }


def read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return parse_env(fh.read())
    except OSError:
        print("file not found: %s" % path, file=sys.stderr)
        sys.exit(2)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("env_file")
    parser.add_argument("example_file")
    args = parser.parse_args(argv)
    result = audit(read(args.env_file), read(args.example_file))
    print(json.dumps(result))
    return 1 if any(result.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
