"""Paths, user configuration and a tiny .env loader."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_REPO = "Lethe044/agentskill-kit"
DEFAULT_BRANCH = "main"
RAW_BASE = "https://raw.githubusercontent.com/%s/%s/" % (DEFAULT_REPO, DEFAULT_BRANCH)
DEFAULT_REGISTRY = RAW_BASE + "registry/index.json"
DEFAULT_THRESHOLD = 0.8

CONFIG_KEYS = {
    "provider": "Default LLM provider (ollama, groq, gemini, openrouter, ...)",
    "model": "Default model name for the provider",
    "base_url": "Override the provider base URL",
    "lang": "Interface language (en or tr)",
    "registry": "Registry index URL or local path",
    "threshold": "Minimum quality score (0-1) to accept a forged skill",
    "max_rounds": "Maximum refinement rounds for forge",
    "output_dir": "Default directory for forged skills",
}


def home_dir() -> Path:
    """Directory for config, memory and the install ledger."""
    env = os.environ.get("ASKIT_HOME")
    p = Path(env).expanduser() if env else Path.home() / ".agentskill-kit"
    p.mkdir(parents=True, exist_ok=True)
    return p


def config_path() -> Path:
    return home_dir() / "config.json"


def load_config() -> Dict[str, Any]:
    p = config_path()
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_config(data: Dict[str, Any]) -> None:
    config_path().write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def get_setting(key: str, default: Any = None) -> Any:
    env = os.environ.get("ASKIT_" + key.upper())
    if env:
        return env
    return load_config().get(key, default)


def set_setting(key: str, value: Any) -> None:
    if key not in CONFIG_KEYS:
        raise KeyError(key)
    cfg = load_config()
    if value is None or value == "":
        cfg.pop(key, None)
    else:
        cfg[key] = value
    save_config(cfg)


def memory_path() -> Path:
    return home_dir() / "memory.jsonl"


def ledger_path() -> Path:
    return home_dir() / "installed.json"


def load_dotenv(path: Optional[Path] = None) -> int:
    """Load KEY=VALUE pairs from .env into os.environ without overriding."""
    p = path or Path.cwd() / ".env"
    if not p.is_file():
        return 0
    count = 0
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.startswith("export "):
                line = line[7:]
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
                val = val[1:-1]
            if key and key not in os.environ:
                os.environ[key] = val
                count += 1
    except (OSError, UnicodeDecodeError):
        return count
    return count
