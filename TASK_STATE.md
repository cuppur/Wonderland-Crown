# TASK_STATE — 断线恢复用

> 断线重连后：先读本文件，再按"下一步"继续。每完成一个阶段立即更新本文件并 git commit。

## 当前任务：对局 UI 重构展示页（只出展示 HTML，不改 index.html）

- 工作区：`.claude/worktrees/eager-moser-5dea90`，分支 `UI`（本地唯一分支，作为主线）。
- 产出文件：`design/ui-preview.html`（自包含静态页，无外部依赖）。
- 截图自检：Playwright 自带 headless shell + `python -m http.server`，不要用 Edge/Chrome。

### 已确认的设计决定（用户 2026-10-06 拍板，不要再问）

- 美术：俯视"手绘感"，全部 Canvas 程序绘制（噪声色块、笔触草纹、柔边花丛），不用外部图片；明亮糖果色。
- 不沿用 10-01 的扁平展示页，完全重做。
- 城堡：单层城墙覆盖三路 + 每路一个水平门洞（左门朝右、右门朝左，中门最大）+ 门前出生平台 + 墙顶一门主炮（蓝/红圆底座、深灰短炮管）。
- 适配：战场随屏幕比例拉伸（不留黑边）；道路几何按画布宽高参数化；单位速度按路长换算，保证任意比例走完一路时间相同。手机仅横屏。
- HUD 为独立 DOM 组件：顶部细条（双方血条 + 中间倒计时，系统按钮收进一个菜单按钮）；底部一行（金币 + 4 卡 + 2 技能），战场约占 70% 高度。
- 卡牌只显示 Emoji 图标、名称、费用、定位标签；详细数值长按/悬停（title）。
- 单位继续用 Microsoft Segoe UI Emoji；单位底圈去掉纯黑粗圈，改细描边 + 轻落地阴影。
- 展示页只做对局画面、只做交汇战线；可交互动态演示（自动出兵、炮台转向开火、卡牌可点出兵、冷却遮罩）。
- 比例切换按钮：16:9 电脑 / 19.5:9 手机横屏 / 4:3 平板 / 自适应窗口。
- 诊断原因和整改措施写在最终聊天汇报里，不放进页面。

### 现状诊断（已核实，用于最终汇报）

1. 视角冲突：背景 `fairy-garden-battlefield-v1.png` 是带天空/远山的透视插画，道路是俯视平面描边 + 半写实石纹贴图 `fairy-road-stone-texture-v1.png`。
2. 画风冲突：城墙是粗描边奶油卡通块，炮台另一套圆底座，与插画背景、石纹道路是三套美术语言。
3. 适配：固定 1280×720 画布 + 锁 16:9 外壳，手机横屏缩成小块、HUD 整体缩小。
4. `fairy-castle-gate-v1.png`、`fairy-cannon-barrel-v1.png` 只加载不绘制（仅测试契约引用）。
5. 顶部 HUD 和底部 dock 占比过大，系统按钮 5 个平铺；卡牌信息堆叠。

### 阶段计划

- [x] P0 建立本文件并提交
- [x] P1 页面骨架：比例切换、stage 容器、HUD DOM 组件（顶栏、底栏金币/4卡/2技能、菜单按钮）
- [x] P2 Canvas 战场：程序手绘草地、交汇道路（参数化）、三门城墙、墙顶炮台（已嵌入，待截图调整）
- [x] P3 动态演示：自动出兵、按路长换算速度、单位交战、炮台转向开火、卡牌点击出兵与冷却、金币增长、倒计时
- [ ] P4 截图自检 1920×1080 / 844×390 / 1024×768，修问题
- [ ] P5 最终汇报（诊断 + 整改措施 + 落地步骤），更新记忆

### P1 结构约定（P2/P3 要遵守）

- 文件末尾有三个 `<script>`：第 1 个是 P1（舞台/比例/菜单，导出 `window.QJ={$,$$,stage,fitStage}`）；第 2 个占位 `/*P2-FIELD*/`，替换成战场绘制；第 3 个占位 `/*P3-DEMO*/`，替换成演示逻辑，末尾保留 `QJ.fitStage();`。
- 舞台尺寸变化时派发 `window` 事件 `stage-resize`（detail `{w,h}`），P2 监听它重建画布与道路几何。
- HUD 尺寸全部用 rem，`html` 的 font-size = 基准单位 u（`computeUnit`：`max(4.3, min(h/100, w*.0072))` px）。
- 战场安全区：顶栏占 top .9rem~6.5rem，底栏占 bottom .9rem~14.3rem（含 1.2rem 选中上浮）；道路纵向范围要落在这两者之间。
- DOM id：`#field` 画布，`#pHp/#eHp` 血条 `<i>`，`#pHpText/#eHpText`，`#timer`，`#coinText/#coinBar`，`.card[data-type]`，`.skill[data-skill=potion|burst]`，`.cd` 冷却遮罩（父元素加 `.cooling` 并设 `--p` 0~1、文字为秒数），`.selected`/`.poor`/`.buffed` 状态类，`#hint`（加 `.show`），`#autoBtn`、`#restartBtn`、`#pauseItem`。

### P2 接口（P3 使用）

- `QJ.field = {ctx, canvas, TEAM, INK, rr, circle, drawWall(g,F,side,st), drawCannon(g,F,side,st), muzzle(F,side,angle), highlightLane(g,F,i,color), nearestLane(F,x,y), rng, F, bg, dpr}`。
- `drawWall` 的 st：`{hp:0~1, shake, flash, time}`；`drawCannon` 的 st：`{angle, recoil:0~1, glow:0~1}`。
- 几何 `F`：`paths[3]`（Path：`at(t)`、`angle(t)`、`nearest(x,y)`、`length`、`trace(g)`；t=0 为己方出生平台、t=1 为敌方出生平台），`rw` 路宽，`S0` 线宽基准，`unitR` 单位半径，`k` = 当前路长/原版 1070px（速度、射程乘 k），`pivot.player/enemy` 炮台中心，`ys` 三路 y，`cx/cy`。
- 尺寸变化后派发 `field-ready` 事件；每帧先 `ctx.drawImage(field.bg,0,0,F.w,F.h)` 再画城墙、单位、炮台、特效。

### 下一步

P4：截图自检。脚本 `%TEMP%/qjwg/shot2.py`（若丢失就重写：http.server 8771 起在 worktree 根目录，Playwright chromium headless 打开 `/design/ui-preview.html`，用 `window.__QJ_DEMO__.step(秒)` 快进后截图），检查 1920×1080 / 844×390 / 1024×768 的 16:9、19.5:9、4:3 和自适应模式。

## 已暂停的任务：项目清理（用户叫停，"已做的不管，没做的搁着"）

已完成：
- 主目录 beauty 未提交工作（Pixi 版、角色、output 等）已永久删除；主目录现为 detached HEAD @2173db7。
- 删除分支 beauty、master、codex/UI、claude/musing-gagarin-76474b、claude/nice-hugle-5903b0；移除对应 worktree、692c 损坏工作区、codex refs、.git 临时对象并 gc。

搁置未做（不要主动做）：
- 删 `fairy-castle-gate-v1.png`、`fairy-cannon-barrel-v1.png` 及代码/清单/测试引用。
- 删 `PROJECT_HANDOFF.md`、精简 `AGENTS.md`。
- 删历史属性表（保留最新 `20260730.xlsx`；它与 20260726 数值完全一致，仅样式/元数据不同；测试仍锁 20260726，所以 `tests/verify_game.py` 目前失败）。
- 敏感词替换：用户明确叫停，不要替换游戏用词。
