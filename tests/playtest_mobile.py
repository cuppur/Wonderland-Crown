"""Canvas regression in touch/high-DPR Chromium and native WebKit.

Checks actual battlefield pixels, tiny fullscreen-transition sizes, legacy Canvas
APIs, readback restrictions, orientation, deployment and explicit surface release.
Uses no accounts or personal API settings. Run: python tests/playtest_mobile.py
"""
import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/playwright/mobile"
OUT.mkdir(parents=True, exist_ok=True)


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def copyfile(self, source, output):
        try:
            super().copyfile(source, output)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass  # Closing a WebKit page can cancel its audio resource request.


server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Quiet, directory=str(ROOT)))
threading.Thread(target=server.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{server.server_port}/index.html?test=1"
report = {"checks": [], "pageErrors": [], "consoleErrors": [], "cases": []}
TRACK_CANVASES = """(() => {
  const create=document.createElement.bind(document);window.__MOBILE_CANVASES__=[];
  document.createElement=function(name,...args){const n=create(name,...args);if(name.toLowerCase()==='canvas')__MOBILE_CANVASES__.push(n);return n;};
})();"""
LEGACY = """delete CanvasRenderingContext2D.prototype.roundRect;
delete CanvasRenderingContext2D.prototype.getTransform;
delete CanvasRenderingContext2D.prototype.filter;"""
BLOCK_READBACK = """CanvasRenderingContext2D.prototype.getImageData=function(){throw new DOMException('Canvas readback unavailable','SecurityError');};"""
ANDROID_UA = 'Mozilla/5.0 (Linux; Android 12; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Mobile Safari/537.36'


def battlefield_pixels(png):
    image = Image.open(BytesIO(png)).convert("RGB")
    w, h = image.size
    sample = image.crop((int(w * .12), int(h * .26), int(w * .88), int(h * .62)))
    pixels = sample.get_flattened_data() if hasattr(sample, "get_flattened_data") else sample.getdata()
    cream = sum(r >= 200 and g >= 165 and b >= 100 and r - g > 5 for r, g, b in pixels)
    assert cream > sample.width * sample.height * .01, "Roads/castles missing: only grass/DOM remains"
    return cream


try:
    with sync_playwright() as pw:
        cases = [
            ("desktop", pw.chromium, {"viewport": {"width": 1920, "height": 1080}}, None),
            ("android", pw.chromium, {"viewport": {"width": 844, "height": 390}, "is_mobile": True, "has_touch": True, "device_scale_factor": 3}, None),
            ("android-legacy", pw.chromium, {"viewport": {"width": 844, "height": 390}, "is_mobile": True, "has_touch": True, "device_scale_factor": 3}, LEGACY),
            ("android-readback", pw.chromium, {"viewport": {"width": 844, "height": 390}, "is_mobile": True, "has_touch": True, "device_scale_factor": 3}, BLOCK_READBACK),
            ("webkit-touch", pw.webkit, {"viewport": {"width": 844, "height": 390}, "is_mobile": True, "has_touch": True, "device_scale_factor": 3}, None),
        ]
        for name, engine, options, patch in cases:
            if name.startswith('android'):
                options['user_agent'] = ANDROID_UA
            browser = engine.launch(headless=True)
            for mode in ["cross", "straight"]:
                context = browser.new_context(**options)
                context.add_init_script(TRACK_CANVASES)
                if patch:
                    context.add_init_script(patch)
                page = context.new_page()
                page.on("pageerror", lambda e: report["pageErrors"].append(str(e)))
                page.on("console", lambda m: report["consoleErrors"].append(m.text) if m.type == "error" else None)
                page.goto(url, wait_until="load")
                page.locator(f'[data-mode="{mode}"]').click()
                page.locator("#startBtn").click()
                page.locator("#menuOverlay").wait_for(state="hidden")
                page.wait_for_function("__QJWG_TEST__.snapshot().scene.loaded")
                before = page.evaluate("__QJWG_TEST__.snapshot().timeLeft")
                # Reproduce the short-lived layout state that previously killed RAF.
                for size in [0, 1, 80]:
                    page.evaluate("n=>{const s=document.getElementById('game-shell');s.style.width=n+'px';s.style.height=n+'px';dispatchEvent(new Event('resize'));}", size)
                    page.wait_for_timeout(80)
                page.evaluate("()=>{const s=document.getElementById('game-shell');s.style.removeProperty('width');s.style.removeProperty('height');dispatchEvent(new Event('resize'));}")
                page.wait_for_timeout(450)
                after = page.evaluate("__QJWG_TEST__.snapshot()")
                assert after["scene"]["loaded"] and after["timeLeft"] < before
                # Simulate orientation/viewport changes while preserving gameplay.
                if name != "desktop":
                    page.evaluate("async()=>{if(document.fullscreenElement)await document.exitFullscreen();}")
                    page.set_viewport_size({"width": 390, "height": 844})
                    page.wait_for_timeout(150)
                    assert page.locator("#mobileGate").is_visible()
                    page.set_viewport_size({"width": 844, "height": 390})
                    page.wait_for_timeout(300)
                page.locator('[data-type="snake"]').click()
                point = page.evaluate("()=>{const s=__QJWG_TEST__.snapshot(),f=CandyField.buildGeometry(s.scene.width,s.scene.height,s.mode),p=f.paths[1].at(.75);return CandyField.project(f,p.x,p.y);}")
                page.locator("#gameCanvas").click(position={"x": point["x"], "y": point["y"]})
                assert any(u["type"] == "snake" and u["side"] == "player" for u in page.evaluate("__QJWG_TEST__.snapshot().units"))
                png = page.screenshot(path=str(OUT / f"{name}-{mode}.png"))
                cream = battlefield_pixels(png)
                pool = page.evaluate("()=>({live:__MOBILE_CANVASES__.filter(c=>c.width&&c.height).length,pixels:__MOBILE_CANVASES__.reduce((n,c)=>n+c.width*c.height,0),main:gameCanvas.width*gameCanvas.height})")
                assert pool["live"] == 3 and pool["pixels"] <= pool["main"] * 3, pool
                backing = page.evaluate("()=>({dpr:gameCanvas.width/__QJWG_TEST__.snapshot().scene.width,pixels:gameCanvas.width*gameCanvas.height})")
                if name != "desktop":
                    assert 2 <= backing["dpr"] <= 2.51 and backing["pixels"] <= 2205000, backing
                record = {"browser": name, "map": mode, "creamPixels": cream, "canvasPool": pool, "backing": backing, "timerContinues": True}
                report["cases"].append(record)
                report["checks"].append(name + ":" + mode)
                print(f"[PASS] {name}/{mode}: visible roads/castles, clock, deployment, transient-size recovery, bounded canvas surfaces", flush=True)
                context.close()
            browser.close()
        assert not report["pageErrors"] and not report["consoleErrors"], report
        report["passed"] = True
        print("ALL MOBILE TESTS PASSED: 10 browser/map scenarios", flush=True)
finally:
    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    server.shutdown(); server.server_close()
