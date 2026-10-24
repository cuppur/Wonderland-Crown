"""Exercise the October balance changes in the actual battle engine."""
import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/playwright/balance'
OUT.mkdir(parents=True, exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args): pass
server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Quiet, directory=str(ROOT)))
threading.Thread(target=server.serve_forever, daemon=True).start()
url = f'http://127.0.0.1:{server.server_port}/index.html?test=1'
html = (ROOT/'index.html').read_text(encoding='utf-8').replace('const game=new Game();', 'const game=new Game();window.__balance={game,units:UNIT_DATA,buffs:BUFFS,potion:POTION};')
report = {'checks': [], 'errors': []}
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width':1920,'height':1080})
        page.on('pageerror', lambda e: report['errors'].append(str(e)))
        page.add_init_script('window.requestAnimationFrame=()=>1;')
        page.route('**/index.html?test=1', lambda r:r.fulfill(status=200,content_type='text/html',body=html))
        page.goto(url)
        result = page.evaluate("""()=>{
          const {game:g,units,buffs,potion}=__balance;g.start();
          const towers=Object.values(g.towers).map(t=>[t.hp,t.maxHp]);
          const lion=g.createUnit('player','lion',1,.2),victim=g.createUnit('enemy','elephant',1,.8);
          g.units=[lion,victim];g.resolveUnitHit(lion,victim,lion.attack);const normalHit=1000-victim.hp;
          lion.hp=300;g.units=[lion];g.updateUnits(1);const regen=lion.hp-300;
          g.buffUnit(lion);victim.hp=1000;g.resolveUnitHit(lion,victim,lion.attack);const enhancedHit=1000-victim.hp;
          const enhanced={};for(const type of Object.keys(units)){
            const u=g.createUnit('player',type,1,.2);g.buffUnit(u);const first=u.range;
            const duplicate=g.buffUnit(u);enhanced[type]={range:u.range,first,duplicate,scale:u.visualScale,size:u.size,hp:u.maxHp,attack:u.attack,regen:u.regen};
          }
          const snake=g.createUnit('player','snake',1,.2);victim.hp=1000;victim.poisons=[];
          g.resolveUnitHit(snake,victim,snake.attack);g.buffUnit(snake);g.resolveUnitHit(snake,victim,snake.attack);
          const poisons=victim.poisons.map(p=>({dps:p.dps,duration:p.t}));
          const commander=new OrdinaryCommander('player',{units,buffs,potion});
          const aiRanges=Object.fromEntries(Object.keys(units).map(t=>[t,commander.stats(t,true).range]));
          const rangeHits=[];for(const type of Object.keys(units)){for(const buffed of [false,true]){for(const inside of [false,true]){
            g.start();const u=g.createUnit('player',type,1,.35),v=g.createUnit('enemy','elephant',1,.65);
            if(buffed)g.buffUnit(u);u.attackClock=0;v.attackClock=999;
            v.x=u.x+u.range*g.laneScale(1)+v.size*.35*g.unitScale()+(inside?-.5:.5);v.y=u.y;g.units=[u,v];
            g.updateUnits(0);rangeHits.push({type,buffed,inside,attacked:u.attackClock>0});
          }}}
          g.start();return {rangeHits,towers,normalHit,regen,enhancedHit,enhanced,poisons,aiRanges,restartHp:g.towers.player.hp,report:document.querySelector('#reportBody').textContent};
        }""")
        assert result['towers'] == [[5000,5000],[5000,5000]] and result['restartHp']==5000
        assert (result['normalHit'],result['enhancedHit'],result['regen']) == (25,50,15)
        for t, r in {'snake':40,'lion':50,'elephant':60,'dragon':80}.items():
            u=result['enhanced'][t]
            assert abs(u['range']-r*1.3)<1e-8 and abs(u['scale']-.7*1.3)<1e-8
            assert not u['duplicate'] and u['first']==u['range'] and result['aiRanges'][t]==u['range']
        assert all(r['inside']==r['attacked'] for r in result['rangeHits']), result['rangeHits']
        assert result['poisons'] == [{'dps':2,'duration':10},{'dps':4,'duration':15}]
        assert '50.0' in result['report'] and '25.0' in result['report'] and '15.60' in result['report']
        assert not report['errors'], report['errors']
        report.update(passed=True, measurements=result)
        report['checks']=['5000城墙开局与重开','狮子25/50直伤及15每秒回血','四种强化射程与体型+30%且不重复放大','强化毒15秒独立叠加','AI射程估计和数值报告同步','四单位普通与强化射程内外实际攻击边界']
        for label in report['checks']: print('[PASS] '+label, flush=True)
        browser.close()
finally:
    (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    server.shutdown();server.server_close()
