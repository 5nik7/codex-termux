#!/usr/bin/env python3
"""Measure local warm wrapper overhead with a disposable fake Codex (offline)."""
import argparse
import importlib.util
import json
import math
import platform
from pathlib import Path
import statistics
import subprocess
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--samples', type=int, default=50)
parser.add_argument('--output', type=Path)
options = parser.parse_args()
if not 5 <= options.samples <= 1000:
    parser.error('--samples must be 5..1000')
spec = importlib.util.spec_from_file_location('wrapper_tests', ROOT / 'tests/test_wrapper.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
fixture = module.WrapperTests()
fixture.setUp()
series = {}
try:
    commands = {
        'help': ['--help'],
        'wrapper_version': ['--wrapper-version'],
        'zsh_generation': ['completion', 'zsh'],
        'codex_version_fixture': ['run', '--version'],
        'proxy_and_noop_fixture': ['--wrapper-no-update', 'chatgpt'],
    }
    for name, args in commands.items():
        samples = []
        for i in range(options.samples + 5):
            begin = time.perf_counter_ns()
            child = subprocess.run([module.BASH, str(module.WRAPPER), *args], env=fixture.env,
                                   cwd=fixture.root, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.PIPE, timeout=10)
            elapsed = (time.perf_counter_ns() - begin) / 1e6
            if child.returncode:
                raise RuntimeError(child.stderr.decode(errors='replace'))
            if i >= 5:
                samples.append(elapsed)
        series[name] = {'samples_ms': samples, 'median_ms': statistics.median(samples),
                        'p95_ms': sorted(samples)[math.ceil(.95 * len(samples)) - 1]}
    result = {'schema_version': 1, 'host': platform.system(), 'machine': platform.machine(),
              'samples_per_series': options.samples, 'warmups_per_series': 5,
              'method': 'Sequential local warm wall-time samples, uncontrolled host/cache; fake Codex, no network. Not native Android evidence.',
              'series': series}
    if options.output:
        options.output.write_text(json.dumps(result, indent=2) + '\n')
    for name, item in series.items():
        print(f"{name}: median {item['median_ms']:.3f} ms; p95 {item['p95_ms']:.3f} ms")
finally:
    fixture.tearDown()
