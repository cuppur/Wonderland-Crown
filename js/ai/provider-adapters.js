/* Text-only adapters. Provider-specific thinking stays private and is never passed to memory/UI. */
(() => {
  'use strict';
  const E = window.EVA;
  const DEFAULTS = {
    mock: '', openai: 'https://api.openai.com/v1', compatible: 'http://127.0.0.1:1234/v1',
    anthropic: 'https://api.anthropic.com/v1', gemini: 'https://generativelanguage.googleapis.com/v1beta',
    deepseek: 'https://api.deepseek.com/v1', custom: ''
  };
  const LEVELS = ['auto', 'minimal', 'low', 'medium', 'high', 'max'];
  const SYSTEM = `You control one side of the three-lane strategy game 奇境王冠. Use only the structured Observation and bounded public memory. Return JSON only: {"schemaVersion":1,"summary":"brief public tactic in Chinese","commands":[]}. Never output hidden thoughts or chain-of-thought. At most 6 commands. Commands: deploy {unit:snake|lion|elephant|dragon,lane:top|middle|bottom}; usePotion {unit}; useBurst {lane}; advance/hold/retreat {lane}; focusTarget {lane,targetId:enemy unit id or "enemy-tower"}; setRallyPoint {lane,progress:0.04..0.96}; switchLane {lane,toLane} only on cross map, performed at center junction. Lanes name your own gate; cross lanes exit opposite top/bottom gate. Hold stops marching but attacks in range. Retreat walks back to own gate without attacking. Rally walks to progress then holds. Orders persist for present and future units on that lane until replaced. Potion affects the next deployment of that type. Burst hits enemies on your half of the selected route, not towers. Respect live coins/cooldowns; do not request duplicate card deployments. Empty commands means WAIT. Match time and cooldowns advance independently of API wall-clock latency.`;

  function reasoningCapability(config) {
    const { provider, model = '', reasoningProtocol = 'auto', modelMetadata: meta } = config;
    if (reasoningProtocol === 'none') return { levels: ['auto'], kind: 'none', note: '不发送推理参数' };
    if (['compatible', 'custom'].includes(provider) && reasoningProtocol === 'effort') return { levels: LEVELS, kind: 'openai', note: '按所选兼容协议发送 reasoning_effort' };
    if (provider === 'mock') return { levels: ['auto'], kind: 'none', note: 'Mock 无推理强度' };
    if (provider === 'anthropic') {
      const effort = meta?.capabilities?.effort;
      if (effort?.supported === false) return { levels: ['auto'], kind: 'none', note: '模型不支持推理强度' };
      if (effort?.supported) return { levels: ['auto', ...LEVELS.filter(x => effort[x]?.supported)], kind: 'anthropic', adaptive: meta?.capabilities?.thinking?.types?.adaptive?.supported, note: '档位来自模型能力元数据' };
      if (/claude-(opus-4-[5678]|sonnet-4-6)(-|$)/.test(model)) return { levels: ['auto', 'low', 'medium', 'high', ...(model.includes('opus-4-6') ? ['max'] : [])], kind: 'anthropic', adaptive: /4-[678]/.test(model), note: '已知型号的 effort；未知型号保留 Auto' };
    }
    if (provider === 'gemini') {
      if (/gemini-3(?:[.-]|$)/.test(model)) return { levels: model.includes('flash') ? ['auto', 'minimal', 'low', 'medium', 'high'] : ['auto', 'low', ...(model.includes('3.1') ? ['medium'] : []), 'high'], kind: 'gemini-level', note: 'thinkingLevel；仅显示该系列支持的档位' };
      if (/gemini-2\.5/.test(model)) return { levels: LEVELS, kind: 'gemini-budget', minimum: model.includes('lite') ? 512 : 128, note: '档位转换为 thinkingBudget；受单次 token 上限约束' };
    }
    if (provider === 'deepseek' && /deepseek-(flash|v4)/.test(model)) return { levels: ['auto', 'low', 'high', 'max'], kind: 'deepseek', note: 'thinking + reasoning_effort' };
    if (['openai', 'compatible', 'custom'].includes(provider)) {
      const advertised = meta?.supported_reasoning_efforts;
      if (Array.isArray(advertised)) return { levels: ['auto', ...LEVELS.filter(l => advertised.includes(l))], kind: 'openai', note: '档位来自服务端元数据' };
      if (/^(o[134]|gpt-5|gpt-6)/.test(model) && !/chat|non-reasoning/.test(model)) return { levels: ['auto', ...(/^gpt-5(?:-|$)/.test(model) && !/^gpt-5-[1-9]/.test(model) ? ['minimal'] : []), 'low', 'medium', 'high'], kind: 'openai', note: '保守型号档位；Auto 交由服务端默认' };
    }
    return { levels: ['auto'], kind: 'none', note: provider === 'compatible' || provider === 'custom' ? '能力未知；如服务支持可选择 reasoning_effort 协议' : '模型不支持或能力未知，使用服务端默认' };
  }
  function normalizeReasoningLevel(config) {
    const cap = reasoningCapability(config), level = config.reasoning || 'auto';
    if (level === 'auto') return {};
    if (!cap.levels.includes(level)) throw new Error('CONFIG: selected reasoning level is unsupported');
    if (cap.kind === 'openai') return { reasoning_effort: level };
    if (cap.kind === 'deepseek') return { thinking: { type: 'enabled' }, reasoning_effort: level };
    if (cap.kind === 'anthropic') return { output_config: { effort: level }, ...(cap.adaptive ? { thinking: { type: 'adaptive' } } : {}) };
    if (cap.kind === 'gemini-level') return { thinkingConfig: { thinkingLevel: level } };
    if (cap.kind === 'gemini-budget') return { thinkingConfig: { thinkingBudget: Math.max(cap.minimum, Math.min(({ minimal: 512, low: 1024, medium: 4096, high: 8192, max: 16384 })[level], (config.maxTokens || 4096) - 512)) } };
    return {};
  }
  function publicResponse(data) {
    if (Array.isArray(data?.choices)) return { id: data.id, model: data.model, choices: data.choices.map(c => ({ finish_reason: c.finish_reason, message: { role: c.message?.role, content: c.message?.content } })), usage: data.usage };
    if (Array.isArray(data?.content)) return { id: data.id, model: data.model, stop_reason: data.stop_reason, content: data.content.filter(c => c.type === 'text').map(c => ({ type: 'text', text: c.text })), usage: data.usage };
    if (Array.isArray(data?.candidates)) return { candidates: data.candidates.map(c => ({ finishReason: c.finishReason, content: { parts: (c.content?.parts || []).filter(p => !p.thought && typeof p.text === 'string').map(p => ({ text: p.text })) } })), usageMetadata: data.usageMetadata };
    return { error: data?.error ? { type: data.error.type, code: data.error.code } : null };
  }
  function scrub(value, key) {
    const replace = s => (key ? s.split(key).join('[REDACTED]') : s).replace(/Bearer\s+[^\s"']+/gi, 'Bearer [REDACTED]');
    if (typeof value === 'string') return replace(value);
    if (Array.isArray(value)) return value.map(v => scrub(v, key));
    if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).filter(([k]) => !/apiKey|authorization|reasoning_content|thinking|signature/i.test(k)).map(([k, v]) => [k, scrub(v, key)]));
    return value;
  }
  class ProviderAdapter {
    constructor(config) { this.config = { ...config }; }
    async request(path, body, signal) {
      const c = this.config;
      let base;
      try { base = new URL(c.baseUrl.trim()); } catch (_) { throw new Error('CONFIG: Base URL 无效'); }
      if (!['http:', 'https:'].includes(base.protocol) || base.username || base.password || base.search || base.hash) throw new Error('CONFIG: Base URL 须为不含密钥/查询参数的 HTTP(S) 地址');
      const url = base.href.replace(/\/$/, '') + path;
      const headers = { 'Content-Type': 'application/json' };
      if (c.provider === 'anthropic') { headers['x-api-key'] = c.apiKey; headers['anthropic-version'] = '2023-06-01'; if (c.transport === 'direct') headers['anthropic-dangerous-direct-browser-access'] = 'true'; }
      else if (c.provider === 'gemini') headers['x-goog-api-key'] = c.apiKey;
      else if (c.apiKey) headers.Authorization = 'Bearer ' + c.apiKey;
      let res;
      try {
        res = await fetch(c.transport === 'relay' ? '/eva/api/proxy' : url, c.transport === 'relay'
          ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url, method: body ? 'POST' : 'GET', headers, body, timeout: c.timeout || 20 }), signal }
          : { method: body ? 'POST' : 'GET', headers, ...(body ? { body: JSON.stringify(body) } : {}), signal });
      } catch (err) { if (signal?.aborted) throw err; throw new Error('NETWORK: 无法连接服务，请检查 URL 或使用本地代理'); }
      if (!res.ok) throw new Error(res.status === 504 ? 'TIMEOUT: API 请求超时' : `HTTP_${res.status}: ${({ 401: '密钥无效', 403: '访问被拒绝', 429: '请求限流', 500: '服务端错误', 502: '网络或上游服务错误' })[res.status] || 'API 请求失败'}`);
      const text = await res.text();
      if (text.length > 2000000) throw new Error('JSON_PARSE: API response too large');
      try { return JSON.parse(text); } catch (_) { throw new Error('JSON_PARSE: API response is not JSON'); }
    }
    async listModels(signal) {
      let path = '/models', result = [];
      for (let page = 0; page < 10; page++) {
        const data = await this.request(path, null, signal), models = data.data || data.models;
        if (!Array.isArray(models)) throw new Error('MODELS_UNSUPPORTED: 请手动输入模型 ID');
        result.push(...models.filter(m => this.config.provider !== 'gemini' || !m.supportedGenerationMethods || m.supportedGenerationMethods.includes('generateContent')).map(m => ({ ...m, id: (m.id || m.name || '').replace(/^models\//, '') })).filter(m => m.id));
        if (data.nextPageToken) path = '/models?pageToken=' + encodeURIComponent(data.nextPageToken);
        else if (data.has_more && data.last_id) path = '/models?after_id=' + encodeURIComponent(data.last_id);
        else break;
      }
      return result;
    }
    async decide(observation, memory, signal) {
      const spec = this.buildRequest(SYSTEM, JSON.stringify({ observation, memory })), data = await this.request(spec.path, spec.body, signal);
      return { text: scrub(this.extractText(data), this.config.apiKey), raw: scrub(publicResponse(data), this.config.apiKey), usage: this.usage(data) };
    }
  }
  class OpenAICompatibleAdapter extends ProviderAdapter {
    buildRequest(system, user) { const c = this.config, cap = reasoningCapability(c); return { path: '/chat/completions', body: {
      model: c.model, messages: [{ role: 'system', content: system }, { role: 'user', content: user }], stream: false,
      [cap.kind === 'openai' ? 'max_completion_tokens' : 'max_tokens']: c.maxTokens || 4096,
      ...normalizeReasoningLevel(c), ...(c.jsonMode ? { response_format: { type: 'json_object' } } : {})
    } }; }
    extractText(d) { const c = d.choices?.[0]; if (c?.finish_reason === 'length') throw new Error('JSON_PARSE: token 上限导致输出截断，请提高单次上限'); if (typeof c?.message?.content !== 'string') throw new Error('JSON_PARSE: 缺少文本回答'); return c.message.content; }
    usage(d) { return { inputTokens: d.usage?.prompt_tokens ?? null, outputTokens: d.usage?.completion_tokens ?? null, reasoningTokens: d.usage?.completion_tokens_details?.reasoning_tokens ?? null }; }
  }
  class OpenAIAdapter extends OpenAICompatibleAdapter {}
  class DeepSeekAdapter extends OpenAICompatibleAdapter {}
  class CustomAdapter extends OpenAICompatibleAdapter {}
  class AnthropicAdapter extends ProviderAdapter {
    buildRequest(system, user) { const c = this.config; return { path: '/messages', body: { model: c.model, system, messages: [{ role: 'user', content: user }], max_tokens: c.maxTokens || 4096, ...normalizeReasoningLevel(c) } }; }
    extractText(d) { if (d.stop_reason === 'max_tokens') throw new Error('JSON_PARSE: token 上限导致输出截断'); const text = d.content?.filter(c => c.type === 'text').map(c => c.text).join(''); if (!text) throw new Error('JSON_PARSE: 缺少文本回答'); return text; }
    usage(d) { return { inputTokens: d.usage?.input_tokens ?? null, outputTokens: d.usage?.output_tokens ?? null, reasoningTokens: null }; }
  }
  class GeminiAdapter extends ProviderAdapter {
    buildRequest(system, user) { const c = this.config; return { path: '/models/' + encodeURIComponent(c.model.replace(/^models\//, '')) + ':generateContent', body: {
      systemInstruction: { parts: [{ text: system }] }, contents: [{ role: 'user', parts: [{ text: user }] }],
      generationConfig: { maxOutputTokens: c.maxTokens || 4096, responseMimeType: 'application/json', ...normalizeReasoningLevel(c) }
    } }; }
    extractText(d) { if (d.candidates?.[0]?.finishReason === 'MAX_TOKENS') throw new Error('JSON_PARSE: token 上限导致输出截断'); const text = d.candidates?.[0]?.content?.parts?.filter(p => !p.thought && typeof p.text === 'string').map(p => p.text).join(''); if (!text) throw new Error('JSON_PARSE: 缺少文本回答'); return text; }
    usage(d) { return { inputTokens: d.usageMetadata?.promptTokenCount ?? null, outputTokens: d.usageMetadata?.candidatesTokenCount ?? null, reasoningTokens: d.usageMetadata?.thoughtsTokenCount ?? null }; }
  }
  const classes = { openai: OpenAIAdapter, compatible: OpenAICompatibleAdapter, anthropic: AnthropicAdapter, gemini: GeminiAdapter, deepseek: DeepSeekAdapter, custom: CustomAdapter, mock: E.MockAgent };
  E.Providers = { defaults: DEFAULTS, levels: LEVELS, reasoningCapability, normalizeReasoningLevel,
    create(config) { if (!classes[config.provider]) throw new Error('CONFIG: 未知 Provider'); return new classes[config.provider](config); }, scrub, systemPrompt: SYSTEM };
})();
