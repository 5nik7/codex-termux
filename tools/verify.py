#!/usr/bin/env python3
"""Offline verification and deterministic standalone-build check."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
binary = ROOT / 'bin/codex-termux'
before = binary.read_bytes()
commands = [
    [sys.executable, '-B', 'tools/build.py'],
    ['bash', '-n', 'bin/codex-termux'],
    ['node', '--check', 'src/runtime.cjs'],
    ['bash', '-n', 'completions/codex-termux.bash'],
    ['node', '--test', 'tests/runtime.test.cjs'],
    [sys.executable, '-B', 'tests/test_wrapper.py'],
]
if shutil.which('zsh'):
    commands.insert(4, ['zsh', '-n', 'completions/_codex-termux'])
for command in commands:
    print('+ ' + ' '.join(command), flush=True)
    child = subprocess.run(command, cwd=ROOT)
    if child.returncode:
        raise SystemExit(child.returncode)
if binary.read_bytes() != before:
    raise SystemExit('generated standalone was stale; build updated it, rerun verification')
print('Standalone SHA-256:', hashlib.sha256(binary.read_bytes()).hexdigest())
print('Offline verification passed.')
