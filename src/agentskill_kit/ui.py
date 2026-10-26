"""Tiny terminal helpers: colours, tables and status lines (no dependencies)."""

from __future__ import annotations

import os
import sys
from typing import Iterable, List, Sequence

_FORCE_NO_COLOR = False


def set_no_color(value: bool = True) -> None:
    global _FORCE_NO_COLOR
    _FORCE_NO_COLOR = value


def color_enabled(stream=None) -> bool:
    if _FORCE_NO_COLOR or os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    stream = stream or sys.stdout
    return hasattr(stream, "isatty") and stream.isatty()


_CODES = {
    "red": "31", "green": "32", "yellow": "33", "blue": "34", "magenta": "35",
    "cyan": "36", "gray": "90", "bold": "1", "dim": "2",
}


def paint(text: str, *styles: str) -> str:
    if not color_enabled():
        return text
    codes = ";".join(_CODES[s] for s in styles if s in _CODES)
    return "\x1b[%sm%s\x1b[0m" % (codes, text) if codes else text


def enable_windows_ansi() -> None:
    if os.name == "nt":
        try:
            os.system("")  # turns on VT processing in recent consoles
        except Exception:
            pass


def setup_stdio() -> None:
    """Make output safe on consoles that are not UTF-8 by default."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass
    enable_windows_ansi()


def ok(msg: str) -> str:
    return "%s %s" % (paint("ok", "green", "bold"), msg)


def warn(msg: str) -> str:
    return "%s %s" % (paint("!!", "yellow", "bold"), msg)


def fail(msg: str) -> str:
    return "%s %s" % (paint("xx", "red", "bold"), msg)


def info(msg: str) -> str:
    return "%s %s" % (paint("--", "cyan"), msg)


def heading(msg: str) -> str:
    return paint(msg, "bold")


def table(rows: Sequence[Sequence[str]], headers: Sequence[str] = (), indent: int = 0) -> str:
    """Render a plain text table. Widths ignore colour codes."""
    import re
    ansi = re.compile(r"\x1b\[[0-9;]*m")

    def vlen(s: str) -> int:
        return len(ansi.sub("", s))

    all_rows: List[Sequence[str]] = ([tuple(headers)] if headers else []) + [tuple(r) for r in rows]
    if not all_rows:
        return ""
    cols = max(len(r) for r in all_rows)
    widths = [0] * cols
    for r in all_rows:
        for i, cell in enumerate(r):
            widths[i] = max(widths[i], vlen(str(cell)))
    pad = " " * indent
    lines = []
    for idx, r in enumerate(all_rows):
        cells = []
        for i in range(cols):
            cell = str(r[i]) if i < len(r) else ""
            cells.append(cell + " " * (widths[i] - vlen(cell)))
        line = pad + "  ".join(cells).rstrip()
        if headers and idx == 0:
            line = paint(line, "bold")
        lines.append(line)
        if headers and idx == 0:
            lines.append(pad + "  ".join("-" * w for w in widths))
    return "\n".join(lines)


def truncate(text: str, width: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= width else text[: max(0, width - 3)] + "..."
