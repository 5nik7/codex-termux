# Validation: codex-termux

## 0.3.1 candidate: authentication recovery notices

Date: 2026-09-19. Base: `2832dc94a26d27b4616724fc3a5ae1f33f305b3b`,
plus the authentication-notice patch. Native host: Linux x64, Node v24.19.0,
Python 3.12.14; Bash, Zsh and groff checks ran on this host. Exact tool and
input identities are recorded in
[verification.json](docs/evidence/0.3.1/verification.json).

The full `python3 -B tools/verify.py` passed **78 tests, no skips**:

| Suite | Passed | Evidence |
| --- | ---: | --- |
| Node runtime | 18 | Existing proxy/runtime behavior plus bounded log parsing, old-entry exclusion, rotation/truncation and unsafe-file handling |
| Bash wrapper | 30 | Existing launch/signal contracts plus real PTY notices, status preservation, opt-out, custom paths and private JSON |
| Wrapper package | 27 | Isolated package lifecycle and recovery fixtures |
| Release artifacts | 3 | Deterministic archives, both manifests and extracted-source installation |

Generated-byte/checksum validation, shell/Node syntax, local documentation
links, real Zsh completion and warning-free groff rendering also passed.
The new log fixtures exercise the user's reported HTTP 401/token_expired
payload inside expected tracing records. No live credentials, accounts,
logs, phone installation or real MCP endpoint were used.

The PTY regression caught an initially retained temporary auth-offset file;
cleanup now removes it with the proxy log. A focused rerun and the full verifier
passed after that correction. Recorded input hashes describe the corrected
candidate, not that intermediate implementation.

Final asset construction also exposed a collector bug: a directory named
`0.3.1` was mistaken for a `.1` manual. The collector now skips real directories,
and archive parity/install coverage checks that the new evidence file is included.
The full verifier was rerun after this correction. The 18 Node runtime tests
also passed separately under umask `077`.

Limits: automatic notices run after eligible interactive sessions exit, using
only the first 256 KiB appended to an existing diagnostic log. They are saved
error evidence, not account-health verification. Disabled/differently formatted
logs, custom paths, scan limits, rotation and concurrent writers can limit
detection. Generic MCP records do not establish that codex_apps was the server.
No real-account refresh behavior or native Android compatibility for the new
notice is claimed. No new startup benchmark or performance number is claimed.

Before release, verify on native Termux at a recorded candidate revision:

1. Run the normal verifier and capture source identity/tool versions.
2. Run `manage auth-check --json`. Record the fixed result only; never publish
   raw private diagnostic logs or authentication files. An unavailable log is
   not an authentication failure.
3. Confirm healthy launches remain quiet and existing Ctrl+C behavior works.
4. When a real expiry next occurs naturally, confirm that an existing log record
   produces the recovery notice after exit. Do not alter credentials to induce
   failure. Check custom log-path configuration if needed.

### Native Termux follow-up: owner-reported checks

The owner installed wrapper 0.3.1 on native Android Termux and
confirmed it with `codex-termux --wrapper-version`. The selected
Codex runtime reported `codex-cli 0.155.1`.

The initial `manage auth-check --json` result was `unavailable`.
After explicitly enabling Codex's plaintext TUI log with `log_dir`,
the checker could read `codex-tui.log` and returned `no_match`.

The owner subsequently confirmed persistent logging, normal launches,
and the diagnostic check without the temporary log-path override.

These results establish local installation and healthy-session log
reading. They do not establish live authentication validity or
recognition of a naturally occurring expired-token error. That
real-error observation remains outstanding.

## Historical 0.3.0 validation

This document preserves the original pre-release Linux validation and records
subsequent results separately. The original test counts, tool versions, hashes,
and timing measurements belong to that Linux run. Native Termux results below
are based on the owner's report and are not inferred from Linux verification.

## Original pre-release Linux validation

Date: 2026-09-18. Native host: Linux x64, Bash 5.2, Node v24.19.0,
Zsh 5.9, Python 3.12.14. All installation prefixes, homes, and
failure fixtures were disposable and test-owned.

Standalone SHA-256: `351820d6482f38ced465a2448f288d9ec9820ac64ddf168a6ad94e699946f77c`.
Source base: `1f9e155b8c1e64e7c1ec374cde89a187a96ee5a9`, plus the delivered changes.
At the time of this original validation, no pushed commit, published release,
or phone execution was claimed. Later release and Termux results appear below.

### Completed checks

`python3 -B tools/verify.py` passed **69 tests, with no skips**:

| Suite | Passed | Scope |
| --- | ---: | --- |
| Node runtime | 13 | Proxy, transport, matching npm packages, staged runtime updates/rollback |
| Bash wrapper | 26 | Streams, arguments, exit status, login filtering, signals, help, real Zsh completion |
| Wrapper package | 27 | Installation, updates, checksum refusals, failure recovery, curl/wget fixtures, uninstall |
| Release artifacts | 3 | Both manifests, repeatable archives, extraction/install, tag/output refusal |

The verifier also checked generated bytes/checksums, Bash/Node/Zsh syntax,
local Markdown links, and a warning-free groff render of the manual.
The GitHub workflow YAML parsed locally; GitHub Actions had not yet been run
at the time of this original validation.

Package tests verified equal-version no-ops, refusal to downgrade, standalone
adoption without executing the old script, preserved symlink targets, retained
backups, unchanged active selection after failed upgrade, and recovery after
an injected SIGKILL. Partial uninstall failure restored all public entries.
Modified managed entries, special files, symlink parents, checksum corruption,
and concurrent-operation locks were refused.

A real pseudo-terminal confirmed that an uninstaller whose source arrives on
stdin still accepts/declines through `/dev/tty`. Separate tests covered a piped
installer inside a checkout, pinned remote asset paths, the wget-only fallback,
color inheritance, and package help without Node/npm. Download tests used local
stub clients; no public 0.3.0 release was available to download during this
original validation.

Source ZIP and tar members matched, both builds were byte-identical on this
host, and an extracted source bundle installed into an owned prefix. These are
same-host build results, not cross-host compression-byte guarantees.

### Warm wrapper measurements

50 measurements and 5 warmups per series, sequential wall time on this
uncontrolled Linux host. The final wrapper was measured separately from tests.

| Series | Median | p95 |
| --- | ---: | ---: |
| `help` | 4.313 ms | 6.634 ms |
| `wrapper_version` | 3.503 ms | 4.659 ms |
| `zsh_generation` | 5.302 ms | 6.547 ms |
| `codex_version_fixture` | 32.297 ms | 37.636 ms |
| `proxy_and_noop_fixture` | 86.444 ms | 98.081 ms |

Help/wrapper version and completion do not start Node. Normal launches gained
no package network check. The Codex/proxy series use a Node fixture, not real
interactive Codex or a model call. These measurements are not cold-start,
Android performance, or a controlled comparison against 0.2.0.

Raw samples are in [benchmark.json](docs/evidence/0.3.0/benchmark.json).
The [verification log](docs/evidence/0.3.0/verification.log) and
[input identities](docs/evidence/0.3.0/verification.json) record the executed
checks and exact code/test inputs. Validation text was completed afterward;
it is not a self-hashed input. Historical evidence remains in
[docs/history/0.2.0](docs/history/0.2.0/README.md).

### Outstanding checks at the time of original validation

The owner reported that 0.2.0 worked on their native Termux setup. That is useful
prior experience, not new 0.3.0 package evidence. At that time, the following
checks remained:

1. Run the delivered verifier and record native Termux tool versions/results.
2. Review `bash install.sh --source . --dry-run`, then confirm a local install.
3. Check wrapper/Codex versions, man-page discovery, and Zsh completion.
4. Reuse the existing working login and normal explicitly chosen Codex flags;
   verify interactive input, Ctrl+C continuation, and a response.
5. Check same-version no-op and `manage uninstall --dry-run`.
6. Review the actual tag-workflow run. After publication, test hosted downloads
   into a disposable prefix as described in [RELEASING.md](RELEASING.md).

Fresh-device Termux package installation, native Android failure injection,
GitHub-hosted release downloads, and independent publisher signing were not
established by the original Linux tests. Those tests did not modify live
authentication/configuration, a global npm installation, a real Termux prefix,
or a remote repository.

## Permission-fixture correction: Linux follow-up

The owner reported a native Termux failure at `tests/runtime.test.cjs:113`.
On 2026-09-18, the same failure was reproduced on Linux x64 / Node v24.19.0
from tag `v0.3.0` (commit `9091e90f411a57e3b0e210d554f4c8404effc01b`):
the focused test passed under umask `022` and failed under `077`. The original
fixture requested mode `0755` at creation, which umask `077` reduced to `0700`.
The runtime correctly accepted that private directory; the rejection fixture
had not established the permissions it intended to test.

The test now applies `chmod(0755)` to its disposable directory and asserts its
actual mode before testing rejection. The caller's umask and runtime safety
checks are unchanged. All 13 Node tests passed under each of `022` and `077`.
The full `python3 -B tools/verify.py` passed all 69 tests under `077`, with no
skips; generated-file/checksum, syntax, documentation, and manual checks passed.
The standalone wrapper SHA-256 remains the value recorded above.

These results are local Linux evidence. The original linked verification log
and input identities above describe the earlier pre-release run; they are not
logs of this follow-up. The follow-up was performed against the recorded tag
plus the test correction, before a commit for the fix was recorded.

No startup measurements were rerun for the test-only correction. The original
Linux timings retain their original provenance and limitations.

## Native Termux follow-up: owner-reported verification

After applying the permission-fixture correction, the owner reported that this
command completed successfully on native Termux:

```bash
python3 -B tools/verify.py
```

The result applies to the owner's corrected working-tree source. A tested
commit or complete source fingerprint was not supplied for that successful run.
The full successful output was not supplied, so this record does not copy the
Linux per-suite counts or claim that all optional checks ran on Termux.

| Item | Recorded result |
| --- | --- |
| Execution environment | Native Termux on Android, as reported by the owner |
| Full verifier | Passed, as reported by the owner |
| Permission fixture | Corrected to set and assert mode `0755` before rejection |
| Successful-run tool versions and umask | Not yet captured in this record |
| Successful-run per-suite counts and optional skips | Not yet captured in this record |
| Native Termux startup measurements | No new measurements recorded |

The Termux failure was consistent with the `077` reproduction on Linux. The
phone's actual umask was not supplied and should not be inferred from that
reproduction. Previously shared Node/npm versions were not recaptured with the
successful run and are not presented here as its verified toolchain.

To complete the environment record, capture the following from the verification
environment and add the actual output with its capture time:

```bash
date -u '+%Y-%m-%dT%H:%M:%SZ'
uname -sm
bash --version
node --version
npm --version
python3 --version
zsh --version
umask
```

A later environment capture documents that later observation; it does not
retroactively establish the exact versions used in the successful run. Record
any optional Zsh or groff skips from the actual verifier output separately.

The correction changes the disposable test fixture, not the runtime permission
checks. It does not change the caller's umask, install a runtime, or require
reinstalling the working wrapper. Passing the verifier exercises its isolated
fixtures; it does not establish fresh-device setup or real account behavior.

## Published release and update-check checkpoint

On 2026-09-18, a read-only GitHub check confirmed:

- The [v0.3.0 draft-release workflow](https://github.com/5nik7/codex-termux/actions/runs/35370875604)
  completed successfully for commit
  `9091e90f411a57e3b0e210d554f4c8404effc01b`.
- [Release v0.3.0](https://github.com/5nik7/codex-termux/releases/tag/v0.3.0)
  was published at `2026-09-18T16:59:42Z`, was not marked as a prerelease,
  and listed all 15 expected release assets.

These are workflow and release-metadata observations, not an independent
download and checksum audit of all published assets.

The owner reported that the following command worked after publication:

```bash
codex-termux manage self-update --check
```

This records a successful update check. It does not by itself prove a complete
hosted download, installation, upgrade, rollback, or uninstall cycle.

The published `v0.3.0` source archives retain the original permission test.
The working-tree correction does not replace that release or its assets.
Corrected release archives must use a new version when a later release is
prepared; the published tag and assets should remain unchanged.

## Remaining evidence to capture

- Native Termux tool versions, umask, detailed verifier output, and any optional
  skips associated with a recorded source revision.
- A recorded CI run for the permission-fixture correction. Current main at
  `2832dc94a26d27b4616724fc3a5ae1f33f305b3b` already includes the separate
  runtime step under umask `077`; source presence alone is not run evidence.
- Detailed native Termux smoke-test results for installed help, the manual,
  completion, and interactive Codex input/signals on a recorded wrapper version.
- A complete hosted package download and lifecycle check in a disposable prefix,
  including checksum validation and preservation checks, as described in
  [RELEASING.md](RELEASING.md).
- Fresh-device setup and independent publisher-signing evidence, if those
  capabilities are to be claimed.

An item listed here may have been tried by the owner without a detailed record;
its inclusion means that this document does not yet establish that evidence.
The historical Linux evidence, the later Linux reproduction, and the owner's
Termux report should remain distinct when adding future results.
