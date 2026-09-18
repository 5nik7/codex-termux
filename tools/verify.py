#!/usr/bin/env python3
"""Offline verification and deterministic standalone-build check."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
binary = ROOT / 'bin/codex-termux'
commands = [
    [sys.executable, '-B', 'tools/build.py', '--check'],
    ['bash', '-n', 'bin/codex-termux'],
    ['bash', '-n', 'install.sh'],
    ['bash', '-n', 'uninstall.sh'],
    ['node', '--check', 'src/runtime.cjs'],
    ['bash', '-n', 'completions/codex-termux.bash'],
    ['node', '--test', 'tests/runtime.test.cjs'],
    [sys.executable, '-B', 'tests/test_wrapper.py'],
    [sys.executable, '-B', 'tests/test_package.py'],
    [sys.executable, '-B', 'tests/test_release.py'],
    [sys.executable, '-B', 'tools/check_docs.py'],
]
if shutil.which('zsh'):
    commands.insert(4, ['zsh', '-n', 'completions/_codex-termux'])
for command in commands:
    print('+ ' + ' '.join(command), flush=True)
    child = subprocess.run(command, cwd=ROOT)
    if child.returncode:
        raise SystemExit(child.returncode)
if shutil.which('groff'):
    print('+ groff -Wall -Tutf8 -man man/codex-termux.1 (render check)', flush=True)
    child = subprocess.run(['groff', '-Wall', '-Tutf8', '-man', 'man/codex-termux.1'], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if child.returncode or child.stderr:
        raise SystemExit('Manual render failed or warned: ' + child.stderr.decode(errors='replace'))
else:
    print('SKIP: groff is unavailable; manual rendering is not verified on this host.')
print('Standalone SHA-256:', hashlib.sha256(binary.read_bytes()).hexdigest())
print('Offline verification passed.')
