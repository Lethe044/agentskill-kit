"""LLM access through plain HTTP. No SDKs, no extra dependencies.

Free options come first: Ollama (local), Groq, Gemini and OpenRouter all offer
a free tier or free models. Paid keys for OpenAI or Anthropic are optional and
work the same way. Anything that speaks the OpenAI chat completions protocol
can be used through the ``custom`` provider.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .config import get_setting

USER_AGENT = "agentskill-kit (+https://github.com/Lethe044/agentskill-kit)"
RETRY_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}


class ProviderError(Exception):
    """Raised for configuration problems and failed API calls."""


@dataclass
class ProviderSpec:
    name: str
    label: str
    base_url: str
    key_env: str = ""
    default_model: str = ""
    free: bool = True
    kind: str = "openai"  # openai | anthropic | mock
    note: str = ""
    extra_key_envs: tuple = ()
    signup: str = ""


PROVIDERS: Dict[str, ProviderSpec] = {
    "ollama": ProviderSpec("ollama", "Ollama (local)", "http://localhost:11434/v1", "", "",
                           True, note="Runs on your machine. No key, no limits.",
                           signup="https://ollama.com/download"),
    "lmstudio": ProviderSpec("lmstudio", "LM Studio (local)", "http://localhost:1234/v1", "", "",
                             True, note="Start the local server in LM Studio first.",
                             signup="https://lmstudio.ai"),
    "groq": ProviderSpec("groq", "Groq (free tier)", "https://api.groq.com/openai/v1", "GROQ_API_KEY",
                         "llama-3.3-70b-versatile", True, note="Fast hosted open models, generous free tier.",
                         signup="https://console.groq.com/keys"),
    "gemini": ProviderSpec("gemini", "Google Gemini (free tier)",
                           "https://generativelanguage.googleapis.com/v1beta/openai", "GEMINI_API_KEY",
                           "gemini-2.5-flash", True, extra_key_envs=("GOOGLE_API_KEY",),
                           note="Free tier through Google AI Studio.", signup="https://aistudio.google.com/apikey"),
    "openrouter": ProviderSpec("openrouter", "OpenRouter (free models)", "https://openrouter.ai/api/v1",
                               "OPENROUTER_API_KEY", "meta-llama/llama-3.3-70b-instruct:free", True,
                               note="Models ending in :free cost nothing.", signup="https://openrouter.ai/keys"),
    "openai": ProviderSpec("openai", "OpenAI (paid, optional)", "https://api.openai.com/v1", "OPENAI_API_KEY",
                           "gpt-4o-mini", False, signup="https://platform.openai.com/api-keys"),
    "anthropic": ProviderSpec("anthropic", "Anthropic (paid, optional)", "https://api.anthropic.com/v1",
                              "ANTHROPIC_API_KEY", "claude-haiku-5-5", False, kind="anthropic",
                              signup="https://console.anthropic.com/settings/keys"),
    "custom": ProviderSpec("custom", "Custom OpenAI-compatible endpoint", "", "ASKIT_API_KEY", "", True,
                           note="Set ASKIT_BASE_URL and ASKIT_MODEL (and ASKIT_API_KEY if needed)."),
    "mock": ProviderSpec("mock", "Offline demo model", "", "", "mock-forge", True, kind="mock",
                         note="Returns a built-in example skill. For demos and tests, no network."),
}

AUTO_ORDER = ["groq", "gemini", "openrouter", "anthropic", "openai"]
OLLAMA_PREFERENCE = ["qwen2.5-coder", "qwen3", "llama3.3", "llama3.1", "llama3.2", "mistral", "gemma", "phi"]


@dataclass
class ChatResult:
    content: str
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0


def _http_json(url: str, payload: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None,
               timeout: float = 120.0, method: Optional[str] = None) -> Any:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    hdrs = {"Content-Type": "application/json", "User-Agent": USER_AGENT, "Accept": "application/json"}
    hdrs.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method or ("POST" if data else "GET"))
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def _error_message(exc: urllib.error.HTTPError) -> str:
    try:
        body = exc.read().decode("utf-8", errors="replace")
        data = json.loads(body)
        if isinstance(data, list) and data:
            data = data[0]
        err = data.get("error", data) if isinstance(data, dict) else data
        if isinstance(err, dict):
            return str(err.get("message") or err)[:300]
        return str(err)[:300]
    except Exception:
        return exc.reason if hasattr(exc, "reason") else str(exc)


def strip_reasoning(text: str) -> str:
    """Remove <think> blocks that reasoning models put in the answer."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S | re.I)
    text = re.sub(r"^.*?</think>", "", text, flags=re.S) if "</think>" in text and "<think>" not in text else text
    return text.strip()


class LLM:
    """A configured model endpoint."""

    def __init__(self, spec: ProviderSpec, model: str = "", api_key: str = "", base_url: str = "",
                 timeout: float = 120.0, max_retries: int = 4, scripted: Optional[List[str]] = None):
        self.spec = spec
        self.model = model or spec.default_model
        self.api_key = api_key
        self.base_url = (base_url or spec.base_url).rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._scripted = list(scripted) if scripted is not None else None
        self.calls = 0

    @property
    def name(self) -> str:
        return self.spec.name

    @property
    def is_free(self) -> bool:
        return self.spec.free

    def describe(self) -> str:
        return "%s / %s" % (self.spec.name, self.model or "?")

    def _headers(self) -> Dict[str, str]:
        h: Dict[str, str] = {}
        if self.spec.kind == "anthropic":
            h["x-api-key"] = self.api_key
            h["anthropic-version"] = "2023-06-01"
        elif self.api_key:
            h["Authorization"] = "Bearer " + self.api_key
        if self.spec.name == "openrouter":
            h["HTTP-Referer"] = "https://github.com/Lethe044/agentskill-kit"
            h["X-Title"] = "agentskill-kit"
        return h

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.2, max_tokens: int = 4096) -> ChatResult:
        self.calls += 1
        if self.spec.kind == "mock":
            from .mockmodel import mock_reply
            if self._scripted is not None:
                if not self._scripted:
                    raise ProviderError("mock provider ran out of scripted replies")
                return ChatResult(self._scripted.pop(0), model="mock")
            return ChatResult(mock_reply(messages), model="mock")
        if not self.base_url:
            raise ProviderError("no base URL for provider %r (set ASKIT_BASE_URL)" % self.name)
        if not self.model:
            raise ProviderError("no model chosen for %s. Pass --model, or run: askit providers --models" % self.name)
        if self.spec.kind == "anthropic":
            return self._chat_anthropic(messages, temperature, max_tokens)
        payload = {"model": self.model, "messages": messages, "temperature": temperature,
                   "max_tokens": max_tokens}
        data = self._request(self.base_url + "/chat/completions", payload)
        try:
            msg = data["choices"][0]["message"]
            content = msg.get("content") or ""
            if isinstance(content, list):
                content = "".join(p.get("text", "") for p in content if isinstance(p, dict))
        except (KeyError, IndexError, TypeError, AttributeError):
            raise ProviderError("unexpected response from %s: %s" % (self.name, str(data)[:200]))
        usage = data.get("usage") or {}
        return ChatResult(strip_reasoning(content), data.get("model", self.model),
                          int(usage.get("prompt_tokens", 0) or 0), int(usage.get("completion_tokens", 0) or 0))

    def _chat_anthropic(self, messages: List[Dict[str, str]], temperature: float, max_tokens: int) -> ChatResult:
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        convo = [m for m in messages if m["role"] != "system"]
        payload: Dict[str, Any] = {"model": self.model, "max_tokens": max_tokens,
                                   "temperature": temperature, "messages": convo}
        if system:
            payload["system"] = system
        data = self._request(self.base_url + "/messages", payload)
        try:
            content = "".join(b.get("text", "") for b in data["content"] if b.get("type") == "text")
        except (KeyError, TypeError):
            raise ProviderError("unexpected response from anthropic: %s" % str(data)[:200])
        usage = data.get("usage") or {}
        return ChatResult(content.strip(), data.get("model", self.model),
                          int(usage.get("input_tokens", 0)), int(usage.get("output_tokens", 0)))

    def _request(self, url: str, payload: Dict[str, Any]) -> Any:
        last = ""
        for attempt in range(self.max_retries + 1):
            try:
                return _http_json(url, payload, self._headers(), self.timeout)
            except urllib.error.HTTPError as exc:
                msg = _error_message(exc)
                if exc.code in RETRY_STATUS and attempt < self.max_retries:
                    wait = _retry_after(exc, attempt)
                    time.sleep(wait)
                    last = "HTTP %d: %s" % (exc.code, msg)
                    continue
                raise ProviderError(self._explain(exc.code, msg))
            except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
                reason = getattr(exc, "reason", exc)
                last = str(reason)
                if attempt < self.max_retries:
                    time.sleep(min(2 ** attempt, 8))
                    continue
                hint = ""
                if self.spec.name in ("ollama", "lmstudio"):
                    hint = " Is the local server running?"
                raise ProviderError("could not reach %s: %s.%s" % (self.name, last, hint))
        raise ProviderError("request failed after retries: %s" % last)

    def _explain(self, code: int, msg: str) -> str:
        base = "%s returned HTTP %d: %s" % (self.name, code, msg)
        if code in (401, 403):
            env = self.spec.key_env or "ASKIT_API_KEY"
            return base + ". Check the API key in %s." % env
        if code == 404:
            return base + ". The model name may be wrong. Run: askit providers --models --provider %s" % self.name
        if code == 429:
            return base + ". Rate limit reached. Wait a minute or switch provider."
        return base

    def list_models(self) -> List[str]:
        if self.spec.kind == "mock":
            return ["mock-forge"]
        data = _http_json(self.base_url + "/models", None, self._headers(), 30)
        items = data.get("data") or data.get("models") or []
        names = []
        for it in items:
            if isinstance(it, dict):
                names.append(str(it.get("id") or it.get("name")))
            else:
                names.append(str(it))
        return sorted(n.replace("models/", "") for n in names if n)


def _retry_after(exc: urllib.error.HTTPError, attempt: int) -> float:
    try:
        ra = exc.headers.get("Retry-After") if exc.headers else None
        if ra:
            return min(float(ra), 60.0)
    except (ValueError, TypeError):
        pass
    return min(1.5 * (2 ** attempt), 30.0)


def ollama_models(base: str = "http://localhost:11434", timeout: float = 1.0) -> List[str]:
    try:
        data = _http_json(base.rstrip("/") + "/api/tags", None, None, timeout)
        return [m.get("name", "") for m in data.get("models", []) if m.get("name")]
    except Exception:
        return []


def _pick_ollama_model(installed: List[str]) -> str:
    for pref in OLLAMA_PREFERENCE:
        for name in installed:
            if name.lower().startswith(pref):
                return name
    return installed[0] if installed else ""


def _env_key(spec: ProviderSpec) -> str:
    for env in (spec.key_env,) + tuple(spec.extra_key_envs):
        if env and os.environ.get(env):
            return os.environ[env]
    return ""


def detect_available() -> List[str]:
    """Providers that look usable right now: local first, then free keys, then paid keys."""
    keyed = [n for n in AUTO_ORDER if _env_key(PROVIDERS[n])]
    keyed.sort(key=lambda n: (not PROVIDERS[n].free, AUTO_ORDER.index(n)))
    return (["ollama"] if ollama_models() else []) + keyed


def resolve_provider(name: Optional[str] = None, model: Optional[str] = None,
                     base_url: Optional[str] = None, api_key: Optional[str] = None) -> LLM:
    chosen = (name or get_setting("provider") or "").lower()
    if not chosen:
        avail = detect_available()
        if not avail:
            raise ProviderError(
                "No LLM provider found. Free options:\n"
                "  - Ollama (local):  install from https://ollama.com, then run: ollama pull llama3.1\n"
                "  - Groq (free tier): set GROQ_API_KEY (https://console.groq.com/keys)\n"
                "  - Gemini (free tier): set GEMINI_API_KEY (https://aistudio.google.com/apikey)\n"
                "  - OpenRouter (free models): set OPENROUTER_API_KEY\n"
                "Or try the offline demo with --provider mock.")
        chosen = avail[0]
    if chosen not in PROVIDERS:
        raise ProviderError("unknown provider %r. Choose one of: %s" % (chosen, ", ".join(PROVIDERS)))
    spec = PROVIDERS[chosen]
    chosen_model = model or get_setting("model") or ""
    url = base_url or (get_setting("base_url") if chosen == (get_setting("provider") or "") else "") or ""
    key = api_key or _env_key(spec)
    if chosen == "custom":
        url = url or os.environ.get("ASKIT_BASE_URL", "")
        chosen_model = chosen_model or os.environ.get("ASKIT_MODEL", "")
        if not url:
            raise ProviderError("custom provider needs ASKIT_BASE_URL (and usually ASKIT_MODEL)")
    if chosen == "ollama" and not chosen_model:
        chosen_model = _pick_ollama_model(ollama_models())
        if not chosen_model:
            raise ProviderError("Ollama is not running or has no models. Try: ollama pull llama3.1")
    if spec.key_env and not key and chosen not in ("custom",):
        raise ProviderError("%s needs an API key. Set %s%s" % (
            spec.label, spec.key_env, (" (get one at %s)" % spec.signup) if spec.signup else ""))
    return LLM(spec, chosen_model, key, url)


def provider_status() -> List[Dict[str, Any]]:
    rows = []
    for name, spec in PROVIDERS.items():
        if spec.kind == "mock":
            state = "built in"
        elif name in ("ollama", "lmstudio"):
            base = spec.base_url.replace("/v1", "")
            if name == "ollama":
                models = ollama_models(base)
                state = "running (%d models)" % len(models) if models else "not detected"
            else:
                try:
                    _http_json(spec.base_url + "/models", None, None, 1.0)
                    state = "running"
                except Exception:
                    state = "not detected"
        elif name == "custom":
            state = "configured" if os.environ.get("ASKIT_BASE_URL") else "not set"
        else:
            state = "key found" if _env_key(spec) else "no key"
        rows.append({"name": name, "label": spec.label, "free": spec.free, "state": state,
                     "model": spec.default_model, "key_env": spec.key_env, "signup": spec.signup})
    return rows
