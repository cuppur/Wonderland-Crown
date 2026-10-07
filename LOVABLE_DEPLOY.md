# Lovable 公网部署
https://qijing-wangguan.lovable.app
项目根目录已经是可直接托管的静态网页结构：`index.html`、`css/`、`assets/`。

1. 将本项目同步到 GitHub 仓库。
2. 在 Lovable 中导入该仓库。
3. 将站点入口设为项目根目录的 `index.html`，无需构建命令。
4. 确认 Lovable 发布产物保留 `assets/images/`、`assets/audio/`、`assets/data/` 的原始目录结构。
5. 发布后用手机访问 HTTPS 公网地址；首次点击后浏览器才允许播放 BGM。

本项目不再生成 ZIP 或内嵌资源版 HTML。所有运行资源通过相对公网路径加载。
