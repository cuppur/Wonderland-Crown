# 奇境王冠发布

稳定分支为 UI，AI 对战分支为 EVA；GitHub 默认分支使用 UI。
仓库：https://github.com/cuppur/Wonderland-Crown
公网：https://qijing-wangguan.lovable.app
Lovable 项目：Wonderland Crown Portal（72e4454c-102f-490a-89bb-af66ac4996be）。

项目为静态游戏，无构建步骤。部署 UI 的 index.html、css/、js/、assets/，必须包括 js/candy-field.js，并保留目录结构。
已有 Lovable 项目在 public/game/ 中保存原游戏，首页 iframe 加载 /game/index.html。更新时替换其中的游戏文件，保持游戏自身代码；发布后验证 /game/index.html 和所有资源。

本地双击根目录的两个 cmd 启动器。EVA 分支的本地 API 配置使用 Windows 加密保存在项目外；不上传密钥、凭据、日志或本地代理服务。UI 公网部署不包含 EVA 配置。
