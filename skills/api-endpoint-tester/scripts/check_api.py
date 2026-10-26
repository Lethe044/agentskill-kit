#!/usr/bin/env python3
"""Run HTTP checks from a JSON file and report the results."""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request


def run_check(base_url, check):
    method = str(check.get("method", "GET")).upper()
    url = base_url.rstrip("/") + "/" + str(check.get("path", "")).lstrip("/")
    headers = dict(check.get("headers") or {})
    data = None
    if "json" in check:
        data = json.dumps(check["json"]).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    started = time.time()
    status, body, reason = None, "", ""
    try:
        with urllib.request.urlopen(request, timeout=float(check.get("timeout", 10))) as resp:
            status = resp.status
            body = resp.read(200000).decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        status = exc.code
        body = exc.read(200000).decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError) as exc:
        reason = "request failed: %s" % getattr(exc, "reason", exc)
    elapsed = int((time.time() - started) * 1000)
    if not reason:
        expected = int(check.get("expect_status", 200))
        if status != expected:
            reason = "expected status %d, got %d" % (expected, status)
        elif "expect_body_contains" in check and str(check["expect_body_contains"]) not in body:
            reason = "body does not contain %r" % check["expect_body_contains"]
    result = {"name": check.get("name") or "%s %s" % (method, check.get("path", "")), "ok": not reason,
              "status": status, "elapsed_ms": elapsed}
    if reason:
        result["reason"] = reason
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checks", help="JSON file with a list of checks")
    parser.add_argument("--base-url", required=True)
    args = parser.parse_args(argv)
    try:
        with open(args.checks, encoding="utf-8") as fh:
            checks = json.load(fh)
    except OSError:
        print("file not found: %s" % args.checks, file=sys.stderr)
        return 2
    except ValueError:
        print("invalid JSON in %s" % args.checks, file=sys.stderr)
        return 3
    if not isinstance(checks, list) or not all(isinstance(c, dict) and "path" in c for c in checks):
        print("checks must be a list of objects that each have a path", file=sys.stderr)
        return 3
    results = [run_check(args.base_url, c) for c in checks]
    failed = sum(1 for r in results if not r["ok"])
    print(json.dumps({"base_url": args.base_url, "passed": len(results) - failed, "failed": failed,
                      "results": results}))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
