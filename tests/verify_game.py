from __future__ import annotations

import hashlib
import shutil
import struct
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "index.html"
STYLE = ROOT / "css" / "style.css"
PROTOTYPE = ROOT / "源代码" / "prototype_castle_layout.html"
TABLE_DIR = ROOT / "单位属性表"
EXPECTED_TABLE = "20260710.xlsx"
EXPECTED_TABLE_SHA256 = {
    "9290F54AC364812D97442BE968CE8A34FAA0D7FD8EE8A417DA8405A52ABDDB58",
}


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
if not STYLE.is_file():
    fail(f"找不到外部样式文件：{STYLE}")
if PROTOTYPE.exists():
    fail(f"正式吸收后仍残留临时城墙原型：{PROTOTYPE}")

tables = [p for p in TABLE_DIR.glob("*.xlsx") if p.stem.isdigit()]
if not tables:
    fail("单位属性表目录中没有按日期命名的 xlsx")
latest = max(tables, key=lambda p: int(p.stem))
if latest.name != EXPECTED_TABLE:
    fail(f"发现更新的属性表 {latest.name}；请先重新同步游戏数值")
table_hash = hashlib.sha256(latest.read_bytes()).hexdigest().upper()
if table_hash not in EXPECTED_TABLE_SHA256:
    fail(f"{latest.name} 内容已变化；请重新读取并同步属性")

html_source = HTML.read_text(encoding="utf-8")
source = html_source + "\n" + STYLE.read_text(encoding="utf-8")

required = {
    "游戏标题": "<title>奇境王冠</title>",
    "外部样式入口": '<link rel="stylesheet" href="./css/style.css" />',
    "微软 Emoji 字体": 'font-family:"Segoe UI Emoji"',
    "蛇最新属性": "snake:{name:'毒影蛇',cost:10,hp:400,attack:10,speed:100,range:60,interval:.2,cooldown:3,regen:10",
    "狮最新属性": "lion:{name:'圣鬃狮',cost:10,hp:500,attack:20,speed:70,range:70,interval:.5,cooldown:3,regen:10",
    "象最新属性": "elephant:{name:'磐石象',cost:10,hp:800,attack:15,speed:50,range:80,interval:.8,cooldown:3,regen:20",
    "龙最新属性": "dragon:{name:'星焰龙',cost:15,hp:600,attack:30,speed:60,range:100,interval:1,cooldown:5,regen:15",
    "蛇药水倍率": "snake:{hp:1,attack:1,speed:2,attackSpeed:2,regen:1,poisonDamage:2,poisonDuration:1}",
    "狮药水倍率": "lion:{hp:1.3,attack:2,speed:1,attackSpeed:1.3,regen:1,killHeal:2}",
    "象药水倍率": "elephant:{hp:2,attack:1,speed:1,attackSpeed:1,regen:2,heavyDamage:2}",
    "龙药水倍率": "dragon:{hp:1.3,attack:1.3,speed:1.3,attackSpeed:1.3,regen:1.3,burnDamage:1.3,burnDuration:1.3}",
    "蛇中毒": "const pd=2*(u.buffed?(u.buff.poisonDamage||1):1),dur=10*(u.buffed?(u.buff.poisonDuration||1):1)",
    "狮击杀回血": "const h=100*(lion.buffed?(lion.buff.killHeal||1):1)",
    "象三秒重击": "if(u.type==='elephant'&&u.charge>=3)u.heavyReady=true",
    "象三倍伤害": "mult=3*(u.buffed?(u.buff.heavyDamage||1):1)",
    "龙燃烧": "v.burnDps=20*(u.buffed?(u.buff.burnDamage||1):1);v.burn=3*(u.buffed?(u.buff.burnDuration||1):1)",
    "药水属性": "const POTION={cost:5,cooldown:20};",
    "爆裂炮属性": "const BURST={cost:20,cooldown:20,damage:1000,shots:10};",
    "守门炮属性": "const GUARD_CANNON={interval:2,windup:.28,damage:200,rangeFactor:.25};",
    "城门血量": "kind:'tower',side,hp:10000,maxHp:10000",
    "金币增长": "this.coins.player+=1*dt;this.coins.enemy+=1*dt;",
    "正式道路范围": "roadStart:105,roadEnd:1175",
    "按单位尺寸计算出生距离": "const distance=UNIT_DATA[type].size+CASTLE_GEOMETRY.spawnGap",
    "双方镜像出生参数": "return side==='player'?distance/path.length:1-distance/path.length;",
    "童话基地几何": "const CASTLE_GEOMETRY={wallHalfWidth:46,wallTop:198,wallBottom:522,gateHalfHeights:[23,34,23]",
    "城墙中部炮台几何": "const CANNON_GEOMETRY={mountOffsetY:0,barrelLength:38,baseRadius:20,recoilDistance:4};",
    "共享炮口计算": "const muzzle=this.cannonMuzzle(t)",
    "炮口闪光绘制": "else if(f.kind==='muzzle')",
    "炮口烟雾绘制": "else if(f.kind==='smoke')",
    "炮弹短拖尾": "ctx.moveTo(p.x-dx/d*18,p.y-dy/d*18)",
    "恢复旧版连续交汇路面": "ctx.fill(outer,'evenodd')",
    "恢复旧版交汇几何": "centerTop=292+inset,centerBottom=428-inset",
    "生成花园背景": "./assets/images/fairy-garden-battlefield-v1.png",
    "生成城堡立绘": "./assets/images/fairy-castle-gate-v1.png",
    "生成道路纹理": "./assets/images/fairy-road-stone-texture-v1.png",
    "生成童话炮身": "./assets/images/fairy-cannon-barrel-v1.png",
    "透明中毒图标": "./assets/images/poison-status-icon-v1.png",
    "道路纹理蒙版": "ctx.fillStyle=this.roadPattern()||'#f7dfaa'",
    "底部卡牌与金币": "#bottomDock{top:auto;bottom:1.2%",
    "左下战术键": "#tactical{top:auto;left:1.2%;right:auto;bottom:1.4%",
    "返回首页按钮": 'id="homeBtn"',
    "暂停按钮": 'id="pauseBtn"',
    "BGM 文件": "./assets/audio/BGM.ogg",
    "单发音效": "./assets/audio/cannon1.mp3",
    "连发音效": "./assets/audio/explosions.mp3",
    "单炮出膛计数": "this.cannonLaunches++;this.cannonLaunchesBySide[side]++",
    "单炮出膛触发一次音效": "audio.playCannon(flight+FX_TIMING.cannonExplosion)",
    "单发音频限时": "this.playTimed(voice,clipped,false)",
    "十连发动画时长": "const BURST_VISUAL_DURATION=FX_TIMING.burstLead+(BURST.shots-1)*FX_TIMING.burstStep+FX_TIMING.burstExplosion;",
    "十连发音频拟合": "this.playTimed(this.burstVoice,visualDuration,true)",
    "基础棋子视觉缩小30%": "const UNIT_BASE_VISUAL_SCALE=.7;",
    "药水相对基础体型放大": "u.visualScale=UNIT_BASE_VISUAL_SCALE*1.4",
    "重击状态图标": "if(u.heavyReady)ctx.fillText('💢'",
    "药水王冠状态": "if(u.buffed)ctx.fillText('👑'",
    "中毒绿色视觉": "ctx.fillStyle='rgba(80,190,82,.24)'",
    "图片中毒标识": "ctx.drawImage(poisonStatusIcon,-size/2,-size/2,size,size)",
    "中毒标识保持18像素": "18/(u.visualScale||1)",
    "中毒标识呼吸动画": "const phase=performance.now()/900*TAU,pulse=1+Math.sin(phase)*.08",
    "燃烧单位火焰": "if(u.burn>0){const flicker=",
    "双倍龙火焰弹": "ctx.arc(0,0,18,0,TAU)",
    "音频逐帧截止": "audio.updateClips();game.update(dt)",
    "全场部署参数": "deploy(side,type,lane,spawnT=null)",
    "点击部署仅选择道路": "if(target.d>DEPLOY_SNAP_RADIUS){this.hint('请点击道路范围内');return;}if(this.deploy('player',s.type,target.i))",
    "拖拽部署仅选择道路": "if(target.d>DEPLOY_SNAP_RADIUS)game.hint('请拖到道路范围内');else if(!game.deploy('player',d.type,target.i))",
    "道路吸附半径": "const DEPLOY_SNAP_RADIUS=46;",
    "按路线门口攻击城墙": "gate=this.paths[u.lane].at(u.side==='player'?1:0),td=Math.hypot(gate.x-u.x,gate.y-u.y)-45",
    "连发元数据竞态兜底": "this.burstVoice.fallbackDuration=11.740862",
    "移动端禁止缩放 viewport": "maximum-scale=1, user-scalable=no, viewport-fit=cover",
    "移动端性能模式": "const mobilePerformanceMode=",
    "移动端横屏锁定": "screen.orientation?.lock",
    "移动端全屏请求": "document.documentElement.requestFullscreen",
    "触摸开始支持": "addEventListener('touchstart'",
    "触摸拖动支持": "addEventListener('touchmove'",
    "触摸结束支持": "addEventListener('touchend'",
    "首次触摸音频解锁": "document.addEventListener('pointerdown',()=>{audio.ensureContext()",
}
for label, token in required.items():
    require(source, token, label)

forbidden = {
    "旧吸血逻辑": "lifesteal",
    "旧城墙 5000 魔数": "maxHp===5000",
    "旧圆形交汇函数": "drawCrossHub",
    "药水放大判定体积": "u.size*=1.3",
    "旧药水紫色光圈": "ctx.strokeStyle='rgba(214,154,255,.82)'",
    "旧重击黄色准备光圈": "if(u.type==='elephant'&&u.heavyReady){ctx.strokeStyle='#ffd45d'",
    "临时 UI 原型": "layoutPrototype",
    "临时原型切换器": "layoutPrototypeSwitcher",
    "旧己方半场提示": "只能在己方半场部署",
    "旧己方半场点击限制": "p.x>FIELD.centerX",
    "旧己方半场寻路限制": "nearestLane(p,true)",
    "卡牌属性描述节点": "<div class=\"card-stats\">",
}
for label, token in forbidden.items():
    forbid(source, token, label)

assets = [
    ROOT / "assets" / "audio" / "BGM.ogg",
    ROOT / "assets" / "audio" / "cannon1.mp3",
    ROOT / "assets" / "audio" / "explosions.mp3",
]
for asset in assets:
    if not asset.is_file() or asset.stat().st_size <= 0:
        fail(f"音频资源无效：{asset}")

png_assets = {
    ROOT / "assets" / "images" / "fairy-garden-battlefield-v1.png": (1200, 675, False),
    ROOT / "assets" / "images" / "fairy-castle-gate-v1.png": (512, 512, True),
    ROOT / "assets" / "images" / "fairy-road-stone-texture-v1.png": (512, 512, False),
    ROOT / "assets" / "images" / "fairy-cannon-barrel-v1.png": (512, 256, True),
    ROOT / "assets" / "images" / "poison-status-icon-v1.png": (512, 512, True),
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
