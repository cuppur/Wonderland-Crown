# 奇境王冠 — 项目工作规则

开始修改前先读本文件和 `TASK_STATE.md`（当前任务进度与断线恢复点）。

## 1. 项目简介

- 单机、三路、固定四卡的即时对抗小游戏，玩法参考轻量化《皇室战争》：消耗持续增长的金币部署蛇、狮、象、龙，单位沿三路自动前进交战，摧毁对方城门或倒计时结束比较城门生命。
- 技术栈：原生 HTML/CSS/JavaScript、Canvas 2D、HTMLAudioElement、Web Audio API；无框架、无包管理器、无构建步骤，源码即运行产物。
- 主要平台：Windows 桌面现代浏览器（重点 1920×1080），兼顾手机横屏。

## 2. 运行与测试

- 启动：项目根目录执行 `python -m http.server 8765 --bind 127.0.0.1`，打开 `http://127.0.0.1:8765/index.html?test=1`。
- 测试：`python tests/verify_game.py`（静态契约、资源、属性表哈希、JS 语法），必须全部 PASS。
- 浏览器回归命令：`python tests/playtest_game.py`（需开发环境 Python Playwright；不属于游戏运行依赖）。截图/报告位于 `output/playwright/`。
- 浏览器检查：用 Playwright 自带 headless Chromium，不要用本机 Edge/Chrome（会触发 IDM 弹窗）。检查 console、`window.__QJWG_TEST__.snapshot()` 和关键交互。
- 测试探针 `window.__QJWG_TEST__` 与隐藏的 `#qjwgTestProbe` 只在 localhost 且 URL 含 `test` 时启用。

## 3. 目录结构

```text
奇境王冠/
├─ index.html                 # 正式入口：页面结构 + 战斗/音频/交互 JavaScript
├─ css/style.css              # 一套 rem 尺度的正式 HUD/弹窗样式
├─ js/candy-field.js           # 预览/正式共用的 2.5D 几何、投影、地面、宫殿、糖果炮
├─ assets/
│  ├─ images/                 # 中毒状态图标（地面/建筑使用程序绘制）
│  ├─ audio/                  # BGM.ogg、cannon1.mp3（单发）、explosions.mp3（连发）
│  └─ data/resource-manifest.json
├─ design/                    # UI 重构展示页与截图，不是正式代码
├─ tests/verify_game.py        # 静态/语法/属性表/资源契约
├─ tests/playtest_game.py      # Playwright 实测；启动临时服务器并保存截图
├─ 单位属性表/                 # 按日期命名的 xlsx，最新一份是数值来源，只读
├─ TASK_STATE.md              # 当前任务阶段与下一步
└─ LOVABLE_DEPLOY.md          # 静态站点部署说明
```

## 4. index.html 模块位置

- 常量与数值：`UNIT_DATA`、`BUFFS`、`POTION`、`BURST`、`GUARD_CANNON`、`FX_TIMING`、`FIELD`、`CASTLE_GEOMETRY`（数值只在 index.html 内维护）。
- 地图与路径：`Path` 类、`Game.buildPaths()`、`CandyField.buildGeometry()`；两种模式“三路战线”和“交汇战线”。
- 战斗：`Game` 类（部署、单位更新、攻击、城墙、炮台、AI、渲染）。
- 卡牌与拖拽：`.card` DOM、`queueDrag()`、`beginDrag()`、`finishDrag()`。
- 技能：魔力药水（拖到卡牌，强化下一只）、爆裂炮阵（选一路连续 10 炮）。
- 音频：`AudioManager`。

### 绘制与坐标约定（2026-10-07）

- 正式战场填满视口；`W/H` 取实际容器尺寸，`CandyField.buildGeometry()` 推导三路/门口/平台/炮台位置。
- 战斗保留地面坐标；绘制用 `CandyField.project()`，点击和拖拽用 `unproject()`。上路深度 0.8，下路 1.0。立体物件按脚底位置缩放。
- 单位基础数值不改；移速/射程按各路线 `length/1070` 换算。窗口缩放保留 t/血量/冷却，并同步炮弹位置/拖尾/速度。
- 守门炮的射程与优先级以基地地面中心计算，绘制炮台坐在中路塔顶；两个位置分别使用，不能让塔顶高度影响上下路防守范围。
- `CandyField.muzzle()` 是唯一可见炮口计算，Game 转为地面坐标用于炮弹/FX；含转向、0.55 纵向压扁和后坐。不要在发射/绘制中各写一套偏移。
- 背景（包括模糊道路蒙版）只在尺寸/模式变化时缓存；宫殿按血量百分位缓存，炮台/Emoji/特效实时绘制。手机 DPR ≤1.25。
- HUD 统一 rem 基准；原版饱和渐变卡牌外观保留。系统按钮在菜单内，版本仅首页。发布静态文件须同时保留 `index.html`、`css/`、`js/`、`assets/`。

## 5. UI 长期设计要求

- 风格：简约、儿童向、可爱、童话感；不写实、不做复杂中世纪风、不用强 3D 透视；柔和色块与轻渐变，少用强阴影和厚纹理。
- 战场与单位识别优先，装饰不能干扰玩法。左侧蓝方、右侧红方。
- 三条道路清楚，与草地边界分明。
- 城堡覆盖三路，每路一个水平正对道路的门（左门朝右、右门朝左），门前有出生平台；每侧只有一门主炮。
- 单位继续使用 Microsoft Segoe UI Emoji，不生成或替换动物立绘。
- HUD、卡牌、技能做成可随屏幕比例缩放的独立 DOM 组件，不用固定贴图。

## 6. 开发限制

- 不推翻重写，优先在现有结构上小步修改；不擅自更换技术栈或添加依赖。
- 不删除已正常工作的功能：双地图、拖拽、药水、炮阵、AI、音频、暂停、首页、全屏、数值报告。
- 改单位数值前先确认 `单位属性表/` 里最新的文件，并同步 `tests/verify_game.py` 的文件名与 SHA256。
- 每次修改后必须跑 `python tests/verify_game.py`；修改 UI 后必须在 1920×1080 截图检查，并至少抽查一个小尺寸。
- 避免继续追加覆盖旧规则的新一套 CSS。
- 大任务分阶段：每完成一个阶段更新 `TASK_STATE.md` 并 git commit。未经用户明确要求不要推送到远程仓库。
