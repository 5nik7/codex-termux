# Changelog

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
