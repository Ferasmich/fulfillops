"""Temporary measurement proxy: one upstream request, no retries or credentials."""

import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Proxy(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        connection = http.client.HTTPConnection("fulfillops-api", 80, timeout=3)
        try:
            connection.request("GET", self.path)
            result = connection.getresponse()
            data = result.read()
            status = result.status
            content_type = result.getheader("Content-Type", "application/octet-stream")
        except (OSError, http.client.HTTPException):
            status, data, content_type = 502, b"upstream unavailable", "text/plain"
        finally:
            connection.close()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        return


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8080), Proxy).serve_forever()
