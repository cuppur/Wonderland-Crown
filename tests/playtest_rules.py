"""Runtime regression for delayed damage, state guards, pause ownership and clocks.
Uses response-only instrumentation; shipping files expose no additional globals.
"""
import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/playwright/rules';OUT.mkdir(parents=True,exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
 def copyfile(self,source,output):
  try:super().copyfile(source,output)
  except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(ROOT)))
threading.Thread(target=server.serve_forever,daemon=True).start()
url=f'http://127.0.0.1:{server.server_port}/index.html?test=1'
html=(ROOT/'index.html').read_text(encoding='utf-8').replace('const game=new Game();','const game=new Game();window.__rules={game,loop,resize,togglePause,showReport,closeReport,syncEnvironmentPause,getDragging:()=>dragging};')
checks=[];errors=[];measurements={}
def passed(label):checks.append(label);print('[PASS] '+label,flush=True)
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True)
  for mobile in [False,True]:
   context=browser.new_context(viewport={'width':844 if mobile else 1920,'height':390 if mobile else 1080},has_touch=mobile,device_scale_factor=3 if mobile else 1,user_agent='Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/130.0 Mobile Safari/537.36' if mobile else None)
   page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
   page.route('**/index.html?test=1',lambda r:r.fulfill(status=200,content_type='text/html',body=html))
   page.add_init_script('window.requestAnimationFrame=fn=>1;')
   page.goto(url);page.wait_for_function('!!window.__rules')
   result=page.evaluate("""()=>{const g=__rules.game;g.start();g.coins.player=30;g.updateUnits=()=>{};g.updateCannons=()=>{};g.updateProjectiles=()=>{};g.updateAI=()=>{};const u=g.createUnit('enemy','elephant',1,.02);g.units=[u];g.useBurst('player',1);u.x=g.battleEvents[0].x;u.y=g.battleEvents[0].y;for(let i=0;i<100;i++)g.fx.push({kind:'summon',x:0,y:0,t:5,max:5,side:'player'});g.last=1000;__rules.loop(1000);const events=g.battleEvents.length,fx=g.fx.length;g.update(.5);g.update(.5);g.update(.1);return {events,fx,hp:u.hp,coins:g.coins.player,pending:g.battleEvents.length}}""")
   assert result['events']==10 and result['hp']==0 and result['coins']<12 and result['pending']==0,result
   if mobile:assert result['fx']<=90,result
   measurements['burst_mobile' if mobile else 'burst_desktop']=result
   passed(('手机' if mobile else '桌面')+'拥挤特效仍完整结算炮阵伤害')
   context.close()
  context=browser.new_context(viewport={'width':1920,'height':1080},device_scale_factor=2)
  page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
  page.route('**/index.html?test=1',lambda r:r.fulfill(status=200,content_type='text/html',body=html));page.add_init_script('window.requestAnimationFrame=fn=>1;');page.goto(url)
  page.evaluate('__rules.game.start()')
  b=page.locator('[data-type="snake"]').bounding_box();point=page.evaluate("()=>{const g=__rules.game,p=g.paths[1].at(.4);return CandyField.project(g.field,p.x,p.y)}")
  page.mouse.move(b['x']+b['width']/2,b['y']+b['height']/2);page.mouse.down();page.mouse.move(point['x'],point['y'],steps=5)
  assert page.evaluate('!!__rules.getDragging()')
  page.evaluate('__rules.game.end("test")');page.mouse.up()
  result=page.evaluate("()=>({state:__rules.game.state,coins:__rules.game.coins.player,units:__rules.game.units.length,ghost:document.querySelectorAll('.drag-ghost').length})")
  assert result=={'state':'ended','coins':15,'units':0,'ghost':0},result
  passed('结算取消拖卡且松手不扣费、不生成单位')
  result=page.evaluate("""()=>{const g=__rules.game;const out=[];for(const state of ['menu','paused','ended']){g.state=state;g.coins.player=40;out.push([g.deploy('player','snake',1),g.armPotion('player','dragon'),g.useBurst('player',1),g.coins.player])}return out}""")
  assert all(r==[False,False,False,40] for r in result),result
  passed('所有非对局状态拒绝动物、药水、炮阵并保留金币')
  result=page.evaluate("""()=>{const g=__rules.game;for(const k of ['updateUnits','updateCannons','updateProjectiles','updateFx','updateAI','updateHUD'])g[k]=()=>{};const out=[];for(const fps of [10,20,30,60,120]){g.start();for(let i=0;i<fps;i++)g.update(1/fps);out.push({fps,elapsed:g.elapsed,coins:g.coins.player,timeLeft:g.timeLeft})}return out}""")
  assert all(abs(r['elapsed']-1)<1e-8 and abs(r['coins']-16)<1e-8 and abs(r['timeLeft']-299)<1e-8 for r in result),result
  measurements['clock']=result;passed('10/20/30/60/120 FPS 的计时与金币速度一致')
  result=page.evaluate("""()=>{const g=__rules.game;g.start();g.update(2);const paused=g.state;const before=g.timeLeft;g.update(.2);__rules.togglePause();g.update(.1);return {paused,before,after:g.timeLeft,state:g.state}}""")
  assert result['paused']=='paused' and result['state']=='playing' and abs(result['before']-result['after']-.1)<1e-8,result
  passed('长时间挂起暂停，明确继续后恢复正常时间')
  result=page.evaluate("""()=>{const g=__rules.game;g.start();g.setPause('manual',true);__rules.showReport();__rules.closeReport();const manual=g.state;g.setPause('manual',false);__rules.showReport();g.setPause('portrait',true);__rules.closeReport();const portrait=g.state;g.setPause('portrait',false);return {manual,portrait,restored:g.state}}""")
  assert result=={'manual':'paused','portrait':'paused','restored':'playing'},result
  passed('报告关闭尊重手动暂停与竖屏暂停的独立原因')
  result=page.evaluate("""()=>{const g=__rules.game;g.duration=1.005;g.start();for(let i=0;i<100;i++)g.update(1/60);return {elapsed:g.elapsed,coins:g.coins.player,state:g.state}}""")
  assert result['state']=='ended' and abs(result['elapsed']-1.005)<1e-8 and abs(result['coins']-16.005)<1e-8,result
  passed('非整帧结束时间与最后一帧金币完整结算')
  result=page.evaluate("""()=>{const g=__rules.game,proto=Object.getPrototypeOf(g);g.updateUnits=proto.updateUnits;g.updateCannons=proto.updateCannons;g.updateProjectiles=proto.updateProjectiles;g.updateFx=proto.updateFx;g.duration=300;const out=[];for(const fps of [10,20,60]){g.start();const u=g.createUnit('player','snake',1,.1);u.hp=400;u.poisons=[{dps:2,t:.8}];g.units=[u];for(let i=0;i<fps;i++)g.update(1/fps);out.push({fps,t:u.t,hp:u.hp,poisons:u.poisons.length})}return out}""")
  assert all(abs(r['t']-result[0]['t'])<1e-9 and abs(r['hp']-result[0]['hp'])<1e-9 and r['poisons']==0 for r in result),result
  measurements['physics']=result;passed('低帧率的实际行军、回血、中毒结算与 60 FPS 一致')
  context.close();browser.close()
  browser=pw.webkit.launch(headless=True);context=browser.new_context(viewport={'width':844,'height':390},has_touch=True,is_mobile=True)
  page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.route('**/index.html?test=1',lambda r:r.fulfill(status=200,content_type='text/html',body=html));page.goto(url);page.evaluate('__rules.game.start()')
  page.set_viewport_size({'width':390,'height':844});page.wait_for_function('__rules.game.state==="paused"');before=page.evaluate('__rules.game.timeLeft');page.wait_for_timeout(1100);after=page.evaluate('__rules.game.timeLeft');assert before==after
  page.screenshot(path=str(OUT/'portrait-paused.png'));page.set_viewport_size({'width':844,'height':390});page.wait_for_function('__rules.game.state==="playing"')
  passed('触屏竖屏自动暂停、遮挡期间计时冻结、横屏自动恢复')
  page.evaluate('__rules.togglePause()');page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(100);page.set_viewport_size({'width':844,'height':390});page.wait_for_timeout(150);assert page.evaluate('__rules.game.state')=='paused'
  passed('手动暂停后旋转往返仍保持暂停')
  page.evaluate("()=>{const g=__rules.game;g.start();Object.defineProperty(document,'hidden',{configurable:true,value:true});document.dispatchEvent(new Event('visibilitychange'))}");assert page.evaluate('__rules.game.state')=='paused';before=page.evaluate('__rules.game.timeLeft');page.wait_for_timeout(150);assert page.evaluate('__rules.game.timeLeft')==before
  page.evaluate("()=>{Object.defineProperty(document,'hidden',{configurable:true,value:false});document.dispatchEvent(new Event('visibilitychange'))}");assert page.evaluate('__rules.game.state')=='playing';passed('隐藏页面冻结对局，返回页面恢复且不追赶后台时间')
  context.close();browser.close()
 assert not errors,errors
 print(f'ALL RULE TESTS PASSED: {len(checks)} checks',flush=True)
finally:
 (OUT/'report.json').write_text(json.dumps({'checks':checks,'errors':errors,'measurements':measurements},ensure_ascii=False,indent=2),encoding='utf-8');server.shutdown();server.server_close()
