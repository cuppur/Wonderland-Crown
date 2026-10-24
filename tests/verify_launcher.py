"""Real Git regression for locating and updating the ordinary game checkout."""
import importlib.util,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('launch_game',ROOT/'tools/launch_game.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
with tempfile.TemporaryDirectory(prefix='qjwg-launcher-test-') as tmp:
 root=Path(tmp).resolve();module.ROOT=root
 def git(*a,cwd=None):return subprocess.run(['git','-C',str(cwd or root),'-c','user.name=Test','-c','user.email=test@example.invalid',*a],check=True,text=True,capture_output=True,encoding='utf-8').stdout.strip()
 git('init','-b','UI');(root/'index.html').write_text('one',encoding='utf-8');git('add','index.html');git('commit','-m','one');git('checkout','--detach')
 dest=module.checkout('ui');assert git('rev-parse','HEAD',cwd=dest)==git('rev-parse','UI');print('[PASS] missing ordinary checkout is created at the requested commit')
 (root/'index.html').write_text('two',encoding='utf-8');git('add','index.html');git('commit','-m','two');git('update-ref','refs/heads/UI',git('rev-parse','HEAD'))
 assert module.checkout('ui')==dest and (dest/'index.html').read_text()=='two';print('[PASS] clean cached checkout follows the updated main branch')
 (dest/'index.html').write_text('personal edit',encoding='utf-8');(dest/'notes.txt').write_text('keep',encoding='utf-8')
 (root/'index.html').write_text('three',encoding='utf-8');git('add','index.html');git('commit','-m','three');git('update-ref','refs/heads/UI',git('rev-parse','HEAD'))
 try:module.checkout('ui')
 except RuntimeError as e:assert '未提交改动' in str(e)
 else:raise AssertionError('dirty cache must not be replaced')
 assert (dest/'index.html').read_text()=='personal edit' and (dest/'notes.txt').read_text()=='keep';print('[PASS] tracked and untracked personal edits are preserved')
 try:module.checkout('unsupported')
 except ValueError:pass
 else:raise AssertionError('unsupported modes must be rejected')
 print('[PASS] launcher only accepts the ordinary mode')
with tempfile.TemporaryDirectory(prefix='qjwg-active-checkout-') as tmp:
 root=Path(tmp).resolve();module.ROOT=root
 git('init','-b','UI');(root/'index.html').write_text('stable',encoding='utf-8');git('add','index.html');git('commit','-m','stable')
 assert module.checkout('ui')==root
 git('checkout','--detach');active=root/'stable';git('worktree','add',str(active),'UI')
 (root/'index.html').write_text('personal edits',encoding='utf-8')
 assert module.checkout('ui')==active and (root/'index.html').read_text()=='personal edits'
 print('[PASS] actual UI checkout is selected without touching unrelated personal edits')
