"""Check the published UI iframe in desktop and touch/high-DPR Chromium/WebKit."""
import argparse
import hashlib
import json
import subprocess
from io import BytesIO
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument('--url', default='https://qijing-wangguan.lovable.app')
parser.add_argument('--proxy', help='Optional HTTP proxy for the development network')
args = parser.parse_args()
network = {'proxy': {'server': args.proxy}} if args.proxy else {}
OUT = Path(__file__).resolve().parents[1] / 'output/playwright/published-mobile'
OUT.mkdir(parents=True, exist_ok=True)
report = {'url': args.url, 'checks': [], 'pageErrors': [], 'consoleErrors': [], 'badResources': [], 'navigationRetries': []}


def open_page(context):
    # Keep transient transport failures separate from errors in a loaded game.
    for attempt in range(3):
        page = context.new_page()
        events = {'pageErrors': [], 'consoleErrors': [], 'badResources': []}
        page.on('pageerror', lambda e, events=events: events['pageErrors'].append(str(e)))
        page.on('console', lambda m, events=events: events['consoleErrors'].append(m.text) if m.type == 'error' else None)
        page.on('response', lambda r, events=events: events['badResources'].append({'url':r.url,'status':r.status}) if '/game/' in r.url and r.status >= 400 else None)
        try:
            page.goto(args.url, wait_until='domcontentloaded', timeout=60000)
            return page, events
        except Exception as error:
            if 'net::ERR_TIMED_OUT' not in str(error) or attempt == 2:
                for key in events:
                    report[key].extend(events[key])
                raise
            report['navigationRetries'].append({'attempt': attempt+1, 'error': str(error), 'events': events})
            print('[RETRY] public navigation timed out before the game loaded', flush=True)
            page.close()


def visible_field(png):
    image = Image.open(BytesIO(png)).convert('RGB')
    w, h = image.size
    image = image.crop((int(w*.12), int(h*.26), int(w*.88), int(h*.62)))
    pixels = image.get_flattened_data() if hasattr(image, 'get_flattened_data') else image.getdata()
    cream = sum(r >= 200 and g >= 165 and b >= 100 and r-g > 5 for r,g,b in pixels)
    assert cream > image.width*image.height*.01, 'Published battlefield is blank'
    return cream


try:
    with sync_playwright() as p:
        scenarios = [
            ('desktop', p.chromium, {'viewport': {'width': 1920, 'height': 1080}}),
            ('android-touch', p.chromium, {'viewport': {'width': 844, 'height': 390}, 'is_mobile': True, 'has_touch': True, 'device_scale_factor': 3}),
            ('webkit-touch', p.webkit, {'viewport': {'width': 844, 'height': 390}, 'is_mobile': True, 'has_touch': True, 'device_scale_factor': 3}),
        ]
        for name, engine, options in scenarios:
            if name == 'android-touch':
                options['user_agent'] = 'Mozilla/5.0 (Linux; Android 12; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Mobile Safari/537.36'
            browser = engine.launch(headless=True, **network)
            context = browser.new_context(**options)
            for mode in ['cross', 'straight']:
                page, events = open_page(context)
                game = page.frame_locator('iframe[title="奇境王冠"]')
                game.locator('#startBtn').wait_for(timeout=60000)
                frame = next(f for f in page.frames if '/game/index.html' in f.url)
                frame.wait_for_function("document.readyState==='complete' && typeof CandyField==='object'", timeout=60000)
                assert game.locator('.mode-option').count() == 2 and game.locator('#evaEnterBtn').count() == 0
                game.locator(f'[data-mode="{mode}"]').click()
                game.locator('#startBtn').click()
                game.locator('#menuOverlay').wait_for(state='hidden')
                page.wait_for_timeout(400)
                timer = game.locator('#timer').inner_text()
                # Reproduce fullscreen's short-lived unusable iframe layout.
                frame.evaluate("()=>{const s=document.getElementById('game-shell');s.style.width='1px';s.style.height='1px';dispatchEvent(new Event('resize'));}")
                page.wait_for_timeout(100)
                frame.evaluate("()=>{const s=document.getElementById('game-shell');s.style.removeProperty('width');s.style.removeProperty('height');dispatchEvent(new Event('resize'));}")
                # Canvas-heavy WebKit can need more than 1.5 wall-clock seconds
                # to advance a displayed whole second (the game caps each dt).
                frame.wait_for_function("previous=>document.getElementById('timer').textContent!==previous", arg=timer, timeout=10000)
                assert game.locator('#timer').inner_text() != timer
                game.locator('[data-type="snake"]').click()
                point = frame.evaluate("()=>{const f=CandyField.buildGeometry(innerWidth,innerHeight,'"+mode+"'),p=f.paths[1].at(.75);return CandyField.project(f,p.x,p.y);}")
                game.locator('#gameCanvas').click(position={'x':point['x'],'y':point['y']})
                # The public UI refreshes the cooldown on the next animation frame.
                frame.wait_for_function("Number(document.querySelector('[data-type=\"snake\"] .cool-label').textContent)>0", timeout=5000)
                assert float(game.locator('[data-type="snake"] .cool-label').inner_text()) > 0
                png = page.screenshot(path=str(OUT / f'{name}-{mode}.png'))
                cream = visible_field(png)
                backing = frame.evaluate("()=>{const c=document.getElementById('gameCanvas');return {dpr:c.width/c.clientWidth,pixels:c.width*c.height};}")
                if name != 'desktop':
                    assert 2 <= backing['dpr'] <= 2.51 and backing['pixels'] <= 2205000, backing
                game.locator('#menuBtn').click()
                assert game.locator('#topButtons').is_visible()
                report['checks'].append({'browser':name,'map':mode,'creamPixels':cream,'backing':backing,'timerContinues':True,'deployment':True})
                print(f'[PASS] published {name}/{mode}: battlefield pixels, timer, deployment, transition recovery and menu', flush=True)
                page.close()
                for key in events:
                    report[key].extend(events[key])
            browser.close()
        request = p.request.new_context(**network)
        try:
            report['resources'] = []
            for name in ['index.html','css/style.css','js/candy-field.js','assets/data/resource-manifest.json','assets/images/poison-status-icon-v1.png','assets/audio/BGM.ogg','assets/audio/cannon1.mp3','assets/audio/explosions.mp3']:
                response = request.get(args.url.rstrip('/')+'/game/'+name, timeout=60000)
                expected = subprocess.run(['git','show','UI:'+name], check=True, capture_output=True).stdout
                matches = response.status == 200 and hashlib.sha256(response.body()).digest() == hashlib.sha256(expected).digest()
                report['resources'].append({'path':name,'http':response.status,'matchesUI':matches})
                assert matches, name+' does not match UI source'
                print('[PASS] published source matches UI: '+name, flush=True)
        finally:
            request.dispose()
        assert not report['pageErrors'] and not report['consoleErrors'] and not report['badResources'], report
        report['passed'] = True
        print('[PASS] six public browser/map scenarios; no uncaught errors or failed game resources', flush=True)
finally:
    (OUT/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
