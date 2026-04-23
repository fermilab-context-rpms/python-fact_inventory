"""Minimal mock fact_inventory API for ansible-test integration testing.

Accepts any POST and replies 201 Created with a small JSON body.
Not for production use - no auth, no validation, no persistence.
"""

import http.server
import json


class Handler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)
        body = json.dumps({"status": "accepted"}).encode("utf-8")
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass  # keep ansible-test output quiet


if __name__ == "__main__":
    http.server.HTTPServer(("127.0.0.1", 8123), Handler).serve_forever()
