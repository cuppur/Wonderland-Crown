from __future__ import annotations

import hashlib
import math
import shutil
import struct
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "index.html"
STYLE = ROOT / "css" / "style.css"
TABLE_DIR = ROOT / "单位属性表"
EXPECTED_TABLE = "20260730.xlsx"
EXPECTED_TABLE_SHA256 = {
    "29FAB6D7CCFA1175778D9706FF7D4277CAFB72D29D1F72DD90C42BAAA9F232B2",
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
    "蛇最新属性": "snake:{name:'毒影蛇',cost:10,hp:500,attack:10,speed:80,range:60,interval:.2,cooldown:5,regen:10",
    "狮最新属性": "lion:{name:'圣鬃狮',cost:10,hp:700,attack:20,speed:60,range:70,interval:.5,cooldown:5,regen:10",
    "象最新属性": "elephant:{name:'磐石象',cost:10,hp:1000,attack:15,speed:40,range:80,interval:.8,cooldown:5,regen:20",
    "龙最新属性": "dragon:{name:'星焰龙',cost:10,hp:800,attack:20,speed:50,range:100,interval:1,cooldown:5,regen:15",
    "蛇药水倍率": "snake:{hp:1,attack:1,speed:2,attackSpeed:2,regen:1,poisonDamage:2,poisonDuration:1}",
    "狮药水倍率": "lion:{hp:2,attack:2,speed:1,attackSpeed:1,regen:1,killHeal:2}",
    "报告移除建议费用": "<th>每金币价值</th></tr>",
    "象药水倍率": "elephant:{hp:2,attack:1,speed:1,attackSpeed:1,regen:2,heavyDamage:2}",
    "龙药水倍率": "dragon:{hp:1.3,attack:1.3,speed:1.3,attackSpeed:1.3,regen:1.3,burnDamage:1.3,burnDuration:1.3}",
    "蛇中毒": "const pd=2*(u.buffed?(u.buff.poisonDamage||1):1),dur=10*(u.buffed?(u.buff.poisonDuration||1):1)",
    "狮击杀回血": "const h=100*(lion.buffed?(lion.buff.killHeal||1):1)",
    "狮击杀回血特效事件": "this.fx.push({kind:'lionHeal',x:lion.x,y:lion.y,t:.75,max:.75})",
    "狮击杀回血特效绘制": "else if(f.kind==='lionHeal')",
    "AI五金币购买药水": "this.coins.enemy>=POTION.cost&&Math.random()<.3",
    "AI开局三秒禁出兵": "if(elapsed<3||elapsed-this.aiLastDeployAt<2)return",
    "AI出兵至少间隔两秒": "if(this.deploy('enemy',type,lane))this.aiLastDeployAt=elapsed",
    "AI出兵时间测试记录": "at:this.elapsed",
    "默认五分钟": "<option value=\"300\" selected>5 分钟</option>",
    "无限制时长选项": "<option value=\"unlimited\">无限制</option>",
    "无限制计时显示": "else $('#timer').textContent='∞'",
    "无限制不触发时间结束": "if(Number.isFinite(this.duration)){this.timeLeft-=dt",
    "无限制仍记录经过时间": "const elapsed=this.elapsed",
    "单位对拼剑击事件": "kind:'clash'",
    "单位对拼剑击动效": "else if(f.kind==='clash')",
    "象三秒重击": "if(u.type==='elephant'&&u.charge>=3)u.heavyReady=true",
    "象三倍伤害": "mult=3*(u.buffed?(u.buff.heavyDamage||1):1)",
    "龙燃烧": "v.burnDps=20*(u.buffed?(u.buff.burnDamage||1):1);v.burn=3*(u.buffed?(u.buff.burnDuration||1):1)",
    "药水属性": "const POTION={cost:5,cooldown:20};",
    "爆裂炮属性": "const BURST={cost:20,cooldown:20,damage:1000,shots:10};",
    "守门炮属性": "const GUARD_CANNON={interval:2,windup:.28,damage:150,rangeFactor:.2};",
    "炮台最短角度差": "const shortestAngleDelta=(from,to)=>Math.atan2(Math.sin(to-from),Math.cos(to-from));",
    "炮台回中不绕远路": "t.angle+=shortestAngleDelta(t.angle,rest)*clamp(dt*2.4,0,1)",
    "三路战线标题": "<b>三路战线</b><span>三条平行路线，战线清晰</span>",
    "交汇战线精简说明": "<b>交汇战线</b><span>三条道路汇入平滑路面</span>",
    "模式标题居中": ".mode-option b{text-align:center}",
    "计时器内层虚线隐藏": "#centerHud::after{display:none}",
    "城门血量": "kind:'tower',side,hp:10000,maxHp:10000",
    "金币增长": "this.coins.player+=1*dt;this.coins.enemy+=1*dt;",
    "初始金币": "this.coins={player:15,enemy:15}",
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
    "生成道路纹理": "./assets/images/fairy-road-stone-texture-v1.png",
    "透明中毒图标": "./assets/images/poison-status-icon-v1.png",
    "道路纹理蒙版": "const pattern=this.roadPattern()",
    "统一道路视觉配置": "const ROAD_VISUAL={",
    "柔和道路中心色": "centerColor:'#F3DDA4'",
    "柔和道路边缘色": "sideColor:'#EFD6A0'",
    "道路纹理透明度": "textureAlpha:.22",
    "道路纹理放大": "textureTileSize:288",
    "柔和边缘过渡": "transitionColor:'rgba(151,174,91,.16)'",
    "两地图共享道路参数": "ROAD_VISUAL.crossInsets",
    "底部卡牌与金币": "#bottomDock{top:auto;bottom:1.2%",
    "左下战术键": "#tactical{top:auto;left:1.2%;right:auto;bottom:1.4%",
    "精简药水按钮": "🧪 魔力药水 · ${POTION.cost}G",
    "精简炮阵按钮": "💥 爆裂炮阵 · ${BURST.cost}G",
    "返回首页按钮": 'id="homeBtn"',
    "暂停按钮": 'id="pauseBtn"',
    "BGM 文件": "./assets/audio/BGM.ogg",
    "首页交互不播放BGM": "else audio.ensureContext();",
    "移动端仅在对局中播放BGM": "if(game.state==='playing'&&!audio.muted&&audio.bgm.paused)audio.playBgm(false)",
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
    "中毒图标缩小至60%": "size=s*1.35",
    "中毒图标移到棋子外侧": "u.size+12/vs,-u.size-10/vs",
    "中毒标识呼吸动画": "const phase=performance.now()/900*TAU,pulse=1+Math.sin(phase)*.08",
    "燃烧单位火焰": "if(u.burn>0){const flicker=",
    "双倍龙火焰弹": "ctx.arc(0,0,18,0,TAU)",
    "音频逐帧截止": "audio.updateClips();game.update(dt)",
    "全场部署参数": "deploy(side,type,lane,spawnT=null)",
    "点击部署仅选择道路": "if(target.d>DEPLOY_SNAP_RADIUS){this.hint('请点击道路范围内');return;}if(this.deploy('player',s.type,target.i))",
    "拖拽部署仅选择道路": "if(target.d>DEPLOY_SNAP_RADIUS)game.hint('请拖到道路范围内');else if(!game.deploy('player',d.type,target.i))",
    "炮阵点击仅允许道路": "if(target.d>DEPLOY_SNAP_RADIUS){this.hint('请点击道路范围内');return;}if(this.useBurst('player',target.i))",
    "炮阵拖离道路自动取消": "if(target.d>DEPLOY_SNAP_RADIUS)game.hint('已取消爆裂炮阵');else if(!game.useBurst('player',target.i))",
    "单位淡蓝色道路引导": "'rgba(133,218,255,.95)'",
    "道路吸附半径": "const DEPLOY_SNAP_RADIUS=46;",
    "按可见门口端点攻击城墙": "gate=this.paths[u.lane].at(u.side==='player'?1:0),td=Math.hypot(gate.x-u.x,gate.y-u.y);",
    "连发元数据竞态兜底": "this.burstVoice.fallbackDuration=11.740862",
    "移动端禁止缩放 viewport": "maximum-scale=1, user-scalable=no, viewport-fit=cover",
    "移动端性能模式": "const mobilePerformanceMode=",
    "移动端横屏锁定": "screen.orientation?.lock",
    "移动端全屏请求": "document.documentElement.requestFullscreen",
    "触摸开始支持": "addEventListener('touchstart'",
    "触摸拖动支持": "addEventListener('touchmove'",
    "触摸结束支持": "addEventListener('touchend'",
    "首次触摸自动进入横屏全屏": "document.addEventListener('pointerdown',()=>{if(mobilePerformanceMode)enterMobileMode()",
    "报告固定底部返回区": "class=\"report-footer\"",
    "报告移动端公式折叠": "$('#reportFormula').open=!mobilePerformanceMode",
    "报告触摸滚动区": "html.mobile-device .report-content",
    "报告打开时解除战场触摸拦截": "#game-shell.report-open{touch-action:pan-x pan-y}",
}
for label, token in required.items():
    require(source, token, label)


def shortest_angle_delta(current: float, target: float) -> float:
    return math.atan2(math.sin(target - current), math.cos(target - current))


if abs(math.degrees(shortest_angle_delta(math.radians(-170), math.radians(180)))) > 11:
    fail("炮台跨越 -π/π 时没有选择最短转向")

forbidden = {
    "首页副标题": "童话战场 · 固定四卡 · 单机对抗",
    "旧道路深绿硬边": "ctx.strokeStyle='#599c50'",
    "六块灰色门前平台": "CASTLE_GEOMETRY.platformHalfWidth",
    "对局版本文字": 'id="versionTag"',
    "药水详细描述": "拖到卡牌：下一只强化 · ${POTION.cooldown}秒",
    "炮阵详细描述": "一路${BURST.shots}炮 · ${BURST.cooldown}秒 · 每炮${BURST.damage}",
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
    "报告模型建议费用": "模型建议费用",
    "报告模型结论": "模型结论",
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
    ROOT / "assets" / "images" / "fairy-road-stone-texture-v1.png": (512, 512, False),
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
        fail(f"图片缺少透明通道：{asset}")

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

print("[PASS] 最新属性表未被修改，且仍为 20260730.xlsx")
print("[PASS] 四单位、药水、城门、金币、爆裂炮和守门炮静态配置已同步")
print("[PASS] 底部卡牌、左下战术键、双地图道路与系统按钮契约存在")
print("[PASS] BGM、单发炮、连发炮资源存在，音画限时逻辑存在")
print("[PASS] 花园背景、道路纹理和中毒图标 PNG 有效并已接入")
print("[PASS] 点击与拖拽均允许在整条道路任意位置部署")
print("[PASS] HTML 内联 JavaScript 语法检查通过")
