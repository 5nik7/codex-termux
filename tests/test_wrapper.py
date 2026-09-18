#!/usr/bin/env python3
"""Disposable integration tests. No real account, package install, or live config."""
import json
import os
from pathlib import Path
import pty
import select
import shutil
import signal
import socket
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / 'bin/codex-termux'
NODE = shutil.which('node')
BASH = shutil.which('bash')
ZSH = shutil.which('zsh')
FAKE = r'''#!/usr/bin/env node
const fs = require('node:fs');
const args = process.argv.slice(2);
if (args.length === 1 && ['--version', '-V'].includes(args[0])) {
  process.stdout.write('codex-cli 0.153.4\n'); process.exit(0);
}
const result = {args, cwd:process.cwd(), tty:!!process.stdin.isTTY,
  api:!!process.env.OPENAI_API_KEY, access:!!process.env.CODEX_ACCESS_TOKEN,
  proxy:process.env.HTTPS_PROXY || '', ca:process.env.SSL_CERT_FILE || ''};
if (process.env.FIXTURE_RECORD) fs.writeFileSync(process.env.FIXTURE_RECORD, JSON.stringify(result));
if (process.env.FIXTURE_READY) fs.writeFileSync(process.env.FIXTURE_READY, String(process.pid));
if (process.env.FIXTURE_WAIT) {
  process.on('SIGTERM', ()=>{process.exit(143)});
  process.on('SIGINT', ()=>{if(process.env.FIXTURE_INT_CONTINUE)fs.writeFileSync(process.env.FIXTURE_INT_CONTINUE,'received');else process.exit(130)});
  setTimeout(()=>process.exit(91), 8000);
} else {
  if (args.includes('--with-api-key') || args.includes('stdin-fixture')) {
    const input=fs.readFileSync(0,'utf8'); result.input_length=input.length;
  }
  console.log(JSON.stringify(result));
  if (process.env.FIXTURE_STDERR) console.error('fixture-stderr');
  process.exit(Number(process.env.FIXTURE_EXIT || 0));
}
'''


class WrapperTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='codex-termux-integration-')
        self.root = Path(self.tmp.name)
        self.home = self.root / 'home space 雪'; self.home.mkdir()
        self.prefix = self.root / 'prefix'; (self.prefix / 'bin').mkdir(parents=True)
        (self.prefix / 'etc/tls').mkdir(parents=True)
        (self.prefix / 'etc/tls/cert.pem').write_text('fixture-ca')
        self.temp = self.root / 'tmp'; self.temp.mkdir()
        self.record = self.root / 'record.json'
        self.fake = self.prefix / 'bin/codex'
        self.fake.write_text(FAKE.replace('#!/usr/bin/env node', '#!' + NODE, 1))
        self.fake.chmod(0o755)
        self.env = {
            'PATH': f'{self.prefix}/bin:{Path(NODE).parent}:/usr/bin:/bin',
            'HOME': str(self.home), 'PREFIX': str(self.prefix), 'TERMUX_VERSION': 'test-fixture',
            'TMPDIR': str(self.temp), 'TERM': 'xterm-256color', 'LANG': 'C.UTF-8',
            'CODEX_TERMUX_CODEX_BIN': str(self.fake), 'CODEX_TERMUX_AUTO_UPDATE': 'off',
            'FIXTURE_RECORD': str(self.record), 'OPENAI_API_KEY': 'fake-credential-never-real',
            'CODEX_ACCESS_TOKEN': 'fake-token-never-real',
        }

    def tearDown(self):
        self.tmp.cleanup()

    def run_wrapper(self, *args, env=None, input=None):
        return subprocess.run([BASH, str(WRAPPER), *args], env=env or self.env,
                              input=input, text=True, capture_output=True, timeout=12,
                              cwd=self.root)

    def assert_ok(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_help_and_wrapper_version_do_not_need_node_or_termux(self):
        env = {'HOME': str(self.home), 'PATH': '/nonexistent', 'COLUMNS': '30'}
        for args in [('--help',), ('--wrapper-version',), ('completion', 'bash'), ('completion', 'zsh')]:
            result = self.run_wrapper(*args, env=env)
            self.assert_ok(result)
            self.assertNotIn('\x1b', result.stdout)
        self.assertFalse(self.record.exists())
        self.assertEqual(list(self.temp.iterdir()), [])

    def test_no_argument_launch_and_proxy_cleanup(self):
        result = self.run_wrapper()
        self.assert_ok(result)
        report = json.loads(result.stdout)
        self.assertEqual(report['args'], [])
        self.assertRegex(report['proxy'], r'^http://127\.0\.0\.1:\d+$')
        self.assertTrue(report['api'])
        self.assertEqual(list(self.temp.iterdir()), [])

    def test_chatgpt_preserves_args_cwd_streams_and_status(self):
        args = ['exec', '', 'space here', '雪', '"quote"', '\\end\\', '$HOME', ';touch nope', '--', '--help']
        env = {**self.env, 'FIXTURE_EXIT': '37', 'FIXTURE_STDERR': '1'}
        result = self.run_wrapper('chatgpt', *args, env=env)
        self.assertEqual(result.returncode, 37, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['args'], args)
        self.assertEqual(report['cwd'], str(self.root))
        self.assertFalse(report['api']); self.assertFalse(report['access'])
        self.assertEqual(result.stderr, 'fixture-stderr\n')
        self.assertEqual(list(self.temp.iterdir()), [])

    def test_unknown_commands_are_passthrough_and_run_bypasses_reserved_names(self):
        for args in [('new-codex-command', 'one'), ('run', 'manage', 'whatever')]:
            result = self.run_wrapper(*args); self.assert_ok(result)
            self.assertEqual(json.loads(result.stdout)['args'], list(args[1:] if args[0] == 'run' else args))

    def test_local_codex_version_and_status_need_no_proxy_or_ca(self):
        (self.prefix / 'etc/tls/cert.pem').unlink()
        for args in [('--version',), ('run', '--version'), ('chatgpt', '--version'), ('status',), ('logout',)]:
            result = self.run_wrapper(*args); self.assert_ok(result)
            self.assertEqual(list(self.temp.iterdir()), [])
        self.assertEqual(json.loads(result.stdout)['proxy'], '')

    def test_login_defaults_and_api_secret_via_stdin(self):
        result = self.run_wrapper('login'); self.assert_ok(result)
        report = json.loads(result.stdout)
        self.assertEqual(report['args'], ['login', '--device-auth'])
        self.assertFalse(report['api'])
        result = self.run_wrapper('login-api'); self.assert_ok(result)
        report = json.loads(result.stdout)
        self.assertEqual(report['args'], ['login', '--with-api-key'])
        self.assertEqual(report['input_length'], len(self.env['OPENAI_API_KEY']) + 1)
        self.assertNotIn(self.env['OPENAI_API_KEY'], result.stdout + result.stderr)

    def test_stdin_pipe_passes_through(self):
        result = self.run_wrapper('exec', 'stdin-fixture', input='line one\nline two\n')
        self.assert_ok(result)
        self.assertEqual(json.loads(result.stdout)['input_length'], 18)

    def test_bad_args_are_rejected_before_proxy_or_launch(self):
        for args in [('status', 'x'), ('test', 'x'), ('completion', 'fish'),
                     ('setup', '--wat'), ('manage', 'update', '--json'),
                     ('manage', 'update', '--check', '--yes'), ('manage', 'rollback', '--check')]:
            result = self.run_wrapper(*args)
            self.assertEqual(result.returncode, 2, (args, result.stderr))
        self.assertFalse(self.record.exists()); self.assertEqual(list(self.temp.iterdir()), [])

    def test_configuration_is_literal_and_cli_overrides_env(self):
        config = self.root / 'config'
        marker = self.root / 'must-not-exist'
        config.write_text(f'proxy_allow=$(touch {marker})\ncolor=always\n')
        env = {**self.env, 'CODEX_TERMUX_COLOR': 'never'}
        result = self.run_wrapper('--wrapper-config', str(config), '--help', env=env)
        self.assert_ok(result); self.assertFalse(marker.exists()); self.assertNotIn('\x1b', result.stdout)
        result = self.run_wrapper('--wrapper-config', str(config), '--wrapper-color', 'always', '--help', env=env)
        self.assert_ok(result); self.assertIn('\x1b', result.stdout)
        config.write_text('color=auto\ncolor=never\n')
        self.assertEqual(self.run_wrapper('--wrapper-config', str(config), '--help').returncode, 1)
        config.write_text(f'$(touch {marker})=bad\n')
        self.assertEqual(self.run_wrapper('--wrapper-config', str(config), '--help').returncode, 1)
        self.assertFalse(marker.exists())

    def test_invalid_override_never_triggers_setup_package_repair(self):
        for override in (self.root / 'absent', self.prefix / 'bin/broken'):
            if override.name == 'broken':
                override.write_text('#!' + BASH + '\nexit 42\n'); override.chmod(0o755)
            env = {**self.env, 'CODEX_TERMUX_CODEX_BIN': str(override)}
            result = self.run_wrapper('setup', '--yes', env=env)
            self.assertEqual(result.returncode, 1)
            self.assertNotIn('complete', result.stdout.lower())
        self.assertEqual(list(self.temp.iterdir()), [])

    def test_setup_checks_working_override_without_changes(self):
        result = self.run_wrapper('setup', '--yes'); self.assert_ok(result)
        self.assertIn('Nothing installed', result.stdout)
        self.assertEqual(list(self.temp.iterdir()), [])

    def test_fresh_setup_requests_node_and_npm_separately_then_checks_installation(self):
        # A private PATH starts with no Node/npm/curl or CA. The pkg stub supplies
        # those and an already-working Codex launcher, without a real install.
        owned_bin = self.root / 'fresh-bin'; owned_bin.mkdir()
        for command in ('uname', 'mkdir', 'ln', 'timeout'):
            os.symlink(shutil.which(command), owned_bin / command)
        (self.prefix / 'etc/tls/cert.pem').unlink()
        marker = self.root / 'pkg-args'
        pkg = owned_bin / 'pkg'
        pkg.write_text('''#!''' + BASH + '''
printf '%s\\n' "$@" >"$FIXTURE_PKG_RECORD"
ln -s "$FIXTURE_NODE" "$FIXTURE_BIN/node"
ln -s "$FIXTURE_NPM" "$FIXTURE_BIN/npm"
ln -s "$FIXTURE_CURL" "$FIXTURE_BIN/curl"
ln -s "$FIXTURE_GIT" "$FIXTURE_BIN/git"
ln -s "$FIXTURE_CODEX" "$FIXTURE_BIN/codex"
printf 'fixture-ca' >"$PREFIX/etc/tls/cert.pem"
''')
        pkg.chmod(0o755)
        env = {**self.env, 'PATH': str(owned_bin), 'FIXTURE_NODE': NODE,
               'FIXTURE_NPM': shutil.which('npm'), 'FIXTURE_CURL': shutil.which('curl'), 'FIXTURE_GIT': shutil.which('git'),
               'FIXTURE_CODEX': str(self.fake), 'FIXTURE_BIN': str(owned_bin),
               'FIXTURE_PKG_RECORD': str(marker)}
        env.pop('CODEX_TERMUX_CODEX_BIN')
        denied = self.run_wrapper('setup', env=env)
        self.assertEqual(denied.returncode, 1)
        self.assertFalse(marker.exists())
        result = self.run_wrapper('setup', '--yes', env=env)
        self.assert_ok(result)
        self.assertEqual(marker.read_text().splitlines(), ['install', '-y', 'nodejs', 'npm', 'curl', 'git', 'ca-certificates'])
        self.assertIn('Codex 0.153.4 is working', result.stdout)

    def test_dry_run_does_not_expose_prompt_or_touch_runtime(self):
        result = self.run_wrapper('--wrapper-dry-run', 'chatgpt', '--sandbox', 'danger-full-access', 'private prompt')
        self.assert_ok(result)
        self.assertIn('argument count: 3', result.stdout)
        self.assertNotIn('private prompt', result.stdout + result.stderr)
        self.assertFalse(self.record.exists()); self.assertEqual(list(self.temp.iterdir()), [])

    def test_dry_run_refuses_maintenance_before_any_install_or_probe(self):
        for args in [('setup', '--yes'), ('manage', 'update', '--yes'),
                     ('manage', 'rollback', '--yes'), ('login-api',), ('--wrapper-info',)]:
            result = self.run_wrapper('--wrapper-dry-run', *args)
            self.assertEqual(result.returncode, 2, (args, result.stderr))
        self.assertFalse(self.record.exists())
        self.assertEqual(list(self.temp.iterdir()), [])
        self.assertFalse((self.home / '.cache').exists())
        self.assertFalse((self.home / '.local').exists())

    def test_json_info_is_logo_and_color_free(self):
        result = self.run_wrapper('--wrapper-color', 'always', '--wrapper-banner', 'always', '--wrapper-info', '--json')
        self.assert_ok(result)
        report = json.loads(result.stdout)
        self.assertEqual(report['wrapper_version'], (ROOT / 'VERSION').read_text().strip())
        self.assertEqual(report['codex_version'], '0.153.4')
        self.assertNotIn('\x1b', result.stdout)
        self.assertEqual(result.stderr, '')

    def test_responsive_header_and_no_color(self):
        for width in (12, 16, 30, 66, 100):
            env = {**self.env, 'COLUMNS': str(width), 'NO_COLOR': '1'}
            result = self.run_wrapper('--wrapper-banner', 'always', '--help', env=env)
            self.assert_ok(result)
            header = result.stdout.split('\n\n')[0]
            self.assertTrue(all(len(line) <= width for line in header.splitlines()))
            self.assertNotIn('\x1b', result.stdout)

    def test_help_uses_separate_command_option_and_description_colors(self):
        result = self.run_wrapper('--wrapper-color', 'always', '--help')
        self.assert_ok(result)
        for style in ['\x1b[1;32m', '\x1b[1;33m', '\x1b[37m', '\x1b[1;35m']:
            self.assertIn(style, result.stdout)
        self.assertFalse(self.record.exists())

    def test_term_signal_cleans_proxy_and_direct_child(self):
        ready = self.root / 'ready'
        env = {**self.env, 'FIXTURE_READY': str(ready), 'FIXTURE_WAIT': '1'}
        proc = subprocess.Popen([BASH, str(WRAPPER), 'chatgpt'], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 4
            while not ready.exists() and time.monotonic() < deadline:
                time.sleep(.01)
            self.assertTrue(ready.exists())
            child = int(ready.read_text())
            proc.terminate(); out, err = proc.communicate(timeout=4)
            self.assertEqual(proc.returncode, 143, out + err)
            with self.assertRaises(ProcessLookupError): os.kill(child, 0)
            self.assertEqual(list(self.temp.iterdir()), [])
        finally:
            if proc.poll() is None: proc.kill(); proc.communicate()

    def test_console_group_ctrl_c_reaches_child_and_cleans_proxy(self):
        ready = self.root / 'ready'
        env = {**self.env, 'FIXTURE_READY': str(ready), 'FIXTURE_WAIT': '1'}
        proc = subprocess.Popen([BASH, str(WRAPPER), 'chatgpt'], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
        try:
            deadline = time.monotonic() + 4
            while not ready.exists() and time.monotonic() < deadline: time.sleep(.01)
            self.assertTrue(ready.exists())
            os.killpg(proc.pid, signal.SIGINT)
            out, err = proc.communicate(timeout=4)
            self.assertEqual(proc.returncode, 130, out + err)
            self.assertEqual(list(self.temp.iterdir()), [])
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGKILL); proc.communicate()

    def test_console_interrupt_keeps_proxy_when_codex_stays_open(self):
        ready = self.root / 'ready'; received = self.root / 'int'
        env = {**self.env, 'FIXTURE_READY': str(ready), 'FIXTURE_WAIT': '1', 'FIXTURE_INT_CONTINUE': str(received)}
        proc = subprocess.Popen([BASH, str(WRAPPER), 'chatgpt'], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
        try:
            deadline = time.monotonic() + 4
            while not ready.exists() and time.monotonic() < deadline: time.sleep(.01)
            self.assertTrue(ready.exists())
            os.killpg(proc.pid, signal.SIGINT)
            while not received.exists() and time.monotonic() < deadline: time.sleep(.01)
            self.assertTrue(received.exists()); self.assertIsNone(proc.poll())
            port = int(json.loads(self.record.read_text())['proxy'].rsplit(':', 1)[1])
            with socket.create_connection(('127.0.0.1', port), timeout=2) as sock:
                sock.sendall(b'GET / HTTP/1.1\r\nHost: localhost\r\n\r\n')
                self.assertIn(b'405', sock.recv(1024))
            proc.terminate(); proc.communicate(timeout=4)
            self.assertEqual(proc.returncode, 143)
            self.assertEqual(list(self.temp.iterdir()), [])
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGKILL); proc.communicate()

    def test_generated_completions_match_source(self):
        for shell, file in [('bash', 'codex-termux.bash'), ('zsh', '_codex-termux')]:
            result = self.run_wrapper('completion', shell); self.assert_ok(result)
            self.assertEqual(result.stdout, (ROOT / 'completions' / file).read_text())

    def test_bash_completion_routes_and_passthrough_boundary(self):
        script = r'''
source "$COMPLETION"
COMP_WORDS=(codex-termux manage up); COMP_CWORD=2
_codex_termux_complete; printf '%s\n' "${COMPREPLY[@]}"
COMP_WORDS=(codex-termux completion z); COMP_CWORD=2
_codex_termux_complete; printf '%s\n' "${COMPREPLY[@]}"
COMP_WORDS=(codex-termux manage self); COMP_CWORD=2
_codex_termux_complete; printf '%s\n' "${COMPREPLY[@]}"
COMP_WORDS=(codex-termux manage self-update --ch); COMP_CWORD=3
_codex_termux_complete; printf '%s\n' "${COMPREPLY[@]}"
COMP_WORDS=(codex-termux manage uninstall --color ne); COMP_CWORD=4
_codex_termux_complete; printf '%s\n' "${COMPREPLY[@]}"
COMP_WORDS=(codex-termux chatgpt manage up); COMP_CWORD=3
_codex_termux_complete; printf 'passed:%s\n' "${#COMPREPLY[@]}"
'''
        result = subprocess.run([BASH, '--noprofile', '--norc', '-c', script], env={**self.env, 'COMPLETION': str(ROOT / 'completions/codex-termux.bash')}, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, 'update\nzsh\nself-update\n--check\nnever\npassed:0\n')

    def test_cached_update_prompt_decline_preserves_launch_and_no_update_suppresses_it(self):
        cache = self.home / '.cache/codex-termux'
        cache.mkdir(parents=True, mode=0o700)
        (cache / 'update').write_text(f'1\n{int(time.time())}\n0.999.0\n')
        env = {**self.env, 'CODEX_TERMUX_AUTO_UPDATE': 'ask'}
        env.pop('CODEX_TERMUX_CODEX_BIN')
        for no_update in (False, True):
            pid, master = pty.fork()
            if pid == 0:
                args = [BASH, str(WRAPPER)]
                if no_update: args.append('--wrapper-no-update')
                os.execve(BASH, [*args, 'chatgpt'], env)
            output = b''
            try:
                deadline = time.monotonic() + 5
                answered = False
                while time.monotonic() < deadline:
                    if select.select([master], [], [], .1)[0]:
                        try: chunk = os.read(master, 65536)
                        except OSError: break
                        if not chunk: break
                        output += chunk
                        if b'[y/N]' in output and not answered:
                            os.write(master, b'n\n'); answered = True
                _, status = os.waitpid(pid, 0)
                self.assertEqual(os.waitstatus_to_exitcode(status), 0, output)
                self.assertEqual(b'[y/N]' in output, not no_update)
                self.assertIn(b'"args":[]', output)
            finally:
                try: os.kill(pid, signal.SIGKILL)
                except ProcessLookupError: pass
                try: os.waitpid(pid, 0)
                except ChildProcessError: pass
                os.close(master)
        self.assertFalse((self.home / '.local/share/codex-termux').exists())

    def test_noninteractive_and_exec_never_prompt_or_auto_check(self):
        env = {**self.env, 'CODEX_TERMUX_AUTO_UPDATE': 'ask'}
        env.pop('CODEX_TERMUX_CODEX_BIN')
        for args in [('chatgpt',), ('chatgpt', 'exec', 'prompt'), ('login',)]:
            result = self.run_wrapper(*args, env=env); self.assert_ok(result)
            self.assertNotIn('[y/N]', result.stderr)
        self.assertFalse((self.home / '.cache/codex-termux').exists())

    @unittest.skipUnless(ZSH, 'Zsh is not installed')
    def test_zsh_completion_candidates_with_real_zsh(self):
        script = r'''
autoload -Uz compinit
compinit -D -i
source "$COMPLETION"
_describe() { local array=$4; print -rl -- "${(@P)array}"; }
words=(codex-termux manage up); CURRENT=3; _codex_termux
words=(codex-termux completion z); CURRENT=3; _codex_termux
words=(codex-termux manage self-update --ch); CURRENT=4; _codex_termux
words=(codex-termux manage uninstall --dry); CURRENT=4; _codex_termux
'''
        result = subprocess.run([ZSH, '-f', '-c', script], env={**self.env, 'ZDOTDIR': str(self.home), 'COMPLETION': str(ROOT / 'completions/_codex-termux')}, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('update:Check or install Codex npm runtime', result.stdout)
        self.assertIn('zsh:Zsh completion with descriptions', result.stdout)
        self.assertIn('self-update:Update wrapper, completion and manual', result.stdout)
        self.assertIn('--check:Compare wrapper versions only', result.stdout)
        self.assertIn('--dry-run:Preview removal', result.stdout)

    @unittest.skipUnless(ZSH, 'Zsh is not installed')
    def test_zsh_actual_tab_completion_in_owned_pty(self):
        # No live dotfiles, startup files, package work or external commands on Tab.
        child, master = pty.fork()
        if child == 0:
            os.execve(ZSH, [ZSH, '-f'], {**self.env, 'ZDOTDIR': str(self.home), 'PS1': 'CT_PROMPT> '})
        transcript = b''
        try:
            def send(text): os.write(master, text.encode())
            def until(needle, seconds=5):
                nonlocal transcript
                deadline = time.monotonic() + seconds
                while needle not in transcript and time.monotonic() < deadline:
                    if select.select([master], [], [], .1)[0]:
                        try: transcript += os.read(master, 65536)
                        except OSError: break
                self.assertIn(needle, transcript)
            until(b'CT_PROMPT>')
            send("autoload -Uz compinit; compinit -D -i; source '" + str(ROOT / 'completions/_codex-termux') + "'; function codex-termux { print -r -- COMPLETED:$*; }; print READY_MARK\n")
            until(b'READY_MARK\r\n')
            send('codex-termux manage up\t\n')
            until(b'COMPLETED:manage update')
            send('exit\n')
            _, status = os.waitpid(child, 0)
            self.assertEqual(os.waitstatus_to_exitcode(status), 0)
        finally:
            try: os.kill(child, signal.SIGKILL)
            except ProcessLookupError: pass
            try: os.waitpid(child, 0)
            except ChildProcessError: pass
            os.close(master)


if __name__ == '__main__':
    unittest.main(verbosity=2)
