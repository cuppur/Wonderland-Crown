/* EVA v1: pure structured state, no renderer or DOM dependency. */
(() => {
  'use strict';
  const E = window.EVA = window.EVA || {};
  const LANES = ['top', 'middle', 'bottom'];
  const ACTIONS = ['deploy', 'usePotion', 'useBurst', 'advance', 'hold', 'retreat', 'focusTarget', 'switchLane', 'setRallyPoint'];
  const round = n => Math.round(n * 1000) / 1000;
  const other = side => side === 'player' ? 'enemy' : 'player';
  const laneIndex = (side, mode, lane) => side === 'enemy' && mode === 'cross' ? 2 - LANES.indexOf(lane) : LANES.indexOf(lane);
  const laneName = (side, mode, index) => LANES[side === 'enemy' && mode === 'cross' ? 2 - index : index];
  E.Protocol = { schemaVersion: 1, LANES, ACTIONS, laneIndex, laneName, other };

  class ObservationBuilder {
    constructor(engine) { this.engine = engine; }
    build(side, id) {
      const s = this.engine.readState(), foe = other(side), progress = t => round(side === 'player' ? t : 1 - t);
      const status = team => ({
        side: team === 'player' ? 'blue' : 'red', towerHp: round(s.towers[team].hp), towerMaxHp: s.towers[team].maxHp,
        coins: round(s.coins[team]), cooldowns: Object.fromEntries(Object.entries({ ...s.cool[team], ...s.tacticCool[team] }).map(([k, v]) => [k, round(v)])),
        potionArmed: s.potionArmed[team]
      });
      const units = s.units.map(u => ({
        id: u.id, owner: u.side === side ? 'self' : 'enemy', type: u.type, lane: laneName(side, s.mode, u.lane),
        progress: progress(u.t), position: { x: round(side === 'player' ? u.x : 1 - u.x), y: round(u.y) },
        hp: round(u.hp), maxHp: u.maxHp, attack: u.attack, attackInterval: u.interval,
        movementPerSecond: round(u.speed / 1070), rangeProgress: round(u.range / 1070), buffed: u.buffed,
        status: u.status, order: u.order || 'advance', focusTargetId: u.focusTargetId ?? null,
        rallyProgress: u.rallyT == null ? null : progress(u.rallyT)
      }));
      const lanes = Object.fromEntries(LANES.map(name => {
        const here = units.filter(u => u.lane === name), friends = here.filter(u => u.owner === 'self'), enemies = here.filter(u => u.owner === 'enemy');
        return [name, { exitLane: s.mode === 'cross' ? LANES[2 - LANES.indexOf(name)] : name,
          friendlyIds: friends.map(u => u.id), enemyIds: enemies.map(u => u.id),
          friendlyHp: round(friends.reduce((n, u) => n + u.hp, 0)), enemyHp: round(enemies.reduce((n, u) => n + u.hp, 0)),
          nearestThreatProgress: enemies.length ? Math.min(...enemies.map(u => u.progress)) : null }];
      }));
      return { schemaVersion: 1, observationId: id, tick: s.tick, gameTime: round(s.elapsed),
        timeRemaining: Number.isFinite(s.timeLeft) ? round(s.timeLeft) : null, map: s.mode,
        self: status(side), enemy: status(foe), units, lanes,
        rules: { ...s.rules, maxCommands: 6, supportedCommands: s.mode === 'cross' ? ACTIONS : ACTIONS.filter(a => a !== 'switchLane'),
          coordinates: 'progress and position.x increase from self toward enemy; y increases from top to bottom; lanes name self gate; all units and resources are public' },
        recentEvents: s.events.slice(-12).map(e => ({ ...e, side: e.side ? (e.side === side ? 'self' : 'enemy') : null,
          lane: Number.isInteger(e.lane) ? laneName(side, s.mode, e.lane) : null })) };
    }
  }

  class CommandValidator {
    static parse(text) {
      if (typeof text !== 'string' || text.length > 64000) throw new Error('JSON_PARSE: response must be text under 64KB');
      let value;
      try { value = JSON.parse(text.trim().replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '')); }
      catch (_) { throw new Error('JSON_PARSE: model did not return valid JSON'); }
      if (!value || value.schemaVersion !== 1 || typeof value.summary !== 'string' || !Array.isArray(value.commands)) throw new Error('INVALID_COMMAND: expected schemaVersion=1, summary, commands');
      return { schemaVersion: 1, summary: value.summary.slice(0, 280), commands: value.commands };
    }
    // Validate against live state immediately before execution, reserving resources within the batch.
    static execute(engine, side, packet, apply) {
      const state = engine.readState(), accepted = [], rejected = [], seen = new Set(), issued = new Set();
      const budget = { coins: state.coins[side], cool: { ...state.cool[side] }, skills: { ...state.tacticCool[side] }, armed: state.potionArmed[side] };
      if (packet?.schemaVersion !== 1 || !Array.isArray(packet.commands)) return { accepted, rejected: [{ command: null, reason: 'INVALID_SCHEMA' }] };
      for (const [i, c] of packet.commands.entries()) {
        let reason = null;
        if (i >= 6) reason = 'COMMAND_LIMIT';
        else if (state.state !== 'playing') reason = 'GAME_NOT_PLAYING';
        else if (!c || typeof c !== 'object' || Array.isArray(c) || !ACTIONS.includes(c.action)) reason = 'UNKNOWN_ACTION';
        else if (!LANES.includes(c.lane) && c.action !== 'usePotion') reason = 'INVALID_LANE';
        else if (Object.keys(c).some(k => !['action', 'unit', 'lane', 'targetId', 'toLane', 'progress'].includes(k))) reason = 'UNKNOWN_FIELD';
        const key = c && typeof c === 'object' ? JSON.stringify(Object.keys(c).sort().map(k => [k, c[k]])) : String(c);
        if (!reason && seen.has(key)) reason = 'DUPLICATE';
        seen.add(key);
        if (!reason && ['deploy', 'usePotion'].includes(c.action)) {
          const unit = Object.hasOwn(state.rules.units, c.unit) ? state.rules.units[c.unit] : null;
          if (!unit) reason = 'UNKNOWN_UNIT';
          else if (c.action === 'deploy') {
            if (budget.cool[c.unit] > 0 || issued.has('deploy:' + c.unit)) reason = 'UNIT_COOLDOWN';
            else if (budget.coins < unit.cost) reason = 'INSUFFICIENT_COINS';
            else { budget.coins -= unit.cost; budget.cool[c.unit] = unit.cooldown; if (budget.armed === c.unit) budget.armed = null; }
          } else if (budget.armed) reason = 'POTION_ALREADY_ARMED';
          else if (budget.skills.potion > 0) reason = 'SKILL_COOLDOWN';
          else if (budget.coins < state.rules.potion.cost) reason = 'INSUFFICIENT_COINS';
          else { budget.coins -= state.rules.potion.cost; budget.skills.potion = state.rules.potion.cooldown; budget.armed = c.unit; }
        }
        if (!reason && c.action === 'useBurst') {
          if (budget.skills.burst > 0) reason = 'SKILL_COOLDOWN';
          else if (budget.coins < state.rules.burst.cost) reason = 'INSUFFICIENT_COINS';
          else { budget.coins -= state.rules.burst.cost; budget.skills.burst = state.rules.burst.cooldown; }
        }
        if (!reason && c.action === 'focusTarget' && c.targetId !== 'enemy-tower' && !state.units.some(u => !u.dead && u.side !== side && u.id === c.targetId)) reason = 'INVALID_TARGET';
        if (!reason && c.action === 'switchLane' && (state.mode !== 'cross' || !LANES.includes(c.toLane) || c.toLane === c.lane)) reason = 'LANE_SWITCH_UNAVAILABLE';
        if (!reason && c.action === 'setRallyPoint' && (typeof c.progress !== 'number' || !Number.isFinite(c.progress) || c.progress < .04 || c.progress > .96)) reason = 'INVALID_RALLY_POINT';
        const orderKey = 'order:' + c?.lane;
        if (!reason && !['deploy', 'usePotion', 'useBurst'].includes(c.action) && issued.has(orderKey)) reason = 'CONFLICTING_ORDER';
        if (reason) { rejected.push({ command: c, reason }); continue; }
        try {
          const clean = Object.fromEntries(Object.entries(c).filter(([k]) => ['action', 'unit', 'lane', 'targetId', 'toLane', 'progress'].includes(k)));
          if (!apply(clean)) { rejected.push({ command: clean, reason: 'STATE_CHANGED' }); continue; }
          accepted.push(clean);
          if (c.action === 'deploy') issued.add('deploy:' + c.unit);
          else if (!['usePotion', 'useBurst'].includes(c.action)) issued.add(orderKey);
        } catch (_) { rejected.push({ command: c, reason: 'EXECUTION_REJECTED' }); }
      }
      return { accepted, rejected };
    }
  }
  class AgentMemory {
    constructor() { this.summary = ''; this.commands = []; this.observations = []; this.enemyBehavior = []; }
    remember(o, packet, result) {
      this.summary = packet.summary;
      this.commands.push({ at: o.gameTime, accepted: result.accepted, rejected: result.rejected }); this.commands = this.commands.slice(-8);
      this.observations.push({ at: o.gameTime, selfHp: o.self.towerHp, enemyHp: o.enemy.towerHp, coins: o.self.coins,
        lanes: Object.fromEntries(Object.entries(o.lanes).map(([k, v]) => [k, { friendlyHp: v.friendlyHp, enemyHp: v.enemyHp }])) }); this.observations = this.observations.slice(-6);
      this.enemyBehavior = o.recentEvents.filter(e => e.side === 'enemy').slice(-8);
    }
    context() { return { publicStrategy: this.summary, recentCommands: this.commands, recentObservations: this.observations, recentEnemyBehavior: this.enemyBehavior }; }
  }
  E.ObservationBuilder = ObservationBuilder; E.CommandValidator = CommandValidator; E.AgentMemory = AgentMemory;
})();
