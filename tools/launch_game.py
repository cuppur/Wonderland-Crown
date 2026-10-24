"""One-click Windows launcher for the ordinary game."""
from __future__ import annotations

import argparse
import hashlib
import io
import re
import json
import os
import subprocess
import sys
import time
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def checkout(mode):
    if mode != 'ui':
        raise ValueError('Unsupported game mode')
    expected = 'UI'
    branch = subprocess.run(['git', '-C', str(ROOT), 'symbolic-ref', '--quiet', '--short', 'HEAD'], capture_output=True, text=True, encoding='utf-8').stdout.strip()
    if branch == expected:
        return ROOT
    result = subprocess.run(['git', '-C', str(ROOT), 'worktree', 'list', '--porcelain'], capture_output=True, text=True, encoding='utf-8', check=True)
    for entry in result.stdout.split('\n\n'):
        lines = entry.splitlines()
        if 'branch refs/heads/' + expected in lines:
            return Path(next(line[9:] for line in lines if line.startswith('worktree ')))
    common = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', '--path-format=absolute', '--git-common-dir'], capture_output=True, text=True, encoding='utf-8', check=True).stdout.strip()
    destination = Path(common).parent / '.local-worktrees' / mode
    # Resolve every time: a detached fallback must follow the selected branch.
    ref = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', '--verify', expected], capture_output=True, text=True)
    target = expected if ref.returncode == 0 else 'origin/' + expected
    target_sha = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', '--verify', target + '^{commit}'], capture_output=True, text=True, check=True).stdout.strip()
    if not (destination / 'index.html').is_file():
        destination.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['git', '-C', str(ROOT), 'worktree', 'add', '--detach', str(destination), target_sha], check=True, capture_output=True)
    else:
        actual_root = subprocess.run(['git', '-C', str(destination), 'rev-parse', '--show-toplevel'], capture_output=True, text=True, check=True).stdout.strip()
        if Path(actual_root).resolve() != destination.resolve():
            raise RuntimeError('备用目录不是独立 Git 工作区，请保留文件并检查：' + str(destination))
        current = subprocess.run(['git', '-C', str(destination), 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
        if current != target_sha:
            dirty = subprocess.run(['git', '-C', str(destination), 'status', '--porcelain', '--untracked-files=all'], capture_output=True, text=True, check=True).stdout.strip()
            if dirty:
                raise RuntimeError('备用工作区有未提交改动，已保留，无法自动更新：' + str(destination))
            subprocess.run(['git', '-C', str(destination), 'checkout', '--detach', target_sha], check=True, capture_output=True)
    return destination


def build_id(root, mode):
    digest = hashlib.sha256((str(root.resolve()) + mode).encode())
    paths = [root / 'index.html'] + list((root / 'js').rglob('*.js')) + list((root / 'css').glob('*.css')) + list((root / 'tools').glob('*.py'))
    for path in sorted(paths):
        digest.update(path.read_bytes())
    return digest.hexdigest()[:20]


def health(port):
    try:
        with urlopen(f'http://127.0.0.1:{port}/launch/api/health', timeout=.5) as response:
            return json.load(response)
    except (OSError, ValueError):
        return None


def serve(root, mode, port):
    build = build_id(root, mode)
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            kwargs['directory'] = str(root)
            super().__init__(*args, **kwargs)

        def log_message(self, *_):
            pass

        def end_headers(self):
            # A mode can previously have occupied this port in another checkout.
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('X-QJWG-Mode', mode)
            self.send_header('X-QJWG-Build', build)
            super().end_headers()

        def send_head(self):
            if urlsplit(self.path).path in {'/', '/index.html'}:
                html = (root / 'index.html').read_text(encoding='utf-8')
                # CSS and scripts need fresh URLs too: their old cache entries
                # can survive a fresh navigation of the entry document.
                html = re.sub(r'((?:src|href)=["\'])(\./(?:js|css)/[^"\'?]+)(?:\?[^"\']*)?(["\'])',
                              lambda m:m[1]+m[2]+'?launch='+build+m[3], html)
                payload = html.encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                return io.BytesIO(payload)
            return super().send_head()

        def do_GET(self):
            if self.headers.get('Host') not in {f'127.0.0.1:{port}', f'localhost:{port}'}:
                self.send_error(421)
                return
            if self.path == '/launch/api/health':
                payload = json.dumps({'gameMode': mode, 'build': build, 'pid': os.getpid(), 'root': str(root.resolve())}).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return
            path = unquote(urlsplit(self.path).path)
            if path not in {'/', '/index.html', '/favicon.ico'} and not path.startswith(('/js/', '/css/', '/assets/')):
                self.send_error(404)
                return
            if any(p.startswith('.') or p == '..' for p in path.split('/')[1:]) or not (root / path.lstrip('/')).resolve().is_relative_to(root):
                self.send_error(404)
                return
            super().do_GET()
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.serve_forever()


def launch(mode, open_browser=True):
    root = checkout(mode)
    build = build_id(root, mode)
    first = 8765
    for port in range(first, first + 10):
        info = health(port)
        if info and info.get('gameMode') == mode and info.get('build') == build:
            break
        import socket
        try:
            with socket.socket() as probe:
                probe.bind(('127.0.0.1', port))
        except OSError:
            continue
        logdir = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'WonderlandCrown'
        logdir.mkdir(parents=True, exist_ok=True)
        with (logdir / ('server-' + mode + '.log')).open('wb') as logfile:
            process = subprocess.Popen([sys.executable, str(root / 'tools/launch_game.py'), '--mode', mode, '--serve', '--port', str(port)], cwd=root, stdout=logfile, stderr=logfile, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        for _ in range(50):
            info = health(port)
            if info and info.get('build') == build:
                break
            if process.poll() is not None:
                raise RuntimeError('Game server did not start; see the local server log')
            time.sleep(.1)
        else:
            raise RuntimeError('Game server start timed out')
        break
    else:
        raise RuntimeError('No available local game port')
    query = 'mode=' + mode + '&launch=' + build
    url = f'http://127.0.0.1:{port}/index.html?' + query
    if open_browser:
        webbrowser.open(url)
    print(url)
    return url


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['ui'], required=True)
    parser.add_argument('--serve', action='store_true')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--no-open', action='store_true')
    args = parser.parse_args()
    if args.serve:
        serve(ROOT, args.mode, args.port)
    else:
        try:
            launch(args.mode, not args.no_open)
        except Exception:
            print('Could not launch the game. Check Python/Git and %LOCALAPPDATA%/WonderlandCrown/server-*.log.', file=sys.stderr)
            sys.exit(1)
