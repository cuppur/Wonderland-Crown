# 奇境王冠发布

稳定分支为 UI，AI 对战分支为 EVA；GitHub 默认分支使用 UI。
仓库：https://github.com/cuppur/Wonderland-Crown
公网：https://qijing-wangguan.lovable.app
Lovable 项目：Wonderland Crown Portal（72e4454c-102f-490a-89bb-af66ac4996be）。

项目为静态游戏，无构建步骤。部署 UI 的 index.html、css/、js/、assets/，必须包括 js/candy-field.js，并保留目录结构。
已有 Lovable 项目在 public/game/ 中保存原游戏，首页 iframe 加载 /game/index.html。更新时替换其中的游戏文件，保持游戏自身代码；发布后验证 /game/index.html 和所有资源。

本地双击根目录的两个 cmd 启动器。EVA 分支的本地 API 配置使用 Windows 加密保存在项目外；不上传密钥、凭据、日志或本地代理服务。UI 公网部署不包含 EVA 配置。

2026-10-07 手机修复已发布：UI 运行文件来源 8867525，Lovable 内容提交 864513569af54e5ac257e47dbc5aa2a80fdb23ad。首页 iframe 与绘图脚本使用 20261007-mobile2 缓存版本。
公网六个桌面/安卓触屏/WebKit 与双地图组合通过，八个运行文件与 UI Git blob 逐字节一致；报告位于 output/playwright/published-mobile/report.json，截图在同目录。
运行 python tests/playtest_published_mobile.py 可复验；开发网络需要代理时附加 --proxy 参数。测试检查实际战场像素、计时、出兵、全屏暂态尺寸恢复和菜单，不能只缩小桌面窗口判断手机正常。

同日高清版已发布：UI 运行来源 468bbf4，Lovable 内容提交 b71bcb944372e4b87daa25d2f6738519076e6f86，缓存版本 20261007-hd1。
手机 DPR 最高 2.5，并按约 220 万像素限制；地面/道路缓存使用相同 DPR。道路几何、宽度、圆角与投影保持上一版计算，只增加路外蘑菇、棉花糖云朵和花簇。
公网六场景与八文件对照全部通过，安卓模拟 844×390 主画布为 2110×975（2057250 像素）；最新版报告覆盖前一轮手机修复报告，修改前截图另保存在 output/playwright/hd/。

2026-10-08 六项缺陷与困难普通 AI 已发布：UI 运行来源 cce1d69（游戏核心 5c0008d）；Lovable 内容提交 2d6e7b38644923dffe9eddc02f20462f2a0484f6，部署 ID 69a05027-9773-4659-bdd4-905aaaef900b，缓存版本 20261007-hard1。
新增 js/ordinary-ai.js，发布必须保留两个 js 文件；三个原文件与新增 AI 脚本已经逐字核对。正式发布以 Git LF 字节为准，resource-manifest.json 的脚本字节数/哈希与实际 LF 文件一致；打包附件应从 git show 取 content、bytes、SHA256，避免 Windows 工作区 CRLF 导致哈希歧义。
公网桌面、安卓触屏、WebKit × 双地图六场景及九资源 Git blob 检查通过，已加载游戏无脚本/console 错误或资源 HTTP 失败。手机测试新增竖屏冻结、横屏恢复和保留手动暂停验证，困难指挥器已加载。报告/截图仍在 output/playwright/published-mobile/。
道路形状和单位规则未变；普通 AI 策略、保留约束与 64 场旧 AI 对照结果见 ORDINARY_AI.md。UI 部署继续不包含 EVA 凭据或本地 API 代理。

2026-10-11 最新单位表与更多道路旁装饰已发布：UI运行来源d7b0f7a，Lovable内容提交bf5c7bca29d5a71a63980011f42dd57f33438ddb，部署ID 3ba8f5bd-6ae8-4ea2-afb6-ad7b02d2bca8，缓存版本20261011-meadow1。
数值取自只读20261010.xlsx：狮子攻击30/回血15每秒，药水体型与射程+30%，强化蛇毒4每秒持续15秒，城墙5000。药水射程实际实现与普通AI候选评估保持一致。UI与EVA均已保存，公网仍发布普通UI版本。
1920×1080与844×390双地图各100簇路外花簇、双蘑菇、棉花糖云朵和糖果植被；完整道路几何保持此前版本，静态背景继续复用。发布更新index.html、js/candy-field.js、js/ordinary-ai.js及assets/data/resource-manifest.json，首页iframe及脚本版本同步，CSS、图片与音频保留。
四份新源码在发布前逐字核对，九个公网运行资源在发布后与UI Git LF字节完全一致。桌面、安卓触屏模拟、WebKit触屏×双地图六场景通过，检查战场像素、新数值、100簇布局、计时/部署、暂态尺寸恢复、竖屏冻结/横屏恢复、手动暂停和菜单；无已加载游戏脚本/console错误或资源HTTP失败。截图与报告仍在output/playwright/published-mobile/。
附件来源output/playwright/deploy/wonderland-meadow-balance-20261011.json，内容从git show UI:<路径>生成，不上传本地凭据、属性表、测试文件或代理服务。
