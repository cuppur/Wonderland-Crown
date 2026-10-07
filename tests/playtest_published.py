"""Check the deployed stable UI in bundled Chromium; never sends personal APIs."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument('--url', default='https://qijing-wangguan.lovable.app')
args = parser.parse_args()
OUT = Path(__file__).resolve().parents[1] / 'output/playwright/published'
OUT.mkdir(parents=True, exist_ok=True)
report = {'url': args.url, 'checks': [], 'pageErrors': [], 'consoleErrors': [], 'badResources': []}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})
    page.on('pageerror', lambda error: report['pageErrors'].append(str(error)))
    page.on('console', lambda message: report['consoleErrors'].append(message.text) if message.type == 'error' else None)
    page.on('response', lambda response: report['badResources'].append({'url': response.url, 'status': response.status}) if '/game/' in response.url and response.status >= 400 else None)
    page.goto(args.url, wait_until='domcontentloaded', timeout=60000)
    game = page.frame_locator('iframe[title="奇境王冠"]')
    game.locator('#startBtn').wait_for(timeout=45000)
    frame = next(f for f in page.frames if '/game/index.html' in f.url)
    frame.wait_for_function("document.readyState === 'complete' && typeof CandyField === 'object'", timeout=60000)
    assert game.locator('.mode-option').count() == 2
    assert game.locator('#evaEnterBtn').count() == 0
    page.screenshot(path=str(OUT / 'home-desktop.png'))
    game.locator('#startBtn').click()
    game.locator('#menuOverlay').wait_for(state='hidden')
    page.wait_for_timeout(2000)
    assert game.locator('#timer').inner_text() not in ('', '5:00')
    assert game.locator('.card').count() == 4
    game.locator('[data-type="snake"]').click()
    frame = next(f for f in page.frames if '/game/index.html' in f.url)
    point = frame.evaluate("() => { const f=CandyField.buildGeometry(innerWidth,innerHeight,'cross'),p=f.paths[1].at(.75); return CandyField.project(f,p.x,p.y); }")
    page.mouse.click(point['x'], point['y'])
    page.wait_for_timeout(250)
    assert float(game.locator('[data-type="snake"] .cool-label').inner_text()) > 0
    page.screenshot(path=str(OUT / 'battle-desktop.png'))
    report['checks'].append('1920x1080: live homepage, stable UI only, both maps, timer, four cards and deployment')
    print('[PASS] published desktop starts and deploys', flush=True)

    page.set_viewport_size({'width': 844, 'height': 390})
    page.wait_for_timeout(400)
    assert game.locator('#bottomDock').is_visible()
    game.locator('#menuBtn').click()
    assert game.locator('#topButtons').is_visible()
    page.screenshot(path=str(OUT / 'battle-phone.png'))
    report['checks'].append('844x390: battlefield, cards and system menu remain accessible')
    print('[PASS] published phone layout and system menu', flush=True)
    assert not report['pageErrors'] and not report['badResources']
    report['resources'] = []
    for name in ['index.html', 'css/style.css', 'js/candy-field.js', 'assets/data/resource-manifest.json', 'assets/images/poison-status-icon-v1.png', 'assets/audio/BGM.ogg', 'assets/audio/cannon1.mp3', 'assets/audio/explosions.mp3']:
        response = page.request.get(args.url.rstrip('/') + '/game/' + name, timeout=60000)
        expected = subprocess.run(['git', 'show', 'UI:' + name], check=True, capture_output=True).stdout
        matches = response.status == 200 and hashlib.sha256(response.body()).digest() == hashlib.sha256(expected).digest()
        report['resources'].append({'path': name, 'http': response.status, 'matchesUI': matches})
        assert matches, name + ' does not match UI source'
        print('[PASS] published source matches UI: ' + name, flush=True)
    report['checks'].append('all eight public runtime resources match the UI Git blobs byte for byte')
    report['passed'] = True
    browser.close()
(OUT / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('[PASS] no uncaught errors or failed game resources', flush=True)
