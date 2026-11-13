#!/usr/bin/env python3
"""Summarize an OpenAPI 3 or Swagger 2 JSON document."""
import argparse
import json
import sys

METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace")


def servers_of(doc):
    if doc.get("servers"):
        return [str(s.get("url", "")) for s in doc["servers"] if isinstance(s, dict)]
    if doc.get("host"):
        scheme = (doc.get("schemes") or ["https"])[0]
        return ["%s://%s%s" % (scheme, doc["host"], doc.get("basePath", ""))]
    return []


def summarize(doc):
    spec = doc.get("openapi") or doc.get("swagger") if isinstance(doc, dict) else None
    if not spec:
        raise ValueError("not an OpenAPI or Swagger document")
    global_security = bool(doc.get("security"))
    endpoints, by_tag = [], {}
    for path, item in sorted((doc.get("paths") or {}).items()):
        if not isinstance(item, dict):
            continue
        for method in METHODS:
            op = item.get(method)
            if not isinstance(op, dict):
                continue
            tags = op.get("tags") or ["untagged"]
            secured = bool(op["security"]) if "security" in op else global_security
            endpoints.append({"method": method.upper(), "path": path, "summary": op.get("summary", ""),
                              "tags": tags, "secured": secured, "deprecated": bool(op.get("deprecated"))})
            for tag in tags:
                by_tag[tag] = by_tag.get(tag, 0) + 1
    schemas = (doc.get("components") or {}).get("schemas") or doc.get("definitions") or {}
    info = doc.get("info") or {}
    return {
        "title": info.get("title", ""),
        "version": str(info.get("version", "")),
        "spec": str(spec),
        "servers": servers_of(doc),
        "operations": len(endpoints),
        "deprecated": sum(1 for e in endpoints if e["deprecated"]),
        "unsecured": sum(1 for e in endpoints if not e["secured"]),
        "by_tag": by_tag,
        "schemas": len(schemas),
        "endpoints": endpoints,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", help="OpenAPI or Swagger JSON file")
    args = parser.parse_args(argv)
    try:
        with open(args.file, encoding="utf-8") as fh:
            doc = json.load(fh)
    except OSError:
        print("file not found: %s" % args.file, file=sys.stderr)
        return 2
    except ValueError:
        print("invalid JSON in %s" % args.file, file=sys.stderr)
        return 3
    try:
        result = summarize(doc)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 3
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
