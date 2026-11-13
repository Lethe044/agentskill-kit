#!/usr/bin/env python3
"""Explain a five field cron expression in plain English."""
import argparse
import json
import re
import sys

MACROS = {
    "@yearly": "0 0 1 1 *", "@annually": "0 0 1 1 *", "@monthly": "0 0 1 * *", "@weekly": "0 0 * * 0",
    "@daily": "0 0 * * *", "@midnight": "0 0 * * *", "@hourly": "0 * * * *",
}
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
LIMITS = [("minute", 0, 59), ("hour", 0, 23), ("day-of-month", 1, 31), ("month", 1, 12), ("day-of-week", 0, 7)]
DAYS_IN_MONTH = {1: 31, 2: 29, 3: 31, 4: 30, 5: 31, 6: 30, 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}


class CronError(Exception):
    pass


def to_number(token, index):
    token = token.lower()
    if index == 3 and token[:3] in [m[:3].lower() for m in MONTHS] and len(token) == 3:
        return [m[:3].lower() for m in MONTHS].index(token) + 1
    if index == 4 and token[:3] in [d[:3].lower() for d in DAYS] and len(token) == 3:
        return [d[:3].lower() for d in DAYS].index(token)
    if not token.isdigit():
        raise CronError("invalid value %r in the %s field" % (token, LIMITS[index][0]))
    return int(token)


def validate(field, index):
    unit, low, high = LIMITS[index]
    for part in field.split(","):
        base, _, step = part.partition("/")
        if step and (not step.isdigit() or int(step) == 0):
            raise CronError("invalid step %r in the %s field" % (step, unit))
        if base == "*":
            continue
        ends = base.split("-")
        if len(ends) > 2:
            raise CronError("invalid range %r in the %s field" % (base, unit))
        nums = [to_number(e, index) for e in ends]
        if any(n < low or n > high for n in nums):
            raise CronError("%s value out of range (%d-%d): %s" % (unit, low, high, base))
        if len(nums) == 2 and nums[0] > nums[1]:
            raise CronError("range starts after it ends in the %s field: %s" % (unit, base))


def label(token, index):
    n = to_number(token, index)
    if index == 3:
        return MONTHS[n - 1]
    if index == 4:
        return DAYS[n % 7]
    return str(n)


def join_words(items):
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def describe(field, index):
    unit = LIMITS[index][0]
    parts = []
    for part in field.split(","):
        base, _, step = part.partition("/")
        if base == "*":
            parts.append("every %s %ss" % (step, unit) if step else "every %s" % unit)
        elif "-" in base:
            lo, hi = base.split("-")
            text = "%s through %s" % (label(lo, index), label(hi, index))
            parts.append("every %s %ss from %s" % (step, unit, text) if step else text)
        else:
            parts.append(label(base, index))
    return join_words(parts)


def is_number(value):
    return value.isdigit()


def time_part(minute, hour):
    if is_number(minute) and is_number(hour):
        return "At %02d:%02d" % (int(hour), int(minute))
    if minute == "*" and hour == "*":
        return "Every minute"
    if minute.startswith("*/") and hour == "*" and "," not in minute:
        return "Every %s minutes" % minute[2:]
    if is_number(minute) and hour == "*":
        return "At minute %s of every hour" % minute
    if is_number(minute) and hour.startswith("*/") and "," not in hour:
        return "At minute %s, every %s hours" % (minute, hour[2:])
    return "At minute %s past hour %s" % (describe(minute, 0), describe(hour, 1))


def explain(expression):
    expression = expression.strip()
    if expression.lower() in MACROS:
        expression = MACROS[expression.lower()]
    elif expression.startswith("@"):
        raise CronError("unknown macro %s" % expression)
    fields = expression.split()
    if len(fields) != 5:
        raise CronError("a cron expression needs 5 fields (minute hour day-of-month month day-of-week), got %d" % len(fields))
    for index, field in enumerate(fields):
        validate(field, index)
    minute, hour, dom, month, dow = fields
    parts = []
    if dom != "*":
        parts.append("on day-of-month %s" % describe(dom, 2))
    if month != "*":
        parts.append("in %s" % describe(month, 3))
    if dow != "*":
        parts.append("on %s" % describe(dow, 4))
    text = "%s, %s" % (time_part(minute, hour), ", ".join(parts) if parts else "every day")
    warnings = []
    if is_number(dom) and is_number(month) and int(dom) > DAYS_IN_MONTH[int(month)] and dow == "*":
        warnings.append("this schedule never runs: %s has no day %s" % (MONTHS[int(month) - 1], dom))
    if dom != "*" and dow != "*":
        warnings.append("day-of-month and day-of-week are both set: classic cron runs on either match")
    return {"expression": expression, "expanded": fields, "description": text, "warnings": warnings}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("expression", nargs="+", help="cron expression, quoted or as separate words")
    args = parser.parse_args(argv)
    try:
        result = explain(" ".join(args.expression))
    except CronError as exc:
        print("invalid cron expression: %s" % exc, file=sys.stderr)
        return 2
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
