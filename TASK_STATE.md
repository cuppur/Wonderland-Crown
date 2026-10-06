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
- [x] P4 截图自检 1920×1080 / 844×390 / 1024×768，修问题（修了 drawBlades 漏参；u 基准放大到 h/88；自适应模式隐藏工具栏、菜单里加"退出自适应预览"；精简技能/金币短文案）
- [x] P5 最终汇报（诊断 + 整改措施 + 落地步骤），更新记忆

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

P5：给用户最终汇报（诊断 + 整改措施 + 落地到 index.html 的步骤），更新记忆。之后若用户要求落地，新开阶段 P6+。

## 当前任务（2026-10-07 起）：第二轮规划（grill-me 访谈中，先不动代码）

用户 8 条反馈：
1. 城堡造型要完全重新设计，先给多个方案让用户选，先不做。
2. 不替换敏感词（已确认与风控无关），此项关闭。
3. 原版卡片区更好看，展示页卡片区要回到原版风格。
4. 道路太宽；去掉黄色道路中间的白色提亮线。
5. 动物行走要居中（展示页里 offset 随机 ±0.17 路宽，导致不居中）。
6. 道路两两交汇处的锐角要加圆角过渡（用户截图里的红线位置：交汇口两侧的内角）。
7. 顶栏和底栏太小，要变大。
8. 继续清理无关/无用/过时内容。

访谈结论（逐轮追加）：
- 第1轮：城堡方案用一页 HTML 概念图给用户挑（Canvas 画、并排、可放大，不改游戏代码）；方向放三种：圆塔要塞群（类皇室战争）、蘑菇童话村、糖果蛋糕城；玩法不变只换造型（每路一门、每侧一门主炮、城门 7000 血）；卡片区还原原版外观（托盘、橙色金币块、饱和渐变竖卡、右上角费用），只做组件化随比例缩放。
- 第2轮：道路收窄到约 70%；去掉中间白色提亮线，保留路面小石子；单位严格走中线，允许重叠（去掉随机 offset）；分岔/交汇内角圆角半径约一个路宽。
- 第3轮：顶栏/底栏放大约 35%（1080p 顶约 85px、底约 190px），电脑和手机都放大；清理执行三项：删 fairy-castle-gate-v1.png + fairy-cannon-barrel-v1.png（同步删 index.html 加载代码、manifest、测试断言）、删 PROJECT_HANDOFF.md 并按真实结构重写精简版 AGENTS.md、删历史属性表只留 20260730.xlsx 并把测试改锁它；manifest 旧 source 字段和 LOVABLE_DEPLOY.md 保留不动；执行顺序：展示页修改 + 城堡概念页一起做，用户看完再选城堡、再决定是否落地 index.html。
- 用户截图红线位置：所有道路分岔/汇合处的内侧锐角（城墙附近两条路分开处、中央交汇口上下两侧）都要圆角过渡。

### 第二轮执行阶段（用户已确认规划，2026-10-07）

- [x] Q1 清理：删两张未绘制图片及引用；删 PROJECT_HANDOFF.md、重写精简 AGENTS.md；删历史属性表只留 20260730.xlsx、测试改锁它；跑 `python tests/verify_game.py` 必须 PASS
- [ ] Q2 展示页修改 `design/ui-preview.html`：卡片区还原原版外观（组件化）；路宽 ×0.7、去白线留石子；单位走中线；分岔/交汇内角圆角约一路宽；HUD 放大约 35%
- [ ] Q3 城堡概念页 `design/castle-concepts.html`：圆塔要塞群 / 蘑菇童话村 / 糖果蛋糕城，三方案并排，同一战场底图，玩法结构不变
- [ ] Q4 截图自检 + 汇报，等用户选城堡

Q1 结果：删了 fairy-castle-gate-v1.png、fairy-cannon-barrel-v1.png（含 index.html preload/加载/测试探针字段、manifest 条目、测试断言）；顺带去掉 style.css 里 11 处指向不存在路径 `css/assets/fairy-road-stone-texture-v1.png` 的 404 背景图（原本就加载失败，画面不变）；删 PROJECT_HANDOFF.md，AGENTS.md 重写为精简版；属性表只留 20260730.xlsx，测试改锁它，verify_game.py 全 PASS；浏览器实测开局出兵正常、无 console 错误、无 404。

下一步：Q2（改 design/ui-preview.html）。

Q2 参考数据（原版 1080p 实测的最终生效样式，换算 1rem≈16.6px）：
- #bottomDock 736×203，flex 对齐 stretch，padding 10/13，gap 10，border 4px #a06d9d，圆角 27，底色 #f3dce8；阴影 inset 0 3px #fff, 0 0 0 3px #ffe8a1, 0 6px 0 #7a567d, 0 12px 19px rgba(56,40,61,.4)；::before "🌸"、::after "🌼" 19px，top -13px，left/right 18px。
- #resourceBox 宽 118，padding 8，gap 5，border 3px #d49b56，圆角 17，底色 #f2cf83，阴影 inset 0 2px #fff, 0 3px #a8683e，文字色 #65403f；#coinText 20px/1000 #593013，text-shadow 0 1px #fff4bd，内容 "🟡 19.4"（toFixed(1)）；#coinBar 高 9，border 2px #6c351c，圆角 99，底色 #5b2f1c；#coinFill 渐变 90deg #f0a918→#fff08d，inset 0 1px #fff7bd；#income 11px/800，透明度 .72，文案“金币增长：1 / 秒”。
- .card 136×175，padding 1/6，border 3px #fff6d4，圆角 20，居中对齐；阴影 inset 0 2px #fff, 0 0 0 3px #8c6a9c, 0 5px 0 #705179, 0 9px 13px rgba(0,0,0,.27)；渐变 160deg：蛇 #efffd8,#abe88f 56%,#72bf85；狮 #fff4cf,#ffd078 58%,#ed9563；象 #eafdff,#9fdef0 58%,#75aede；龙 #fcecff,#d9a8ef 58%,#a77fcb；::before inset 3px，1px rgba(255,255,255,.48) 描边，圆角 9。
- .card-art 高 43%，Emoji 46px，背景 radial at 50% 95% rgba(255,255,255,.68)→透明 63%；.cost 34px 圆，top/right 5px，border 2px #fff6b5，radial at 35% 30% #fff9b8, #e9a92c 55%, #86510e 57%，阴影 0 2px #6f3d0e, 0 4px 7px rgba(0,0,0,.4)，16px/1000 #2a1903；.card-name 14px/1000 #492919，text-shadow 0 1px #fff9d0；.card-role 9px/800，透明度 .72。
- 冷却：.cool-mask 从底部按百分比升高，渐变 rgba(31,23,25,.64)→rgba(12,9,13,.86)；.cool-label 24px/1000 #fff7cf，阴影 0 2px 5px #000，显示 toFixed(1) 秒；不可用/冷却 filter grayscale(.72) brightness(.68)；选中 outline 3px #fff7bf + box-shadow 0 0 0 3px #9c551f, 0 0 18px #ffe787，brightness 1.16，上移 3px；药水强化 .armed outline 3px #d798ff + 紫色辉光 + 左下“药水强化”角标。
- 技能原版：药水底色 #d7b7e8、炮阵底色 #f3b184，border 3px #fff1c8，圆角 18，阴影 inset 0 2px #fff, 0 0 0 3px #7f5b98, 0 5px #654777, 0 9px 14px rgba(0,0,0,.27)，文字 13px/700 #613b65。
- 真实数值（展示页要对齐）：城门 10000 血、开局 15 金币、每秒 +1 金币（AGENTS 旧文档写的 7000 血/20 金币/2 每秒是过时数据）。

Q2 实现要点：u = max(6.5, min(h/65, w*.0097))（约为原来的 1.35 倍）；战场安全区 top=7.4u、bottom=h-14.2u；几何新增 R=s*.4（建筑/单位尺度基准），rw=R*.7 只用于路面，单位/城墙/门/平台/炮台/特效都改用 R；道路圆角用“形态学闭运算”：把路面栅格化后做两次 EDT 得到 SDF，再按阈值合成绿色压边、沙土边、路面三层，圆角半径 = rw；去掉白色中线；单位 offset 置 0。

## 已暂停的任务：项目清理（用户叫停，"已做的不管，没做的搁着"）

已完成：
- 主目录 beauty 未提交工作（Pixi 版、角色、output 等）已永久删除；主目录现为 detached HEAD @2173db7。
- 删除分支 beauty、master、codex/UI、claude/musing-gagarin-76474b、claude/nice-hugle-5903b0；移除对应 worktree、692c 损坏工作区、codex refs、.git 临时对象并 gc。

后续：贴图/交接文档/历史属性表三项已在第二轮 Q1 完成。
- 敏感词替换：用户确认与风控无关，永久关闭，不要替换游戏用词。
- manifest 里的旧 `source` 路径字段和 LOVABLE_DEPLOY.md：用户选择保留，不要动。
