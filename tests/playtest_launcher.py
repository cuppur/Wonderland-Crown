"""Exercise the real Windows cmd entry and a browser with legacy beauty cache."""
import json, os, subprocess, tempfile, threading
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs
from urllib.request import build_opener, ProxyHandler
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
COMMON=Path(subprocess.check_output(['git','rev-parse','--path-format=absolute','--git-common-dir'],cwd=ROOT,text=True).strip()).parent
OUT=ROOT/'output/playwright/launcher';OUT.mkdir(parents=True,exist_ok=True)
report={'checks':[],'errors':[]}
opener=build_opener(ProxyHandler({}))
with tempfile.TemporaryDirectory(prefix='qjwg-cmd-capture-') as tmp:
 tmp=Path(tmp);capture=tmp/'opened.json'
 (tmp/'sitecustomize.py').write_text("import os,json,webbrowser\ndef capture(url,*args,**kwargs):\n with open(os.environ['QJWG_LAUNCH_CAPTURE'],'w',encoding='utf-8') as f:json.dump(url,f)\n return True\nwebbrowser.open=capture\n",encoding='utf-8')
 env=os.environ.copy();env['PYTHONPATH']=str(tmp)+os.pathsep+env.get('PYTHONPATH','');env['QJWG_LAUNCH_CAPTURE']=str(capture)
 result=subprocess.run(['cmd','/d','/c',str(COMMON/'一键启动-普通游戏.cmd')],env=env,cwd=tmp,capture_output=True,timeout=30)
 assert result.returncode==0 and capture.is_file(),result.stdout+result.stderr
 url=json.loads(capture.read_text(encoding='utf-8'));parts=urlsplit(url);query=parse_qs(parts.query);assert query['mode']==['ui'] and len(query['launch'][0])==20
 origin=f'{parts.scheme}://{parts.netloc}'
 with opener.open(origin+'/launch/api/health') as r:info=json.load(r)
 assert info['gameMode']=='ui' and info['build']==query['launch'][0]
 branch=subprocess.check_output(['git','-C',info['root'],'branch','--show-current'],text=True).strip();assert branch=='UI',info
 with opener.open(url) as r:
  html=r.read().decode();assert 'BeautySprites' not in html
  assert 'no-store' in r.headers.get('Cache-Control','') and r.headers['X-QJWG-Mode']=='ui'
  assert './css/style.css?launch='+info['build'] in html and './js/ordinary-ai.js?launch='+info['build'] in html
 report.update(url=url,root=info['root'],branch=branch)
 report['checks'].append('真实根目录普通cmd从任意工作目录执行，打开带版本UI地址且指向UI工作区')
 # Real HTTP caching, without routing (Playwright routing disables the cache).
 legacy={'active':True}
 class Relay(SimpleHTTPRequestHandler):
  def __init__(self,*a,**kw):super().__init__(*a,directory=str(COMMON),**kw)
  def log_message(self,*a):pass
  def end_headers(self):
   if legacy['active']:self.send_header('Cache-Control','public, max-age=3600')
   super().end_headers()
  def do_GET(self):
   if legacy['active']:return super().do_GET()
   with opener.open(origin+self.path) as r:
    body=r.read();self.send_response(r.status)
    for h in ['Content-Type','Cache-Control','Pragma','X-QJWG-Mode','X-QJWG-Build']:
     if r.headers.get(h):self.send_header(h,r.headers[h])
    self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
 server=ThreadingHTTPServer(('127.0.0.1',0),Relay);threading.Thread(target=server.serve_forever,daemon=True).start()
 try:
  with sync_playwright() as p:
   browser=p.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1920,'height':1080})
   local=f'http://127.0.0.1:{server.server_port}'
   page.goto(local+'/index.html?test=1');page.wait_for_function('typeof BeautyCharacters!=="undefined"')
   legacy['active']=False
   page.goto(local+'/index.html?test=1');report['legacyCacheReproduced']=page.evaluate('typeof BeautyCharacters!=="undefined"')
   page.on('pageerror',lambda e:report['errors'].append(str(e)))
   response=page.goto(local+parts.path+'?'+parts.query+'&test=1');page.wait_for_function('!!window.__QJWG_TEST__')
   config=page.evaluate('__QJWG_TEST__.config()');assert 'BeautySprites' not in page.content()
   assert config['units']['lion']['attack']==25 and [config['units'][t]['range'] for t in ['snake','lion','elephant','dragon']]==[40,50,60,80]
   page.locator('#startBtn').click();page.wait_for_timeout(300);assert page.locator('#menuOverlay').is_hidden()
   page.screenshot(path=str(OUT/'ordinary-after-beauty-cache.png'))
   page.set_viewport_size({'width':844,'height':390});page.wait_for_timeout(200);page.screenshot(path=str(OUT/'ordinary-small-after-cache.png'))
   assert not report['errors'],report['errors'];browser.close()
   report['checks'].append('预热beauty页面和样式脚本缓存后，同浏览器从普通启动地址进入新属性动物对局')
 finally:server.shutdown();server.server_close()
report['passed']=True
(OUT/'entry-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for label in report['checks']:print('[PASS] '+label,flush=True)
print('Legacy cache reproduced:',report['legacyCacheReproduced'],flush=True)
print('Opened ordinary URL:',url,flush=True)
