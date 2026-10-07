"""Focused browser regression for model-list diagnostics; no real API credentials."""
from __future__ import annotations

import importlib.util
import json
import socket
import ssl
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import URLError

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/playwright/model-list'
OUT.mkdir(parents=True, exist_ok=True)
spec = importlib.util.spec_from_file_location('eva_server', ROOT / 'tools/eva_server.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
server = module.make_server(0)
mode, requests, checks, errors = 'ok', [], [], []
KEY = 'model-list-fixture-not-a-real-key'


class Fixture(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        requests.append(self.path)
        status = int(mode) if mode.isdigit() else 200
        if mode == 'redirect':
            self.send_response(302)
            self.send_header('Location', f'http://127.0.0.1:{self.server.server_port}/redirected/models')
            self.end_headers()
            return
        if mode == 'html':
            body, content = b'<html>Login page</html>', 'text/html'
        else:
            data = {'error': KEY} if status != 200 else {'data': [] if mode == 'empty' else ['local-alpha', None, {'id': 'local-beta'}]}
            body, content = json.dumps(data).encode(), 'application/json'
        self.send_response(status)
        self.send_header('Content-Type', content)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


fixture = ThreadingHTTPServer(('127.0.0.1', 0), Fixture)
for service in (server, fixture):
    threading.Thread(target=service.serve_forever, daemon=True).start()


def passed(text):
    checks.append(text)
    print('[PASS] ' + text, flush=True)


try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(f'http://127.0.0.1:{server.server_port}/index.html')
        page.locator('#evaEnterBtn').click()
        form = page.locator('[data-side="player"]')
        form.locator('[data-field="provider"]').select_option('custom')
        form.locator('[data-field="baseUrl"]').fill(f'http://127.0.0.1:{fixture.server_port}/v1')
        form.locator('[data-field="apiKey"]').fill(KEY)
        status = form.locator('[data-info="connection"]')

        def query():
            form.locator('[data-op="models"]').click()
            page.wait_for_function("!document.querySelector('[data-side=player] [data-op=models]').disabled")
            return status.inner_text()

        assert '已获取 2 个模型' in query()
        assert form.locator('[data-field="model"]').input_value() == 'local-alpha'
        passed('object/string model lists populate and select a model without requiring a prior model ID')
        for code, expected in [('401', '密钥'), ('403', '拒绝'), ('404', 'Base URL'), ('429', '限流'), ('500', '服务端')]:
            mode = code
            message = query()
            assert f'HTTP_{code}' in message and expected in message, message
            assert KEY not in message
            passed(f'{code} displays the actual model-list failure without leaking upstream text or key')
            if code == '401':
                page.screenshot(path=str(OUT / 'models-error-desktop.png'))
        for case, expected in [('empty', '空的模型列表'), ('html', '不是 JSON'), ('redirect', '重定向')]:
            mode = case
            assert expected in query()
            passed(case + ' has actionable model-list diagnostics')
        assert '/redirected/models' not in requests
        for reason, expected in [(ssl.SSLCertVerificationError('fixture'), '证书'), (socket.gaierror('fixture'), '域名'), ('fixture network failure', '系统代理')]:
            opener = Mock()
            opener.open.side_effect = URLError(reason)
            with patch.object(module, 'build_opener', return_value=opener):
                assert expected in query()
            passed('relay classifies ' + expected + ' failure without returning raw upstream errors')
        request_count = len(requests)
        page.route('**/eva/api/health', lambda route: route.fulfill(status=404, body='Not found'))
        assert 'RELAY_UNAVAILABLE' in query()
        assert len(requests) == request_count
        passed('ordinary static server gives EVA launcher instructions before sending credentials')
        page.unroute('**/eva/api/health')
        mode = 'ok'
        assert '已获取 2 个模型' in query()
        passed('model query recovers after failure')
        form.locator('[data-field="baseUrl"]').fill('https://www.packyapi.ai/v1')
        assert 'https://cf.api.fan/v1' in form.locator('[data-info="baseUrl"]').inner_text()
        assert form.locator('[data-field="baseUrl"]').input_value() == 'https://www.packyapi.ai/v1'
        assert form.locator('[data-field="apiKey"]').input_value() == KEY
        passed('Packy endpoint hint appears while preserving the entered address and key')
        assert '模型响应速度仍可能不同' in page.locator('#evaConfigOverlay').inner_text()
        page.locator('#evaFair').uncheck()
        enemy_period = page.locator('[data-side="enemy"] [data-field="interval"]')
        enemy_period.select_option('10')
        page.locator('#evaFair').check()
        assert not enemy_period.is_enabled() and enemy_period.input_value() == '3'
        passed('fair-period explanation and actual interval synchronization agree')
        page.screenshot(path=str(OUT / 'config-help-desktop.png'))
        page.set_viewport_size({'width': 844, 'height': 390})
        page.locator('#evaFair').scroll_into_view_if_needed()
        page.screenshot(path=str(OUT / 'config-help-phone.png'))
        assert not errors, errors
        passed('desktop/mobile configuration screenshots and zero uncaught browser exceptions')
        browser.close()
    (OUT / 'report.json').write_text(json.dumps({'checks': checks, 'pageErrors': errors, 'realCredentialsUsed': False}, ensure_ascii=False, indent=2), encoding='utf-8')
finally:
    for service in (server, fixture):
        service.shutdown()
        service.server_close()
