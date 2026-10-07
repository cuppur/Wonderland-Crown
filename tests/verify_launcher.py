"""Real isolated Git regression for updating launcher fallback worktrees safely."""
import importlib.util,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('launch_game',ROOT/'tools/launch_game.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
with tempfile.TemporaryDirectory(prefix='qjwg-launcher-test-') as tmp:
 root=Path(tmp).resolve();root.relative_to(Path(tempfile.gettempdir()).resolve())
 module.ROOT=root
 def git(*a,cwd=None):return subprocess.run(['git','-C',str(cwd or root),'-c','user.name=Test','-c','user.email=test@example.invalid',*a],check=True,text=True,capture_output=True,encoding='utf-8').stdout.strip()
 git('init','-b','UI');(root/'index.html').write_text('one',encoding='utf-8');git('add','index.html');git('commit','-m','one');git('branch','EVA')
 dest=module.checkout('eva');assert git('rev-parse','HEAD',cwd=dest)==git('rev-parse','EVA');print('[PASS] missing target worktree creates a detached checkout at the requested commit')
 (root/'index.html').write_text('two',encoding='utf-8');git('add','index.html');git('commit','-m','two');git('update-ref','refs/heads/EVA',git('rev-parse','HEAD'))
 assert module.checkout('eva')==dest and (dest/'index.html').read_text()=='two';assert git('rev-parse','HEAD',cwd=dest)==git('rev-parse','EVA');print('[PASS] clean cached checkout follows an updated branch')
 (dest/'index.html').write_text('personal edit',encoding='utf-8');(dest/'notes.txt').write_text('keep',encoding='utf-8')
 (root/'index.html').write_text('three',encoding='utf-8');git('add','index.html');git('commit','-m','three');git('update-ref','refs/heads/EVA',git('rev-parse','HEAD'))
 try:module.checkout('eva')
 except RuntimeError as e:assert '未提交改动' in str(e)
 else:raise AssertionError('dirty cache must not be replaced')
 assert (dest/'index.html').read_text()=='personal edit' and (dest/'notes.txt').read_text()=='keep';print('[PASS] local tracked and untracked changes are preserved with a clear error')
