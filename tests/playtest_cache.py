"""Verify background reuse and cropped castles without clipping or road changes."""
import json,threading
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/playwright/cache';OUT.mkdir(parents=True,exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*a):pass
 def copyfile(self,s,o):
  try:super().copyfile(s,o)
  except (BrokenPipeError,ConnectionAbortedError,ConnectionResetError):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(ROOT)));threading.Thread(target=server.serve_forever,daemon=True).start()
html=(ROOT/'index.html').read_text(encoding='utf-8').replace('const game=new Game();','const game=new Game();window.__cache={game,resize};')
results=[];errors=[]
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True)
  for width,height,dpr in [(1920,1080,2),(844,390,3),(1024,768,2)]:
   page=browser.new_page(viewport={'width':width,'height':height},device_scale_factor=dpr);page.on('pageerror',lambda e:errors.append(str(e)));page.add_init_script('window.requestAnimationFrame=()=>1;');page.route('**/index.html?test=1',lambda r:r.fulfill(status=200,content_type='text/html',body=html));page.goto(f'http://127.0.0.1:{server.server_port}/index.html?test=1')
   for mode in ['cross','straight']:
    result=page.evaluate("""mode=>{const g=__cache.game;g.mode=mode;g.start();g.render();const bg=g.staticBg,oldWalls=[g.wallCache.player.canvas,g.wallCache.enemy.canvas];let calls=0;const original=CandyField.background;CandyField.background=(...a)=>{calls++;return original(...a)};const t=performance.now();for(let i=0;i<3;i++){g.start();g.render();}const ms=performance.now()-t;CandyField.background=original;const reused=bg===g.staticBg&&oldWalls[0]===g.wallCache.player.canvas&&oldWalls[1]===g.wallCache.enemy.canvas;const main=gameCanvas.width*gameCanvas.height,dpr=gameCanvas.width/g.field.w;const rgbaMiB=4*(main+g.staticBg.width*g.staticBg.height+g.wallCache.player.canvas.width*g.wallCache.player.canvas.height+g.wallCache.enemy.canvas.width*g.wallCache.enemy.canvas.height)/1048576;
    // Compare alpha extents of a direct full-surface drawing with the cropped one.
    const checks=[];for(const side of ['player','enemy'])for(const hp of [1,.7,.1]){const f=g.field,b=CandyField.wallBounds(f,side,dpr),full=document.createElement('canvas'),crop=document.createElement('canvas');full.width=gameCanvas.width;full.height=gameCanvas.height;crop.width=b.width;crop.height=b.height;const a=full.getContext('2d'),c=crop.getContext('2d');a.setTransform(dpr,0,0,dpr,0,0);c.setTransform(dpr,0,0,dpr,-b.x*dpr,-b.y*dpr);CandyField.drawWall(a,f,side,{hp});CandyField.drawWall(c,f,side,{hp});const data=a.getImageData(0,0,full.width,full.height).data,small=c.getImageData(0,0,crop.width,crop.height).data;let clipped=0,changed=0,maxDelta=0,largeDelta=0;const ox=Math.round(b.x*dpr),oy=Math.round(b.y*dpr);for(let y=0;y<full.height;y++)for(let x=0;x<full.width;x++){const i=(y*full.width+x)*4,inside=x>=ox&&x<ox+crop.width&&y>=oy&&y<oy+crop.height;if(!inside){if(data[i+3])clipped++;}else{const j=((y-oy)*crop.width+x-ox)*4;let delta=0;for(let k=0;k<4;k++)delta=Math.max(delta,Math.abs(data[i+k]-small[j+k]));if(delta){changed++;maxDelta=Math.max(maxDelta,delta);if(delta>8)largeDelta++;}}}checks.push({side,hp,clipped,changed,maxDelta,largeDelta});CandyField.releaseCanvas(full);CandyField.releaseCanvas(crop);}return {mode,reused,calls,restart3Ms:ms,rgbaMiB,checks}}""",mode)
    assert result['reused'] and result['calls']==0,result
    assert all(c['clipped']==0 for c in result['checks']),result
    # Canvas rasterizers may round antialiasing at a translated origin differently.
    assert all(c['largeDelta']<100 for c in result['checks']),result
    if width==1920:assert result['rgbaMiB']<85,result
    result.update(width=width,height=height);results.append(result)
    page.screenshot(path=str(OUT/f'{width}x{height}-{mode}.png'));print(f"[PASS] {width}x{height}/{mode}: same-size cache reused, castles complete, RGBA {result['rgbaMiB']:.1f} MiB",flush=True)
   page.close()
  browser.close()
 assert not errors,errors
finally:
 (OUT/'report.json').write_text(json.dumps({'cases':results,'errors':errors},ensure_ascii=False,indent=2),encoding='utf-8');server.shutdown();server.server_close()
