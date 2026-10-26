import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "check_api.py")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        return

    def _reply(self, code, body):
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/health":
            self._reply(200, "status ok")
        else:
            self._reply(404, "missing")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(length) or b"{}")
        self._reply(201, "created " + payload.get("name", ""))


class CheckApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), Handler)
        cls.url = "http://127.0.0.1:%d" % cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def run_script(self, checks, base=None):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump(checks, fh)
        try:
            proc = subprocess.run([sys.executable, SCRIPT, fh.name, "--base-url", base or self.url],
                                  capture_output=True, text=True, timeout=30)
        finally:
            os.unlink(fh.name)
        return proc

    def test_passing_checks(self):
        proc = self.run_script([
            {"name": "health", "path": "/health", "expect_body_contains": "ok"},
            {"name": "create", "method": "POST", "path": "/items", "json": {"name": "demo"}, "expect_status": 201,
             "expect_body_contains": "demo"}])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual((data["passed"], data["failed"]), (2, 0))

    def test_wrong_status_fails(self):
        proc = self.run_script([{"name": "gone", "path": "/nope"}])
        self.assertEqual(proc.returncode, 1)
        result = json.loads(proc.stdout)["results"][0]
        self.assertFalse(result["ok"])
        self.assertIn("expected status 200, got 404", result["reason"])

    def test_body_assertion_fails(self):
        proc = self.run_script([{"path": "/health", "expect_body_contains": "degraded"}])
        self.assertEqual(proc.returncode, 1)

    def test_connection_error_is_a_failed_check(self):
        proc = self.run_script([{"path": "/health", "timeout": 2}], base="http://127.0.0.1:1")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("request failed", json.loads(proc.stdout)["results"][0]["reason"])

    def test_bad_checks_file(self):
        proc = self.run_script({"not": "a list"})
        self.assertEqual(proc.returncode, 3)


if __name__ == "__main__":
    unittest.main()
