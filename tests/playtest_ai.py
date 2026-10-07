"""Ordinary commander scenarios and seeded matches against the previous AI.
Only local public battle state and existing game actions are used.
"""
import json,threading
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/playwright/ai';OUT.mkdir(parents=True,exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*a):pass
 def copyfile(self,s,o):
  try:super().copyfile(s,o)
  except (BrokenPipeError,ConnectionAbortedError,ConnectionResetError):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(ROOT)));threading.Thread(target=server.serve_forever,daemon=True).start()
html=(ROOT/'index.html').read_text(encoding='utf-8').replace('const game=new Game();','const game=new Game();window.__ai={game,audio,rules:{units:UNIT_DATA,buffs:BUFFS,potion:POTION,burst:BURST,fxTiming:FX_TIMING}};')
checks=[];errors=[];report={}
def passed(label):checks.append(label);print('[PASS] '+label,flush=True)
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1920,'height':1080});page.on('pageerror',lambda e:errors.append(str(e)));page.add_init_script('window.requestAnimationFrame=()=>1;');page.route('**/index.html?test=1',lambda r:r.fulfill(status=200,content_type='text/html',body=html));page.goto(f'http://127.0.0.1:{server.server_port}/index.html?test=1')
  page.add_script_tag(path=str(ROOT/'tests/fixtures/legacy-ai.js'))
  page.evaluate("()=>{for(const k of ['start','stopGame','sfx','playBurst','playCannon','finishGame'])__ai.audio[k]=()=>{};}")
  cases=page.evaluate("""()=>{const g=__ai.game,R=__ai.rules,results={};const setup=(coins,last=3)=>{g.start();g.elapsed=10;g.coins.enemy=coins;g.aiCommander=new OrdinaryCommander('enemy',R);g.aiCommander.lastDeploy=last;return g.aiCommander};
   let c=setup(10);c.update(g);results.saving={phase:c.phase,coins:g.coins.enemy,spawns:g.spawnHistory.length,armed:g.potionArmed.enemy};
   g.coins.enemy=25;g.elapsed=25;c.update(g);const first=g.spawnHistory[0];g.elapsed=27.1;g.coins.enemy+=2.1;c.update(g);results.wave={phase:c.phase,spawns:g.spawnHistory.map(u=>({type:u.type,lane:u.lane,at:u.at})),coins:g.coins.enemy,buffed:g.units[0]?.buffed};
   c=setup(20);g.units=[.8,.84,.88].map(t=>g.createUnit('player','lion',1,t));c.update(g);results.rescue={phase:c.phase,burst:g.burstUses,armed:g.potionArmed.enemy,coins:g.coins.enemy};
   c=setup(10);g.tacticCool.enemy.burst=20;g.units=[g.createUnit('player','lion',2,.94)];c.update(g);results.defendLowGold={phase:c.phase,armed:g.potionArmed.enemy,spawns:g.spawnHistory.map(u=>({type:u.type,lane:u.lane})),coins:g.coins.enemy};
   c=setup(15);g.tacticCool.enemy.burst=20;g.units=[g.createUnit('player','lion',0,.83),g.createUnit('player','lion',2,.94),...Array.from({length:3},()=>g.createUnit('enemy','lion',0,.82))];c.update(g);results.balance={phase:c.phase,spawns:g.spawnHistory.map(u=>({type:u.type,lane:u.lane}))};
   c=setup(15,-Infinity);g.elapsed=120;g.towers.player.hp=1000;c.update(g);results.finish={phase:c.phase,type:g.spawnHistory[0]?.type,buffed:g.units[0]?.buffed};
   c=setup(100,-Infinity);g.elapsed=2.99;c.update(g);results.early=g.spawnHistory.length;g.elapsed=3.1;c.nextThink=0;c.update(g);g.elapsed=4.99;c.nextThink=0;c.update(g);results.spacing=g.spawnHistory.map(u=>u.at);
   return results}""")
  report['scenarios']=cases
  assert cases['saving']=={'phase':'save-wave','coins':10,'spawns':0,'armed':None},cases
  passed('安全局面主动攒币，不用药水花掉唯一出兵预算')
  assert len(cases['wave']['spawns'])==2 and cases['wave']['spawns'][0]['type']!=cases['wave']['spawns'][1]['type'] and cases['wave']['spawns'][0]['lane']==cases['wave']['spawns'][1]['lane'] and cases['wave']['buffed'] and cases['wave']['coins']>=0,cases
  passed('25 金币组织强化前排与不同支援卡，间隔至少两秒且预算不超支')
  assert cases['rescue']['burst']==1 and cases['rescue']['armed'] is None and cases['rescue']['coins']==0,cases
  passed('高收益救急炮阵优先于药水')
  assert len(cases['defendLowGold']['spawns'])==1 and cases['defendLowGold']['armed'] is None and cases['defendLowGold']['spawns'][0]['lane']==2,cases
  passed('10 金币紧急防守直接出兵，不先买药水')
  assert cases['balance']['spawns'][0]['lane']==2,cases
  passed('考虑己方现有兵力，优先补防没有保护的路线')
  assert cases['finish']['type']=='snake' and cases['finish']['buffed'],cases
  passed('低血量城门使用强化快速单位抢终结')
  assert cases['early']==0 and len(cases['spacing'])==1 and cases['spacing'][0]>=3,cases
  passed('严格保持三秒前禁出兵和相邻部署至少两秒')
  matches=page.evaluate("""async()=>{const g=__ai.game,R=__ai.rules,random=Math.random,out=[],realUpdate=g.updateAI,realHUD=g.updateHUD,realEnd=g.end;g.updateHUD=()=>{};g.end=function(){this.state='ended'};
   try{for(const mode of ['cross','straight'])for(const newSide of ['enemy','player'])for(const seed of [7,29,101,503,11,47,137,997,3,19,61,211,401,809,1601,2027]){
    let rng=seed;Math.random=()=>{rng=(Math.imul(rng,1664525)+1013904223)|0;return (rng>>>0)/4294967296};g.mode=mode;g.duration=300;g.start();const commander=new OrdinaryCommander(newSide,R),oldSide=newSide==='enemy'?'player':'enemy',flip=oldSide==='player';
    const legacy={aiClock:1.2,aiLastDeployAt:-Infinity,get units(){return g.units.map(u=>({...u,side:flip?(u.side==='player'?'enemy':'player'):u.side,t:flip?1-u.t:u.t}))},get elapsed(){return g.elapsed},get coins(){return {enemy:g.coins[oldSide]}},get cool(){return {enemy:g.cool[oldSide]}},get tacticCool(){return {enemy:g.tacticCool[oldSide]}},get potionArmed(){return {enemy:g.potionArmed[oldSide]}},deploy(s,t,l){return g.deploy(oldSide,t,l)},armPotion(s,t){return g.armPotion(oldSide,t)},useBurst(s,l){return g.useBurst(oldSide,l)}};
    g.updateAI=dt=>{commander.update(g);LegacyOrdinaryAI.call(legacy,dt)};
    const actions=[];const methods={};for(const name of ['deploy','armPotion','useBurst']){methods[name]=g[name];g[name]=function(...args){const side=args[0],before=this.coins[side],ok=methods[name].apply(this,args);if(ok)actions.push({name,side,spent:before-this.coins[side],at:this.elapsed});return ok}}
    for(let tick=0;tick<18001&&g.state==='playing';tick++){g.update(1/60);if(tick%1800===0)await new Promise(r=>setTimeout(r,0));if(g.coins.player<-.00001||g.coins.enemy<-.00001)throw Error('negative budget')}
    for(const name of Object.keys(methods))g[name]=methods[name];
    const a=g.towers[newSide].hp,b=g.towers[oldSide].hp,history=g.spawnHistory.filter(u=>u.side===newSide);if(history.some(u=>u.at<3)||history.some((u,i)=>i&&u.at-history[i-1].at<2))throw Error('AI deployment timing violated');
    for(const side of ['player','enemy']){const spend=actions.filter(a=>a.side===side).reduce((n,a)=>n+a.spent,0);if(Math.abs(g.coins[side]-(15+g.elapsed-spend))>1e-6)throw Error('unequal economy')}
    out.push({mode,newSide,seed,result:a>b?'win':a<b?'loss':'draw',newHp:a,oldHp:b,elapsed:g.elapsed,newDeploys:history.length,oldDeploys:g.spawnHistory.length-history.length,burstUses:g.burstUses});
   }return out}finally{Math.random=random;g.updateAI=realUpdate;g.updateHUD=realHUD;g.end=realEnd}
  }""")
  report['matches']=matches;wins=sum(m['result']=='win' for m in matches);losses=sum(m['result']=='loss' for m in matches)
  print(json.dumps({'wins':wins,'losses':losses,'draws':len(matches)-wins-losses},ensure_ascii=False),flush=True)
  assert wins>losses, 'New strategy must outperform the old AI in the fixed mirrored sample'
  passed(f'双地图、双方位置、十六随机种子对照实战：新 AI {wins} 胜 / {losses} 负 / {len(matches)-wins-losses} 平')
  passed('全部对照对局金币收支一致，没有额外收入、越过冷却或抢跑部署')
  assert not errors,errors;browser.close()
finally:
 report.update(checks=checks,errors=errors);(OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');server.shutdown();server.server_close()
