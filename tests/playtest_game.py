"""Real-browser regression using Playwright's bundled Chromium, never system browsers.

Run: python tests/playtest_game.py
Starts an ephemeral local HTTP server; screenshots and report go to output/playwright/.
Python Playwright is a developer tool, not a runtime dependency of the static game.
"""
from __future__ import annotations

import json
import math
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/playwright"
OUT.mkdir(parents=True, exist_ok=True)


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(ROOT)))
threading.Thread(target=server.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{server.server_port}/index.html?test=1"
checks = []
errors = []


def passed(label):
    checks.append(label)
    print(f"[PASS] {label}", flush=True)


with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("response", lambda r: errors.append(f"HTTP {r.status} {r.url}") if r.status >= 400 else None)

    def snapshot():
        return page.evaluate("window.__QJWG_TEST__.snapshot()")

    def step(seconds):
        page.evaluate("s => window.__QJWG_TEST__.step(s)", seconds)

    def menu_item(selector):
        page.locator("#menuBtn").click()
        page.locator(selector).click()

    def fresh(mode="cross", duration="300"):
        page.goto(URL)
        page.locator(f'[data-mode="{mode}"]').click()
        page.locator("#durationSelect").select_option(duration)
        page.locator("#startBtn").click()

    def point(lane=1, t=.82, offroad=False):
        return page.evaluate("""({lane,t,offroad})=>{
          const s=__QJWG_TEST__.snapshot(),f=CandyField.buildGeometry(s.geometry.viewport.w,s.geometry.viewport.h,s.mode),q=f.paths[lane].at(t);
          if(offroad){q.x=f.rs+f.L*.12;q.y=(f.ys[0]+f.cy)/2;}
          return CandyField.project(f,q.x,q.y);
        }""", {"lane": lane, "t": t, "offroad": offroad})

    def drag(selector, target):
        box = page.locator(selector).bounding_box()
        x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        page.mouse.move(x, y)
        page.mouse.down()
        page.mouse.move(x + 12, y - 10)
        page.mouse.move(target["x"], target["y"], steps=12)
        page.mouse.up()
        page.wait_for_timeout(380)  # Existing click suppression following a drag.

    def card_target(type_):
        b = page.locator(f'.card[data-type="{type_}"]').bounding_box()
        return {"x": b["x"] + b["width"] / 2, "y": b["y"] + b["height"] / 2}

    try:
        page.goto(URL)
        assert page.locator("#menuOverlay").is_visible()
        assert page.locator(".map-thumb").count() == 2
        thumbs = page.locator(".map-thumb").evaluate_all("cs=>cs.map(c=>c.toDataURL())")
        assert thumbs[0] != thumbs[1]
        page.screenshot(path=str(OUT / "game-home-desktop.png"))
        passed("首页、两张不同地图缩略图与版本位置")

        fresh()
        s = snapshot()
        assert s["towerHp"] == {"player": 10000, "enemy": 10000}
        assert 15 <= s["coins"]["player"] < 16
        assert s["geometry"]["projection"] == {"top": .8, "bottom": 1}
        p = point(0)
        page.locator('.card[data-type="snake"]').click()
        page.mouse.click(p["x"], p["y"])
        history = page.evaluate("__QJWG_TEST__.spawnHistory()")
        u = next(u for u in history if u["side"] == "player")
        assert u["lane"] == 0 and .01 < u["t"] < .1
        passed("点击敌方半场选择上路，单位从己方门前出生")

        step(6)
        drag('.card[data-type="lion"]', point(2))
        history = page.evaluate("__QJWG_TEST__.spawnHistory()")
        u = next(u for u in history if u["side"] == "player" and u["type"] == "lion")
        assert u["lane"] == 2 and u["t"] < .1
        passed("卡牌拖拽与透视反投影选路")

        step(5)
        drag("#potionBtn", card_target("elephant"))
        assert snapshot()["potionArmed"]["player"] == "elephant"
        assert page.locator('.card[data-type="elephant"]').evaluate("e=>e.classList.contains('armed')")
        step(10)
        page.locator('.card[data-type="elephant"]').click()
        p = point(1)
        page.mouse.click(p["x"], p["y"])
        u = next(u for u in snapshot()["units"] if u["side"] == "player" and u["type"] == "elephant")
        assert u["buffed"] and u["maxHp"] == 2000 and u["regen"] == 40
        assert snapshot()["potionArmed"]["player"] is None
        passed("药水拖卡只强化下一只单位，原属性倍率保留")

        step(10)
        page.locator('.card[data-type="dragon"]').click()
        before = len(page.evaluate("__QJWG_TEST__.spawnHistory()"))
        p = point(offroad=True)
        page.mouse.click(p["x"], p["y"])
        assert len(page.evaluate("__QJWG_TEST__.spawnHistory()")) == before
        passed("草地区域拒绝投放，三路点击容差")

        fresh()
        step(6)
        before = snapshot()["coins"]["player"]
        drag("#burstBtn", point(offroad=True))
        s = snapshot()
        assert s["counters"]["burstUses"] == 0 and s["coins"]["player"] >= before
        drag("#burstBtn", point(0))
        s = snapshot()
        assert s["counters"]["burstUses"] == 1 and s["tacticCool"]["player"]["burst"] > 18
        assert abs(s["audio"]["metrics"]["lastBurstVisualDuration"] - 1.49) < .001
        passed("炮阵拖离道路取消，合法路线连续10炮与1.49秒音频")

        fresh()
        page.locator("#qjwgSeedCannonTargets").click()
        page.wait_for_function("__QJWG_TEST__.snapshot().counters.cannonLaunches >= 2")
        s = snapshot()
        shot = s["lastCannonShot"]
        assert s["config"]["guardCannon"]["groundOrigin"]["y"] == s["config"]["field"]["centerY"]
        for key in ("projectileStart", "muzzleFx", "smokeFx"):
            assert shot[key] == shot["muzzle"]
        projected = page.evaluate("""shot=>{
          const s=__QJWG_TEST__.snapshot(),f=CandyField.buildGeometry(s.geometry.viewport.w,s.geometry.viewport.h,s.mode);
          return CandyField.project(f,shot.muzzle.x,shot.muzzle.y);
        }""", shot)
        assert math.hypot(projected["x"] - shot["visibleMuzzle"]["x"], projected["y"] - shot["visibleMuzzle"]["y"]) < .000001
        assert s["counters"]["cannonLaunches"] == s["audio"]["metrics"]["cannonPlayCount"]
        assert all(s["counters"]["cannonLaunchesBySide"].values())
        assert s["audio"]["bgmReady"] == 4 and s["audio"]["cannonReady"] == 4 and s["audio"]["burstReady"] == 4
        passed("双方可见炮口/炮弹/闪光/烟雾一致；单发次数等于音效次数；音频解码")

        menu_item("#pauseBtn")
        a = snapshot()
        page.wait_for_timeout(300)
        b = snapshot()
        assert a["state"] == b["state"] == "paused" and a["timeLeft"] == b["timeLeft"]
        assert a["coins"] == b["coins"]
        page.set_viewport_size({"width": 844, "height": 390})
        b = snapshot()
        assert [u["t"] for u in a["units"]] == [u["t"] for u in b["units"]]
        assert a["coins"] == b["coins"] and a["towerHp"] == b["towerHp"]
        passed("暂停冻结战斗，窗口缩放保留单位进度/金币/血量")
        menu_item("#pauseBtn")
        menu_item("#reportBtn")
        assert snapshot()["state"] == "paused" and page.locator("#reportOverlay").is_visible()
        assert page.locator("#reportBody tr").count() == 4
        page.screenshot(path=str(OUT / "game-report-phone.png"))
        page.locator("#closeReportBtn").click()
        assert snapshot()["state"] == "playing"
        menu_item("#audioBtn")
        assert page.locator("#audioBtn .btn-icon").inner_text() == "🔇"
        menu_item("#audioBtn")
        assert page.locator("#audioBtn .btn-icon").inner_text() == "🔊"
        passed("暂停/继续、报告自动暂停与恢复、音频开关")

        menu_item("#fullBtn")
        page.wait_for_timeout(200)
        fullscreen = page.evaluate("!!document.fullscreenElement")
        if fullscreen:
            menu_item("#fullBtn")
            page.wait_for_timeout(200)
            assert not page.evaluate("!!document.fullscreenElement")
        passed("全屏入口与退出" if fullscreen else "全屏入口可调用（浏览器策略拒绝时保留提示）")

        menu_item("#homeBtn")
        assert snapshot()["state"] == "menu" and page.locator("#menuOverlay").is_visible()
        assert snapshot()["audio"]["bgmPaused"]
        fresh(duration="180")
        step(181)
        assert snapshot()["state"] == "ended" and page.locator("#resultOverlay").is_visible()
        page.screenshot(path=str(OUT / "game-result-phone.png"))
        page.locator("#restartBtn").click()
        assert snapshot()["state"] == "playing" and snapshot()["towerHp"]["player"] == 10000
        fresh(duration="unlimited")
        step(5)
        assert page.locator("#timer").inner_text() == "∞" and snapshot()["state"] == "playing"
        ai = [u for u in page.evaluate("__QJWG_TEST__.spawnHistory()") if u["side"] == "enemy"]
        assert all(u["at"] >= 3 for u in ai)
        assert all(b["at"]-a["at"] >= 2 for a,b in zip(ai,ai[1:]))
        passed("首页、时间结束结算、重开、无限计时与AI出兵时间")

        for w,h,label in [(1920,1080,"desktop"),(844,390,"phone"),(1024,768,"tablet")]:
            # Mobile auto-fullscreen can leave Chromium's native headless window
            # maximized after document.exitFullscreen. Use a new browser per size.
            browser.close()
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width":w,"height":h}, device_scale_factor=1)
            page.on("pageerror",lambda e:errors.append(str(e)))
            page.on("console",lambda m:errors.append(m.text) if m.type == "error" else None)
            page.on("response",lambda r:errors.append(f"HTTP {r.status} {r.url}") if r.status>=400 else None)
            for mode in ("cross","straight"):
                fresh(mode)
                for type_,lane in [("snake",0),("lion",1),("elephant",2),("dragon",1)]:
                    if snapshot()["coins"]["player"] < 10:
                        step(10)
                    page.locator(f'.card[data-type="{type_}"]').click()
                    p=point(lane,.86)
                    page.mouse.click(p["x"],p["y"])
                    if type_ == "snake":
                        progress=page.evaluate("""()=>{
                          const a=__QJWG_TEST__.snapshot().units.find(u=>u.side==='player'&&u.type==='snake');
                          __QJWG_TEST__.step(.5);
                          const b=__QJWG_TEST__.snapshot().units.find(u=>u.id===a.id);
                          return b.t-a.t;
                        }""")
                        assert math.isclose(progress,80*.5/1070,abs_tol=1e-8)
                menu_item("#pauseBtn")
                page.wait_for_timeout(250)
                layout=page.locator("#bottomDock,.card,#potionBtn,#burstBtn,#menuBtn").evaluate_all("es=>es.map(e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height}})")
                assert all(r["x"]>=0 and r["y"]>=0 and r["x"]+r["w"]<=w+1 and r["y"]+r["h"]<=h+1 for r in layout)
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                assert snapshot()["geometry"]["viewport"] == {"w":w,"h":h}
                assert page.locator(".card").count() == 4
                menu_item("#pauseBtn")
                page.wait_for_timeout(2400)
                page.screenshot(path=str(OUT/f"game-{mode}-{label}.png"))
                if label == "phone" and mode == "cross":
                    menu_item("#reportBtn")
                    assert not page.locator("#reportFormula").evaluate("e=>e.open")
                    page.screenshot(path=str(OUT/"game-report-phone.png"))
                    scroll = page.locator(".report-table-scroll")
                    scroll.evaluate("e=>e.scrollLeft=e.scrollWidth")
                    assert scroll.evaluate("e=>e.scrollLeft > 0")
                    page.locator("#closeReportBtn").click()
            passed(f"{w}×{h} 双地图截图与控件边界/全屏比例")

        browser.close()
        browser=pw.chromium.launch(headless=True)
        page=browser.new_page(viewport={"width":390,"height":844})
        page.on("pageerror",lambda e:errors.append(str(e)))
        page.goto(URL)
        page.wait_for_timeout(150)
        assert page.locator("#mobileGate").is_visible()
        page.screenshot(path=str(OUT/"game-portrait.png"))
        passed("手机竖屏旋转提示")
        page.wait_for_timeout(250)
        assert page.locator("#qjwgTestProbe").text_content()
        assert not errors, errors
        passed("console/pageerror/HTTP 404 为0，隐藏测试探针有效")
        (OUT/"playtest-report.json").write_text(json.dumps({"checks":checks,"errors":errors,"fullscreen":fullscreen},ensure_ascii=False,indent=2),encoding="utf-8")
    except Exception:
        page.screenshot(path=str(OUT/"failure.png"))
        state=snapshot()
        print(json.dumps({"errors":errors,"state":state["state"],"coins":state["coins"],"units":len(state["units"]),"counters":state["counters"]},ensure_ascii=False),flush=True)
        raise
    finally:
        browser.close()
        server.shutdown()
