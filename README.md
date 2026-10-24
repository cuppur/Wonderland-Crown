# 奇境王冠

安卓版：[下载 2026.10.24 APK](https://github.com/cuppur/Wonderland-Crown/releases/download/v2026.10.24/WonderlandCrown-Android-v2026.10.24.apk) · [Release 与校验文件](https://github.com/cuppur/Wonderland-Crown/releases/tag/v2026.10.24)

安卓为完整离线横屏动物版，安装后显示“奇境王冠·新版”。沿用原签名与包名，可更新旧的同名新版应用。

项目根目录提供两个 Windows 一键入口：

- **一键启动-普通游戏.cmd**：稳定 UI 版本，玩家对抗普通 AI。
- **一键启动-EVA对战.cmd**：两个 AI 自主对战，自动打开 API 配置页。

双击即可自动启动本地服务并打开浏览器。不要直接双击 index.html；EVA 真实 API 需要本地代理。
运行依赖是 Python 3.10+；切换到未检出的另一分支还需要 Git。测试使用 Playwright，不属于游戏运行依赖。

GitHub 保留两个分支：UI（默认稳定版）和 EVA（AI 实验场）。启动器按 Git 分支名定位 UI / EVA 工作区，不把当前检出的 beauty 草稿当作普通游戏；缺少另一工作区时，会从已有的本地/远程分支创建本地检出。

EVA 配置页支持「保存 API 配置」和「删除已保存配置」。保存后自动载入双方 URL、模型、请求选项及密钥；开始比赛会自动检查连接。
Windows 本机保存文件位于 %LOCALAPPDATA%/WonderlandCrown/eva-settings.dpapi，使用当前 Windows 账户加密；它不在项目目录和 GitHub 中。不要把凭据文件复制进仓库。

普通游戏公开网站：https://qijing-wangguan.lovable.app
GitHub：https://github.com/cuppur/Wonderland-Crown
部署只同步 UI 分支的 index.html、css、js 和 assets，保留原目录结构。EVA 的个人密钥和本地代理不部署到公网。

开发检查：python tests/verify_game.py；普通游戏浏览器回归：python tests/playtest_game.py。EVA 额外检查：python tests/playtest_eva.py --quick 和 python tests/playtest_eva_save.py。
