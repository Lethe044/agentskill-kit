#!/usr/bin/env python3
"""Decode a JWT without verifying it and flag common risks."""
import argparse
import base64
import json
import sys
from datetime import datetime, timezone

DAY = 86400


def b64json(part):
    padded = part + "=" * (-len(part) % 4)
    return json.loads(base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8"))


def stamp(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        return datetime.fromtimestamp(value, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (OverflowError, OSError, ValueError):
        return None


def parse_now(text):
    if text is None:
        return datetime.now(timezone.utc).timestamp()
    if text.isdigit():
        return float(text)
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()


def inspect(token, now):
    token = token.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("a JWT has three dot separated parts")
    try:
        header, payload = b64json(parts[0]), b64json(parts[1])
    except (ValueError, UnicodeError):
        raise ValueError("header or payload is not base64url encoded JSON")
    if not isinstance(header, dict) or not isinstance(payload, dict):
        raise ValueError("header and payload must be JSON objects")
    warnings = []
    alg = header.get("alg")
    if str(alg).lower() == "none":
        warnings.append("alg is none: the token is unsigned")
    if not parts[2]:
        warnings.append("the signature is empty")
    exp, iat, nbf = payload.get("exp"), payload.get("iat"), payload.get("nbf")
    expired = None
    if isinstance(exp, (int, float)) and not isinstance(exp, bool):
        expired = now >= exp
        if expired:
            warnings.append("the token is expired")
    else:
        warnings.append("no exp claim: the token never expires")
    if isinstance(nbf, (int, float)) and not isinstance(nbf, bool) and now < nbf:
        warnings.append("the token is not valid yet")
    lifetime = None
    if isinstance(exp, (int, float)) and isinstance(iat, (int, float)):
        lifetime = int(exp - iat)
        if lifetime > DAY:
            warnings.append("lifetime is longer than 24 hours")
    return {
        "header": header, "payload": payload, "alg": alg, "typ": header.get("typ"),
        "issued_at": stamp(iat), "not_before": stamp(nbf), "expires_at": stamp(exp),
        "expired": expired, "lifetime_seconds": lifetime, "warnings": warnings,
        "note": "signature not verified",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("token", nargs="?", help="the token (reads stdin when omitted)")
    parser.add_argument("--now", help="current time as epoch seconds or YYYY-MM-DDTHH:MM:SSZ")
    args = parser.parse_args(argv)
    token = args.token if args.token is not None else sys.stdin.read()
    try:
        result = inspect(token, parse_now(args.now))
    except ValueError as exc:
        print("not a valid JWT: %s" % exc, file=sys.stderr)
        return 3
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
