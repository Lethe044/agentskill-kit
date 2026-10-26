#!/usr/bin/env python3
"""Report common Python code smells using the ast module."""
import argparse
import ast
import json
import os
import sys

SKIP_DIRS = {"__pycache__", "node_modules", "venv", "build", "dist"}


def iter_files(paths):
    for path in paths:
        if os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in SKIP_DIRS)
                for name in sorted(files):
                    if name.endswith(".py"):
                        yield os.path.join(root, name)
        else:
            yield path


def check_source(source, filename, max_lines=50, max_args=6):
    try:
        tree = ast.parse(source, filename)
    except SyntaxError as exc:
        return [{"file": filename, "line": exc.lineno or 1, "rule": "syntax-error", "message": str(exc.msg)}]
    findings = []

    def add(node, rule, message):
        findings.append({"file": filename, "line": node.lineno, "rule": rule, "message": message})

    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            add(node, "bare-except", "bare except hides unexpected errors; catch a specific exception")
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defaults = list(node.args.defaults) + [d for d in node.args.kw_defaults if d is not None]
            for default in defaults:
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    add(default, "mutable-default", "mutable default argument in %s()" % node.name)
            count = len(node.args.args) + len(node.args.kwonlyargs) + len(node.args.posonlyargs)
            if count and node.args.args and node.args.args[0].arg in ("self", "cls"):
                count -= 1
            if count > max_args:
                add(node, "too-many-args", "%s() takes %d parameters" % (node.name, count))
            end = getattr(node, "end_lineno", node.lineno)
            if end - node.lineno + 1 > max_lines:
                add(node, "long-function", "%s() is %d lines long" % (node.name, end - node.lineno + 1))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not node.name.startswith("_") and ast.get_docstring(node) is None:
                add(node, "missing-docstring", "public %s %s has no docstring" % (
                    "class" if isinstance(node, ast.ClassDef) else "function", node.name))
    findings.sort(key=lambda f: (f["line"], f["rule"]))
    return findings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="files or directories")
    parser.add_argument("--max-lines", type=int, default=50)
    parser.add_argument("--max-args", type=int, default=6)
    args = parser.parse_args(argv)
    for p in args.paths:
        if not os.path.exists(p):
            print("path not found: %s" % p, file=sys.stderr)
            return 2
    findings = []
    count = 0
    for path in iter_files(args.paths):
        count += 1
        with open(path, encoding="utf-8", errors="replace") as fh:
            findings.extend(check_source(fh.read(), path.replace(os.sep, "/"), args.max_lines, args.max_args))
    print(json.dumps({"files": count, "findings": findings}))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
