"""Verify encrypted save/reload/delete and automatic connection testing in Chromium."""
import importlib.util
import json
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/playwright/settings'
OUT.mkdir(parents=True, exist_ok=True)
spec = importlib.util.spec_from_file_location('eva_server', ROOT / 'tools/eva_server.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
TOKEN = 'save-reload-fixture-not-a-real-key'
checks, errors, requests = [], [], []


def passed(message):
    checks.append(message)
    print('[PASS] ' + message, flush=True)


class Fixture(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_POST(self):
        data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        assert self.headers['Authorization'] == 'Bearer ' + TOKEN
        requests.append(data)
        packet = {'schemaVersion': 1, 'summary': '中路部署狮子。', 'commands': [{'action': 'deploy', 'unit': 'lion', 'lane': 'middle'}]}
        payload = json.dumps({'choices': [{'message': {'content': json.dumps(packet)}, 'finish_reason': 'stop'}], 'usage': {'prompt_tokens': 10, 'completion_tokens': 20}}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


fixture = ThreadingHTTPServer(('127.0.0.1', 0), Fixture)
threading.Thread(target=fixture.serve_forever, daemon=True).start()
try:
    with tempfile.TemporaryDirectory(prefix='eva-save-test-') as temp:
        vault = Path(temp) / 'settings.dpapi'
        server = module.make_server(0, vault)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(viewport={'width': 1920, 'height': 1080})
            page.on('pageerror', lambda e: errors.append(str(e)))
            url = f'http://127.0.0.1:{server.server_port}'
            page.goto(url + '/index.html?eva=1&test=1')
            page.wait_for_function("!document.querySelector('#evaSaveSettings').disabled")
            assert page.locator('#evaConfigOverlay').is_visible()
            for side in ('player', 'enemy'):
                field = lambda name: page.locator(f'[data-side="{side}"] [data-field="{name}"]')
                field('provider').select_option('custom')
                field('baseUrl').fill(f'http://127.0.0.1:{fixture.server_port}/v1')
                field('apiKey').fill(TOKEN)
                field('model').fill('deepseek-flash')
                field('reasoning').select_option('none')
            page.locator('[data-side="player"] [data-field="interval"]').select_option('10')
            page.locator('#evaDebugEnabled').check()
            page.locator('#evaSaveSettings').click()
            page.wait_for_function("document.querySelector('#evaStorageMessage').textContent.includes('已加密保存')")
            assert vault.exists() and TOKEN.encode() not in vault.read_bytes()
            assert TOKEN not in page.evaluate('JSON.stringify(localStorage) + JSON.stringify(sessionStorage)')
            assert server.settings.load()['player']['apiKey'] == TOKEN
            passed('explicit Save encrypts keys on disk and never puts keys in browser storage')

            server.shutdown(); server.server_close()
            server = module.make_server(0, vault)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            url = f'http://127.0.0.1:{server.server_port}'
            page.close()
            page = browser.new_page(viewport={'width': 1920, 'height': 1080})
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.goto(url + '/index.html?eva=1&test=1')
            page.wait_for_function("document.querySelector('#evaStorageMessage').textContent.includes('已自动载入')")
            for side in ('player', 'enemy'):
                assert page.locator(f'[data-side="{side}"] [data-field="apiKey"]').input_value() == TOKEN
                assert page.locator(f'[data-side="{side}"] [data-field="reasoning"]').input_value() == 'none'
            assert page.locator('#evaDebugEnabled').is_checked()
            assert page.locator('[data-side="enemy"] [data-field="interval"]').input_value() == '10'
            page.locator('#evaSaveSettings').scroll_into_view_if_needed()
            page.screenshot(path=str(OUT / 'config-desktop.png'), mask=[page.locator('[data-field="apiKey"]')])
            passed('new server port and browser page restore both keys and options without retyping')

            req = Request(url + '/eva/api/settings/load', data=b'{}', headers={'Content-Type': 'application/json', 'Origin': 'https://other.example'})
            try:
                urlopen(req)
                raise AssertionError('cross-origin settings access allowed')
            except HTTPError as e:
                assert e.code == 403 and TOKEN.encode() not in e.read()
            try:
                urlopen(url + '/eva/api/settings/load')
                raise AssertionError('GET settings access allowed')
            except HTTPError as e:
                assert e.code == 404
            passed('settings retrieval rejects cross-origin requests and ordinary static GET')

            page.locator('#evaStartBtn').click()
            page.wait_for_function("QJWGEngine.state() === 'playing'")
            page.wait_for_function("Object.values(__EVA_TEST__.snapshot().stats).every(s=>s.deployed>0)")
            assert len(requests) >= 4  # Two automatic connection tests, then real game decisions through fixtures.
            assert not errors
            page.evaluate('QJWGEngine.pause()')
            passed('Start automatically verifies saved providers then both deploy through strict command validation')

            page.evaluate('EVA.view.openConfig()')
            page.set_viewport_size({'width': 844, 'height': 390})
            page.locator('#evaSaveSettings').scroll_into_view_if_needed()
            page.screenshot(path=str(OUT / 'config-phone.png'), mask=[page.locator('[data-field="apiKey"]')])
            page.locator('#evaDeleteSettings').click()
            page.wait_for_function("document.querySelector('#evaStorageMessage').textContent.includes('已删除')")
            assert not vault.exists()
            page.reload()
            page.wait_for_function("!document.querySelector('#evaSaveSettings').disabled")
            assert all(page.locator(f'[data-side="{side}"] [data-field="apiKey"]').input_value() == '' for side in ('player', 'enemy'))
            passed('Delete removes the encrypted configuration; refresh does not restore keys; mobile controls accessible')
            browser.close()
        server.shutdown(); server.server_close()
finally:
    fixture.shutdown(); fixture.server_close()
(OUT / 'report.json').write_text(json.dumps({'checks': checks, 'pageErrors': errors, 'fixtureRequests': len(requests)}, indent=2), encoding='utf-8')
print('ALL SAVE TESTS PASSED')
