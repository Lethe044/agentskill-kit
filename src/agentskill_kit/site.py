"""Render the registry web page (static file, used by `registry site` and `serve`)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

TEMPLATE = Path(__file__).with_name("templates") / "site.html"


def render_site(index: Dict[str, Any], title: str = "agentskill-kit skill registry") -> str:
    html = TEMPLATE.read_text(encoding="utf-8")
    data = json.dumps(index, ensure_ascii=False).replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    return html.replace("__TITLE__", title.replace("<", "&lt;")).replace("__DATA__", data)


def write_site(index: Dict[str, Any], out_dir: Any, title: str = "agentskill-kit skill registry") -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(render_site(index, title), encoding="utf-8")
    (out / "index.json").write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    return out / "index.html"
