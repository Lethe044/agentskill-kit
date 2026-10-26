import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

import helpers  # noqa: F401
from helpers import TempDirTest
from agentskill_kit import providers
from agentskill_kit.providers import PROVIDERS, LLM, ProviderError


class FakeAPI(BaseHTTPRequestHandler):
    seen = []
    fail_first = 0

    def log_message(self, *args):
        return

    def _json(self, code, payload, headers=None):
        data = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.endswith("/models"):
            self._json(200, {"data": [{"id": "zeta"}, {"id": "alpha"}]})
        else:
            self._json(404, {"error": {"message": "nope"}})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        FakeAPI.seen.append({"path": self.path, "auth": self.headers.get("Authorization"),
                             "key": self.headers.get("x-api-key"), "body": body})
        if FakeAPI.fail_first > 0:
            FakeAPI.fail_first -= 1
            self._json(429, {"error": {"message": "slow down"}}, {"Retry-After": "0"})
            return
        if body.get("model") == "bad-model":
            self._json(404, {"error": {"message": "model not found"}})
            return
        if self.path.endswith("/messages"):
            self._json(200, {"content": [{"type": "text", "text": "anthropic reply"}], "model": body["model"],
                             "usage": {"input_tokens": 3, "output_tokens": 4}})
            return
        self._json(200, {"choices": [{"message": {"content": "<think>hidden</think>Hello there"}}],
                         "model": body["model"], "usage": {"prompt_tokens": 5, "completion_tokens": 2}})


class ProviderTests(TempDirTest):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), FakeAPI)
        cls.base = "http://127.0.0.1:%d" % cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        super().setUp()
        FakeAPI.seen = []
        FakeAPI.fail_first = 0
        for var in ("GROQ_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY",
                    "ANTHROPIC_API_KEY", "ASKIT_PROVIDER", "ASKIT_MODEL", "ASKIT_BASE_URL"):
            self._clear(var)

    def _clear(self, var):
        old = os.environ.pop(var, None)
        if old is not None:
            self.addCleanup(os.environ.__setitem__, var, old)

    def make(self, name="custom", model="m", key="k", **kw):
        return LLM(PROVIDERS[name], model, key, self.base + "/v1", max_retries=kw.pop("max_retries", 3), **kw)

    def test_chat_openai_protocol(self):
        res = self.make().chat([{"role": "user", "content": "hi"}])
        self.assertEqual(res.content, "Hello there")
        self.assertEqual((res.prompt_tokens, res.completion_tokens), (5, 2))
        seen = FakeAPI.seen[0]
        self.assertEqual(seen["path"], "/v1/chat/completions")
        self.assertEqual(seen["auth"], "Bearer k")
        self.assertEqual(seen["body"]["model"], "m")

    def test_retries_on_rate_limit(self):
        FakeAPI.fail_first = 2
        res = self.make().chat([{"role": "user", "content": "hi"}])
        self.assertEqual(res.content, "Hello there")
        self.assertEqual(len(FakeAPI.seen), 3)

    def test_gives_up_after_retries(self):
        FakeAPI.fail_first = 10
        with self.assertRaises(ProviderError) as ctx:
            self.make(max_retries=1).chat([{"role": "user", "content": "hi"}])
        self.assertIn("429", str(ctx.exception))

    def test_unknown_model_error_is_helpful(self):
        with self.assertRaises(ProviderError) as ctx:
            self.make(model="bad-model").chat([{"role": "user", "content": "hi"}])
        self.assertIn("model name", str(ctx.exception))

    def test_anthropic_protocol(self):
        llm = LLM(PROVIDERS["anthropic"], "claude-test", "secret", self.base + "/v1")
        res = llm.chat([{"role": "system", "content": "be brief"}, {"role": "user", "content": "hi"}])
        self.assertEqual(res.content, "anthropic reply")
        seen = FakeAPI.seen[0]
        self.assertEqual(seen["path"], "/v1/messages")
        self.assertEqual(seen["key"], "secret")
        self.assertEqual(seen["body"]["system"], "be brief")
        self.assertEqual(seen["body"]["messages"], [{"role": "user", "content": "hi"}])

    def test_list_models(self):
        self.assertEqual(self.make().list_models(), ["alpha", "zeta"])

    def test_connection_error(self):
        llm = LLM(PROVIDERS["custom"], "m", "", "http://127.0.0.1:1/v1", max_retries=0)
        with self.assertRaises(ProviderError):
            llm.chat([{"role": "user", "content": "hi"}])

    def test_strip_reasoning(self):
        self.assertEqual(providers.strip_reasoning("<think>a\nb</think>\nanswer"), "answer")
        self.assertEqual(providers.strip_reasoning("no tags"), "no tags")

    def test_missing_model(self):
        with self.assertRaises(ProviderError):
            LLM(PROVIDERS["custom"], "", "", self.base + "/v1").chat([{"role": "user", "content": "x"}])

    def test_mock_provider_needs_nothing(self):
        llm = providers.resolve_provider("mock")
        self.assertIn("=== FILE: SKILL.md ===", llm.chat([{"role": "user", "content": "x"}]).content)
        self.assertTrue(llm.is_free)


class ResolveTests(TempDirTest):
    def setUp(self):
        super().setUp()
        for var in ("GROQ_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY",
                    "ANTHROPIC_API_KEY", "ASKIT_PROVIDER", "ASKIT_MODEL", "ASKIT_BASE_URL", "ASKIT_API_KEY"):
            old = os.environ.pop(var, None)
            if old is not None:
                self.addCleanup(os.environ.__setitem__, var, old)
        self._ollama = providers.ollama_models
        providers.ollama_models = lambda *a, **k: []
        self.addCleanup(setattr, providers, "ollama_models", self._ollama)

    def test_nothing_configured_gives_guidance(self):
        with self.assertRaises(ProviderError) as ctx:
            providers.resolve_provider()
        self.assertIn("Ollama", str(ctx.exception))
        self.assertIn("GROQ_API_KEY", str(ctx.exception))

    def test_free_keys_win_over_paid_ones(self):
        os.environ["OPENAI_API_KEY"] = "paid"
        os.environ["GEMINI_API_KEY"] = "free"
        self.addCleanup(os.environ.pop, "OPENAI_API_KEY", None)
        self.addCleanup(os.environ.pop, "GEMINI_API_KEY", None)
        self.assertEqual(providers.resolve_provider().name, "gemini")

    def test_google_key_alias(self):
        os.environ["GOOGLE_API_KEY"] = "x"
        self.addCleanup(os.environ.pop, "GOOGLE_API_KEY", None)
        self.assertEqual(providers.resolve_provider("gemini").api_key, "x")

    def test_local_model_comes_first(self):
        providers.ollama_models = lambda *a, **k: ["llama3.1:8b", "qwen2.5-coder:7b"]
        os.environ["GROQ_API_KEY"] = "x"
        self.addCleanup(os.environ.pop, "GROQ_API_KEY", None)
        llm = providers.resolve_provider()
        self.assertEqual((llm.name, llm.model), ("ollama", "qwen2.5-coder:7b"))

    def test_explicit_choice_needs_a_key(self):
        with self.assertRaises(ProviderError) as ctx:
            providers.resolve_provider("groq")
        self.assertIn("GROQ_API_KEY", str(ctx.exception))
        with self.assertRaises(ProviderError):
            providers.resolve_provider("nonsense")

    def test_custom_endpoint(self):
        os.environ["ASKIT_BASE_URL"] = "http://localhost:9/v1"
        os.environ["ASKIT_MODEL"] = "tiny"
        for v in ("ASKIT_BASE_URL", "ASKIT_MODEL"):
            self.addCleanup(os.environ.pop, v, None)
        llm = providers.resolve_provider("custom")
        self.assertEqual((llm.base_url, llm.model), ("http://localhost:9/v1", "tiny"))

    def test_model_override_and_config(self):
        from agentskill_kit.config import set_setting
        set_setting("provider", "mock")
        set_setting("model", "my-model")
        llm = providers.resolve_provider()
        self.assertEqual((llm.name, llm.model), ("mock", "my-model"))
        self.assertEqual(providers.resolve_provider(model="other").model, "other")

    def test_status_lists_every_provider(self):
        names = {r["name"] for r in providers.provider_status()}
        self.assertEqual(names, set(PROVIDERS))


if __name__ == "__main__":
    unittest.main()
