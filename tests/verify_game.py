from __future__ import annotations

import hashlib
import shutil
import struct
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "源代码" / "游戏源代码.html"
TABLE_DIR = ROOT / "单位属性表"
EXPECTED_TABLE = "20260710.xlsx"
EXPECTED_TABLE_SHA256 = "236C40B268A140DD11A5C16ABDAB886019A5714E850613C0FDFB3553E3E83D55"


def fail(message: str) -> None:
    print(f"[FAIL] {message}")
    raise SystemExit(1)


def require(source: str, token: str, label: str) -> None:
    if token not in source:
        fail(f"缺少 {label}: {token}")


def forbid(source: str, token: str, label: str) -> None:
    if token in source:
        fail(f"发现不应存在的 {label}: {token}")


if not HTML.is_file():
    fail(f"找不到游戏文件：{HTML}")

tables = [p for p in TABLE_DIR.glob("*.xlsx") if p.stem.isdigit()]
if not tables:
    fail("单位属性表目录中没有按日期命名的 xlsx")
latest = max(tables, key=lambda p: int(p.stem))
if latest.name != EXPECTED_TABLE:
    fail(f"发现更新的属性表 {latest.name}；请先重新同步游戏数值")
table_hash = hashlib.sha256(latest.read_bytes()).hexdigest().upper()
if table_hash != EXPECTED_TABLE_SHA256:
    fail(f"{latest.name} 内容已变化；请重新读取并同步属性")

source = HTML.read_text(encoding="utf-8")

required = {
    "游戏标题": "<title>奇境王冠</title>",
    "微软 Emoji 字体": 'font-family:"Segoe UI Emoji"',
    "蛇最新属性": "snake:{name:'毒影蛇',cost:10,hp:400,attack:10,speed:100,range:60,interval:.2,cooldown:3,regen:10",
    "狮最新属性": "lion:{name:'圣鬃狮',cost:10,hp:500,attack:20,speed:70,range:70,interval:.5,cooldown:3,regen:10",
    "象最新属性": "elephant:{name:'磐石象',cost:10,hp:800,attack:15,speed:50,range:80,interval:.8,cooldown:3,regen:20",
    "龙最新属性": "dragon:{name:'星焰龙',cost:15,hp:600,attack:25,speed:60,range:100,interval:1,cooldown:5,regen:15",
    "药水属性": "const POTION={cost:7,cooldown:15};",
    "爆裂炮属性": "const BURST={cost:20,cooldown:25,damage:1000,shots:10};",
    "守门炮属性": "const GUARD_CANNON={interval:.5,windup:.28,damage:30,rangeFactor:.25};",
    "城门血量": "kind:'tower',side,hp:7000,maxHp:7000",
    "金币增长": "this.coins.player+=2*dt;this.coins.enemy+=2*dt;",
    "加长道路": "roadStart:75,roadEnd:1205",
    "连续交汇路面": "ctx.fill(outer,'evenodd')",
    "生成花园背景": "./assets/fairy-garden-battlefield-v1.png",
    "生成城堡立绘": "./assets/fairy-castle-gate-v1.png",
    "生成道路纹理": "./assets/fairy-road-stone-texture-v1.png",
    "生成童话炮身": "./assets/fairy-cannon-barrel-v1.png",
    "道路纹理蒙版": "ctx.fillStyle=this.roadPattern()||'#f7dfaa'",
    "底部卡牌与金币": "#bottomDock{top:auto;bottom:1.2%",
    "左下战术键": "#tactical{top:auto;left:1.2%;right:auto;bottom:1.4%",
    "返回首页按钮": 'id="homeBtn"',
    "暂停按钮": 'id="pauseBtn"',
    "BGM 文件": "../音效/BGM/BGM%20.ogg",
    "单发音效": "../音效/加农炮/单发/cannon1.mp3",
    "连发音效": "../音效/加农炮/连发/explosions.mp3",
    "单炮出膛触发一次": "this.cannonLaunches++;audio.playCannon(flight+FX_TIMING.cannonExplosion)",
    "单发音频限时": "this.playTimed(voice,clipped,false)",
    "十连发动画时长": "const BURST_VISUAL_DURATION=FX_TIMING.burstLead+(BURST.shots-1)*FX_TIMING.burstStep+FX_TIMING.burstExplosion;",
    "十连发音频拟合": "this.playTimed(this.burstVoice,visualDuration,true)",
    "纯视觉药水放大": "u.visualScale=1.3",
    "音频逐帧截止": "audio.updateClips();game.update(dt)",
    "全场部署参数": "deploy(side,type,lane,spawnT=null)",
    "点击部署点贴合道路": "if(target.d>DEPLOY_SNAP_RADIUS){this.hint('请点击道路范围内');return;}if(this.deploy('player',s.type,target.i,target.t))",
    "拖拽部署点贴合道路": "if(target.d>DEPLOY_SNAP_RADIUS)game.hint('请拖到道路范围内');else if(!game.deploy('player',d.type,target.i,target.t))",
    "道路吸附半径": "const DEPLOY_SNAP_RADIUS=52;",
    "连发元数据竞态兜底": "this.burstVoice.fallbackDuration=11.740862",
}
for label, token in required.items():
    require(source, token, label)

forbidden = {
    "旧吸血逻辑": "lifesteal",
    "旧城墙 5000 魔数": "maxHp===5000",
    "旧圆形交汇函数": "drawCrossHub",
    "药水放大判定体积": "u.size*=1.3",
    "临时 UI 原型": "layoutPrototype",
    "临时原型切换器": "layoutPrototypeSwitcher",
    "旧己方半场提示": "只能在己方半场部署",
    "旧己方半场点击限制": "p.x>FIELD.centerX",
    "旧己方半场寻路限制": "nearestLane(p,true)",
}
for label, token in forbidden.items():
    forbid(source, token, label)

assets = [
    ROOT / "音效" / "BGM" / "BGM .ogg",
    ROOT / "音效" / "加农炮" / "单发" / "cannon1.mp3",
    ROOT / "音效" / "加农炮" / "连发" / "explosions.mp3",
]
for asset in assets:
    if not asset.is_file() or asset.stat().st_size <= 0:
        fail(f"音频资源无效：{asset}")

png_assets = {
    ROOT / "源代码" / "assets" / "fairy-garden-battlefield-v1.png": (1200, 675, False),
    ROOT / "源代码" / "assets" / "fairy-castle-gate-v1.png": (512, 512, True),
    ROOT / "源代码" / "assets" / "fairy-road-stone-texture-v1.png": (512, 512, False),
    ROOT / "源代码" / "assets" / "fairy-cannon-barrel-v1.png": (512, 256, True),
}
for asset, (min_w, min_h, needs_alpha) in png_assets.items():
    if not asset.is_file() or asset.stat().st_size <= 0:
        fail(f"图片资源无效：{asset}")
    head = asset.read_bytes()[:26]
    if len(head) < 26 or head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        fail(f"图片不是有效 PNG：{asset}")
    width, height = struct.unpack(">II", head[16:24])
    color_type = head[25]
    if width < min_w or height < min_h:
        fail(f"图片分辨率过低：{asset} ({width}x{height})")
    if needs_alpha and color_type not in (4, 6):
        fail(f"城堡立绘缺少透明通道：{asset}")

node = shutil.which("node")
if not node:
    fail("未找到 Node.js，无法执行 JavaScript 语法检查")
syntax_check = (
    "const fs=require('fs');"
    "const s=fs.readFileSync(process.argv[1],'utf8');"
    "const blocks=[...s.matchAll(/<script(?:\\s[^>]*)?>([\\s\\S]*?)<\\/script>/gi)];"
    "for(const b of blocks)new Function(b[1]);"
    "console.log(blocks.length);"
)
result = subprocess.run(
    [node, "-e", syntax_check, str(HTML)],
    text=True,
    capture_output=True,
    check=False,
)
if result.returncode != 0:
    fail(f"JavaScript 语法错误：{result.stderr.strip()}")

print("[PASS] 最新属性表未被修改，且仍为 20260710.xlsx")
print("[PASS] 四单位、药水、城门、金币、爆裂炮和守门炮静态配置已同步")
print("[PASS] 底部卡牌、左下战术键、双地图道路与系统按钮契约存在")
print("[PASS] BGM、单发炮、连发炮资源存在，音画限时逻辑存在")
print("[PASS] 花园背景、透明城堡、道路纹理和童话炮身 PNG 有效并已接入")
print("[PASS] 点击与拖拽均允许在整条道路任意位置部署")
print("[PASS] HTML 内联 JavaScript 语法检查通过")
