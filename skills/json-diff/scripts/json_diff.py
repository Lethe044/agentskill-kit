#!/usr/bin/env python3
"""Structural diff of two JSON documents."""
import argparse
import json
import sys


def diff(old, new, path=""):
    changes = []
    if isinstance(old, dict) and isinstance(new, dict):
        for key in sorted(set(old) | set(new)):
            sub = "%s.%s" % (path, key) if path else str(key)
            if key not in old:
                changes.append({"path": sub, "change": "added", "new": new[key]})
            elif key not in new:
                changes.append({"path": sub, "change": "removed", "old": old[key]})
            else:
                changes.extend(diff(old[key], new[key], sub))
    elif isinstance(old, list) and isinstance(new, list):
        for i in range(max(len(old), len(new))):
            sub = "%s[%d]" % (path, i)
            if i >= len(old):
                changes.append({"path": sub, "change": "added", "new": new[i]})
            elif i >= len(new):
                changes.append({"path": sub, "change": "removed", "old": old[i]})
            else:
                changes.extend(diff(old[i], new[i], sub))
    elif old != new or type(old) is not type(new):
        changes.append({"path": path or "$", "change": "changed", "old": old, "new": new})
    return changes


def load(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except OSError:
        print("file not found: %s" % path, file=sys.stderr)
        sys.exit(2)
    except ValueError:
        print("invalid JSON in %s" % path, file=sys.stderr)
        sys.exit(3)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("old")
    parser.add_argument("new")
    args = parser.parse_args(argv)
    changes = diff(load(args.old), load(args.new))
    print(json.dumps({"identical": not changes, "count": len(changes), "changes": changes}))
    return 1 if changes else 0


if __name__ == "__main__":
    sys.exit(main())
