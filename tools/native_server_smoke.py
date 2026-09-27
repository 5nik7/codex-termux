#!/usr/bin/env python3
"""Opt-in native transport smoke; existing npm runtime, empty account, no models.

Usage: python3 -B tools/native_server_smoke.py --runtime /absolute/runtime/root
Never installs, changes a runtime, or reads live auth/config. Not part of verify.py.
"""
import argparse
import base64
import json
import os
from pathlib import Path
import re
import signal
import shutil
import socket
import struct
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--runtime', type=Path, required=True)
args = parser.parse_args()
runtime = args.runtime.resolve(strict=True)
version = json.loads((runtime / 'node_modules/@openai/codex/package.json').read_text())['version']
assert re.fullmatch(r'\d+\.\d+\.\d+', version)
prefix = Path(os.environ['PREFIX'])
assert (prefix / 'bin/node').exists()


def initialize(port, token):
    """A bounded RFC6455 client using only Python's standard library."""
    with socket.create_connection(('127.0.0.1', port), timeout=4) as sock:
        key = base64.b64encode(os.urandom(16)).decode()
        sock.sendall(('GET / HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: Upgrade\r\n'
                      'Upgrade: websocket\r\nSec-WebSocket-Version: 13\r\n'
                      f'Sec-WebSocket-Key: {key}\r\nAuthorization: Bearer {token}\r\n\r\n').encode())
        headers = b''
        while not headers.endswith(b'\r\n\r\n'):
            part = sock.recv(1)
            assert part and len(headers) < 8192
            headers += part
        assert headers.startswith(b'HTTP/1.1 101')
        request = json.dumps({'id': 1, 'method': 'initialize', 'params': {
            'clientInfo': {'name': 'codex_termux_smoke', 'version': (ROOT / 'VERSION').read_text().strip()},
            'capabilities': {'experimentalApi': True}}}).encode()
        mask = os.urandom(4)
        head = bytes([0x81, 0x80 | 126]) + struct.pack('!H', len(request))
        sock.sendall(head + mask + bytes(c ^ mask[i % 4] for i, c in enumerate(request)))

        def take(n):
            result = b''
            while len(result) < n:
                chunk = sock.recv(n - len(result)); assert chunk
                result += chunk
            return result

        head = take(2); assert head[0] == 0x81 and not head[1] & 0x80
        length = head[1] & 127
        if length == 126: length = struct.unpack('!H', take(2))[0]
        assert length < 65536
        reply = json.loads(take(length))
        assert reply['id'] == 1 and 'result' in reply and 'error' not in reply
        # No prompt/thread/model RPC is sent. Closing this socket is intentional.


root = Path(tempfile.mkdtemp(prefix='codex-termux-native-smoke-'))
for name in ('home', 'codex', 'data', 'cache', 'tmp'):
    (root / name).mkdir(mode=0o700)
ident = 'v' + version + '-0000000000000000'
(root / 'data/runtimes').mkdir(mode=0o700)
# Read-only use of an installed, paired runtime; selection is test-owned.
(root / 'data/runtimes' / ident).symlink_to(runtime, target_is_directory=True)
(root / 'data/selection').write_text(f'1\n{ident}\n-\n')
env = {'PATH': str(prefix / 'bin'), 'PREFIX': str(prefix), 'TERMUX_VERSION': 'native-smoke',
       'HOME': str(root / 'home'), 'CODEX_HOME': str(root / 'codex'), 'TMPDIR': str(root / 'tmp'),
       'CODEX_TERMUX_DATA_DIR': str(root / 'data'), 'CODEX_TERMUX_CACHE_DIR': str(root / 'cache'),
       'CODEX_TERMUX_AUTO_UPDATE': 'off', 'OPENAI_API_KEY': 'fake-native-smoke-never-real', 'TERM': 'xterm-256color'}
command = [str(prefix / 'bin/bash'), str(ROOT / 'bin/codex-termux'), '--wrapper-no-config']

def run(*argv):
    proc = subprocess.run([*command, *argv], env=env, cwd=root, text=True, capture_output=True, timeout=30)
    assert proc.returncode == 0, proc.stderr
    return proc.stdout

shell = None
try:
    marker = root / 'started'
    shell = subprocess.Popen([str(prefix / 'bin/bash'), '-c',
        '"$1" "$2" --wrapper-no-config manage server start --auth inherited && touch "$3"; sleep 30',
        'smoke', command[0], command[1], str(marker)], env=env, cwd=root,
        start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    until = time.monotonic() + 25
    while not marker.exists() and time.monotonic() < until: time.sleep(.1)
    assert marker.exists(), 'native detached start did not become ready'
    file = next((root / 'data').glob('servers/*/active/state.json'))
    state = json.loads(file.read_text())
    token = (file.parent / 'ws.token').read_text().strip()
    os.killpg(shell.pid, signal.SIGHUP); shell.wait(timeout=3)
    assert 'authenticated WebSocket verified' in run('manage', 'server', 'status')
    initialize(state['port'], token)
    assert 'authenticated WebSocket verified' in run('manage', 'server', 'status')
    with socket.create_connection(('127.0.0.1', state['proxyPort']), timeout=3) as sock:
        sock.sendall(b'CONNECT forbidden.invalid:443 HTTP/1.1\r\nHost: forbidden.invalid\r\n\r\n')
        assert b'403 Forbidden' in sock.recv(1024)
    assert 'Usage:' in run('connect', '--help')
    run('manage', 'server', 'stop')
    for port in (state['port'], state['proxyPort'], state['controlPort']):
        try:
            sock = socket.create_connection(('127.0.0.1', port), timeout=.3)
        except OSError:
            continue
        sock.close(); raise AssertionError('owned port survived stop')
    print(f'PASS: native Codex {version}: detached shell HUP, authenticated initialize, client socket exit, proxy survival, client argument parsing, safe stop.')
    print('No live account, model response, tool execution, or interactive resume was tested.')
finally:
    if shell and shell.poll() is None:
        os.killpg(shell.pid, signal.SIGKILL); shell.wait()
    try:
        run('manage', 'server', 'stop')
    except Exception:
        print('Owned native smoke state retained:', root)
        raise
    shutil.rmtree(root)
