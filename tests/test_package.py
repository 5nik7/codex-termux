#!/usr/bin/env python3
"""Package lifecycle tests: owned prefixes only, no live files or network."""
import hashlib
import os
from pathlib import Path
import pty
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which('bash')
VERSION = (ROOT / 'VERSION').read_text().strip()
ASSETS = dict(zip(
    ['codex-termux', 'codex-termux.bash', 'codex-termux.zsh', 'codex-termux.1', 'install.sh', 'uninstall.sh', 'README.md', 'CHANGELOG.md', 'config.example', 'LICENSE', 'VERSION'],
    ['bin/codex-termux', 'completions/codex-termux.bash', 'completions/_codex-termux', 'man/codex-termux.1', 'install.sh', 'uninstall.sh', 'README.md', 'CHANGELOG.md', 'config.example', 'LICENSE', 'VERSION']))
LINKS = ['bin/codex-termux', 'share/bash-completion/completions/codex-termux', 'share/zsh/site-functions/_codex-termux', 'share/man/man1/codex-termux.1', 'share/doc/codex-termux/README.md', 'share/doc/codex-termux/CHANGELOG.md', 'share/doc/codex-termux/config.example', 'share/doc/codex-termux/LICENSE']


def snapshot(root):
    result = {}
    for file in sorted(root.rglob('*')):
        stat = file.lstat()
        value = os.readlink(file) if file.is_symlink() else hashlib.sha256(file.read_bytes()).hexdigest() if file.is_file() else 'directory'
        result[str(file.relative_to(root))] = (stat.st_mode, stat.st_mtime_ns, value)
    return result


class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.templates_tmp = tempfile.TemporaryDirectory(prefix='codex-termux-package-sources-')
        cls.templates = Path(cls.templates_tmp.name)
        cls.next_version = VERSION.rsplit('.', 1)[0] + '.' + str(int(VERSION.rsplit('.', 1)[1]) + 1)
        cls.sources = {}
        for version in [VERSION, cls.next_version]:
            source = cls.templates / version
            shutil.copytree(ROOT, source, ignore=shutil.ignore_patterns('.git', 'dist', '__pycache__'))
            (source / 'VERSION').write_text(version + '\n')
            subprocess.run([sys.executable, '-B', 'tools/build.py'], cwd=source, check=True, stdout=subprocess.DEVNULL)
            cls.sources[version] = source

    @classmethod
    def tearDownClass(cls):
        cls.templates_tmp.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='codex-termux-package-test-')
        self.root = Path(self.tmp.name)
        self.prefix = self.root / 'prefix space 雪'; self.prefix.mkdir()
        self.temp = self.root / 'tmp'; self.temp.mkdir()
        self.home = self.root / 'home'; self.home.mkdir()
        self.commands = self.root / 'commands'; self.commands.mkdir()
        self.state = self.prefix / 'libexec/codex-termux'
        utility_dirs = dict.fromkeys(str(Path(shutil.which(name)).parent) for name in ['bash', 'sha256sum', 'stat', 'cp'])
        self.env = {'PATH': ':'.join([str(self.commands), *utility_dirs]), 'HOME': str(self.home), 'PREFIX': str(self.prefix), 'TMPDIR': str(self.temp), 'TERM': 'xterm-256color', 'LANG': 'C.UTF-8'}
        # Package install must not need or run Node, npm, pkg, or an old wrapper.
        for name in ['node', 'npm', 'pkg']:
            file = self.commands / name
            file.write_text('#!' + BASH + '\nprintf forbidden >"$HOME/forbidden"\nexit 99\n'); file.chmod(0o755)

    def tearDown(self):
        self.tmp.cleanup()

    def run_tool(self, *args, uninstall=False, env=None):
        result = subprocess.run([BASH, str(ROOT / ('uninstall.sh' if uninstall else 'install.sh')), '--prefix', str(self.prefix), *args], env=env or self.env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=12, start_new_session=True)
        self.assertFalse((self.home / 'forbidden').exists(), 'maintenance unexpectedly executed a dependency')
        return result

    def install(self, version=VERSION, *args):
        result = self.run_tool('--source', str(self.sources[version]), '--yes', *args)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_fresh_local_install_all_components_without_node(self):
        self.install()
        for entry in LINKS:
            file = self.prefix / entry
            self.assertTrue(file.is_symlink(), entry); self.assertTrue(file.is_file(), entry)
        self.assertEqual((self.state / 'current/VERSION').read_text(), VERSION + '\n')
        for name in ASSETS:
            self.assertTrue((self.state / 'current' / name).is_file(), name)
        result = subprocess.run([BASH, str(self.prefix / 'bin/codex-termux'), '--wrapper-version'], env=self.env, capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout, 'codex-termux ' + VERSION + '\n')
        self.assertFalse((self.state / 'pending').exists())

    def test_equal_version_noop_leaves_every_prefix_entry_unchanged(self):
        self.install(); before = snapshot(self.prefix)
        result = self.run_tool('--source', str(self.sources[VERSION]))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Already at this version', result.stdout)
        self.assertEqual(snapshot(self.prefix), before)
        self.assertEqual(list(self.temp.iterdir()), [])

    def test_newer_version_switches_pointer_and_preserves_previous_payload(self):
        self.install(); old = os.readlink(self.state / 'current')
        public = {name: (os.readlink(self.prefix / name), (self.prefix / name).lstat().st_mtime_ns) for name in LINKS}
        self.install(self.next_version)
        self.assertNotEqual(os.readlink(self.state / 'current'), old)
        self.assertEqual((self.state / 'current/VERSION').read_text(), self.next_version + '\n')
        self.assertTrue((self.state / old / 'codex-termux').is_file())
        self.assertEqual(public, {name: (os.readlink(self.prefix / name), (self.prefix / name).lstat().st_mtime_ns) for name in LINKS})

    def test_older_version_never_downgrades(self):
        self.install(self.next_version); before = snapshot(self.prefix)
        result = self.run_tool('--source', str(self.sources[VERSION]), '--yes')
        self.assertEqual(result.returncode, 0); self.assertIn('No downgrade', result.stdout)
        self.assertEqual(snapshot(self.prefix), before)

    def test_check_preview_and_no_tty_do_not_install(self):
        for flag in ['--check', '--dry-run']:
            result = self.run_tool('--source', str(self.sources[VERSION]), flag)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(list(self.prefix.iterdir()), [])
        result = self.run_tool('--source', str(self.sources[VERSION]))
        self.assertEqual(result.returncode, 1)
        self.assertIn('terminal is required', result.stderr)
        self.assertEqual(list(self.prefix.iterdir()), [])

    def test_adopts_standalone_without_executing_it_and_backs_up_original(self):
        (self.prefix / 'bin').mkdir()
        old = self.prefix / 'bin/codex-termux'
        content = '#!/bin/bash\nreadonly WRAPPER_VERSION=0.2.0\nprintf forbidden >"$HOME/forbidden"\n'
        old.write_text(content); old.chmod(0o755)
        self.install()
        backups = list((self.state / 'backups').glob('tx.*/links/0'))
        self.assertEqual(len(backups), 1); self.assertEqual(backups[0].read_text(), content)

    def test_legacy_symlink_target_is_not_modified(self):
        original = self.root / 'original-wrapper'
        original.write_text('readonly WRAPPER_VERSION=0.2.0\n')
        (self.prefix / 'bin').mkdir(); os.symlink(original, self.prefix / 'bin/codex-termux')
        self.install(); self.assertEqual(original.read_text(), 'readonly WRAPPER_VERSION=0.2.0\n')
        backup = next((self.state / 'backups').glob('tx.*/links/0'))
        self.assertTrue(backup.is_symlink()); self.assertEqual(os.readlink(backup), str(original))

    def test_missing_link_can_be_repaired_but_modified_entry_is_retained(self):
        self.install(); entry = self.prefix / LINKS[1]; entry.unlink()
        result = self.run_tool('--source', str(self.sources[VERSION]))
        self.assertEqual(result.returncode, 0); self.assertFalse(entry.exists())
        self.install(VERSION, '--repair'); self.assertTrue(entry.is_symlink())
        entry.unlink(); entry.write_text('user completion')
        before = snapshot(self.prefix)
        result = self.run_tool('--source', str(self.sources[self.next_version]), '--yes')
        self.assertEqual(result.returncode, 1); self.assertIn('managed entry was changed', result.stderr)
        self.assertEqual(snapshot(self.prefix), before)

    def test_uninstall_only_owned_entries_and_keep_user_state(self):
        user = self.home / 'auth-fixture'; user.write_text('private fixture, not a credential')
        unrelated = self.prefix / 'unrelated'; unrelated.write_text('keep')
        self.install()
        result = self.run_tool('--yes', uninstall=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        for entry in LINKS: self.assertFalse((self.prefix / entry).is_symlink(), entry)
        self.assertFalse((self.state / 'current').exists())
        self.assertTrue(user.exists()); self.assertEqual(unrelated.read_text(), 'keep')
        self.assertTrue(list((self.state / 'backups').glob('tx.*')))
        self.assertTrue(list((self.state / 'releases').iterdir()))

    def test_uninstall_preview_and_modified_entry_refusal(self):
        self.install(); before = snapshot(self.prefix)
        result = self.run_tool('--dry-run', uninstall=True)
        self.assertEqual(result.returncode, 0); self.assertEqual(snapshot(self.prefix), before)
        entry = self.prefix / LINKS[0]; entry.unlink(); entry.write_text('user replaced command')
        before = snapshot(self.prefix)
        result = self.run_tool('--yes', uninstall=True)
        self.assertEqual(result.returncode, 1); self.assertEqual(snapshot(self.prefix), before)

    def test_uninstaller_preserves_unmanaged_standalone(self):
        (self.prefix / 'bin').mkdir(); (self.prefix / LINKS[0]).write_text('readonly WRAPPER_VERSION=0.2.0\n')
        before = snapshot(self.prefix)
        result = self.run_tool('--yes', uninstall=True)
        self.assertEqual(result.returncode, 0); self.assertIn('Standalone files were preserved', result.stdout)
        self.assertEqual(snapshot(self.prefix), before)

    def test_bad_checksums_manifest_and_source_symlinks_never_touch_prefix(self):
        source = self.root / 'source'; shutil.copytree(self.sources[VERSION], source)
        manifest = source / 'PACKAGE-SHA256SUMS'; original = manifest.read_bytes()
        for value in [original + original.splitlines(keepends=True)[0], original.replace(b'codex-termux.1', b'../escape'), original.replace(b'a', b'b', 1)]:
            manifest.write_bytes(value)
            result = self.run_tool('--source', str(source), '--yes')
            self.assertEqual(result.returncode, 1); self.assertEqual(list(self.prefix.iterdir()), [])
        manifest.write_bytes(original)
        binary = source / 'bin/codex-termux'; binary.unlink(); os.symlink(ROOT / 'bin/codex-termux', binary)
        result = self.run_tool('--source', str(source), '--yes')
        self.assertEqual(result.returncode, 1); self.assertEqual(list(self.prefix.iterdir()), [])

    def test_destination_parent_symlink_and_fifo_are_refused_without_opening(self):
        outside = self.root / 'outside'; outside.mkdir(); os.symlink(outside, self.prefix / 'share')
        result = self.run_tool('--source', str(self.sources[VERSION]), '--yes')
        self.assertEqual(result.returncode, 1); self.assertEqual(list(outside.iterdir()), [])
        (self.prefix / 'share').unlink(); (self.prefix / 'bin').mkdir(); os.mkfifo(self.prefix / LINKS[0])
        result = self.run_tool('--source', str(self.sources[VERSION]), '--yes')
        self.assertEqual(result.returncode, 1)

    def test_state_subdirectory_symlink_is_refused_before_chmod(self):
        self.install()
        backup = self.state / 'backups'; saved = self.state / 'backups-saved'; backup.rename(saved)
        outside = self.root / 'outside'; outside.mkdir(mode=0o755); os.symlink(outside, backup)
        before = snapshot(self.prefix); mode = outside.stat().st_mode
        result = self.run_tool('--source', str(self.sources[self.next_version]), '--yes')
        self.assertEqual(result.returncode, 1); self.assertEqual(outside.stat().st_mode, mode)
        self.assertEqual(snapshot(self.prefix), before)

    def inject_mv(self, target, crash=False, command='mv'):
        file = self.commands / command; real = shutil.which(command); once = self.root / 'fault-fired'
        file.write_text('#!' + sys.executable + '\n' + f'''
import os,sys,signal
from pathlib import Path
if sys.argv[-1] == {str(target)!r} and not Path({str(once)!r}).exists():
    Path({str(once)!r}).write_text('fired')
    {'os.kill(os.getppid(), signal.SIGKILL)' if crash else ''}
    sys.exit(23)
os.execv({real!r}, [{real!r}, *sys.argv[1:]])
'''); file.chmod(0o755)

    def test_failed_initial_install_restores_original_entries(self):
        (self.prefix / 'bin').mkdir(); old = self.prefix / LINKS[0]
        old.write_text('readonly WRAPPER_VERSION=0.2.0\n')
        self.inject_mv(self.prefix / LINKS[3])
        result = self.run_tool('--source', str(self.sources[VERSION]), '--yes')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(old.is_symlink()); self.assertEqual(old.read_text(), 'readonly WRAPPER_VERSION=0.2.0\n')
        self.assertFalse((self.state / 'current').exists()); self.assertFalse((self.state / 'pending').exists())
        for entry in LINKS[1:]: self.assertFalse((self.prefix / entry).is_symlink())

    def test_failed_update_preserves_previous_current_pointer(self):
        self.install(); previous = os.readlink(self.state / 'current')
        self.inject_mv(self.state / 'current')
        result = self.run_tool('--source', str(self.sources[self.next_version]), '--yes')
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(os.readlink(self.state / 'current'), previous)
        self.assertEqual((self.state / 'current/VERSION').read_text().strip(), VERSION)
        self.assertFalse((self.state / 'pending').exists())

    def test_partial_uninstall_failure_restores_all_public_entries(self):
        self.install(); previous = os.readlink(self.state / 'current')
        self.inject_mv(self.prefix / LINKS[2], command='rm')
        result = self.run_tool('--yes', uninstall=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(os.readlink(self.state / 'current'), previous)
        self.assertFalse((self.state / 'pending').exists())
        for entry in LINKS:
            self.assertTrue((self.prefix / entry).is_symlink(), entry)
            self.assertTrue((self.prefix / entry).is_file(), entry)

    def test_interrupted_install_is_detected_and_can_be_explicitly_recovered(self):
        (self.prefix / 'bin').mkdir(); old = self.prefix / LINKS[0]
        old.write_text('readonly WRAPPER_VERSION=0.2.0\n')
        self.inject_mv(self.prefix / LINKS[3], crash=True)
        result = self.run_tool('--source', str(self.sources[VERSION]), '--yes')
        self.assertEqual(result.returncode, -signal.SIGKILL)
        self.assertTrue((self.state / 'pending').exists())
        result = self.run_tool('--source', str(self.sources[VERSION]), '--yes')
        self.assertEqual(result.returncode, 1); self.assertIn('interrupted', result.stderr)
        # Only after wait() proved that the known test process is dead.
        (self.prefix / 'libexec/.codex-termux-package.lock').rmdir()
        result = self.run_tool('--recover', '--yes')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(old.is_symlink()); self.assertEqual(old.read_text(), 'readonly WRAPPER_VERSION=0.2.0\n')
        self.assertFalse((self.state / 'pending').exists())

    def test_lock_refusal_does_not_change_existing_installation(self):
        self.install(); lock = self.prefix / 'libexec/.codex-termux-package.lock'; lock.mkdir()
        before = snapshot(self.prefix)
        result = self.run_tool('--source', str(self.sources[self.next_version]), '--yes')
        self.assertEqual(result.returncode, 1); self.assertIn('another package operation', result.stderr)
        self.assertEqual(snapshot(self.prefix), before)

    def fake_download(self, tool='curl'):
        assets = self.root / 'assets'; assets.mkdir()
        for name, source in ASSETS.items(): shutil.copyfile(self.sources[self.next_version] / source, assets / name)
        shutil.copyfile(self.sources[self.next_version] / 'PACKAGE-SHA256SUMS', assets / 'SHA256SUMS')
        log = self.root / 'urls'
        curl = self.commands / tool
        curl.write_text('#!' + sys.executable + '\n' + f'''
import sys,shutil
from pathlib import Path
args=sys.argv[1:];url=args[-1]
if {tool!r} == 'curl' and (args[0] != '-q' or '--proto-redir' not in args):sys.exit(93)
if {tool!r} == 'wget' and ('--no-config' not in args or '--no-netrc' not in args or '--hsts-file' not in args):sys.exit(94)
with open({str(log)!r},'a') as out:out.write(url+'\\n')
destination=args[args.index({'--output' if tool == 'curl' else '-O'!r})+1]
expected='https://github.com/5nik7/codex-termux/releases/'
if not url.startswith(expected):sys.exit(91)
if '/latest/' not in url and '/v{self.next_version}/' not in url:sys.exit(92)
shutil.copyfile(Path({str(assets)!r})/url.rsplit('/',1)[1],destination)
'''); curl.chmod(0o755)
        return assets, log

    def test_piped_install_resolves_remote_without_source_filename(self):
        assets, log = self.fake_download()
        result = subprocess.run([BASH, '-s', '--', '--prefix', str(self.prefix), '--yes'],
            input=(ROOT / 'install.sh').read_text(), env=self.env, capture_output=True,
            text=True, timeout=12, start_new_session=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.state / 'current/VERSION').read_text().strip(), self.next_version)
        self.assertIn('/latest/download/VERSION', log.read_text())

    def test_wget_fallback_without_curl(self):
        assets, log = self.fake_download(tool='wget')
        for utility in ['bash', 'sha256sum', 'stat', 'id', 'readlink', 'mktemp', 'cp', 'mv', 'ln', 'rm', 'rmdir', 'mkdir', 'chmod', 'dirname']:
            os.symlink(shutil.which(utility), self.commands / utility)
        result = self.run_tool('--remote', '--yes', env={**self.env, 'PATH': str(self.commands)})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.state / 'current/VERSION').read_text().strip(), self.next_version)
        self.assertIn('/latest/download/VERSION', log.read_text())

    def test_remote_check_fetches_only_version_and_remote_install_pins_all_assets(self):
        assets, log = self.fake_download()
        result = self.run_tool('--remote', '--check')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(log.read_text().splitlines(), ['https://github.com/5nik7/codex-termux/releases/latest/download/VERSION'])
        self.assertEqual(list(self.prefix.iterdir()), [])
        log.write_text('')
        result = self.run_tool('--remote', '--yes')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        urls = log.read_text().splitlines()
        self.assertTrue(all('/download/v' + self.next_version + '/' in url for url in urls[1:]))
        self.assertEqual((self.state / 'current/VERSION').read_text().strip(), self.next_version)

    def test_remote_corrupt_asset_fails_before_install(self):
        assets, log = self.fake_download(); (assets / 'codex-termux.1').write_text('corrupted')
        result = self.run_tool('--remote', '--yes')
        self.assertEqual(result.returncode, 1); self.assertIn('checksum mismatch', result.stderr)
        self.assertEqual(list(self.prefix.iterdir()), [])

    def test_installed_wrapper_delegates_uninstall_without_node(self):
        self.install(); before = snapshot(self.prefix)
        result = subprocess.run([BASH, str(self.prefix / 'bin/codex-termux'), 'manage', 'uninstall', '--dry-run'], env=self.env, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Preview only', result.stdout); self.assertEqual(snapshot(self.prefix), before)

    def test_wrapper_package_help_delegates_without_node(self):
        for action in ['self-update', 'uninstall']:
            result = subprocess.run([BASH, str(ROOT / 'bin/codex-termux'), 'manage', action, '--help'],
                env=self.env, capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Wrapper package manager', result.stdout)
            if action == 'uninstall': self.assertNotIn('--source', result.stdout)
        self.assertFalse((self.home / 'forbidden').exists())
        self.assertEqual(list(self.prefix.iterdir()), [])

    def test_wrapper_color_is_inherited_and_package_flag_can_override_it(self):
        command = [BASH, str(ROOT / 'bin/codex-termux'), '--wrapper-color', 'always', 'manage', 'self-update']
        result = subprocess.run([*command, '--help'], env=self.env, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr); self.assertIn('\x1b[', result.stdout)
        result = subprocess.run([*command, '--color', 'never', '--help'], env=self.env, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr); self.assertNotIn('\x1b', result.stdout)
        self.assertFalse((self.home / 'forbidden').exists())

    def test_piped_script_uses_controlling_terminal_for_decline_and_accept(self):
        self.install()
        for answer in [b'n\n', b'y\n']:
            reader, writer = os.pipe()
            pid, master = pty.fork()
            if pid == 0:
                os.close(writer); os.dup2(reader, 0); os.close(reader)
                os.execve(BASH, [BASH, '-s', '--', '--prefix', str(self.prefix)], self.env)
            os.close(reader)
            transcript = b''
            try:
                with os.fdopen(writer, 'wb') as out: out.write((ROOT / 'uninstall.sh').read_bytes())
                deadline = time.monotonic() + 5; replied = False
                while time.monotonic() < deadline:
                    if select.select([master], [], [], .1)[0]:
                        try: chunk = os.read(master, 65536)
                        except OSError: break
                        if not chunk: break
                        transcript += chunk
                        if b'[y/N]' in transcript and not replied: os.write(master, answer); replied = True
                self.assertTrue(replied, transcript)
                _, status = os.waitpid(pid, 0); self.assertEqual(os.waitstatus_to_exitcode(status), 0, transcript)
                self.assertEqual((self.prefix / LINKS[0]).is_symlink(), answer == b'n\n')
            finally:
                try: os.kill(pid, signal.SIGKILL)
                except ProcessLookupError: pass
                try: os.waitpid(pid, 0)
                except ChildProcessError: pass
                os.close(master)


if __name__ == '__main__':
    unittest.main(verbosity=2)
