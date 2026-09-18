# Validation — codex-termux 0.2.0 candidate

Date: 2026-09-18. Host: Linux x64, Bash 5.2.21, Node 24.19.0,
npm 11.9.0, Zsh 5.9, Python 3.12.14.

Standalone SHA-256: `bb47a4439deeece31b92b280c3e5cca4bffffd40b5ab2b75ba1c0434514f120a`.

## Completed checks

- `python3 -B tools/verify.py`: passed. Generated standalone matched source;
  Bash, JavaScript, and Zsh syntax checks passed.
- `node --test tests/runtime.test.cjs`: **13 passed**, no skips.
- `python3 -B tests/test_wrapper.py`: **25 passed**, no skips.
- Real Codex **0.153.4** and **0.153.4-linux-x64** installed using the production
  exact-version npm arguments in a disposable private prefix. Both staged and
  relocated executable version probes passed. Existing global packages were
  not modified.
- The final wrapper selected that real managed runtime and returned
  `codex-cli 0.153.4`. The real registry JSON check reported 0.155.0 as latest
  at the time of verification. Requesting already-active 0.153.4 correctly
  performed no reinstall.
- Real Zsh Tab completion passed in a private pseudo-terminal. A separate native
  terminal check confirmed cyan description headings by default and no default
  cyan with `NO_COLOR`. No live startup files were read or changed.
- Source/package layout and relative documentation links were checked.

Automated coverage includes package pairing, corrupt/missing identity, npm
failure, failed first/relocated version probes, atomic selection preservation,
rollback rejection/success, concurrent-update lock refusal, literal configuration,
help without Node, invalid overrides, setup with separately missing Node/npm,
argument/stream/exit-status preservation, API-key stdin handling using fake
values, cached prompts, noninteractive suppression, maintenance refusal under
`--wrapper-dry-run`, responsive headers, and shell completion.

Real loopback tests cover host allowlist boundaries, bad authorities, non-CONNECT
requests, byte transport, bounded connection establishment, and a tunnel remaining
usable after its connection deadline has expired. Process tests cover TERM,
console-group Ctrl+C exit, and continued proxy operation when Codex handles Ctrl+C
without exiting. No real account credentials were used.

## Warm wrapper measurements

50 measured executions and 5 warmups per series, sequential wall time.

| Series | Median | p95 |
| --- | --- | --- |
| `help` | 3.711 ms | 5.023 ms |
| `wrapper_version` | 3.268 ms | 4.324 ms |
| `zsh_generation` | 4.679 ms | 6.332 ms |
| `codex_version_fixture` | 31.439 ms | 35.206 ms |
| `proxy_and_noop_fixture` | 84.737 ms | 97.312 ms |

These are uncontrolled local Linux measurements. The final two series use a
Node-based fake Codex and do not measure the real Codex TUI or model/network
latency. They establish candidate overhead on this host, not an Android speed
claim, a cold-start result, or a direct comparison against wrapper 0.1.0.
Raw samples are in [benchmark.json](benchmark.json).

Help/wrapper version do not start Node. Normal proxy readiness uses a pipe;
the original 100 ms polling delay has been removed. Registry checks do not block
normal launch. A fresh cached update may require a local bounded version probe
for an unmanaged/global runtime before a notification is shown.

## Still requiring the phone

- Execute this candidate natively on Android/Termux ARM64 with Node 26.4.0/npm
  12.0.2, or the installed native versions. Linux tests using a mocked Termux
  environment do not prove native Android behavior.
- Run `--wrapper-no-update test`, then the normal `chatgpt` invocation using the
  existing working sandbox/approval flags. Reuse the existing login first.
- Check real interactive stdin, terminal resizing, Ctrl+C request interruption,
  device login if needed, and actual end-to-end model responses.
- Use `manage update --check` before choosing an install. Staging/rollback failure
  paths are verified, but a real ARM64 package update has not been executed here.
- Fresh native Termux `pkg` operations were modeled with a disposable fake package
  manager; no real phone package installation or Android minimum-version matrix
  was tested.

No production installation, release publishing, authentication migration, live
shell change, or dots repository change was performed. The original wrapper and
its global npm runtime remain the recovery path on the user's device.
