"""Local web UI for browsing the skills on this machine."""

from __future__ import annotations

import json
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from . import registry
from .site import render_site


def default_roots() -> List[Path]:
    cwd = Path.cwd()
    cands = [cwd / "skills", cwd / ".claude" / "skills", cwd / ".hermes" / "skills",
             Path.home() / ".claude" / "skills", Path.home() / ".hermes" / "skills"]
    out, seen = [], set()
    for c in cands:
        if c.is_dir() and str(c.resolve()) not in seen:
            out.append(c)
            seen.add(str(c.resolve()))
    return out


def make_handler(build: Callable[[], Dict[str, Any]]):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # keep the terminal quiet
            return

        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path in ("/", "/index.html"):
                self._send(200, render_site(build(), "Local skills").encode("utf-8"), "text/html; charset=utf-8")
            elif path == "/index.json":
                self._send(200, json.dumps(build(), ensure_ascii=False).encode("utf-8"), "application/json")
            else:
                self._send(404, b"not found", "text/plain; charset=utf-8")

    return Handler


def serve(roots: List[Path], host: str = "127.0.0.1", port: int = 8765, open_browser: bool = False,
          on_ready: Optional[Callable[[str], None]] = None) -> None:
    def build() -> Dict[str, Any]:
        return registry.build_index(roots, name="local skills", run_tests=False, relative_to=Path.cwd())

    server = ThreadingHTTPServer((host, port), make_handler(build))
    url = "http://%s:%d/" % (host, server.server_address[1])
    if on_ready:
        on_ready(url)
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
