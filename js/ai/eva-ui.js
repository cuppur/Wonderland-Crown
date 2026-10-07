(() => {
  'use strict';
  const E = window.EVA, engine = window.QJWGEngine, $ = s => document.querySelector(s), sides = ['player', 'enemy'];
  const labels = { mock: 'Mock · 无需 API', openai: 'OpenAI', compatible: 'OpenAI-compatible', anthropic: 'Anthropic', gemini: 'Google Gemini', deepseek: 'DeepSeek', custom: 'Custom · Chat Completions' };
  const laneLabels = { top: '上路', middle: '中路', bottom: '下路' }, unitLabels = { snake: '毒影蛇', lion: '圣鬃狮', elephant: '磐石象', dragon: '星焰龙' };
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; };
  const show = n => n.classList.remove('hidden'), hide = n => n.classList.add('hidden');
  const entry = el('section', 'eva-entry');
  entry.innerHTML = '<div><b>EVA</b><small>AI ARENA</small><p>AI 对战实验场 · 让两个 AI 自主进行战斗</p></div><button id="evaEnterBtn" class="secondary">进入 EVA</button>';
  $('#menuOverlay .tips').before(entry);
  const configOverlay = el('div', 'eva-overlay hidden'); configOverlay.id = 'evaConfigOverlay';
  configOverlay.innerHTML = `<section class="eva-dialog" role="dialog" aria-modal="true" aria-labelledby="evaConfigTitle">
    <div class="eva-heading"><div><h2 id="evaConfigTitle">EVA · AI 对战配置</h2><p>选好双方指挥官，测试连接，再进入糖果战场。</p></div><button id="evaConfigBack" class="eva-small-btn">返回</button></div>
    <div class="eva-columns">${sides.map(side => `<section class="eva-side-config ${side}" data-side="${side}"><h3>${side === 'player' ? '曙光王庭 · 蓝方 AI' : '暮影王庭 · 红方 AI'}</h3>
      <label>API Provider<select data-field="provider">${Object.entries(labels).map(([value, name]) => `<option value="${value}">${name}</option>`).join('')}</select></label>
      <label>Base URL<input data-field="baseUrl" type="url" autocomplete="off" spellcheck="false" placeholder="https://your-service.example/v1"></label>
      <div class="eva-note" data-info="baseUrl"></div>
      <label>API Key<input data-field="apiKey" type="password" autocomplete="off" spellcheck="false" placeholder="点击保存后，在本机加密保存"></label>
      <div class="eva-tools"><button data-op="test">测试连接</button><button data-op="models">获取模型列表</button><button data-op="clear">清空输入</button></div>
      <label>模型 ID<input data-field="model" list="evaModels-${side}" autocomplete="off" spellcheck="false" placeholder="查询后选择，或手动输入模型 ID"><datalist id="evaModels-${side}"><option value="aggressive-mock"></option><option value="defensive-mock"></option></datalist></label>
      <div class="eva-field-pair"><label>推理强度<select data-field="reasoning"><option value="auto">Auto</option></select></label><label>AI 决策周期<select data-field="interval"><option value="2">2 秒</option><option value="3" selected>3 秒</option><option value="5">5 秒</option><option value="10">10 秒</option></select></label></div>
      <div class="eva-note" data-info="reasoning"></div>
      <details><summary>请求选项</summary><label>连接方式<select data-field="transport"><option value="relay">本地代理 · 推荐</option><option value="direct">浏览器直连 · 服务须支持 CORS</option></select></label>
      <label>兼容服务推理协议<select data-field="reasoningProtocol"><option value="auto">自动识别 / 服务端默认</option><option value="none">不发送推理参数</option><option value="effort">reasoning_effort（需服务支持）</option></select></label>
      <div class="eva-field-pair"><label>请求超时<select data-field="timeout"><option value="10">10 秒</option><option value="20" selected>20 秒</option><option value="30">30 秒</option><option value="60">60 秒</option></select></label><label>单次 token 上限<select data-field="maxTokens"><option value="2048">2048</option><option value="4096" selected>4096</option><option value="8192">8192</option><option value="16384">16384</option><option value="32768">32768</option></select></label></div>
      <label>JSON 模式<select data-field="jsonMode"><option value="false">仅提示 JSON · 兼容性较好</option><option value="true">请求 JSON 格式 · 需服务支持</option></select></label></details>
      <p class="eva-connection" data-info="connection" role="status">Mock 不消耗 API，可直接开始。</p></section>`).join('')}</div>
    <div class="eva-options"><label>地图<select id="evaMap"><option value="cross">交汇战线</option><option value="straight">三路战线</option></select></label><label>时长<select id="evaDuration"><option value="unlimited">无限制</option><option value="180">3 分钟</option><option value="300">5 分钟</option></select></label><label title="以蓝方设置为准，同步双方的决策间隔；网络响应时间仍各自计算"><input id="evaFair" type="checkbox" checked>公平周期 · 同步间隔</label><label title="查看 AI 输入、公开回复、命令和校验结果；不改变 AI 策略"><input id="evaDebugEnabled" type="checkbox">调试面板 · EVA DEBUG</label><label><input id="evaRemember" type="checkbox">记住非敏感配置</label></div>
    <div class="eva-note">公平周期：同步双方决策间隔，以蓝方设置为准，模型响应速度仍可能不同。调试面板：查看战场数据、公开回复和命令校验，平时可关闭。</div>
    <div class="eva-note">点击「保存 API 配置」后，下次打开自动填入双方配置和密钥；配置使用 Windows 本机账户加密。测试连接会发送一次短请求，开始比赛时也会自动检查未测试的连接。</div>
    <p id="evaStorageMessage" class="eva-note" role="status">正在检查本机保存功能…</p>
    <div class="eva-footer"><button id="evaDeleteSettings" class="eva-small-btn" disabled>删除已保存配置</button><button id="evaSaveSettings" class="secondary" disabled>保存 API 配置</button><button id="evaStartBtn" class="primary">开始比赛</button></div><p id="evaConfigMessage" class="eva-connection" role="status"></p>
  </section>`;
  $('#game-shell').append(configOverlay);
  const agents = {};
  for (const side of sides) {
    const panel = agents[side] = el('section', 'eva-agent ' + side + ' eva-hidden'); panel.id = 'evaAgent-' + side;
    panel.innerHTML = '<div class="eva-agent-head"><span>🤖</span><strong></strong></div><div class="eva-agent-meta"></div><div class="eva-agent-state"><span></span><time></time></div><p class="eva-strategy"></p><div class="eva-command-list"></div><button class="eva-agent-link">查看完整日志</button>';
    panel.querySelector('button').addEventListener('click', () => view.openLogs(side)); $('#game-shell').append(panel);
  }
  const debugBtn = el('button', 'eva-debug-btn eva-hidden', 'EVA DEBUG'); debugBtn.id = 'evaDebugBtn'; $('#game-shell').append(debugBtn);
  const logsOverlay = el('div', 'eva-overlay hidden'); logsOverlay.id = 'evaLogsOverlay';
  logsOverlay.innerHTML = '<section class="eva-dialog" role="dialog" aria-modal="true" aria-labelledby="evaLogsTitle"><div class="eva-heading"><h2 id="evaLogsTitle">EVA · 战斗日志</h2><button id="evaLogsClose" class="eva-small-btn">返回比赛</button></div><div class="eva-log-tabs"><select id="evaLogSide"><option value="player">蓝方 AI</option><option value="enemy">红方 AI</option></select><button id="evaLogTab" class="eva-small-btn">完整日志</button><button id="evaDebugTab" class="eva-small-btn eva-hidden">EVA DEBUG</button><button id="evaExportBtn" class="eva-small-btn">导出 JSON 日志</button></div><div id="evaLogBody" class="eva-log-view"></div><pre id="evaDebugBody" class="eva-debug-pre eva-hidden"></pre></section>';
  $('#game-shell').append(logsOverlay);
  const failureOverlay = el('div', 'eva-overlay hidden'); failureOverlay.id = 'evaFailureOverlay';
  failureOverlay.innerHTML = '<section class="eva-dialog eva-error-panel" role="dialog" aria-modal="true" aria-labelledby="evaFailureTitle"><h2 id="evaFailureTitle" class="eva-error-title"></h2><p id="evaFailureMessage"></p><p>连续 3 轮连接或格式错误，比赛已暂停；双方待处理请求已取消。</p><div class="eva-footer"><button id="evaRetry" class="primary">重试</button><button id="evaReconfigure" class="secondary">重新配置 API</button><button id="evaForfeit" class="eva-small-btn">判负</button></div></section>';
  $('#game-shell').append(failureOverlay);
  const result = el('div'); result.id = 'evaResult'; $('#resultDetail').after(result);
  const form = side => $(`[data-side="${side}"]`), field = (side, name) => form(side).querySelector(`[data-field="${name}"]`);
  const metadata = { player: [], enemy: [] }, tested = { player: null, enemy: null }, configRequests = {};
  const readConfig = side => {
    const c = Object.fromEntries([...form(side).querySelectorAll('[data-field]')].map(n => [n.dataset.field, n.value.trim()]));
    for (const k of ['interval', 'timeout', 'maxTokens']) c[k] = Number(c[k]); c.jsonMode = c.jsonMode === 'true';
    c.modelMetadata = metadata[side].find(m => m.id === c.model) || null; return c;
  };
  const signature = c => { const { modelMetadata, ...values } = c; return JSON.stringify(values); }; // memory only; never saved or exported
  let storageAvailable = false, configEdited = false;
  async function settingsRequest(action, data = {}) {
    const response = await fetch('/eva/api/settings/' + action, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data), cache: 'no-store', signal: AbortSignal.timeout(5000) });
    if (!response.ok) throw new Error('本机配置保存失败，请从根目录的一键启动 EVA 入口打开。');
    return response.json();
  }
  function applySavedSettings(settings) {
    for (const side of sides) {
      for (const [name, value] of Object.entries(settings[side] || {})) if (field(side, name) && name !== 'reasoning') field(side, name).value = String(value);
      providerChanged(side, true); field(side, 'reasoning').value = settings[side].reasoning;
      status(side, '已载入保存的配置；开始比赛时自动测试连接。');
    }
    const options = settings.options || {};
    $('#evaMap').value = options.map || 'cross'; $('#evaDuration').value = options.duration || 'unlimited'; $('#evaFair').checked = options.fair !== false; $('#evaDebugEnabled').checked = options.debug === true; syncFair();
  }
  async function restoreSavedSettings() {
    try {
      if (!['localhost', '127.0.0.1'].includes(location.hostname)) throw new Error('local-only');
      const response = await fetch('/eva/api/health', { cache: 'no-store', signal: AbortSignal.timeout(3000) });
      if (!response.ok || (await response.json()).settingsStorage !== 'windows-dpapi') throw new Error('no-storage');
      storageAvailable = true; $('#evaSaveSettings').disabled = false; $('#evaDeleteSettings').disabled = false;
      const result = await settingsRequest('load');
      if (result.saved && !configEdited) { applySavedSettings(result.settings); $('#evaStorageMessage').textContent = '已自动载入本机加密保存的 API 配置。修改后请再次点击保存。'; }
      else $('#evaStorageMessage').textContent = '支持本机加密保存；点击保存后，下次打开无需重新输入。';
    } catch (_) { $('#evaStorageMessage').textContent = '保存密钥需要根目录「一键启动 EVA」；静态网页仅记住非敏感配置。'; }
  }
  async function saveSettings() {
    await settingsReady;
    if (!storageAvailable) return;
    const button = $('#evaSaveSettings'); button.disabled = true;
    try {
      syncFair(); const data = { schemaVersion: 1, ...Object.fromEntries(sides.map(side => [side, readConfig(side)])), options: { map: $('#evaMap').value, duration: $('#evaDuration').value, fair: $('#evaFair').checked, debug: $('#evaDebugEnabled').checked } };
      for (const side of sides) ensureConfig(data[side]);
      await settingsRequest('save', data); $('#evaStorageMessage').textContent = 'API 配置已加密保存到本机，下次打开自动载入。';
    } catch (err) { $('#evaStorageMessage').textContent = err.message; }
    finally { button.disabled = false; }
  }
  function status(side, message, good = null) { const p = form(side).querySelector('[data-info="connection"]'); p.textContent = message; p.className = 'eva-connection' + (good === true ? ' ok' : good === false ? ' bad' : ''); }
  function reasoning(side) { const c = readConfig(side), cap = E.Providers.reasoningCapability(c), select = field(side, 'reasoning'), previous = select.value; select.replaceChildren(...cap.levels.map(l => { const o = el('option', '', l === 'auto' ? 'Auto · 服务默认' : l === 'none' ? 'None · 关闭推理' : l[0].toUpperCase() + l.slice(1)); o.value = l; return o; })); select.value = cap.levels.includes(previous) ? previous : 'auto'; select.disabled = cap.levels.length === 1; form(side).querySelector('[data-info="reasoning"]').textContent = cap.note; }
  function baseUrlHint(side) {
    const hint = form(side).querySelector('[data-info="baseUrl"]'), value = field(side, 'baseUrl').value.trim();
    hint.replaceChildren();
    if (/^https:\/\/(?:www\.)?packyapi\.(?:ai|com)(?:\/|$)/i.test(value)) {
      hint.append(document.createTextNode('请核对 Packy 数据看板中的 API Endpoint。官方当前主站示例：https://cf.api.fan/v1。'));
      const link = el('a', '', '查看官方说明'); link.href = 'https://docs.packyapi.com/docs/register/#api-端点说明'; link.target = '_blank'; link.rel = 'noopener noreferrer'; hint.append(link);
    } else if (field(side, 'provider').value !== 'mock') hint.textContent = '填写服务商的 API Endpoint，包含版本路径；不包含 /models 或 /chat/completions。';
  }
  function providerChanged(side, keep = false) {
    const provider = field(side, 'provider').value, mock = provider === 'mock';
    field(side, 'baseUrl').disabled = mock; field(side, 'apiKey').disabled = mock; field(side, 'reasoningProtocol').disabled = !['compatible', 'custom'].includes(provider);
    if (!keep) { field(side, 'apiKey').value = ''; field(side, 'baseUrl').value = E.Providers.defaults[provider]; field(side, 'model').value = mock ? (side === 'player' ? 'aggressive-mock' : 'defensive-mock') : ''; metadata[side] = []; $(`#evaModels-${side}`).replaceChildren(); }
    tested[side] = null; reasoning(side); baseUrlHint(side); status(side, mock ? 'Mock 不消耗 API，可直接开始。' : '填入配置后，点击测试连接。');
  }
  function syncFair() { field('enemy', 'interval').disabled = $('#evaFair').checked; if ($('#evaFair').checked) field('enemy', 'interval').value = field('player', 'interval').value; }
  const ensureConfig = c => { if (!c.model) throw new Error('请输入模型 ID'); if (c.provider !== 'mock' && !c.baseUrl) throw new Error('请输入 Base URL'); if (!['mock', 'compatible', 'custom'].includes(c.provider) && !c.apiKey) throw new Error('请输入 API Key'); };
  async function configOperation(side, op) {
    if (configRequests[side]) return;
    const controller = new AbortController(); configRequests[side] = controller;
    const c = readConfig(side), buttons = [...form(side).querySelectorAll('.eva-tools button')]; buttons.forEach(b => b.disabled = true);
    const timer = setTimeout(() => controller.abort('timeout'), c.timeout * 1000); status(side, op === 'models' ? '正在查询模型列表…' : '正在测试连接…');
    try {
      if (op === 'test') ensureConfig(c); else if (c.provider !== 'mock' && !c.baseUrl) throw new Error('请输入 Base URL');
      const adapter = E.Providers.create(c);
      if (op === 'models') {
        metadata[side] = await adapter.listModels(controller.signal);
        if (signature(c) !== signature(readConfig(side))) { status(side, '配置已变更，请重新查询。'); return; }
        $(`#evaModels-${side}`).replaceChildren(...metadata[side].map(m => { const o = el('option'); o.value = m.id; return o; }));
        if (!c.model && metadata[side].length) field(side, 'model').value = metadata[side][0].id;
        reasoning(side); tested[side] = null; status(side, `已获取 ${metadata[side].length} 个模型，可选择或手动输入。`, true);
      } else {
        const o = new E.ObservationBuilder(engine).build(side, 'connection-test');
        const response = await adapter.decide(o, { connectionTest: true, instruction: 'Return schemaVersion 1, a short summary and empty commands.' }, controller.signal);
        E.CommandValidator.parse(response.text);
        if (signature(c) === signature(readConfig(side))) { tested[side] = signature(c); status(side, '连接测试通过，模型已返回结构化 JSON。', true); }
        else status(side, '配置已变更，请重新测试连接。');
      }
    } catch (err) {
      const message = controller.signal.reason === 'timeout' ? '请求超时，请检查服务或调整请求超时。' : controller.signal.aborted ? '请求已取消，可重新查询。' : E.Providers.scrub(err.message, c.apiKey);
      status(side, op === 'models' ? `获取模型列表失败：${message}。确认连接可用后，也可手动输入模型 ID。` : message, false);
    }
    finally { clearTimeout(timer); configRequests[side] = null; buttons.forEach(b => b.disabled = false); }
  }
  const commandText = c => ({ deploy: `↓ ${unitLabels[c.unit] || c.unit} → ${laneLabels[c.lane]}`, usePotion: `🧪 药水 → ${unitLabels[c.unit]}`, useBurst: `大炮 ×10 → ${laneLabels[c.lane]}`, advance: `前进 → ${laneLabels[c.lane]}`, hold: `驻守 → ${laneLabels[c.lane]}`, retreat: `撤退 → ${laneLabels[c.lane]}`, focusTarget: `集火 → ${c.targetId}`, switchLane: `换路 → ${laneLabels[c.toLane]}`, setRallyPoint: `集结 → ${laneLabels[c.lane]} ${Math.round(c.progress * 100)}%` })[c.action] || c.action;
  const view = E.view = {
    configs: null, logPaused: false, debug: false, lastPaint: 0, reconfiguring: false,
    openConfig(reconfigure = false) { this.reconfiguring = reconfigure; $('#evaMap').disabled = reconfigure; $('#evaDuration').disabled = reconfigure; $('#evaStartBtn').textContent = reconfigure ? '继续比赛' : '开始比赛'; hide(failureOverlay); show(configOverlay); $('#evaConfigMessage').textContent = ''; field('player', 'provider').focus(); },
    closeConfig() { hide(configOverlay); Object.values(configRequests).forEach(c => c?.abort()); if (this.reconfiguring && E.arena.failedSide) show(failureOverlay); },
    async start() {
      const button = $('#evaStartBtn'); button.disabled = true;
      try {
        await settingsReady;
        syncFair(); const configs = Object.fromEntries(sides.map(side => [side, readConfig(side)]));
        for (const side of sides) { ensureConfig(configs[side]); if (configRequests[side]) throw new Error('请等待连接测试完成'); }
        const untested = sides.filter(side => configs[side].provider !== 'mock' && tested[side] !== signature(configs[side]));
        if (untested.length) { $('#evaConfigMessage').textContent = '正在检查双方 API 连接…'; await Promise.all(untested.map(side => configOperation(side, 'test'))); }
        for (const side of sides) { if (signature(configs[side]) !== signature(readConfig(side))) throw new Error('配置已更改，请重新开始比赛'); if (configs[side].provider !== 'mock' && tested[side] !== signature(configs[side])) throw new Error((side === 'player' ? '蓝方' : '红方') + '连接未通过，请查看上方具体原因'); }
        this.configs = configs; this.debug = $('#evaDebugEnabled').checked;
        try { if ($('#evaRemember').checked) localStorage.setItem('qjwg-eva-settings-v1', JSON.stringify(Object.fromEntries(sides.map(side => { const { apiKey, modelMetadata, ...safe } = configs[side]; return [side, safe]; })))); else localStorage.removeItem('qjwg-eva-settings-v1'); } catch (_) { $('#evaRemember').checked = false; }
        hide(configOverlay); $('#game-shell').classList.add('eva-match'); agents.player.classList.remove('eva-hidden'); agents.enemy.classList.remove('eva-hidden'); debugBtn.classList.toggle('eva-hidden', !this.debug); $('#evaDebugTab').classList.toggle('eva-hidden', !this.debug); result.replaceChildren(); $('#resultOverlay').classList.add('eva-result');
        if (this.reconfiguring && E.arena.active) { for (const side of sides) { const a = E.arena.agents[side]; a.cancel(); a.config = configs[side]; a.adapter = E.Providers.create(configs[side]); } E.arena.retry(); }
        else { E.arena.stop(); engine.start({ mode: $('#evaMap').value, duration: $('#evaDuration').value }); E.arena.start(configs); }
        this.reconfiguring = false; this.paint();
      } catch (err) { $('#evaConfigMessage').textContent = err.message; }
      finally { button.disabled = false; }
    },
    restart() { E.arena.stop(); result.replaceChildren(); engine.start({ mode: $('#evaMap').value, duration: $('#evaDuration').value }); E.arena.start(this.configs); this.paint(); },
    leave() { E.arena.stop(); hide(configOverlay); hide(logsOverlay); hide(failureOverlay); Object.values(configRequests).forEach(c => c?.abort()); agents.player.classList.add('eva-hidden'); agents.enemy.classList.add('eva-hidden'); debugBtn.classList.add('eva-hidden'); $('#game-shell').classList.remove('eva-match'); $('#resultOverlay').classList.remove('eva-result'); result.replaceChildren(); this.logPaused = false; },
    failed(side) { $('#evaFailureTitle').textContent = (side === 'player' ? '蓝方' : '红方') + ' AI 连接异常'; $('#evaFailureMessage').textContent = E.arena.agents[side].summary; show(failureOverlay); $('#evaRetry').focus(); },
    paint() {
      if (!E.arena.active) return;
      const now = engine.readState().elapsed;
      for (const side of sides) {
        const a = E.arena.agents[side], panel = agents[side]; if (!a) continue;
        panel.querySelector('strong').textContent = a.config.model;
        panel.querySelector('.eva-agent-meta').textContent = `${labels[a.config.provider]} · ${a.config.reasoning.toUpperCase()} · ${a.config.interval}s`;
        const state = panel.querySelector('.eva-agent-state span'); state.textContent = '● ' + a.status + (a.status === 'EXECUTING' ? ' · ' + (a.executedCount || 0) : ''); state.classList.toggle('error', ['ERROR', 'TIMEOUT'].includes(a.status));
        panel.querySelector('time').textContent = a.isThinking ? ((performance.now() - a.started) / 1000).toFixed(1) + 's' : a.latency ? (a.latency / 1000).toFixed(2) + 's' : `${Math.max(0, a.nextAt - now).toFixed(1)}s`;
        panel.querySelector('.eva-strategy').textContent = a.summary;
        panel.querySelector('.eva-command-list').replaceChildren(...a.recent.map(({ at, command }) => el('div', '', `${Math.floor(at / 60)}:${String(Math.floor(at % 60)).padStart(2, '0')} ${commandText(command)}`)));
      }
      $('#modeLabel').textContent = 'EVA · ' + (engine.readState().mode === 'cross' ? '交汇战线' : '三路战线');
    },
    tick(ts) { if (ts - this.lastPaint >= 200) { this.lastPaint = ts; this.paint(); if (!logsOverlay.classList.contains('hidden')) this.paintLogs(); } },
    openLogs(side = 'player', debug = false) { this.logPaused = engine.state() === 'playing'; if (this.logPaused) engine.pause(); $('#evaLogSide').value = side; $('#evaLogBody').classList.toggle('eva-hidden', debug); $('#evaDebugBody').classList.toggle('eva-hidden', !debug); show(logsOverlay); this.paintLogs(); $('#evaLogsClose').focus(); },
    closeLogs() { hide(logsOverlay); if (this.logPaused && !E.arena.failedSide) engine.resume(); this.logPaused = false; },
    paintLogs() {
      const side = $('#evaLogSide').value;
      if (!$('#evaDebugBody').classList.contains('eva-hidden')) { $('#evaDebugBody').textContent = JSON.stringify(E.arena.agents[side]?.debug || { status: '尚无决策' }, null, 2); return; }
      const table = el('table', 'eva-log-table'); const head = el('tr'); for (const t of ['游戏时间 / 决策', 'Provider / 模型', '公开战术摘要', '命令与校验', '延迟 / Tokens / 错误']) head.append(el('th', '', t)); const thead = el('thead'); thead.append(head); table.append(thead); const body = el('tbody');
      for (const e of E.arena.logger.entries.filter(e => e.side === side).slice(-200).reverse()) { const row = el('tr'); for (const text of [e.gameTime.toFixed(1) + 's · ' + e.decisionId, e.provider + ' / ' + e.model, e.publicSummary || 'WAIT', e.commandsAccepted.map(commandText).join('；') + e.commandsRejected.map(r => '\n拒绝：' + r.reason).join(''), `${Math.round(e.latency)}ms · In ${e.inputTokens ?? '?'} / Out ${e.outputTokens ?? '?'} / Reason ${e.reasoningTokens ?? '?'}${e.error ? '\n' + e.error : ''}`]) row.append(el('td', '', text)); body.append(row); }
      table.append(body); $('#evaLogBody').replaceChildren(el('p', 'eva-note', '页面显示最近 200 轮，导出最多 1000 轮；只记录公开摘要与命令。'), table);
    },
    finish(win, reason) {
      E.arena.update(); for (const a of Object.values(E.arena.agents)) a.status = 'IDLE'; this.paint();
      const configs = this.configs, stats = E.arena.logger.summary(), towers = engine.readState().towers;
      $('#resultTitle').style.color = win === 'draw' ? '#9a6ba3' : win === 'player' ? '#3f86bf' : '#bd6d91';
      $('#resultTitle').textContent = win === 'draw' ? 'EVA · 平局' : `胜者：${configs[win].model}`;
      result.replaceChildren(el('div', 'eva-vs', configs.player.model + '  VS  ' + configs.enemy.model));
      $('#resultDetail').textContent = `${reason} · 战斗 ${engine.readState().elapsed.toFixed(1)} 秒`;
      const table = el('table', 'eva-result-table'); const head = el('tr'); for (const text of ['对战统计', '蓝方 AI', '红方 AI']) head.append(el('th', '', text)); table.append(head);
      const rows = [ ['API 请求 / 有效决策', s => `${s.apiRequests || 0} / ${s.decisions}`], ['Input / Output Token', s => `${s.inputTokens} / ${s.outputTokens}${s.usageKnown ? '' : '（部分未报告）'}`], ['Reasoning Token', s => s.reasoningReported ? s.reasoningTokens : '未报告'], ['平均 / 最大响应', s => `${(s.latencyAverage / 1000).toFixed(2)} / ${(s.latencyMax / 1000).toFixed(2)} 秒`], ['执行 / 拒绝命令', s => `${s.accepted} / ${s.rejected}`], ['出兵 / 药水 / 炮阵', s => `${s.deployed} / ${s.potions} / ${s.bursts}`], ['错误 / 取消请求', s => `${s.errors} / ${s.cancelled}`] ];
      for (const [title, format] of rows) { const row = el('tr'); row.append(el('td', '', title)); for (const side of sides) row.append(el('td', '', format(stats[side]))); table.append(row); }
      const hp = el('tr'); hp.append(el('td', '', '最终城墙 HP')); for (const side of sides) hp.append(el('td', '', Math.ceil(towers[side].hp))); table.append(hp); result.append(table, el('p', 'eva-note', '未配置可核验价格，不估算 API 费用。Mock 请求不产生 token 消耗。'));
      const log = el('button', 'secondary', '查看完整战斗日志'); log.addEventListener('click', () => this.openLogs()); result.append(log);
    }
  };
  E.arena = new E.Arena(engine, () => view.paint(), side => view.failed(side));
  for (const side of sides) {
    providerChanged(side);
    form(side).addEventListener('input', ev => { if (!ev.target.dataset.field) return; tested[side] = null; if (ev.target.dataset.field === 'provider') providerChanged(side); else { if (ev.target.dataset.field === 'baseUrl') baseUrlHint(side); if (['model', 'reasoningProtocol'].includes(ev.target.dataset.field)) reasoning(side); status(side, '配置已更新，请测试当前连接。'); } if (side === 'player' && ev.target.dataset.field === 'interval') { tested.enemy = null; syncFair(); } });
    form(side).querySelectorAll('[data-op]').forEach(b => b.addEventListener('click', () => { if (b.dataset.op === 'clear') { field(side, 'apiKey').value = ''; tested[side] = null; status(side, '密钥已清除。'); } else void configOperation(side, b.dataset.op); }));
  }
  try { const stored = JSON.parse(localStorage.getItem('qjwg-eva-settings-v1')); if (stored) { for (const side of sides) { for (const [name, value] of Object.entries(stored[side] || {})) { if (name !== 'apiKey' && field(side, name)) field(side, name).value = String(value); } providerChanged(side, true); } $('#evaRemember').checked = true; } } catch (_) {}
  configOverlay.addEventListener('input', () => { configEdited = true; });
  const settingsReady = restoreSavedSettings();
  $('#evaSaveSettings').addEventListener('click', () => void saveSettings());
  $('#evaDeleteSettings').addEventListener('click', async () => {
    await settingsReady;
    try { await settingsRequest('clear'); for (const side of sides) { field(side, 'apiKey').value = ''; tested[side] = null; } $('#evaStorageMessage').textContent = '已删除本机保存的配置，并清空当前密钥输入。'; }
    catch (err) { $('#evaStorageMessage').textContent = err.message; }
  });
  syncFair(); $('#evaFair').addEventListener('change', () => { syncFair(); tested.enemy = null; });
  $('#evaEnterBtn').addEventListener('click', () => view.openConfig()); $('#evaConfigBack').addEventListener('click', () => view.closeConfig()); $('#evaStartBtn').addEventListener('click', () => view.start());
  if (new URLSearchParams(location.search).get('eva') === '1') void settingsReady.then(() => view.openConfig());
  $('#evaLogsClose').addEventListener('click', () => view.closeLogs()); $('#evaLogSide').addEventListener('change', () => view.paintLogs()); $('#evaLogTab').addEventListener('click', () => { $('#evaLogBody').classList.remove('eva-hidden'); $('#evaDebugBody').classList.add('eva-hidden'); view.paintLogs(); });
  $('#evaDebugTab').addEventListener('click', () => { $('#evaLogBody').classList.add('eva-hidden'); $('#evaDebugBody').classList.remove('eva-hidden'); view.paintLogs(); }); debugBtn.addEventListener('click', () => view.openLogs('player', true));
  $('#evaRetry').addEventListener('click', () => { hide(failureOverlay); E.arena.retry(); }); $('#evaReconfigure').addEventListener('click', () => view.openConfig(true)); $('#evaForfeit').addEventListener('click', () => { const side = E.arena.failedSide; hide(failureOverlay); E.arena.failedSide = null; engine.forfeit(side); });
  $('#evaExportBtn').addEventListener('click', () => { const blob = new Blob([JSON.stringify(E.arena.logger.export(), null, 2)], { type: 'application/json' }), url = URL.createObjectURL(blob), a = el('a'); a.href = url; a.download = 'eva-battle-log.json'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); });
  window.addEventListener('eva-ended', ev => view.finish(ev.detail.win, ev.detail.reason));
  document.addEventListener('keydown', ev => { if (ev.key !== 'Escape') return; if (!logsOverlay.classList.contains('hidden')) { ev.preventDefault(); ev.stopImmediatePropagation(); view.closeLogs(); } else if (!configOverlay.classList.contains('hidden')) { ev.preventDefault(); ev.stopImmediatePropagation(); view.closeConfig(); } else if (!failureOverlay.classList.contains('hidden')) { ev.preventDefault(); ev.stopImmediatePropagation(); } }, true);
  if (window.__QJWG_TEST__) window.__EVA_TEST__ = {
    snapshot: () => E.arena.snapshot(), observation: side => E.arena.observations.build(side, 'test-observation'), submit: (side, packet) => engine.submit(side, packet),
    async simulate(seconds) { for (let i = 0; i < Math.min(seconds, 6000) * 4 && engine.state() === 'playing'; i++) { window.__QJWG_TEST__.step(.25); E.arena.update(); await new Promise(r => setTimeout(r, 0)); } return E.arena.snapshot(); }
  };
})();
