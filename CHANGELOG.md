# Changelog

## 0.4.2 — 2026-10-28

### Human CLI reports

- Add terminal-first pretty reports across wrapper diagnostics, configuration,
  updates, setup, package operations, service status and logs. Use compact
  sections, semantic colors, explicit status words and narrow stacked layouts.
- Add --wrapper-output auto|pretty|raw, CODEX_TERMUX_OUTPUT, output config, and
  package --output. Raw mode preserves service/log bytes and suppresses wrapper
  decoration; JSON, internal protocols and Codex streams remain literal.
- Highlight log timestamps/severity without filtering messages; preserve
  rotation, producer statuses and signal cleanup without recording new logs.
- Remove incoming ANSI styling in pretty logs before adding wrapper colors,
  avoiding visible \x1b sequences. Recognize consecutive logger/Codex timestamps
  and underscore timestamps; retain other controls as safe visible escapes.
- Share embedded Bash presentation helpers and matching Node roles. Extend
  completion, manual, output coverage guidance, repo skill and regression tests.

### CLI consistency

- Add a discoverable repository skill and shared CLI-maintenance guide, required
  by AGENTS.md for relevant changes. Review related controls for continued
  usefulness and use deprecation/migration before removing published interfaces.
- Style server help with the root help renderers and align package help colors
  and label columns. Preserve plain/machine/native-service output contracts.
- Filter server completion by explicit backend and omit already-used server and
  connect options, including aliases; keep completion static and local.
- Check repo-skill links and include contributor guidance in source archives.
  Keep the installed package manifest at 11 payloads.

### Termux service management

- Make runit the default backend for connections and server management; honor
  explicit managed configuration and add per-command `--backend` overrides.
- Route server start/stop/status/restart through Termux `sv`; add bounded waits,
  enable/disable/is-enabled, existing logs with rotation following, and an
  authenticated connection check that never prints tokens.
- Keep lifecycle operations independent of Node/Codex and retain the explicit
  legacy supervisor. Preserve service definitions, credentials, native command
  results, and autostart settings on lifecycle failure.
- Update static Bash/Zsh completion, help/manual, and isolated regression tests.

## 0.4.1 — initial runit connection candidate

- Add explicit runit connection backend for the existing codex-remote service.
- Validate private token files and authenticated loopback WebSockets; preserve
  managed mode as default, argument forwarding, exit status, and cwd behavior.
- Service lifecycle remains owned by termux-services; no automatic migration.

## 0.4.0 — local release candidate, 2026-09-27

- Add explicit `manage server start --auth inherited|chatgpt [--port N]`,
  `manage server status`, `manage server stop`, and `connect [--chatgpt] [--] ...`.
- Detach a private Node supervisor owning its own DNS/CONNECT proxy and a
  loopback capability-token app server. Keep ordinary and `--no-daemon` launches
  independent. This is a WebSocket workaround, not an upstream daemon repair.
- Verify live control ownership and authenticated WebSocket connectivity; refuse
  duplicate starts, unsafe/stale state, incompatible auth reuse and runtime
  mismatch. Preserve uncertain recovery state and never kill from stored PIDs.
- Preserve connection arguments, cwd, streams, exit status and interrupt
  continuation, including resume/fork. Keep help/version/completion fast paths.
- Add isolated lifecycle fixtures and an opt-in native transport smoke tool;
  document Android limits and separate owner-run account/tool acceptance.
- Reject malformed control MAC encodings before constant-time comparison, so
  unauthenticated HTTP requests cannot crash the supervisor with unequal buffers.
- Honor Codex's own `--` delimiter after the optional wrapper delimiter in
  `connect`; preserve literal option-like prompts and default cwd selection.
- Record owner-run native Termux acceptance with Codex CLI 0.157.1 on the
  corrected feature candidate (wrapper 0.3.1), independently reported Linux
  review, and separate local 0.4.0 verification. Preserve the historical evidence
  and include it in the full source archives. Published 0.3.1 assets stay intact.

## 0.3.1

- Add `manage auth-check [--json]` for bounded, offline MCP token-expiry log
  evidence, with explicit unavailable/no-match states and no login-health claim.
- Show recovery commands after eligible interactive exits when newly appended
  diagnostic records contain an MCP HTTP 401 with `token_expired`. Keep generic
  MCP identification conditional and preserve Codex's streams, signals and status.
- Reuse the existing proxy startup for disposable log-offset metadata; add no
  startup network probe, credential inspection, automatic logout, or logging.
- Add `auth_notice`/`auth_log` configuration, environment overrides, static
  completion, manual/help updates, and privacy/TTY regression coverage.
- Include the already-merged restrictive-umask permission-fixture correction in
  the next source archives. Published v0.3.0 assets remain unchanged.
- Fix release collection treating the new `docs/evidence/0.3.1` directory as a
  `.1` manual file; preserve its evidence files in both source archives.

## 0.3.0 — 2026-09-18

- Color command names, options, section headings, descriptions, and the existing
  responsive help header separately; retain plain redirected output and NO_COLOR.
- Add a full `codex-termux(1)` manual and install Bash/Zsh completion together.
- Add standalone `install.sh` and `uninstall.sh`, supporting local source,
  published GitHub releases, curl/wget pipelines, and terminal confirmation.
- Add `manage self-update` and `manage uninstall`, separate from Codex npm
  `manage update` and `manage rollback`; extend static completion and help.
- Compare stable wrapper versions, skip equal/older offers, pin all downloaded
  assets to one version, and validate a strict package checksum manifest.
- Stage complete package payloads, retain pre-existing entries, switch normal
  updates through one pointer, and recover interrupted operations explicitly.
- Refuse uncertain ownership, special files, changed managed entries, and
  conflicting operations. Uninstall preserves auth/config, npm runtimes, and
  package recovery history. Package operations do not need Node/npm/Python.
- Add reproducible source/release packaging, offline lifecycle regressions,
  CI, a draft-release workflow, and a step-by-step publishing guide.
- Preserve the native Node DNS/proxy and Codex runtime-management behavior.

Release downloads become usable only after the owner publishes the release and
its assets. Local Linux verification does not establish native Android package
installation behavior; see [VALIDATION.md](VALIDATION.md).

## 0.2.0 — candidate, 2026-09-18

- Add explicit update checks, exact-version staged installation, and validated
  rollback through `manage`. Keep global npm installation intact.
- Add cached background update checks and optional interactive confirmation.
- Check separate Node.js/npm packages and fresh-Termux prerequisites in setup.
- Add static Bash/Zsh completion and Zsh description styling.
- Add responsive ASCII help header, terminal-aware colors, literal configuration,
  wrapper version, local JSON information, dry-run, and debug options.
- Skip proxy startup for help, wrapper metadata/completion, Codex version,
  authentication status, and logout. Replace proxy readiness polling with a pipe.
- Fix no-argument launch, invalid-override repair attempts, and false setup
  success. Validate setup using an actual bounded executable version check.
- Add CONNECT authority validation, a connect deadline, and lifecycle handling
  that keeps streaming tunnels/proxy alive through a handled console Ctrl+C.
- Preserve passthrough arguments/streams/status, explicit safety settings,
  native Node DNS, API-key filtering for `chatgpt`, and device-auth login.
- Add disposable regression tests, real Zsh terminal acceptance, documentation,
  and a reproducible developer build.

Native Android authentication/interactive behavior still needs user-side
validation. Runtime garbage collection, wrapper self-updating, and other shells
are not part of this candidate.
