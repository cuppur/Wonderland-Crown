"""EVA end-to-end tests in bundled Chromium, with actual local HTTP API fixtures.

No paid API or real key. Run: python tests/playtest_eva.py
Screenshots/evidence: output/playwright/eva-*.png, eva-report.json.
"""
from __future__ import annotations

import importlib.util
import json
import threading
import time
import sys
import socket
QUICK = "--quick" in sys.argv
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/playwright"
OUT.mkdir(parents=True, exist_ok=True)
spec = importlib.util.spec_from_file_location("eva_server", ROOT / "tools/eva_server.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
server = module.make_server(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
records, modes, checks, page_errors, provider_results = [], {}, [], [], {}
mock_result = None
TEST_KEY = "eva-fixture-token-not-a-real-key"
MODELS = {"openai": "gpt-5-mini", "compatible": "local-commander", "anthropic": "claude-fixture", "gemini": "gemini-2.5-flash", "deepseek": "deepseek-flash", "custom": "custom-commander"}


class Fixture(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def send(self, status, data):
        payload = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", f"http://127.0.0.1:{server.server_port}")
        self.send_header("Access-Control-Allow-Headers", "authorization,content-type,x-api-key,x-goog-api-key,anthropic-version")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        try:
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_OPTIONS(self):
        self.send(200, {})

    def do_GET(self):
        provider = self.path.split("/")[1]
        if modes.get(provider) == "no-models":
            self.send(404, {"error": "models unsupported"})
            return
        model = {"id": MODELS[provider]}
        if provider in {"openai", "compatible", "custom"}:
            model["supported_reasoning_efforts"] = ["low", "medium", "high"]
        if provider == "anthropic":
            model["capabilities"] = {"effort": {"supported": True, "low": {"supported": True}, "medium": {"supported": True}, "high": {"supported": True}}, "thinking": {"types": {"adaptive": {"supported": True}}}}
        if provider == "gemini":
            self.send(200, {"models": [{"name": "models/" + MODELS[provider], "supportedGenerationMethods": ["generateContent"], "inputTokenLimit": 10000}, {"name": "models/embedding-fixture", "supportedGenerationMethods": ["embedContent"]}]})
        else:
            self.send(200, {"data": [model]})

    def do_POST(self):
        provider = self.path.split("/")[1]
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        key = self.headers.get("x-api-key") or self.headers.get("x-goog-api-key") or self.headers.get("Authorization", "").removeprefix("Bearer ")
        if key != TEST_KEY:
            self.send(401, {"error": {"message": key}})  # Verify upstream error bodies cannot leak keys.
            return
        mode = modes.get(provider)
        if mode == 'disconnect':
            self.connection.shutdown(socket.SHUT_RDWR)
            self.connection.close()
            return
        if mode in {"401", "403", "429", "500", "504"}:
            self.send(int(mode), {"error": {"message": TEST_KEY}})
            return
        if mode == "slow":
            time.sleep(1)
        if mode == "very-slow":
            time.sleep(5)
        if provider == "gemini":
            user = body["contents"][0]["parts"][0]["text"]
        else:
            user = body["messages"][-1]["content"]
        data = json.loads(user)
        observation = data["observation"]
        assert observation["schemaVersion"] == 1
        assert "self" in observation and "enemy" in observation
        assert not any(word in user.lower() for word in ["image_url", "data:image", "canvas", "outerhtml", "screenshot"])
        records.append({"provider": provider, "body": body, "observation": observation})
        commands = [] if data["memory"].get("connectionTest") else [{"action": "advance", "lane": "middle"}]
        if mode == "invalid-command":
            commands = [{"action": "deploy", "unit": "unicorn", "lane": "outerspace"}]
        packet = {"schemaVersion": 1, "summary": "结构化观察已接收，中路继续前进。", "commands": commands}
        text = "invalid json" if mode == "invalid-json" else json.dumps(packet, ensure_ascii=False)
        if mode == "echo-secret":
            packet["summary"] = TEST_KEY
            text = json.dumps(packet)
        if provider == "anthropic":
            response = {"model": MODELS[provider], "content": [{"type": "thinking", "thinking": "PRIVATE_THOUGHT_SENTINEL"}, {"type": "text", "text": text}], "usage": {"input_tokens": 100, "output_tokens": 20}, "stop_reason": "end_turn"}
        elif provider == "gemini":
            response = {"candidates": [{"content": {"parts": [{"thought": True, "text": "PRIVATE_THOUGHT_SENTINEL"}, {"text": text}]}, "finishReason": "STOP"}], "usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 20, "thoughtsTokenCount": 5}}
        else:
            response = {"model": MODELS[provider], "choices": [{"message": {"content": text, "reasoning_content": "PRIVATE_THOUGHT_SENTINEL"}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 100, "completion_tokens": 20, "completion_tokens_details": {"reasoning_tokens": 5}}}
        self.send(200, response)


fixture = ThreadingHTTPServer(("127.0.0.1", 0), Fixture)
threading.Thread(target=fixture.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{server.server_port}/index.html?test=1"


def passed(message):
    checks.append(message)
    print("[PASS] " + message, flush=True)


def server_request(path, method="GET", data=None, origin=None):
    req = Request(URL.split("/index.html")[0] + path, method=method, data=json.dumps(data).encode() if data else None, headers={"Origin": origin or f"http://127.0.0.1:{server.server_port}", "Content-Type": "application/json"})
    try:
        with urlopen(req) as r:
            return r.status, r.read()
    except HTTPError as e:
        return e.code, e.read()


try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.on("pageerror", lambda e: page_errors.append(str(e)))

        def snap():
            return page.evaluate("__EVA_TEST__.snapshot()")

        def fresh():
            page.goto(URL)
            page.locator("#evaEnterBtn").click()
            for side in ["player", "enemy"]:
                page.locator(f'[data-side="{side}"] [data-field="provider"]').select_option("mock")

        def control(side, name):
            return page.locator(f'[data-side="{side}"] [data-field="{name}"]')

        def simulate(seconds):
            return page.evaluate("s=>__EVA_TEST__.simulate(s)", seconds)

        def settings(side, provider="compatible"):
            control(side, "provider").select_option(provider)
            control(side, "baseUrl").fill(f"http://127.0.0.1:{fixture.server_port}/{provider}/v1")
            control(side, "apiKey").fill(TEST_KEY)
            control(side, "model").fill(MODELS[provider])

        def config_op(side, op):
            page.locator(f'[data-side="{side}"] [data-op="{op}"]').click()
            page.wait_for_function("s=>!document.querySelector(`[data-side='${s}'] [data-op='test']`).disabled", arg=side)

        def start():
            page.locator("#evaStartBtn").click()
            page.wait_for_function("QJWGEngine.state()==='playing'")

        # Ordinary play remains the same on the feature branch.
        page.goto(URL)
        assert page.locator(".mode-option").count() == 2
        page.screenshot(path=str(OUT / "eva-home-desktop.png"))
        page.locator("#startBtn").click()
        page.locator('[data-type="snake"]').click()
        point = page.evaluate("()=>{const s=__QJWG_TEST__.snapshot(),f=CandyField.buildGeometry(1920,1080,s.mode),p=f.paths[1].at(.8);return CandyField.project(f,p.x,p.y)}")
        page.mouse.click(point["x"], point["y"])
        assert page.evaluate("__QJWG_TEST__.spawnHistory().some(u=>u.side==='player')")
        assert not page.evaluate("__EVA_TEST__.snapshot().active")
        passed("ordinary mode still deploys via cards; EVA is inactive")

        fresh()
        page.screenshot(path=str(OUT / "eva-config-desktop.png"))
        assert control("enemy", "interval").is_disabled()
        control("player", "interval").select_option("5")
        assert control("enemy", "interval").input_value() == "5"
        page.locator("#evaFair").uncheck()
        control("enemy", "interval").select_option("2")
        page.locator("#evaFair").check()
        control("player", "interval").select_option("3")
        assert control("enemy", "interval").input_value() == "3"
        page.locator("#evaDebugEnabled").check()
        config_op("player", "test"); config_op("enemy", "test")
        start(); simulate(70)
        s = snap()
        assert all(s["stats"][side]["deployed"] > 0 and s["stats"][side]["potions"] > 0 and s["stats"][side]["bursts"] > 0 for side in ["player", "enemy"])
        assert not any(s["stats"][side]["rejected"] for side in ["player", "enemy"])
        assert all(len(a["memory"]["recentObservations"]) <= 6 and len(a["memory"]["recentCommands"]) <= 8 for a in s["agents"].values())
        assert page.locator("#evaAgent-player").is_visible() and page.locator("#evaAgent-enemy").is_visible()
        page.screenshot(path=str(OUT / "eva-battle-desktop.png"))
        bounds = page.locator("#bottomDock").bounding_box()
        blue, red = [page.locator("#evaAgent-" + side).bounding_box() for side in ["player", "enemy"]]
        assert blue["x"] + blue["width"] < bounds["x"] and red["x"] > bounds["x"] + bounds["width"]
        passed("Mock agents deploy/use both skills through v1 protocol; fair periods, bounded memory, edge panels")

        page.locator("#evaAgent-player button").click()
        assert page.evaluate("QJWGEngine.state()") == "paused"
        assert page.locator(".eva-log-table tbody tr").count() > 0
        page.locator("#evaDebugTab").click()
        assert "observationId" in page.locator("#evaDebugBody").inner_text()
        page.screenshot(path=str(OUT / "eva-debug-desktop.png"))
        page.locator("#evaLogTab").click()
        with page.expect_download() as dl:
            page.locator("#evaExportBtn").click()
        export = json.loads(Path(dl.value.path()).read_text(encoding="utf-8"))
        assert all(k in export["entries"][0] for k in ["timestamp", "observationId", "decisionId", "commandsRequested", "commandsAccepted", "commandsRejected", "retryCount", "reasoningTokens", "estimatedCost"])
        page.locator("#evaLogsClose").click()
        assert page.evaluate("QJWGEngine.state()") == "playing"
        passed("complete logs/debug/export work; opening logs pauses and resumes without stale requests")

        if not QUICK:
            for batch in range(20):
                if page.evaluate("QJWGEngine.state()") == "ended":
                    break
                simulate(120)
                if batch % 4 == 0:
                    print(f"[PROGRESS] Mock battle simulation {batch + 1} x 120s", flush=True)
            assert page.evaluate("QJWGEngine.state()") == "ended"
            assert min(page.evaluate("Object.values(__QJWG_TEST__.snapshot().towerHp)")) == 0
            assert "胜者" in page.locator("#resultTitle").inner_text()
            assert page.locator(".eva-result-table").is_visible()
            assert not any(a["isThinking"] for a in snap()["agents"].values())
            mock_result = {"elapsed": page.evaluate("QJWGEngine.clock()"), "towerHp": page.evaluate("__QJWG_TEST__.snapshot().towerHp"), "stats": snap()["stats"]}
            page.screenshot(path=str(OUT / "eva-result-desktop.png"))
            passed("full autonomous Mock battle reaches tower HP zero and EVA result without altering balance")
    

        # Live engine command behavior: no mock or LLM scheduler during these deterministic checks.
        fresh(); page.evaluate("EVA.view.start(); EVA.arena.stop()")
        def submit(commands, side="player"):
            return page.evaluate("({commands,side})=>__EVA_TEST__.submit(side,{schemaVersion:1,summary:'test',commands})", {"side": side, "commands": commands})
        invalid = submit([{ "action": "deploy", "unit": "toString", "lane": "top" }, {"action": "focusTarget", "lane": "middle", "targetId": 99999}, {"action": "deploy", "unit": "snake", "lane": "invalid"}, {"action": "setRallyPoint", "lane": "top", "progress": -1}, {"action": "hack", "lane": "top"}])
        assert len(invalid["accepted"]) == 0 and len(invalid["rejected"]) == 5
        legal = submit([{ "action": "deploy", "unit": "snake", "lane": "top" }, { "action": "deploy", "unit": "snake", "lane": "top" }, { "action": "deploy", "unit": "lion", "lane": "bottom" }])
        assert len(legal["accepted"]) == 1 and {r["reason"] for r in legal["rejected"]} == {"DUPLICATE", "INSUFFICIENT_COINS"}
        over = submit([{"action": "hold", "lane": "top"}] * 8)
        assert any(r["reason"] == "COMMAND_LIMIT" for r in over["rejected"])
        submit([{"action": "advance", "lane": "top"}]); page.evaluate("__QJWG_TEST__.step(1)")
        before = page.evaluate("()=>{const before=__EVA_TEST__.observation('player').units.find(u=>u.owner==='self').progress;__EVA_TEST__.submit('player',{schemaVersion:1,commands:[{action:'hold',lane:'top'}]});__QJWG_TEST__.step(1);return before;}")
        assert before == page.evaluate("__EVA_TEST__.observation('player').units.find(u=>u.owner==='self').progress")
        submit([{"action": "retreat", "lane": "top"}]); page.evaluate("__QJWG_TEST__.step(.5)")
        assert page.evaluate("__EVA_TEST__.observation('player').units.find(u=>u.owner==='self').progress") < before
        submit([{"action": "advance", "lane": "top"}]); page.evaluate("__QJWG_TEST__.step(.5)")
        target = submit([{"action": "focusTarget", "lane": "top", "targetId": "enemy-tower"}]); assert len(target["accepted"]) == 1
        submit([{"action": "setRallyPoint", "lane": "top", "progress": .12}]); page.evaluate("__QJWG_TEST__.step(4)")
        o = page.evaluate("__EVA_TEST__.observation('player')")
        own = next(u for u in o["units"] if u["owner"] == "self")
        assert own["progress"] == .12 and own["order"] == "hold"
        submit([{"action": "switchLane", "lane": "top", "toLane": "bottom"}]); page.evaluate("__QJWG_TEST__.step(5.5)")
        o = page.evaluate("__EVA_TEST__.observation('player')")
        assert next(u for u in o["units"] if u["owner"] == "self")["lane"] == "bottom"
        # Symmetric observations from equal own-gate deployments, including cross lane mapping.
        fresh(); page.evaluate("EVA.view.start(); EVA.arena.stop()")
        page.evaluate("['player','enemy'].forEach(side=>__EVA_TEST__.submit(side,{schemaVersion:1,commands:[{action:'deploy',unit:'elephant',lane:'top'}]}))")
        observations = page.evaluate("['player','enemy'].map(s=>__EVA_TEST__.observation(s))")
        for o in observations:
            assert o["schemaVersion"] == 1 and o["self"]["coins"] == o["enemy"]["coins"]
            assert "canvas" not in json.dumps(o).lower()
        a, b = [next(u for u in o["units"] if u["owner"] == "self") for o in observations]
        assert a["lane"] == b["lane"] == "top" and a["progress"] == b["progress"] and a["position"] == b["position"]
        passed("live validator rejects bad/duplicate/over-budget/over-limit commands; hold/retreat/advance/focus/rally/switch and symmetry")

        # Exercise real HTTP adapters through UI and the loopback relay. Each gets >=10 valid decisions.
        for provider in MODELS:
            fresh(); settings("player", provider); settings("enemy", provider)
            for side in ["player", "enemy"]:
                config_op(side, "models")
                assert control(side, "reasoning").is_enabled()
                control(side, "reasoning").select_option("high")
                config_op(side, "test")
                assert "连接测试通过" in page.locator(f'[data-side="{side}"] [data-info="connection"]').inner_text()
            start()
            for _ in range(10):
                simulate(20); page.wait_for_timeout(50)
                if all(snap()["stats"][side]["decisions"] >= 10 for side in ["player", "enemy"]): break
            s = snap(); assert all(s["stats"][side]["decisions"] >= 10 for side in ["player", "enemy"])
            provider_results[provider] = {side: s["stats"][side]["decisions"] for side in ["player", "enemy"]}
            assert all(s["stats"][side]["inputTokens"] >= 1000 for side in ["player", "enemy"])
            latest = next(r for r in reversed(records) if r["provider"] == provider)["body"]
            if provider == "anthropic": assert latest["output_config"]["effort"] == "high" and latest["thinking"]["type"] == "adaptive"
            elif provider == "gemini": assert "thinkingBudget" in latest["generationConfig"]["thinkingConfig"] and "thinkingLevel" not in latest["generationConfig"]["thinkingConfig"]
            else: assert latest["reasoning_effort"] == "high"
            content = page.evaluate("JSON.stringify({log:EVA.arena.logger.export(),snap:__EVA_TEST__.snapshot()})")
            assert "PRIVATE_THOUGHT_SENTINEL" not in content and TEST_KEY not in content
            passed(provider + " UI -> models -> reasoning -> connection -> both agents >=10 HTTP decisions; private reasoning excluded")

        # Model-specific capability boundaries and explicit compatible override.
        caps = page.evaluate("""()=>{
          const cap=(provider,model)=>EVA.Providers.reasoningCapability({provider,model}).levels;
          return {pro:cap('gemini','gemini-3-pro-preview'),newFlash:cap('gemini','gemini-3.8-flash'),unknown:cap('openai','unknown-model'),
            budget:EVA.Providers.normalizeReasoningLevel({provider:'gemini',model:'gemini-2.5-flash',reasoning:'high',maxTokens:8192}),
            override:EVA.Providers.normalizeReasoningLevel({provider:'compatible',model:'local-unknown',reasoningProtocol:'effort',reasoning:'medium'})};
        }""")
        assert caps['pro'] == ['auto', 'low', 'high'] and 'minimal' not in caps['newFlash']
        assert caps['unknown'] == ['auto'] and 'thinkingBudget' in caps['budget']['thinkingConfig']
        assert caps['override']['reasoning_effort'] == 'medium'
        passed("model-specific reasoning subsets, Gemini budget vs level, unknown Auto and explicit compatible override")

        # CORS direct transport and redaction even if a model echoes a credential in public text.
        fresh(); settings('player'); page.locator('[data-side="player"] details summary').click(); control('player','transport').select_option('direct')
        config_op('player','test'); start(); simulate(5)
        assert snap()['stats']['player']['decisions'] > 0
        modes['compatible'] = 'echo-secret'; simulate(8)
        content = page.evaluate("JSON.stringify({log:EVA.arena.logger.export(),snap:__EVA_TEST__.snapshot()})")
        assert TEST_KEY not in content and '[REDACTED]' in content
        modes['compatible'] = None
        passed("direct CORS transport works and keys echoed in model text are removed from UI/debug/memory/log")

        # Unsupported /models still permits manual model ID and successful connection.
        modes["compatible"] = "no-models"; fresh(); settings("player")
        config_op("player", "models")
        assert "手动输入" in page.locator('[data-side="player"] [data-info="connection"]').inner_text()
        config_op("player", "test"); start(); simulate(4)
        assert snap()["stats"]["player"]["decisions"] > 0
        modes["compatible"] = None
        passed("/models unsupported has manual fallback; no requirement to choose from a fixed model list")

        # Bad key / URL and HTTP failures stay on configuration page without a JS exception.
        fresh(); settings("player"); control("player", "apiKey").fill("intentionally-invalid-fixture-key"); config_op("player", "test")
        assert "401" in page.locator('[data-side="player"] [data-info="connection"]').inner_text()
        control("player", "baseUrl").fill("not-a-url"); config_op("player", "test")
        assert "无效" in page.locator('[data-side="player"] [data-info="connection"]').inner_text()
        control("player", "baseUrl").fill("http://127.0.0.1:1/v1"); config_op("player", "test")
        assert "502" in page.locator('[data-side="player"] [data-info="connection"]').inner_text()
        passed("wrong key, malformed URL and unreachable upstream fail clearly without exposing keys or crashing")

        # One error waits; repeated errors pause, retry and reconfigure keep the current battle.
        for fault in ["401", "403", "429", "500", "504", "invalid-json", "invalid-command", "disconnect"]:
            modes["compatible"] = None; fresh(); settings("player"); config_op("player", "test"); start(); simulate(4)
            old_elapsed = page.evaluate("QJWGEngine.readState().elapsed")
            modes["compatible"] = fault; simulate(3.5)
            assert page.evaluate("QJWGEngine.state()") == "playing"
            simulate(12)
            assert page.evaluate("QJWGEngine.state()") == "paused" and snap()["failedSide"] == "player"
            assert page.locator("#evaFailureOverlay").is_visible()
            assert snap()["stats"]["player"]["errors"] >= 3
            if fault == "429": page.screenshot(path=str(OUT / "eva-error-desktop.png"))
            modes["compatible"] = None; page.locator("#evaRetry").click(); simulate(3.5)
            assert page.evaluate("QJWGEngine.state()") == "playing" and snap()["agents"]["player"]["errors"] == 0
            assert page.evaluate("QJWGEngine.readState().elapsed") > old_elapsed
            passed(fault + " -> WAIT -> three errors pause -> retry resumes preserved battle")

        modes["compatible"] = None; fresh(); settings("player"); config_op("player", "test"); start(); simulate(4)
        modes["compatible"] = "429"; simulate(13)
        before = page.evaluate("QJWGEngine.readState().elapsed")
        page.locator("#evaReconfigure").click(); control("player", "provider").select_option("mock"); page.locator("#evaStartBtn").click(); simulate(2)
        assert page.evaluate("QJWGEngine.readState().elapsed") > before and snap()["agents"]["player"]["errors"] == 0
        passed("reconfigure replaces a failed adapter without resetting health/time/memory/log")

        # Abort/deadline test and concurrent protection. Test-only short deadline avoids a 10s real wait.
        modes["compatible"] = None; fresh(); settings("player"); config_op("player", "test"); start(); simulate(1)
        modes["compatible"] = "slow"
        page.evaluate("EVA.arena.agents.player.config.timeout=.15;EVA.arena.agents.player.nextAt=QJWGEngine.readState().elapsed")
        for _ in range(3):
            simulate(.25); page.wait_for_timeout(300); simulate(3.5)
        assert page.evaluate("QJWGEngine.state()") == "paused"
        assert snap()["stats"]["player"]["errors"] >= 3
        assert "TIMEOUT" in snap()["agents"]["player"]["summary"]
        passed("actual AbortController deadline aborts slow HTTP calls and pauses after three timeouts")

        modes["compatible"] = None; fresh(); settings("player"); config_op("player", "test"); start(); simulate(1)
        page.wait_for_function("!EVA.arena.agents.player.isThinking")
        modes["compatible"] = "very-slow"; before = len(records)
        page.evaluate("EVA.arena.agents.player.nextAt=QJWGEngine.readState().elapsed")
        simulate(15); page.wait_for_timeout(120)
        assert snap()["agents"]["player"]["isThinking"]
        assert len(records) == before
        page.locator("#menuBtn").click(); page.locator("#pauseBtn").click()
        stats = snap()["stats"]["player"]
        assert not snap()["agents"]["player"]["isThinking"]
        assert page.evaluate("QJWGEngine.state()") == "paused"
        page.wait_for_timeout(5500)
        assert snap()["stats"]["player"] == stats
        assert not any(a["isThinking"] for a in snap()["agents"].values())
        passed("one in-flight call per agent even across many decision periods; pause discards late response and records cancellation")

        # Forfeit, exiting home, restarting normal mode and no credentials in browser storage/log.
        modes["compatible"] = None; fresh(); settings("player"); config_op("player", "test"); page.locator("#evaRemember").check(); start(); simulate(2)
        persisted = page.evaluate("localStorage.getItem('qjwg-eva-settings-v1')")
        assert TEST_KEY not in persisted and 'apiKey' not in persisted
        modes["compatible"] = "invalid-json"; simulate(15); page.locator("#evaForfeit").click()
        assert page.evaluate("QJWGEngine.state()") == "ended" and "AI 连接异常判负" in page.locator("#resultDetail").inner_text()
        page.locator("#backMenuBtn").click(); assert not snap()["active"]
        page.locator("#startBtn").click(); assert not page.evaluate("QJWGEngine.isEva()")
        page.reload(); page.locator("#evaEnterBtn").click(); assert control("player", "apiKey").input_value() == ""
        passed("forfeit/result/home/normal mode work; only explicit non-secret settings persist, keys disappear on reload")
        modes["compatible"] = None

        # Two additional responsive layouts and straight map, using fresh pages (mobile fullscreen).
        for width, height, name in [(1648, 928, "target"), (844, 390, "phone"), (1024, 768, "tablet")]:
            page.close(); page = browser.new_page(viewport={"width": width, "height": height}); page.on("pageerror", lambda e: page_errors.append(str(e)))
            fresh(); page.screenshot(path=str(OUT / f"eva-config-{name}.png")); page.locator("#evaDebugEnabled").check(); page.locator("#evaMap").select_option("straight"); start(); simulate(20)
            assert len(page.evaluate("__QJWG_TEST__.spawnHistory()")) >= 2
            page.screenshot(path=str(OUT / f"eva-battle-{name}.png"))
            for side in ["player", "enemy"]:
                box = page.locator("#evaAgent-" + side).bounding_box()
                assert box["width"] > 30 and box["x"] >= 0 and box["x"] + box["width"] <= width
            rejected = page.evaluate("__EVA_TEST__.submit('player',{schemaVersion:1,summary:'test',commands:[{action:'switchLane',lane:'top',toLane:'bottom'}]}).rejected")
            assert rejected[0]["reason"] == "LANE_SWITCH_UNAVAILABLE"
            page.locator("#evaAgent-enemy button").click(); assert page.locator("#evaLogsOverlay").is_visible(); page.screenshot(path=str(OUT / f"eva-log-{name}.png")); page.locator("#evaLogsClose").click()
            passed(f"{width}x{height} responsive EVA config/straight battle/log; straight map rejects switchLane")

        # Relay rejects cross-origin callers, recursive destinations and non-API URLs.
        assert server_request("/eva/api/health")[0] == 200
        assert server_request("/eva/api/proxy", "POST", {"url": "https://example.com/chat/completions", "method": "GET"}, "https://untrusted.example")[0] == 403
        assert server_request("/eva/api/proxy", "POST", {"url": "file:///etc/passwd", "method": "GET"})[0] == 400
        assert server_request("/.git/config")[0] == 404
        assert server_request("/TASK_STATE.md")[0] == 404
        passed("loopback relay host/origin/path protections and no-secret static serving")
        assert not page_errors, page_errors
        passed("zero uncaught browser exceptions in all success and injected-error flows")
        browser.close()
finally:
    fixture.shutdown(); fixture.server_close(); server.shutdown(); server.server_close()
    (OUT / "eva-report.json").write_text(json.dumps({"checks": checks, "pageErrors": page_errors, "httpFixtureRequests": len(records), "providerDecisions": provider_results, "mockResult": mock_result, "quick": QUICK, "realPaidApiTested": False}, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"EVA: {len(checks)} checks passed; real paid API not used.", flush=True)
