"""
Stdlib Arena server. Use this if FastAPI is not installed.

    python scripts/seed.py
    python arena_server.py
    python scripts/demo_arena.py
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import arena
import core
from kernel import PURPOSE, PURPOSE_ID


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print("[arena]", fmt % args)

    def _send(self, status, body):
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("access-control-allow-origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def _read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        if not raw:
            return {}
        return json.loads(raw.decode())

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("access-control-allow-origin", "*")
        self.send_header("access-control-allow-headers", "*")
        self.send_header("access-control-allow-methods", "GET,POST,OPTIONS")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/":
            self._send(
                200,
                {
                    "name": "TrustMesh API",
                    "version": "0.2.0",
                    "arena": "/arena/health",
                    "purpose": PURPOSE,
                },
            )
            return
        if path == "/arena/health":
            self._send(200, arena.health())
            return
        if path == "/arena/audit":
            qs = parse_qs(parsed.query)
            limit = int(qs.get("limit", ["50"])[0])
            self._send(200, {"purpose": PURPOSE_ID, "events": arena.kernel.recent_audit(limit)})
            return
        self._send(404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            data = self._read_json()
        except json.JSONDecodeError:
            self._send(400, {"error": "invalid json"})
            return
        api_key = self.headers.get("X-API-Key")
        caller = self.headers.get("X-Caller-Id")
        trace = self.headers.get("X-Trace-Id")
        try:
            if path == "/arena/check":
                result = arena.do_check(
                    data,
                    get_trust_score_fn=core.get_trust_score,
                    api_key=api_key,
                    caller_header=caller,
                    trace_id=trace,
                )
                self._send(200, result)
                return
            if path == "/arena/attest":
                result = arena.do_attest(
                    data,
                    get_trust_score_fn=core.get_trust_score,
                    log_interaction_fn=core.record_interaction,
                    api_key=api_key,
                    caller_header=caller,
                    trace_id=trace,
                )
                self._send(200, result)
                return
            if path == "/arena/denied-demo":
                self._send(200, arena.denied_demo(caller or "agent_intruder"))
                return
        except arena.ArenaError as exc:
            self._send(exc.status_code, {"error": exc.detail})
            return
        except Exception as exc:  # noqa: BLE001
            self._send(500, {"error": str(exc)})
            return
        self._send(404, {"error": "not found"})


def main():
    server = ThreadingHTTPServer(("0.0.0.0", 8000), Handler)
    print("TrustMesh Arena server on http://127.0.0.1:8000")
    print(f"purpose: {PURPOSE_ID}")
    server.serve_forever()


if __name__ == "__main__":
    main()
