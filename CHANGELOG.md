# Changelog

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
