#!/usr/bin/env python3
"""Runit routing fixtures and optional real supervision, exclusively in owned roots."""
import os
from pathlib import Path
import re
import select
import shutil
import signal
import subprocess
import time
import unittest

import test_wrapper as base

SV = shutil.which('sv')
RUNSV = shutil.which('runsv')


class RunitTests(unittest.TestCase):
    run_wrapper = base.WrapperTests.run_wrapper
    assert_ok = base.WrapperTests.assert_ok
    tearDown = base.WrapperTests.tearDown

    def setUp(self):
        base.WrapperTests.setUp(self)
        (self.home / '.codex').mkdir()
        self.service = self.prefix / 'var/service/codex-remote'
        self.service.mkdir(parents=True)
        self.marker = self.service / 'down'
        self.calls = self.root / 'sv.calls'
        self.env['SV_RECORD'] = str(self.calls)
        self.sv = self.prefix / 'bin/sv'
        self.sv.write_text('#!' + base.BASH + '''
printf '%s\\n' "$@" > "$SV_RECORD"
printf '%s\\n' 'fixture native sv output'
printf '%s' "${SV_STDERR-}" >&2
exit "${SV_EXIT:-0}"
''')
        self.sv.chmod(0o755)

    def server(self, *args, **kwargs):
        return self.run_wrapper('manage', 'server', *args, **kwargs)

    def call_args(self):
        return self.calls.read_text().splitlines()

    def test_lifecycle_mapping_and_native_streams(self):
        for command in ('start', 'stop', 'restart'):
            result = self.server(command)
            self.assert_ok(result)
            self.assertEqual(self.call_args(), ['-w', '20', command, str(self.service)])
            self.assertEqual(result.stdout, 'fixture native sv output\n')
        self.assert_ok(self.server('stop', '-w', '003'))
        self.assertEqual(self.call_args()[:3], ['-w', '3', 'stop'])
        result = self.server('status', env={**self.env, 'SV_STDERR': 'native diagnostic', 'CODEX_TERMUX_COLOR': 'always'})
        self.assert_ok(result)
        self.assertEqual(result.stdout, 'fixture native sv output\n')
        self.assertEqual(self.call_args(), ['status', str(self.service)])
        self.assertEqual(result.stderr, 'native diagnostic')
        self.assertFalse(self.marker.exists())

    def test_failure_and_timeout_exit_status_preserved(self):
        for command in ('start', 'stop', 'restart', 'status', 'check'):
            for code in (1, 100, 111):
                result = self.server(command, env={**self.env, 'SV_EXIT': str(code)})
                self.assertEqual(result.returncode, code, result.stderr)
                self.assertEqual(result.stdout, 'fixture native sv output\n')
                self.assertNotIn('kill', self.call_args())

    def test_enable_disable_persistence_and_failures(self):
        self.assertEqual(self.server('is-enabled').stdout, 'enabled\n')
        self.assert_ok(self.server('disable'))
        self.assertTrue(self.marker.is_file())
        self.assertEqual(self.marker.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.call_args()[:3], ['-w', '20', 'stop'])
        result = self.server('is-enabled')
        self.assertEqual((result.returncode, result.stdout), (1, 'disabled\n'))
        self.marker.write_text('retain this existing marker')
        self.assert_ok(self.server('disable'))
        self.assertEqual(self.marker.read_text(), 'retain this existing marker')
        self.assert_ok(self.server('start'))
        self.assertTrue(self.marker.exists())
        for command, exists, setting in [('enable', False, 'enabled'), ('disable', True, 'disabled')]:
            result = self.server(command, '--wait', '1', env={**self.env, 'SV_EXIT': '111'})
            self.assertEqual(result.returncode, 111)
            self.assertEqual(self.marker.exists(), exists)
            self.assertIn('autostart remains ' + setting, result.stderr)
        self.assert_ok(self.server('enable'))
        self.assertFalse(self.marker.exists())

    def test_unsafe_service_and_down_marker_are_not_changed(self):
        victim = self.root / 'unrelated'; victim.write_text('preserve')
        self.marker.symlink_to(victim)
        for command in ('enable', 'disable', 'is-enabled'):
            self.assertNotEqual(self.server(command).returncode, 0)
        self.assertFalse(self.calls.exists())
        self.assertEqual(victim.read_text(), 'preserve')
        self.marker.unlink(); self.marker.mkdir()
        self.assertNotEqual(self.server('enable').returncode, 0)
        self.marker.rmdir()
        os.mkfifo(self.marker)
        self.assertNotEqual(self.server('disable').returncode, 0)
        self.marker.unlink()
        target = self.service.with_name('unrelated-service')
        self.service.rename(target); self.service.symlink_to(target, target_is_directory=True)
        self.assertNotEqual(self.server('start').returncode, 0)
        self.assertFalse(self.calls.exists())

    def test_svdir_is_literal_and_overrides_prefix(self):
        root = self.root / 'services space 雪 $(touch bad)'
        service = root / 'codex-remote'; service.mkdir(parents=True)
        self.assert_ok(self.server('status', env={**self.env, 'SVDIR': str(root)}))
        self.assertEqual(self.call_args(), ['status', str(service)])
        self.assertFalse((self.root / 'bad').exists())
        for value in ('relative', '/bad\npath'):
            self.assertNotEqual(self.server('status', env={**self.env, 'SVDIR': value}).returncode, 0)

    def test_invalid_options_do_not_control_service(self):
        cases = [('unknown',), ('start', '--backend', 'bad'), ('start', '--wait'),
                 ('start', '--wait', '0'), ('start', '-w', '301'), ('start', '-w', '-1'),
                 ('start', '-w', '2', '--wait', '3'), ('status', '--wait', '1'),
                 ('start', '--auth', 'chatgpt'), ('start', '--port', '4511'),
                 ('logs', '-n', '0'), ('logs', '--lines', '10001'), ('status', '-f'),
                 ('logs', '-f', '--follow'), ('start', '--backend', 'runit', '--backend', 'managed'),
                 ('restart', '--backend', 'managed'), ('logs', '--backend', 'managed')]
        for args in cases:
            with self.subTest(args=args):
                self.assertEqual(self.server(*args).returncode, 2)
        self.assertFalse(self.calls.exists())

    def test_backend_precedence_and_legacy_stop(self):
        config = self.root / 'config'
        config.write_text('connect_backend=managed\n')
        env = {**self.env, 'CODEX_TERMUX_CONFIG': str(config)}
        self.assertIn('stopped', self.server('status', env=env).stdout)
        self.assertFalse(self.calls.exists())
        self.assert_ok(self.server('status', env={**env, 'CODEX_TERMUX_CONNECT_BACKEND': 'runit'}))
        self.assertTrue(self.calls.exists()); self.calls.unlink()
        self.assertIn('stopped', self.server('status', '--backend', 'managed',
                                           env={**env, 'CODEX_TERMUX_CONNECT_BACKEND': 'runit'}).stdout)
        self.assertFalse(self.calls.exists())
        self.assert_ok(self.server('stop', '--backend', 'managed'))
        self.assert_ok(self.server('status', '--backend', 'runit', env=env))
        invalid = {**env, 'CODEX_TERMUX_CONNECT_BACKEND': 'invalid'}
        self.assert_ok(self.server('status', '--backend', 'runit', env=invalid))
        self.assertEqual(self.server('status', env=invalid).returncode, 2)
        self.assertNotEqual(self.run_wrapper('manage', 'config', 'show', env=invalid).returncode, 0)

    def test_no_node_or_codex_needed_for_lifecycle_and_help(self):
        # The only executables available are our sv stub and normal utilities.
        for tool in ('rm', 'tail'):
            (self.prefix / 'bin' / tool).symlink_to(shutil.which(tool))
        self.fake.unlink()
        env = {**self.env, 'PATH': str(self.prefix / 'bin')}
        for command in ('start', 'stop', 'restart', 'status', 'disable', 'enable', 'is-enabled'):
            self.assert_ok(self.server(command, env=env))
        for args in [(), ('help',), ('--help',), ('start', '--help')]:
            self.assertIn('Runit commands', self.server(*args, env=env).stdout)
        self.sv.unlink()
        result = self.server('start', env=env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('pkg install termux-services', result.stderr)
        self.assert_ok(self.server('help', env=env))

    def test_missing_service_is_not_provisioned(self):
        self.service.rmdir()
        result = self.server('start')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('install the service separately', result.stderr)
        self.assertFalse(self.service.exists())
        self.assertFalse(self.calls.exists())

    def test_existing_logs_without_sv_or_node(self):
        log = self.home / '.local/share/codex-remote/log/current'
        log.parent.mkdir(parents=True)
        log.write_text(''.join(f'line {n}\n' for n in range(120)))
        (self.prefix / 'bin/tail').symlink_to(shutil.which('tail'))
        self.sv.unlink(); self.fake.unlink()
        env = {**self.env, 'PATH': str(self.prefix / 'bin')}
        result = self.server('logs', env=env)
        self.assert_ok(result)
        self.assertEqual(result.stdout.splitlines(), [f'line {n}' for n in range(20, 120)])
        self.assertEqual(self.server('logs', '-n', '2', env=env).stdout, 'line 118\nline 119\n')
        log.unlink()
        self.assertNotEqual(self.server('logs', env=env).returncode, 0)
        target = self.root / 'private'; target.write_text('do not follow')
        log.symlink_to(target)
        result = self.server('logs', env=env)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('do not follow', result.stdout + result.stderr)

    def test_follow_rotation_and_interrupt(self):
        log = self.home / '.local/share/codex-remote/log/current'
        log.parent.mkdir(parents=True); log.write_text('initial\n')
        proc = subprocess.Popen([base.BASH, str(base.WRAPPER), 'manage', 'server', 'logs', '-f', '-n', '1'],
                                env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                start_new_session=True)
        output = b''
        def until(needle):
            nonlocal output
            deadline = time.monotonic() + 10
            while needle not in output and time.monotonic() < deadline:
                if select.select([proc.stdout], [], [], .1)[0]:
                    chunk = os.read(proc.stdout.fileno(), 4096)
                    if not chunk: break
                    output += chunk
            self.assertIn(needle, output)
        try:
            until(b'initial\n')
            log.rename(log.with_name('old')); log.write_text('rotated\n')
            until(b'rotated\n')
            proc.send_signal(signal.SIGINT)
            proc.communicate(timeout=3)
            self.assertIn(proc.returncode, (-signal.SIGINT, 130))
            self.assertFalse(self.calls.exists())
        finally:
            if proc.poll() is None: proc.kill(); proc.communicate()


@unittest.skipUnless(SV and RUNSV, 'real sv/runsv unavailable; routing fixtures still run')
class NativeRunitTests(RunitTests):
    # Explicit test loader below avoids rerunning inherited routing tests.
    def setUp(self):
        super().setUp()
        self.sv.unlink(); self.sv.symlink_to(SV)
        self.marker.touch()
        run = self.service / 'run'
        run.write_text('#!' + base.BASH + '\nexec ' + shutil.which('sleep') + ' 300\n')
        run.chmod(0o700)
        self.supervisor = subprocess.Popen([RUNSV, str(self.service)], env=self.env,
                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                           start_new_session=True)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if self.server('status').returncode == 0: return
            time.sleep(.05)
        self.tearDown()
        self.fail('owned runsv fixture did not become ready')

    def tearDown(self):
        if self.supervisor.poll() is None:
            subprocess.run([SV, 'down', str(self.service)], env=self.env, capture_output=True, timeout=3)
            subprocess.run([SV, 'kill', str(self.service)], env=self.env, capture_output=True, timeout=3)
            subprocess.run([SV, '-w', '3', 'exit', str(self.service)], env=self.env, capture_output=True, timeout=5)
            try: self.supervisor.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(self.supervisor.pid, signal.SIGKILL); self.supervisor.wait()
        super().tearDown()

    def pid(self):
        result = self.server('status'); self.assert_ok(result)
        match = re.search(r'\(pid (\d+)\)', result.stdout)
        self.assertIsNotNone(match, result.stdout)
        return int(match[1])

    def test_real_lifecycle_and_autostart(self):
        self.assertEqual(self.server('is-enabled').returncode, 1)
        self.assert_ok(self.server('start')); pid = self.pid()
        self.assertTrue(self.marker.exists())
        self.assert_ok(self.server('start')); self.assertEqual(self.pid(), pid)
        self.assert_ok(self.server('restart'))
        # A very quick restart can report success before runsv has processed
        # the request on this host. Observe the
        # actual replacement without changing the wrapper's native sv contract.
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            result = self.server('status')
            match = re.search(r'\(pid (\d+)\)', result.stdout)
            if match and int(match[1]) != pid: break
            time.sleep(.05)
        else: self.fail('runit did not replace the owned service process')
        for _ in range(2): self.assert_ok(self.server('stop'))
        self.assertIn('down:', self.server('status').stdout)
        self.assert_ok(self.server('enable')); self.pid()
        self.assertFalse(self.marker.exists())
        self.assert_ok(self.server('disable'))
        self.assertTrue(self.marker.exists())
        self.assertIn('down:', self.server('status').stdout)

    def test_real_timeout_does_not_kill_service(self):
        run = self.service / 'run'
        ready = self.record
        run.write_text('#!' + base.BASH + '\ntrap \'\' TERM\nprintf ready > "$FIXTURE_RECORD"\nexec ' + shutil.which('sleep') + ' 300\n')
        self.assert_ok(self.server('start'))
        deadline = time.monotonic() + 3
        while not ready.exists() and time.monotonic() < deadline: time.sleep(.01)
        self.assertTrue(ready.exists())
        pid = self.pid()
        result = self.server('stop', '-w', '1')
        self.assertNotEqual(result.returncode, 0)
        os.kill(pid, 0)
        self.assertIn('timeout', result.stdout)

    def test_real_missing_supervision_reports_failure(self):
        subprocess.run([SV, '-w', '3', 'exit', str(self.service)], env=self.env, check=True,
                       capture_output=True, timeout=5)
        self.supervisor.wait(timeout=3)
        result = self.server('status')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('runsv not running', result.stdout + result.stderr)


def load_tests(loader, tests, pattern):
    suite = loader.loadTestsFromTestCase(RunitTests)
    suite.addTests(NativeRunitTests(name) for name in NativeRunitTests.__dict__ if name.startswith('test_'))
    return suite


if __name__ == '__main__':
    unittest.main(verbosity=2)
