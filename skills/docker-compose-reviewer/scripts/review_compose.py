#!/usr/bin/env python3
"""Review a docker-compose file for common problems."""
import argparse
import json
import re
import sys

SECRET_NAME = re.compile(r"(PASSWORD|PASSWD|SECRET|TOKEN|API[_-]?KEY|PRIVATE[_-]?KEY)", re.I)


def clean(value):
    return value.strip().strip("\"'")


def parse(text):
    """Return {service: {"line": n, "keys": {key: {"line", "value", "items"}}}}."""
    services = {}
    in_services = False
    current = None
    key = None
    for number, raw in enumerate(text.splitlines(), 1):
        if raw.lstrip().startswith("#"):
            continue
        line = raw.split(" #")[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        body = line.strip()
        if indent == 0:
            in_services = body.startswith("services:")
            current = key = None
            continue
        if not in_services:
            continue
        if indent == 2 and body.endswith(":") and not body.startswith("-"):
            current = clean(body[:-1])
            services[current] = {"line": number, "keys": {}}
            key = None
        elif current is None:
            continue
        elif indent == 4 and not body.startswith("-"):
            name, _, value = body.partition(":")
            key = name.strip()
            services[current]["keys"][key] = {"line": number, "value": clean(value), "items": []}
        elif indent > 4 and key:
            services[current]["keys"][key]["items"].append((number, clean(body.lstrip("- "))))
    return services


def review(text):
    services = parse(text)
    findings = []

    def add(service, line, rule, severity, message):
        findings.append({"service": service, "line": line, "rule": rule, "severity": severity, "message": message})

    for name, svc in services.items():
        keys = svc["keys"]
        image = keys.get("image")
        if image and "@sha256:" not in image["value"] and "${" not in image["value"]:
            last = image["value"].split("/")[-1]
            tag = last.split(":", 1)[1] if ":" in last else ""
            if tag in ("", "latest"):
                add(name, image["line"], "DC001", "warning", "image %s is not pinned to a version" % image["value"])
        if "privileged" in keys and keys["privileged"]["value"].lower() == "true":
            add(name, keys["privileged"]["line"], "DC002", "warning", "container runs privileged")
        for line, item in (keys.get("environment") or {}).get("items", []):
            var = re.split(r"[=:]", item, 1)[0].strip()
            value = item[len(var):].lstrip("=: ").strip()
            if SECRET_NAME.search(var) and value and not value.startswith("${"):
                add(name, line, "DC003", "warning", "%s has a literal value; use ${%s} from an env file" % (var, var))
        for line, item in (keys.get("ports") or {}).get("items", []):
            if re.match(r"^\d+(-\d+)?:\d+", item):
                add(name, line, "DC004", "info", "port %s is published on all interfaces" % item.split(":")[0])
        for line, item in (keys.get("volumes") or {}).get("items", []):
            if "/var/run/docker.sock" in item:
                add(name, line, "DC005", "warning", "the Docker socket is mounted into the container")
        net = keys.get("network_mode")
        if net and net["value"] == "host":
            add(name, net["line"], "DC008", "warning", "network_mode host removes network isolation")
        if "restart" not in keys:
            add(name, svc["line"], "DC006", "info", "no restart policy")
        if "healthcheck" not in keys:
            add(name, svc["line"], "DC007", "info", "no healthcheck")
    findings.sort(key=lambda f: (f["line"], f["rule"]))
    return len(services), findings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", help="path to a compose file")
    args = parser.parse_args(argv)
    try:
        with open(args.file, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        print("file not found: %s" % args.file, file=sys.stderr)
        return 2
    count, findings = review(text)
    print(json.dumps({"services": count, "findings": findings}))
    return 1 if any(f["severity"] == "warning" for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
