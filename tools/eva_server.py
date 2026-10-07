"""Loopback-only static server + optional text API relay. No third-party dependencies.

Run: python tools/eva_server.py --port 8772
Keys are never logged. Explicitly saved settings use Windows account encryption.
"""
from __future__ import annotations

import argparse
import json
import re
import socket
import ssl
import sys
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, unquote
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 2_000_000
sys.path.insert(0, str(Path(__file__).resolve().parent))
from eva_settings import LocalSettings, default_settings_file


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward Authorization to a redirected destination.


class EvaHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, *_):
        pass  # No URL, body, key, or upstream error body in logs.

    def allowed_host(self):
        port = self.server.server_port
        return self.headers.get("Host") in {f"127.0.0.1:{port}", f"localhost:{port}"}

    def reply(self, status, data):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        try:
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def do_GET(self):
        if not self.allowed_host():
            self.reply(421, {"error": "Invalid host"})
            return
        if self.path == "/eva/api/health":
            self.reply(200, {"relay": True, "schemaVersion": 1, "settingsStorage": "windows-dpapi" if self.server.settings is not None else None})
            return
        # Only ship public game files, never agent metadata, spreadsheets, tests, or secrets.
        path = unquote(urlsplit(self.path).path)
        if path not in {"/", "/index.html", "/favicon.ico"} and not path.startswith(("/js/", "/css/", "/assets/")):
            self.reply(404, {"error": "Not a public game resource"})
            return
        if any(p.startswith(".") or p == ".." for p in path.split("/")[1:]):
            self.reply(404, {"error": "Not found"})
            return
        if not (ROOT / path.lstrip("/")).resolve().is_relative_to(ROOT):
            self.reply(404, {"error": "Not found"})
            return
        super().do_GET()

    def do_POST(self):
        origin = self.headers.get("Origin")
        port = self.server.server_port
        if not self.allowed_host() or origin not in {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}:
            self.reply(403, {"error": "Same-origin local requests only", "code": "RELAY_ORIGIN"})
            return
        if self.path in {"/eva/api/settings/load", "/eva/api/settings/save", "/eva/api/settings/clear"}:
            if self.server.settings is None:
                self.reply(503, {"error": "Encrypted local settings unavailable"})
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 64_000:
                    raise ValueError('Settings size')
                data = json.loads(self.rfile.read(length))
                if self.path.endswith('/load'):
                    settings = self.server.settings.load()
                    self.reply(200, {"saved": settings is not None, "settings": settings})
                elif self.path.endswith('/save'):
                    self.server.settings.save(data)
                    self.reply(200, {"saved": True})
                else:
                    self.server.settings.clear()
                    self.reply(200, {"saved": False})
            except (ValueError, TypeError, UnicodeError):
                self.reply(400, {"error": "Invalid saved configuration"})
            except OSError:
                self.reply(500, {"error": "Could not access Windows encrypted settings"})
            return
        if self.path != "/eva/api/proxy":
            self.reply(404, {"error": "Not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_BYTES:
                raise ValueError("Request size")
            data = json.loads(self.rfile.read(length))
            url, method = data["url"], data["method"]
            parsed = urlsplit(url)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
                raise ValueError("URL")
            if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
                raise ValueError("Remote endpoints require HTTPS")
            if parsed.hostname in {"127.0.0.1", "localhost", "::1"} and parsed.port == port:
                raise ValueError("Relay recursion")
            if not re.search(r"/(models(?:/[^/]+:generateContent)?|chat/completions|messages)$", parsed.path):
                raise ValueError("API endpoint")
            if method not in {"GET", "POST"}:
                raise ValueError("Method")
            headers = data.get("headers", {})
            if not isinstance(headers, dict) or any(k.lower() not in {"content-type", "authorization", "x-api-key", "x-goog-api-key", "anthropic-version"} for k in headers):
                raise ValueError("Headers")
            body = data.get("body")
            if method == "GET" and body is not None:
                raise ValueError("GET body")
            payload = json.dumps(body).encode("utf-8") if body is not None else None
            timeout = max(1, min(float(data.get("timeout", 20)), 60))
            req = Request(url, data=payload, headers=headers, method=method)
            with build_opener(NoRedirect).open(req, timeout=timeout) as response:
                raw = response.read(MAX_BYTES + 1)
                if len(raw) > MAX_BYTES:
                    raise ValueError("Response size")
                try:
                    result = json.loads(raw)
                except json.JSONDecodeError:
                    self.reply(502, {"error": "Upstream response is not JSON", "code": "UPSTREAM_JSON"})
                    return
            self.reply(200, result)
        except HTTPError as error:
            self.reply(error.code if 400 <= error.code <= 599 else 502, {"error": "Upstream HTTP error", "code": "UPSTREAM_REDIRECT" if 300 <= error.code < 400 else "UPSTREAM_HTTP"})
        except (TimeoutError, socket.timeout):
            self.reply(504, {"error": "Upstream timeout"})
        except URLError as error:
            code = "UPSTREAM_TLS" if isinstance(error.reason, ssl.SSLError) else "UPSTREAM_DNS" if isinstance(error.reason, socket.gaierror) else "UPSTREAM_NETWORK"
            self.reply(504 if isinstance(error.reason, (TimeoutError, socket.timeout)) else 502, {"error": "Upstream unavailable", "code": code})
        except (ValueError, KeyError, TypeError, UnicodeError):
            self.reply(400, {"error": "Invalid relay request or upstream JSON"})
        except OSError:
            self.reply(502, {"error": "Upstream network failure"})


def make_server(port=8772, settings_file=None):
    server = ThreadingHTTPServer(("127.0.0.1", port), EvaHandler)
    server.settings = LocalSettings(settings_file) if settings_file is not None and os.name == 'nt' else None
    return server


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8772)
    args = parser.parse_args()
    server = make_server(args.port, default_settings_file())
    print(f"EVA Arena: http://127.0.0.1:{server.server_port}/index.html", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
