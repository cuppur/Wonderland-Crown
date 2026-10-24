# 奇境王冠

安卓版：[下载 2026.10.24 APK](https://github.com/cuppur/Wonderland-Crown/releases/download/v2026.10.24/WonderlandCrown-Android-v2026.10.24.apk) · [Release 与校验文件](https://github.com/cuppur/Wonderland-Crown/releases/tag/v2026.10.24)

安卓为完整离线横屏动物版，安装后显示“奇境王冠·新版”。沿用原签名与包名，可更新旧的同名新版应用。

## Windows 启动

双击根目录 **一键启动-普通游戏.cmd**，自动打开普通动物游戏，玩家对抗内置困难 AI。运行依赖 Python 3.10+ 和 Git；无需购买 API 或配置密钥。

默认主分支为 UI。启动器按 Git 分支定位稳定工作区；缺少 UI 工作区时自动创建本地检出。启动网址与脚本样式有构建版本标识，服务禁止缓存，避免旧页面串版。

## 游戏与开发

- 正式入口：index.html；发布需保留 css/、js/、assets/。
- 单位：蛇、狮、象、龙；支持双地图、药水、炮阵、暂停、音频及数值报告。
- 属性来源：单位属性表/ 中最新的日期工作簿，只读维护。
- 静态检查：python tests/verify_game.py。
- 浏览器回归：python tests/playtest_game.py。
- 实际战斗属性：python tests/playtest_balance.py。
- 手机专项：python tests/playtest_mobile.py。
- 启动器隔离：python tests/verify_launcher.py；真实入口与缓存回归：python tests/playtest_launcher.py。

测试使用 Playwright 自带 headless 浏览器，不属于游戏运行依赖。

普通游戏网站：https://qijing-wangguan.lovable.app

GitHub：https://github.com/cuppur/Wonderland-Crown

安卓构建方法见 android-app/README.md；签名文件和个人配置不提交到仓库。
