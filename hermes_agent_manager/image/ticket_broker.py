#!/usr/bin/env python3
"""Mint Hermes gateway attach tickets for the FM bridge."""

from __future__ import annotations

import json
import os
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class TicketHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path.rstrip("/") != "/ticket":
            self._send(404, {"error": "not_found"})
            return
        expected = os.environ.get("HERMES_BRIDGE_SECRET", "")
        provided = self.headers.get("X-Ham-Bridge-Secret", "")
        if not expected or provided != expected:
            self._send(401, {"error": "unauthorized"})
            return
        try:
            payload = _attach_ticket()
        except Exception as error:  # noqa: BLE001
            self._send(500, {"error": str(error)})
            return
        self._send(200, payload)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def _send(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _attach_ticket() -> dict:
    completed = subprocess.run(
        ["hermes", "gateway", "attach", "--json"],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "HERMES_HOME": os.environ.get("HERMES_HOME", "/opt/data")},
    )
    text = (completed.stdout or completed.stderr or "").strip()
    if completed.returncode != 0:
        raise RuntimeError(text or "hermes gateway attach failed")
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("{"):
            return json.loads(line)
    raise RuntimeError(f"unexpected attach output: {text}")


def main() -> None:
    host = os.environ.get("HAM_TICKET_HOST", "0.0.0.0")
    port = int(os.environ.get("HAM_TICKET_PORT", "8650"))
    server = ThreadingHTTPServer((host, port), TicketHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()
