/* Ordinary-mode commander. Reads public battle state; buys only legal cards/skills. */
(() => {
'use strict';
const TYPES=['snake','lion','elephant','dragon'],clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
class OrdinaryCommander {
 constructor(side,rules){this.side=side;this.rules=rules;this.nextThink=0;this.lastDeploy=-Infinity;this.wave=null;this.phase='opening';}
 progress(u){return this.side==='player'?u.t:1-u.t;}
 stats(type,buffed=false){
  const d=this.rules.units[type],b=buffed?this.rules.buffs[type]:{};
  return{type,hp:d.hp*(b.hp||1),attack:d.attack*(b.attack||1),interval:d.interval/(b.attackSpeed||1),speed:d.speed*(b.speed||1),range:d.range*(buffed?this.rules.potion.scale:1),regen:d.regen*(b.regen||1),buffed,buff:b};
 }
 dps(u,horizon=5){
  let d=u.attack/u.interval;
  if(u.type==='snake')d+=2*(u.buff?.poisonDamage||1)/u.interval*Math.min(horizon,10*(u.buff?.poisonDuration||1))*.5;
  if(u.type==='dragon')d+=20*(u.buff?.burnDamage||1);
  if(u.type==='elephant')d+=u.attack*(3*(u.buff?.heavyDamage||1)-1)/3;
  return d;
 }
 power(u){
  const dot=(u.poisons||[]).reduce((n,p)=>n+p.dps*Math.min(3,p.t),0)+(u.burnDps||0)*Math.min(3,u.burn||0);
  return Math.max(0,u.hp-dot+u.regen*2)/700*Math.sqrt(Math.max(.2,this.dps(u)/40));
 }
 lanes(game){
  const foe=this.side==='enemy'?'player':'enemy',alive=game.units.filter(u=>!u.dead),friends=alive.filter(u=>u.side===this.side),enemies=alive.filter(u=>u.side===foe);
  return [0,1,2].map(lane=>{
   const theirs=enemies.filter(u=>u.lane===lane).sort((a,b)=>this.progress(a)-this.progress(b)),ours=friends.filter(u=>u.lane===lane),front=theirs[0];
   const p=front?1-this.progress(front):0,frontGroup=front?theirs.filter(u=>Math.abs(this.progress(u)-this.progress(front))<.18):[];
   // Nearby units can help at the crossing even if their route identifiers differ.
   const support=front?friends.filter(u=>u.lane===lane||Math.hypot(u.x-front.x,u.y-front.y)<game.field.rw*1.6):ours;
   const enemyPower=frontGroup.reduce((n,u)=>n+this.power(u),0),friendlyPower=support.reduce((n,u)=>n+this.power(u)*(front?clamp(1-Math.abs(this.progress(u)-this.progress(front))*2,.1,1):1),0);
   const gateSupport=p>.76?.65:0,deficit=Math.max(0,enemyPower-friendlyPower*.9-gateSupport);
   const eta=front?Math.max(0,((1-p)*1070-front.range)/front.speed):Infinity;
   const danger=deficit*(.4+3.5*p*p*p),attack=ours.reduce((n,u)=>n+this.power(u)*(.35+this.progress(u)),0)-theirs.reduce((n,u)=>n+this.power(u)*.65,0);
   return{lane,ours,theirs,front,frontGroup,p,eta,danger,deficit,friendlyPower,attack};
  });
 }
 matchup(type,buffed,lane){
  const u=this.stats(type,buffed),enemies=lane.frontGroup;
  if(!enemies.length)return this.power(u)+(type==='lion'?.3:0)+(type==='snake'?.1:0);
  const front=enemies[0],aoe=type==='dragon'||type==='elephant';
  const packed=enemies.filter(v=>Math.abs(this.progress(v)-this.progress(front))*1070<=u.range*1.15).length;
  const outgoing=this.dps(u)*Math.max(1,aoe?packed:1);
  const incoming=enemies.reduce((n,v)=>n+this.dps(v,4),0);
  const hp=enemies.reduce((n,v)=>n+v.hp,0),regen=enemies.reduce((n,v)=>n+v.regen,0);
  const killTime=hp/Math.max(5,outgoing-regen),survive=u.hp/Math.max(5,incoming-u.regen);
  const reachAdvantage=(u.range-front.range)/Math.max(20,front.speed);
  const meet=Math.max(0,(this.progress(front)-.04)*1070/(u.speed+front.speed));
  const latePenalty=meet>lane.eta+1?(meet-lane.eta)*.6:0;
  return clamp((survive+reachAdvantage)/Math.max(1,killTime),0,5)+this.power(u)*.24+(aoe&&packed>1?.35:0)-latePenalty;
 }
 choose(game,lane,{buff=false,rush=false,tank=false}={}){
  const cool=game.cool[this.side],armed=game.potionArmed[this.side];let best=null;
  for(const type of TYPES){
   if(cool[type]>0||(armed&&armed!==type))continue;
   const enhanced=armed===type||buff,cost=this.rules.units[type].cost+(buff&&!armed?this.rules.potion.cost:0);
   if(game.coins[this.side]+1e-9<cost)continue;
   let score=this.matchup(type,enhanced,lane);
   if(rush)score+=this.stats(type,enhanced).speed/40;
   if(tank)score+=this.stats(type,enhanced).hp/900;
   if(lane.ours.some(u=>u.type==='elephant'&&this.progress(u)<.7)&&type==='dragon')score+=.7;
   if(lane.ours.some(u=>u.type==='dragon'&&this.progress(u)<.7)&&type==='elephant')score+=.5;
   if(lane.ours.some(u=>u.type===type&&this.progress(u)<.5))score-=.35;
   if(!best||score>best.score)best={type,buff:buff&&!armed,score,cost};
  }
  return best;
 }
 burst(game,lanes){
  if(game.tacticCool[this.side].burst>0||game.battleEvents.some(e=>e.side===this.side))return null;
  const foe=this.side==='enemy'?'player':'enemy',enemies=game.units.filter(u=>!u.dead&&u.side===foe),dir=foe==='player'?1:-1,radius=72*game.laneScale(1);
  let best=null;
  for(const info of lanes){
   let damage=0,kills=0;
   for(const u of enemies){
    let hits=0;
    const engaged=game.units.some(v=>!v.dead&&v.side===this.side&&Math.hypot(v.x-u.x,v.y-u.y)<u.range*game.laneScale(u.lane)+v.size*.35*game.unitScale());
    for(let i=0;i<this.rules.burst.shots;i++){
     const q=i/(this.rules.burst.shots-1),t=this.side==='player'?q*.5:1-q*.5,blast=game.paths[info.lane].at(t);
     const predicted=game.paths[u.lane].at(clamp(u.t+(engaged?0:dir*u.speed/1070*(this.rules.fxTiming.burstLead+i*this.rules.fxTiming.burstStep)),.012,.988));
     if(Math.hypot(predicted.x-blast.x,predicted.y-blast.y)<radius)hits++;
    }
    if(hits){const amount=Math.min(u.hp,hits*this.rules.burst.damage);damage+=amount*(.55+1-this.progress(u));if(amount>=u.hp)kills+=this.power(u);}
   }
   const value=damage/700+kills*.65;
   if(!best||value>best.value)best={lane:info.lane,value,damage,kills};
  }
  return best;
 }
 deploy(game,lane,pick){
  if(!pick||game.elapsed<3||game.elapsed-this.lastDeploy<2)return false;
  if(pick.buff&&!game.armPotion(this.side,pick.type))return false;
  if(!game.deploy(this.side,pick.type,lane))return false;
  this.lastDeploy=game.elapsed;return true;
 }
 update(game){
  if(game.state!=='playing'||game.elapsed+1e-9<this.nextThink)return;
  const lanes=this.lanes(game),danger=[...lanes].sort((a,b)=>b.danger-a.danger)[0],urgent=danger.p>.68&&danger.danger>.65||danger.p>.86&&danger.deficit>.1,pressure=danger.p>.35&&danger.deficit>.45;
  this.nextThink=game.elapsed+(urgent?.18:.4);
  const coins=game.coins[this.side],skills=game.tacticCool[this.side],foe=this.side==='enemy'?'player':'enemy',losing=game.towers[this.side].hp<game.towers[foe].hp;
  const finisher=game.towers[foe].hp<1400||Number.isFinite(game.timeLeft)&&game.timeLeft<25&&losing;
  const burst=this.burst(game,lanes);
  // Rescue skills take precedence over upgrades, and use actual blast coverage.
  if(burst&&coins>=this.rules.burst.cost&&burst.value>(urgent?1.7:3.6)){
   if(game.useBurst(this.side,burst.lane)){this.phase='burst';this.wave=null;return;}
  }
  if(game.elapsed<3||game.elapsed-this.lastDeploy<2)return;
  const canBuff=!game.potionArmed[this.side]&&skills.potion<=0&&coins>=this.rules.potion.cost+10;
  if(urgent||pressure){
   this.wave=null;
   // Saving for a clearing burst is safe only if it arrives before the threat.
   if(burst&&burst.value>3.6&&coins<20&&20-coins+2<danger.eta){this.phase='save-burst';return;}
   if(!game.potionArmed[this.side]&&coins<15&&skills.potion<=Math.max(0,15-coins)&&15-coins+2<danger.eta){this.phase='save-reinforcement';return;}
   const plain=this.choose(game,danger),enhanced=canBuff?this.choose(game,danger,{buff:true}):null;
   const pick=enhanced&&(!plain||enhanced.score>plain.score*1.18)?enhanced:plain;
   this.phase='defend';this.deploy(game,danger.lane,pick);return;
  }
  if(this.wave){
   if(game.elapsed>this.wave.expires){this.wave=null;}
   else{
    const lane=lanes[this.wave.lane],available=this.wave.follow.filter(k=>game.cool[this.side][k]<=0);
    const type=available[0];
    if(type&&coins>=10){this.phase='wave-support';if(this.deploy(game,lane.lane,{type,buff:false})){this.wave=null;}return;}
    this.phase='save-support';return;
   }
  }
  const ranked=lanes.map(l=>({info:l,score:l.attack-l.danger*.8-l.theirs.reduce((n,u)=>n+this.power(u)*.35,0)+(l.lane===1?.08:0)+Math.random()*.06})).sort((a,b)=>b.score-a.score);
  const lane=ranked[0].info;
  if(this.lastDeploy===-Infinity||finisher){
   const pick=this.choose(game,lane,{buff:canBuff,rush:finisher});this.phase=finisher?'finish':'opening';this.deploy(game,lane.lane,pick);return;
  }
  // Pool enough for a frontliner and a different supporting card. Upgrades
  // never consume the ten coins reserved for the follow-up deployment.
  const goal=skills.potion<=Math.max(0,25-coins)&&!game.potionArmed[this.side]?25:20;
  if(coins<goal){this.phase='save-wave';return;}
  const enhanced=canBuff&&coins>=25,front=this.choose(game,lane,{buff:enhanced,tank:true});
  this.phase='wave-front';
  if(this.deploy(game,lane.lane,front)){
   this.wave={lane:lane.lane,expires:game.elapsed+12,follow:front.type==='dragon'?['elephant','lion','snake']:['dragon','snake','lion','elephant'].filter(k=>k!==front.type)};
  }
 }
}
window.OrdinaryCommander=OrdinaryCommander;
})();
