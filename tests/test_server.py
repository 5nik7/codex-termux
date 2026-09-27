#!/usr/bin/env python3
"""Managed server integration: owned roots, native processes, fake credentials."""
import json
import http.server
import http.client
import threading
import os
from pathlib import Path
import signal
import socket
import subprocess
import time
import unittest
import test_wrapper as base

SERVER = r'''
const http = require('node:http'), crypto = require('node:crypto');
if (args[0] === 'app-server') {
  if (process.env.FIXTURE_FAIL_START) process.exit(42);
  const token = fs.readFileSync(args[args.indexOf('--ws-token-file')+1], 'utf8').trim();
  const port = Number(new URL(args[args.indexOf('--listen')+1]).port);
  const srv = http.createServer((req,res)=>{res.end('ready')});
  srv.on('upgrade', (req,sock)=>{
    sock.on('error',()=>{});
    if (!process.env.FIXTURE_NO_AUTH && req.headers.authorization !== 'Bearer '+token) {sock.end('HTTP/1.1 401 Unauthorized\r\nContent-Length: 0\r\n\r\n');return;}
    const accept=crypto.createHash('sha1').update(req.headers['sec-websocket-key']+'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest('base64');
    sock.write('HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: '+accept+'\r\n\r\n');
    sock.on('data',()=>{}); sock.on('end',()=>sock.destroy());
  });
  srv.listen(port,'127.0.0.1');
  process.on('SIGTERM',()=>{if (process.env.FIXTURE_IGNORE_TERM_FILE && fs.existsSync(process.env.FIXTURE_IGNORE_TERM_FILE)) return; process.exit(0);});
  return;
}
'''


class ServerTests(unittest.TestCase):
    setUp = base.WrapperTests.setUp
    def run_wrapper(self, *args, env=None, input=None):
        return subprocess.run([base.BASH, str(base.WRAPPER), *args], env=env or self.env,
                              input=input, text=True, capture_output=True, timeout=25, cwd=self.root)
    assert_ok = base.WrapperTests.assert_ok
    run_tty = base.WrapperTests.run_tty

    def setUp(self):
        base.WrapperTests.setUp(self)
        (self.home / '.codex').mkdir()
        fake = base.FAKE.replace("if (process.env.FIXTURE_READY)", SERVER + "\nif (process.env.FIXTURE_READY)")
        self.fake.write_text(fake.replace('#!/usr/bin/env node', '#!' + base.NODE, 1))
        self.data = self.root / 'private data 雪'
        self.env['CODEX_TERMUX_DATA_DIR'] = str(self.data)
        self.env['CODEX_HOME'] = str(self.home / '.codex')

    def tearDown(self):
        self.run_wrapper('manage', 'server', 'stop')
        if list(self.data.glob('servers/*/active')):
            self.tmp._finalizer.detach()
            self.fail('Owned test state retained for review: ' + str(self.root))
        base.WrapperTests.tearDown(self)

    def start(self, mode='inherited', env=None, extra=()):
        result = self.run_wrapper('manage', 'server', 'start', '--auth', mode, *extra, env=env)
        self.assert_ok(result)
        return result

    def state_path(self):
        return next(self.data.glob('servers/*/active/state.json'))

    def state(self):
        return json.loads(self.state_path().read_text())

    def assert_proxy(self, port):
        with socket.create_connection(('127.0.0.1', port), timeout=2) as sock:
            sock.sendall(b'CONNECT forbidden.invalid:443 HTTP/1.1\r\nHost: forbidden.invalid\r\n\r\n')
            self.assertIn(b'403 Forbidden', sock.recv(1024))

    def test_start_authentication_client_exit_and_stop(self):
        started = self.start()
        state = self.state()
        active = self.state_path().parent
        self.assertEqual(active.stat().st_mode & 0o777, 0o700)
        for file in active.iterdir():
            self.assertEqual(file.stat().st_mode & 0o777, 0o600)
        token = (active / 'ws.token').read_text().strip()
        self.assertNotIn(token, started.stdout + started.stderr)
        # Raw handshake proves the no-token rejection independently of status.
        with socket.create_connection(('127.0.0.1', state['port']), timeout=2) as sock:
            sock.sendall(b'GET / HTTP/1.1\r\nHost: localhost\r\nConnection: Upgrade\r\nUpgrade: websocket\r\nSec-WebSocket-Version: 13\r\nSec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n\r\n')
            self.assertIn(b'401 Unauthorized', sock.recv(1024))
        for args in [('resume', 'thread with spaces', '--last', 'prompt 雪'), ('fork', 'thread-id')]:
            result = self.run_wrapper('connect', '--', *args, env={**self.env, 'FIXTURE_EXIT': '37', 'FIXTURE_STDERR': '1'})
            self.assertEqual(result.returncode, 37, result.stderr)
            record = json.loads(self.record.read_text())
            self.assertEqual(record['args'][-len(args):], list(args))
            self.assertEqual(record['cwd'], str(self.root))
            self.assertIn('fixture-stderr', result.stderr)
            self.assertNotIn(token, result.stdout + result.stderr)
            self.assert_ok(self.run_wrapper('manage', 'server', 'status'))
            self.assert_proxy(state['proxyPort'])
        self.assert_ok(self.run_wrapper('manage', 'server', 'stop'))
        self.assertFalse(active.exists())
        for port in (state['port'], state['proxyPort'], state['controlPort']):
            with self.assertRaises(OSError): socket.create_connection(('127.0.0.1', port), timeout=.3)

    def test_malformed_control_proof_is_rejected_without_lifecycle_damage(self):
        self.start()
        state = self.state()
        active = self.state_path().parent
        # Raw HTTP preserves obs-text bytes. Node decodes 64 bytes of 0x80 as
        # 64 JS characters whose UTF-8 representation is 128 bytes.
        proofs = [b'\x80' * 64, b'g' * 64, b'a' * 63, b'a' * 65, b'0' * 64, b'']
        for operation in ('status', 'stop'):
            for proof in proofs:
                with self.subTest(operation=operation, proof=proof):
                    with socket.create_connection(('127.0.0.1', state['controlPort']), timeout=3) as sock:
                        request = (b'POST /' + operation.encode() + b'/' + b'0' * 48 +
                                   b' HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Length: 0\r\n'
                                   b'Connection: close\r\nX-Codex-Termux-Proof: ' + proof + b'\r\n\r\n')
                        sock.sendall(request)
                        response = http.client.HTTPResponse(sock)
                        response.begin()
                        self.assertEqual(response.status, 403)
                        response.read()
                    self.assertEqual(self.state(), state)
                    os.kill(state['pid'], 0)
                    os.kill(state['childPid'], 0)
                    self.assert_proxy(state['proxyPort'])
                    result = self.run_wrapper('manage', 'server', 'status')
                    self.assert_ok(result)
                    self.assertIn('authenticated WebSocket verified', result.stdout)
        self.assert_ok(self.run_wrapper('manage', 'server', 'stop'))
        self.assertFalse(active.exists())
        for port in (state['port'], state['proxyPort'], state['controlPort']):
            with self.assertRaises(OSError): socket.create_connection(('127.0.0.1', port), timeout=.3)

    def test_connect_preserves_codex_delimiter_and_literal_arguments(self):
        self.start()
        prefix = ['--remote', f"ws://127.0.0.1:{self.state()['port']}",
                  '--remote-auth-token-env', 'CODEX_TERMUX_SERVER_TOKEN', '--cd', str(self.root)]
        forwarded_cases = [('--', text) for text in
                           ('--no-daemon', '--remote', '-Cexample', '--cd', '--remote-auth-token-env', '', 'prompt 雪 with spaces')]
        forwarded_cases += [('resume', 'thread with spaces', '--last'), ('fork', 'thread-id'),
                            ('resume', 'thread-id', '--', '--remote'), ('fork', 'thread-id', '--', '-Cexample')]
        for forwarded in forwarded_cases:
            with self.subTest(forwarded=forwarded):
                self.assert_ok(self.run_wrapper('connect', '--', *forwarded))
                record = json.loads(self.record.read_text())
                self.assertEqual(record['args'], prefix + list(forwarded))
                self.assertEqual(record['cwd'], str(self.root))
        # Without the optional wrapper delimiter, a later -- still belongs to Codex.
        forwarded = ('resume', 'thread-id', '--', '--no-daemon')
        self.assert_ok(self.run_wrapper('connect', *forwarded))
        self.assertEqual(json.loads(self.record.read_text())['args'], prefix + list(forwarded))

    def test_connect_default_and_explicit_cwd_before_delimiter(self):
        self.start()
        prefix = ['--remote', f"ws://127.0.0.1:{self.state()['port']}",
                  '--remote-auth-token-env', 'CODEX_TERMUX_SERVER_TOKEN']
        selected = self.root / 'selected cwd 雪'; selected.mkdir()
        for cwd_args in [(), ('--cd', str(selected)), ('-C', str(selected)),
                         ('--cd=' + str(selected),), ('-C' + str(selected),)]:
            with self.subTest(cwd_args=cwd_args):
                forwarded = [*cwd_args, 'resume', 'thread with spaces', '--', '-Cprompt', '--cd=prompt']
                self.assert_ok(self.run_wrapper('connect', '--', *forwarded))
                default = [] if cwd_args else ['--cd', str(self.root)]
                self.assertEqual(json.loads(self.record.read_text())['args'], prefix + default + forwarded)

    def test_duplicate_and_concurrent_starts(self):
        commands = [base.BASH, str(base.WRAPPER), 'manage', 'server', 'start', '--auth', 'inherited']
        children = [subprocess.Popen(commands, env=self.env, cwd=self.root, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)]
        results = [p.communicate(timeout=25) for p in children]
        self.assertEqual(sorted(p.returncode for p in children), [0, 1], results)
        before = self.state()
        result = self.run_wrapper('manage', 'server', 'start', '--auth', 'inherited')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(before, self.state())

    def test_failed_start_cleanup_and_occupied_port(self):
        result = self.run_wrapper('manage', 'server', 'start', '--auth', 'inherited', env={**self.env, 'FIXTURE_FAIL_START': '1'})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('--no-daemon', result.stderr)
        self.assertEqual(list(self.data.glob('servers/*/active')), [])
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0)); sock.listen()
            result = self.run_wrapper('manage', 'server', 'start', '--auth', 'inherited', '--port', str(sock.getsockname()[1]))
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(list(self.data.glob('servers/*/active')), [])
            self.assertGreater(sock.fileno(), 0)
        self.start()

    def test_start_timeout_rejects_unauthenticated_server_and_cleans_up(self):
        result = self.run_wrapper('manage', 'server', 'start', '--auth', 'inherited',
                                  env={**self.env, 'FIXTURE_NO_AUTH': '1'})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('timed out', result.stderr)
        self.assertEqual(list(self.data.glob('servers/*/active')), [])
        self.assertNotIn('fake-credential', result.stdout + result.stderr)

    def test_stop_timeout_preserves_live_child_proxy_and_recovery_control(self):
        marker = self.root / 'ignore-term'; marker.touch()
        self.start(env={**self.env, 'FIXTURE_IGNORE_TERM_FILE': str(marker)})
        try:
            state = self.state()
            result = self.run_wrapper('manage', 'server', 'stop')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Stop incomplete', result.stderr)
            self.assertTrue(self.state_path().exists())
            os.kill(state['childPid'], 0)
            self.assert_proxy(state['proxyPort'])
            self.assertNotEqual(self.run_wrapper('connect').returncode, 0)
        finally:
            marker.unlink()
            self.assert_ok(self.run_wrapper('manage', 'server', 'stop'))

    def test_private_state_refuses_symlink_and_modified_permissions(self):
        self.start()
        file = self.state_path()
        file.chmod(0o644)
        self.assertNotEqual(self.run_wrapper('manage', 'server', 'stop').returncode, 0)
        file.chmod(0o600)
        token = file.parent / 'ws.token'
        token.rename(file.parent / 'retained-token')
        token.symlink_to(file.parent / 'retained-token')
        self.assertNotEqual(self.run_wrapper('connect').returncode, 0)
        token.unlink(); (file.parent / 'retained-token').rename(token)
        self.assert_ok(self.run_wrapper('manage', 'server', 'status'))
        active = file.parent
        retained = active.with_name('retained-active')
        active.rename(retained); active.symlink_to(active.with_name('missing'))
        try:
            self.assertNotEqual(self.run_wrapper('manage', 'server', 'status').returncode, 0)
            self.assertNotEqual(self.run_wrapper('manage', 'server', 'stop').returncode, 0)
        finally:
            active.unlink(); retained.rename(active)

    def test_connect_ctrl_c_continuation_term_and_piped_stdin(self):
        self.start()
        state = self.state()
        result = self.run_wrapper('connect', 'stdin-fixture', input='private input')
        self.assert_ok(result)
        self.assertEqual(json.loads(result.stdout)['input_length'], 13)
        ready = self.root / 'ready'; received = self.root / 'int'
        env = {**self.env, 'FIXTURE_READY': str(ready), 'FIXTURE_WAIT': '1', 'FIXTURE_INT_CONTINUE': str(received)}
        proc = subprocess.Popen([base.BASH, str(base.WRAPPER), 'connect'], env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
        try:
            until = time.monotonic() + 5
            while not ready.exists() and time.monotonic() < until: time.sleep(.02)
            self.assertTrue(ready.exists())
            os.killpg(proc.pid, signal.SIGINT)
            while not received.exists() and time.monotonic() < until: time.sleep(.02)
            self.assertTrue(received.exists()); self.assertIsNone(proc.poll())
            self.assert_proxy(state['proxyPort'])
            proc.terminate(); proc.communicate(timeout=4)
            self.assertEqual(proc.returncode, 143)
            self.assert_ok(self.run_wrapper('manage', 'server', 'status'))
            self.assert_proxy(state['proxyPort'])
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGKILL); proc.communicate()

    def test_modified_state_never_signals_process(self):
        self.start()
        file = self.state_path(); original = file.read_text(); state = json.loads(original)
        for field, value in [('pid', os.getpid()), ('childPid', os.getpid()), ('id', '0'*32)]:
            modified = {**state, field: value}; file.write_text(json.dumps(modified))
            result = self.run_wrapper('manage', 'server', 'stop')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('no PID was signalled', result.stderr)
            os.kill(state['childPid'], 0)
            file.write_text(original)
        self.assert_ok(self.run_wrapper('manage', 'server', 'status'))

    def test_http_200_impostor_never_receives_token_or_stop(self):
        self.start()
        file = self.state_path(); original = file.read_text(); seen = []
        token = (file.parent / 'ws.token').read_text().strip()

        class Impostor(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                seen.append(self.path + str(self.headers))
                self.send_response(200); self.end_headers(); self.wfile.write(b'{}')
            def log_message(self, *_): pass

        impostor = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Impostor)
        thread = threading.Thread(target=impostor.serve_forever, daemon=True); thread.start()
        try:
            state = json.loads(original); state['controlPort'] = impostor.server_port
            file.write_text(json.dumps(state))
            for args in [('connect',), ('manage', 'server', 'stop')]:
                result = self.run_wrapper(*args)
                self.assertNotEqual(result.returncode, 0)
            self.assertEqual(len(seen), 2)
            self.assertTrue(all(request.startswith('/status/') for request in seen))
            self.assertNotIn(token, ''.join(seen))
        finally:
            file.write_text(original)
            impostor.shutdown(); impostor.server_close(); thread.join()

    def test_stale_state_is_retained_and_not_adopted(self):
        self.start()
        file = self.state_path(); original = file.read_text(); state = json.loads(original)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            state['controlPort'] = sock.getsockname()[1]
        file.write_text(json.dumps(state))
        for operation in ('status', 'stop'):
            result = self.run_wrapper('manage', 'server', operation)
            self.assertNotEqual(result.returncode, 0)
        self.assertTrue(file.exists())
        result = self.run_wrapper('manage', 'server', 'start', '--auth', 'inherited')
        self.assertNotEqual(result.returncode, 0)
        file.write_text(original)

    def test_auth_modes_and_credential_mismatch(self):
        self.start()
        self.assertTrue(json.loads(self.record.read_text())['api'])
        for args, env in [(('connect', '--chatgpt'), self.env), (('connect',), {**self.env, 'OPENAI_API_KEY': 'different-fake'})]:
            result = self.run_wrapper(*args, env=env)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('authentication', result.stderr)
        self.assert_ok(self.run_wrapper('manage', 'server', 'stop'))
        self.start('chatgpt')
        self.assertFalse(json.loads(self.record.read_text())['api'])
        self.assertNotEqual(self.run_wrapper('connect').returncode, 0)
        self.assert_ok(self.run_wrapper('connect', '--chatgpt'))
        self.assertFalse(json.loads(self.record.read_text())['access'])

    def test_runtime_mismatch_and_stop_without_runtime(self):
        self.start()
        self.fake.write_text(self.fake.read_text() + '\n// changed identity\n')
        for args in [('connect',), ('manage', 'server', 'status')]:
            result = self.run_wrapper(*args)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('runtime', result.stdout + result.stderr)
        self.fake.unlink()
        self.assert_ok(self.run_wrapper('manage', 'server', 'stop'))

    def test_custom_codex_home_and_literal_config(self):
        home = self.root / 'other codex 雪'; home.mkdir()
        config = self.root / 'wrapper-config'
        config.write_text('auto_update=off\ncodex_bin=' + str(self.fake) + '\n')
        env = {**self.env, 'CODEX_HOME': str(home), 'CODEX_TERMUX_CONFIG': str(config)}
        try:
            self.start('chatgpt', env=env)
            self.assertEqual(self.state()['home'], str(home))
            self.assertIn('stopped', self.run_wrapper('manage', 'server', 'status').stdout)
            self.assert_ok(self.run_wrapper('connect', '--chatgpt', env=env))
        finally:
            self.assert_ok(self.run_wrapper('manage', 'server', 'stop', env=env))

    def test_incompatible_options_and_reserved_port(self):
        for args in [('connect', '--no-daemon'), ('connect', '--remote=ws://127.0.0.1:9'),
                     ('connect', '--remote-auth-token-env', 'OTHER'), ('manage', 'server', 'start'),
                     ('manage', 'server', 'start', '--auth', 'chatgpt', '--port', '4500')]:
            result = self.run_wrapper(*args)
            self.assertEqual(result.returncode, 2, result.stderr)
        for flag in ('--no-daemon', '--no-daemon=true', '--remote', '--remote=ws://127.0.0.1:9',
                     '--remote-auth-token-env', '--remote-auth-token-env=OTHER'):
            for wrapper_delimiter in ((), ('--',)):
                with self.subTest(flag=flag, wrapper_delimiter=wrapper_delimiter):
                    result = self.run_wrapper('connect', *wrapper_delimiter, flag, '--', 'literal prompt')
                    self.assertEqual(result.returncode, 2, result.stderr)
        self.assertFalse(self.data.exists())

    def test_detached_start_survives_hup_to_starting_shell(self):
        # A real session leader starts the wrapper, then remains until HUP.
        marker = self.root / 'started'
        shell = subprocess.Popen([base.BASH, '-c',
            'bash "$1" manage server start --auth inherited && touch "$2"; sleep 30',
            'fixture', str(base.WRAPPER), str(marker)], env=self.env, cwd=self.root,
            start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            until = time.monotonic() + 10
            while not marker.exists() and time.monotonic() < until: time.sleep(.05)
            self.assertTrue(marker.exists())
            state = self.state()
            os.killpg(shell.pid, signal.SIGHUP); shell.wait(timeout=3)
            self.assert_ok(self.run_wrapper('manage', 'server', 'status'))
            self.assert_proxy(state['proxyPort'])
        finally:
            if shell.poll() is None: os.killpg(shell.pid, signal.SIGKILL); shell.wait()

    def test_connect_pty_interrupt_continuation(self):
        self.start()
        # Reuse foreground signal fixture; connect follows exactly run_codex's
        # existing wait/stream path (the base suite exercises INT continuation).
        status, output = self.run_tty(['connect', 'resume', '--last'], self.env)
        self.assertEqual(status, 0, output)
        self.assertTrue(json.loads(self.record.read_text())['tty'])
        self.assert_ok(self.run_wrapper('manage', 'server', 'status'))


if __name__ == '__main__':
    unittest.main()
