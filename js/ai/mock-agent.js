(() => {
  'use strict';
  const E = window.EVA;
  class MockAgent {
    constructor(config) { this.config = config; this.calls = 0; }
    async decide(o, memory, signal) {
      if (signal.aborted) throw new DOMException('Aborted', 'AbortError');
      this.calls++;
      const defensive = this.config.model === 'defensive-mock', lane = defensive
        ? Object.keys(o.lanes).sort((a, b) => o.lanes[b].enemyHp - o.lanes[a].enemyHp)[0]
        : ['bottom', 'top', 'middle'][Math.floor(o.gameTime / 30) % 3];
      let coins = o.self.coins;
      const commands = [], skill = this.calls % 12;
      // Deliberately save enough coins for both skills; no privileged engine access.
      if (o.self.cooldowns.burst === 0 && coins >= o.rules.burst.cost && skill >= 6) {
        commands.push({ action: 'useBurst', lane }); coins -= o.rules.burst.cost;
      }
      const type = (defensive ? ['lion', 'elephant', 'dragon', 'snake'] : ['snake', 'lion', 'dragon', 'elephant'])
        .find(k => o.self.cooldowns[k] === 0 && coins >= o.rules.units[k].cost);
      if (type && !o.self.potionArmed && o.self.cooldowns.potion === 0 && coins >= o.rules.units[type].cost + o.rules.potion.cost && skill < 6) {
        commands.push({ action: 'usePotion', unit: type }); coins -= o.rules.potion.cost;
      }
      const savingBurst = o.self.cooldowns.burst === 0 && skill >= 6 && coins < o.rules.burst.cost;
      if (type && !savingBurst && coins >= o.rules.units[type].cost) commands.push({ action: 'deploy', unit: o.self.potionArmed || type, lane });
      commands.push({ action: 'advance', lane });
      const packet = { schemaVersion: 1, summary: defensive ? '优先守住压力最大的路线，积攒金币反击；炮阵清理近端敌军。' : '轮换进攻路线，用药水强化先锋，积攒炮阵应对敌军。', commands };
      return { text: JSON.stringify(packet), raw: { mock: true, packet }, usage: { inputTokens: 0, outputTokens: 0, reasoningTokens: 0 } };
    }
    async listModels() { return [{ id: 'aggressive-mock' }, { id: 'defensive-mock' }]; }
  }
  E.MockAgent = MockAgent;
})();
