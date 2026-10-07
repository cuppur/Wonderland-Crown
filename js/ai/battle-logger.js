(() => {
  'use strict';
  const E = window.EVA;
  class BattleLogger {
    constructor() { this.entries = []; this.stats = {}; for (const side of ['player', 'enemy']) this.stats[side] = { requests: 0, apiRequests: 0, decisions: 0, errors: 0, cancelled: 0, inputTokens: 0, outputTokens: 0, reasoningTokens: 0, reasoningReported: false, usageKnown: true, latencyTotal: 0, latencyCount: 0, latencyMax: 0, accepted: 0, rejected: 0, deployed: 0, potions: 0, bursts: 0 }; }
    record(entry) {
      this.entries.push(entry); if (this.entries.length > 1000) this.entries.shift();
      const s = this.stats[entry.side]; if (!s) return;
      s.requests++; s.apiRequests = (s.apiRequests || 0) + (entry.provider === 'mock' ? 0 : 1);
      s.latencyTotal += entry.latency; s.latencyCount++; s.latencyMax = Math.max(s.latencyMax, entry.latency);
      if (entry.error?.startsWith('CANCELLED')) s.cancelled++;
      else if (entry.error) s.errors++; else s.decisions++;
      for (const key of ['inputTokens', 'outputTokens', 'reasoningTokens']) { if (entry[key] == null && key !== 'reasoningTokens') s.usageKnown = false; if (key === 'reasoningTokens' && entry[key] != null) s.reasoningReported = true; s[key] += entry[key] || 0; }
      s.accepted += entry.commandsAccepted.length; s.rejected += entry.commandsRejected.length;
      for (const c of entry.commandsAccepted) { if (c.action === 'deploy') s.deployed++; if (c.action === 'usePotion') s.potions++; if (c.action === 'useBurst') s.bursts++; }
    }
    summary() { return Object.fromEntries(Object.entries(this.stats).map(([side, s]) => [side, { ...s, latencyAverage: s.latencyCount ? s.latencyTotal / s.latencyCount : 0, estimatedCost: null }])); }
    export() { return { schemaVersion: 1, entries: this.entries, stats: this.summary(), retainedEntries: this.entries.length, maxRetainedEntries: 1000 }; }
  }
  E.BattleLogger = BattleLogger;
})();
