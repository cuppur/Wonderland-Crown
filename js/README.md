# JavaScript 模块拆分顺序

当前阶段只完成 CSS 抽离。JavaScript 仍在 `index.html` 中运行，避免一次性迁移破坏稳定玩法。

后续顺序：`audio.js` → `ui.js` / `cards.js` → `skills.js` / `ai.js` / `units.js` / `battle.js` / `game.js` → `main.js`。

拆分期间使用普通 `defer` 脚本和统一命名空间，兼容静态公网托管，不引入框架或构建工具。
