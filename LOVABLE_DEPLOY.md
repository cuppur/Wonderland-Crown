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
