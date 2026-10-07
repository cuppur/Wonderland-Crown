"""Opt-in real API playtest. Credentials stay in memory; no traces/HAR/DOM dumps.

Run only when the user authorizes API usage:
python tests/playtest_eva_live.py --credentials-file C:/path/api.txt
Expected sections: Packy / DeepSeek, an optional URL, and each section's key.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import threading
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/playwright/live-api'


def load_credentials(path):
    configs, current = {}, None
    for line in Path(path).read_text(encoding='utf-8-sig').splitlines():
        if re.search(r'packy', line, re.I):
            current = 'packy'
        elif re.search(r'deepseek|深度求索', line, re.I):
            current = 'deepseek'
        if not current:
            continue
        c = configs.setdefault(current, {})
        urls = re.findall(r'https?://[^\s\"\'<>]+', line)
        keys = re.findall(r'\bsk-[A-Za-z0-9_-]{12,}\b|(?<![A-Za-z0-9])[a-fA-F0-9]{32,}(?![A-Za-z0-9])', line)
        if urls:
            c['baseUrl'] = urls[0].rstrip('，。,;；')
        if keys:
            c['apiKey'] = keys[0]
    for name in ('packy', 'deepseek'):
        if not configs.get(name, {}).get('apiKey'):
            raise ValueError('Credential file needs labeled Packy and DeepSeek sections with keys')
    configs['deepseek'].setdefault('baseUrl', 'https://api.deepseek.com/v1')
    if not configs['packy'].get('baseUrl'):
        raise ValueError('Packy Base URL missing from credential file')
    if configs['packy']['baseUrl'].endswith('/v'):
        configs['packy']['baseUrl'] += '1'
    return configs


def run(args):
    credentials = load_credentials(args.credentials_file)
    secrets = [c['apiKey'] for c in credentials.values()]

    def scrub(value):
        if isinstance(value, str):
            for key in secrets:
                value = value.replace(key, '[REDACTED]')
            return re.sub(r'Bearer\s+[^\s\"\']+', 'Bearer [REDACTED]', value, flags=re.I)
        if isinstance(value, list):
            return [scrub(v) for v in value]
        if isinstance(value, dict):
            return {k: scrub(v) for k, v in value.items() if k.lower() not in {'apikey', 'authorization', 'thinking', 'reasoning_content'}}
        return value

    def emit(value):
        print(json.dumps(scrub(value), ensure_ascii=False), flush=True)

    OUT.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location('eva_server', ROOT / 'tools/eva_server.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    server = module.make_server(0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    report = {'realPaidApiTested': True, 'credentialsPersisted': False, 'models': {}, 'connection': {}, 'pageErrors': [], 'targetDecisionsPerSide': args.decisions}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={'width': 1920, 'height': 1080})
            page.on('pageerror', lambda e: report['pageErrors'].append(scrub(str(e))))
            page.goto(f'http://127.0.0.1:{server.server_port}/index.html?test=1')
            page.locator('#evaEnterBtn').click()

            def field(side, name):
                return page.locator(f'[data-side="{side}"] [data-field="{name}"]')

            for side, name, provider in [('player', 'packy', 'custom'), ('enemy', 'deepseek', 'deepseek')]:
                field(side, 'provider').select_option(provider)
                field(side, 'baseUrl').fill(credentials[name]['baseUrl'])
                field(side, 'apiKey').fill(credentials[name]['apiKey'])
                page.locator(f'[data-side="{side}"] details summary').click()
                field(side, 'timeout').select_option('60')
                field(side, 'maxTokens').select_option('2048')
                field(side, 'jsonMode').select_option('true')
            field('player', 'interval').select_option('10')
            page.locator('#evaRemember').uncheck()
            page.locator('#evaDebugEnabled').check()
            page.locator('#evaDuration').select_option('unlimited')

            def operation(side, op):
                page.locator(f'[data-side="{side}"] [data-op="{op}"]').click()

            def wait_operation(side):
                page.wait_for_function("s => !document.querySelector(`[data-side='${s}'] [data-op='test']`).disabled", arg=side, timeout=70000)
                return page.locator(f'[data-side="{side}"] [data-info="connection"]').inner_text()

            for side in ('player', 'enemy'):
                operation(side, 'models')
            for side in ('player', 'enemy'):
                message = wait_operation(side)
                if '已获取' not in message:
                    raise RuntimeError(side + ' model list: ' + message)
                ids = page.locator(f'#evaModels-{side} option').evaluate_all('(nodes) => nodes.map(n => n.value)')
                model = args.packy_model if side == 'player' else args.deepseek_model
                if model not in ids:
                    raise RuntimeError(side + ' chosen model unavailable in this key model list')
                field(side, 'model').fill(model)
                field(side, 'reasoning').select_option(args.reasoning)
                report['models'][side] = {'ids': ids, 'selected': model, 'baseUrl': credentials['packy' if side == 'player' else 'deepseek']['baseUrl']}
                report['models'][side]['reasoning'] = args.reasoning
                emit({'stage': 'models', 'side': side, **report['models'][side]})
            for side in ('player', 'enemy'):
                operation(side, 'test')
            for side in ('player', 'enemy'):
                message = wait_operation(side)
                report['connection'][side] = message
                emit({'stage': 'connection', 'side': side, 'message': message})
                if '连接测试通过' not in message:
                    raise RuntimeError(side + ' connection: ' + message)
            page.screenshot(path=str(OUT / 'config-desktop.png'), mask=[field('player', 'apiKey'), field('enemy', 'apiKey')])
            page.locator('#evaStartBtn').click()
            page.wait_for_function("QJWGEngine.state() === 'playing'")
            deadline, last_emit, last_errors = time.monotonic() + args.max_seconds, 0, {}
            while time.monotonic() < deadline:
                snapshot = page.evaluate('__EVA_TEST__.snapshot()')
                counts = {side: snapshot['stats'][side]['decisions'] for side in ('player', 'enemy')}
                for side in counts:
                    count = snapshot['stats'][side]['errors']
                    if count > last_errors.get(side, 0):
                        record = page.evaluate('s => EVA.arena.logger.entries.filter(e => e.side === s && e.error).slice(-1)[0]', side)
                        emit({'stage': 'decision-error', 'side': side, 'error': record['error'], 'rejected': record['commandsRejected']})
                    last_errors[side] = count
                if time.monotonic() - last_emit >= 15:
                    emit({'stage': 'battle', 'decisions': counts, 'states': {side: snapshot['agents'][side]['status'] for side in counts}, 'errors': {side: snapshot['stats'][side]['errors'] for side in counts}})
                    last_emit = time.monotonic()
                for side, count in counts.items():
                    if count >= args.decisions:
                        page.evaluate('s => { EVA.arena.agents[s].nextAt = Infinity; }', side)
                if all(count >= args.decisions for count in counts.values()):
                    break
                if page.evaluate('QJWGEngine.state()') != 'playing':
                    report['failure'] = {side: snapshot['agents'][side]['summary'] for side in counts}
                    report['snapshot'] = snapshot
                    report['logs'] = page.evaluate('EVA.arena.logger.export()')
                    raise RuntimeError('Battle paused or ended before target decision count')
                if not any(a['isThinking'] for a in snapshot['agents'].values()):
                    page.evaluate('s => __EVA_TEST__.simulate(s)', 10)
                else:
                    page.wait_for_timeout(250)
            page.evaluate('QJWGEngine.pause()')
            report['snapshot'] = page.evaluate('__EVA_TEST__.snapshot()')
            report['logs'] = page.evaluate('EVA.arena.logger.export()')
            report['game'] = page.evaluate('() => { const s=QJWGEngine.readState(); return {elapsed:s.elapsed,towers:s.towers,unitCount:s.units.length}; }')
            report['passed'] = all(report['snapshot']['stats'][side]['decisions'] >= args.decisions and report['snapshot']['stats'][side]['deployed'] > 0 for side in ('player', 'enemy')) and not report['pageErrors']
            page.screenshot(path=str(OUT / 'battle-desktop.png'))
            page.set_viewport_size({'width': 844, 'height': 390})
            page.screenshot(path=str(OUT / 'battle-phone.png'))
            emit({'stage': 'result', 'passed': report['passed'], 'stats': report['snapshot']['stats'], 'game': report['game']})
            browser.close()
    except Exception as e:
        report['passed'] = False
        report['error'] = scrub(str(e))
        emit({'stage': 'failed', 'message': report['error']})
    finally:
        server.shutdown()
        server.server_close()
        safe_report = scrub(report)
        payload = json.dumps(safe_report, ensure_ascii=False, indent=2)
        if any(key in payload for key in secrets):
            raise RuntimeError('Secret redaction failed; report not saved')
        (OUT / 'report.json').write_text(payload, encoding='utf-8')
    return bool(report.get('passed'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--credentials-file', required=True)
    parser.add_argument('--packy-model', default='deepseek-flash')
    parser.add_argument('--deepseek-model', default='deepseek-flash')
    parser.add_argument('--reasoning', choices=['auto', 'none', 'low', 'high', 'max'], default='none')
    parser.add_argument('--decisions', type=int, default=10)
    parser.add_argument('--max-seconds', type=int, default=360)
    arguments = parser.parse_args()
    if not 1 <= arguments.decisions <= 20:
        parser.error('decisions must be between 1 and 20')
    sys.exit(0 if run(arguments) else 1)
