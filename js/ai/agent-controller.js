(() => {
  'use strict';
  const E = window.EVA;
  class AgentController {
    constructor(side, config, arena) {
      this.side = side; this.config = { ...config }; this.arena = arena; this.adapter = E.Providers.create(config); this.memory = new E.AgentMemory();
      this.status = 'IDLE'; this.isThinking = false; this.nextAt = 0; this.serial = 0; this.epoch = 0; this.errors = 0; this.started = 0;
      this.latency = 0; this.summary = '等待首轮观察'; this.recent = []; this.debug = null; this.controller = null;
    }
    cancel() {
      this.epoch++; this.controller?.abort();
      if (this.pending) {
        this.arena.logger.record({ ...this.pending, latency: performance.now() - this.started, error: 'CANCELLED: game paused or ended; no command executed',
          commandsRequested: [], commandsAccepted: [], commandsRejected: [], publicSummary: '', inputTokens: null, outputTokens: null, reasoningTokens: null, estimatedCost: null });
        this.pending = null;
      }
      this.isThinking = false; this.controller = null; this.status = 'IDLE';
    }
    tick() {
      if (this.isThinking || !this.arena.active || this.arena.engine.state() !== 'playing') return;
      const now = this.arena.engine.readState().elapsed;
      if (now < this.nextAt) { if (!['ERROR', 'TIMEOUT'].includes(this.status) && performance.now() >= (this.executingUntil || 0)) this.status = 'COOLDOWN'; return; }
      void this.decide();
    }
    async decide() {
      if (this.isThinking) return;
      const epoch = ++this.epoch, id = this.arena.matchId + ':' + this.side + ':' + (++this.serial);
      this.isThinking = true; this.status = 'OBSERVING'; this.started = performance.now();
      const observation = this.arena.observations.build(this.side, id + ':obs'), controller = this.controller = new AbortController();
      this.pending = { timestamp: new Date().toISOString(), gameTime: observation.gameTime, side: this.side, provider: this.config.provider, model: this.config.model, observationId: observation.observationId, decisionId: id, retryCount: this.errors };
      const timeout = setTimeout(() => controller.abort('timeout'), (this.config.timeout || 20) * 1000);
      let response, packet, validation = { accepted: [], rejected: [] }, error = null;
      const retryCount = this.errors;
      try {
        this.status = 'THINKING';
        response = await this.adapter.decide(observation, this.memory.context(), controller.signal);
        if (epoch !== this.epoch || !this.arena.active || this.arena.engine.state() !== 'playing') return;
        packet = E.CommandValidator.parse(response.text); this.status = 'EXECUTING';
        validation = this.arena.engine.submit(this.side, packet);
        this.executedCount = validation.accepted.length; this.executingUntil = performance.now() + 350;
        this.summary = packet.summary; this.recent = [...validation.accepted.map(c => ({ at: observation.gameTime, command: c })), ...this.recent].slice(0, 3);
        this.memory.remember(observation, packet, validation);
        if (packet.commands.length && !validation.accepted.length) throw new Error('INVALID_COMMAND: 本轮命令全部被拒绝，执行 WAIT');
        this.errors = 0;
      } catch (e) {
        if (epoch !== this.epoch || !this.arena.active || this.arena.engine.state() !== 'playing') return;
        error = controller.signal.reason === 'timeout' ? 'TIMEOUT: API 超时，本轮 WAIT' : E.Providers.scrub(e?.message || 'NETWORK: API 异常', this.config.apiKey);
        this.status = error.startsWith('TIMEOUT') ? 'TIMEOUT' : 'ERROR'; this.summary = error; this.errors++;
      } finally {
        clearTimeout(timeout);
        if (epoch !== this.epoch) return;
        this.isThinking = false; this.controller = null; this.latency = performance.now() - this.started;
        if (!this.arena.active || this.arena.engine.state() !== 'playing') return;
        this.nextAt = this.arena.engine.readState().elapsed + (this.config.interval || 3);
        const entry = { timestamp: new Date().toISOString(), gameTime: observation.gameTime, side: this.side, provider: this.config.provider, model: this.config.model,
          observationId: observation.observationId, decisionId: id, publicSummary: packet?.summary || '', commandsRequested: packet?.commands || [],
          commandsAccepted: validation.accepted, commandsRejected: validation.rejected, latency: this.latency,
          inputTokens: response?.usage?.inputTokens ?? null, outputTokens: response?.usage?.outputTokens ?? null, reasoningTokens: response?.usage?.reasoningTokens ?? null,
          estimatedCost: null, error, retryCount };
        this.pending = null; this.arena.logger.record(entry);
        this.debug = { observation, rawApiResponse: response?.raw || null, parsedCommand: packet || null, validation, latency: this.latency, error };
        if (!error) this.status = 'EXECUTING';
        if (this.errors >= 3) this.arena.fail(this.side);
        this.arena.changed();
      }
    }
  }
  class Arena {
    constructor(engine, changed, fail) { this.engine = engine; this.changed = changed; this.onFailure = fail; this.observations = new E.ObservationBuilder(engine); this.active = false; this.agents = {}; this.logger = new E.BattleLogger(); this.lastState = 'menu'; }
    start(configs) {
      this.stop(); this.matchId = String(Date.now()); this.logger = new E.BattleLogger(); this.active = true; this.failedSide = null;
      this.agents = Object.fromEntries(['player', 'enemy'].map(side => [side, new AgentController(side, configs[side], this)])); this.lastState = 'playing'; this.changed();
    }
    stop() { this.active = false; Object.values(this.agents).forEach(a => a.cancel()); }
    update() {
      if (!this.active) return;
      const state = this.engine.state();
      if (state !== this.lastState) {
        if (state !== 'playing') Object.values(this.agents).forEach(a => a.cancel());
        this.lastState = state;
      }
      if (state === 'playing') Object.values(this.agents).forEach(a => a.tick());
    }
    fail(side) { this.failedSide = side; this.engine.pause(); Object.values(this.agents).forEach(a => a.cancel()); this.onFailure(side); }
    retry() { this.failedSide = null; for (const a of Object.values(this.agents)) { a.errors = 0; a.nextAt = this.engine.readState().elapsed; } this.engine.resume(); }
    snapshot() { return { active: this.active, failedSide: this.failedSide, stats: this.logger.summary(), agents: Object.fromEntries(Object.entries(this.agents).map(([side, a]) => [side, { status: a.status, isThinking: a.isThinking, serial: a.serial, summary: a.summary, recent: a.recent, latency: a.latency, errors: a.errors, memory: a.memory.context(), debug: a.debug }])) }; }
  }
  E.AgentController = AgentController; E.Arena = Arena;
})();
