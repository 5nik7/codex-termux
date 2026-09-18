# codex-termux development rules

Preserve the working native Termux DNS/proxy solution and existing CLI behavior.
This standalone wrapper is separate from the dots CLI and its Go roadmap.

- Edit `src/frontend.sh`, `src/runtime.cjs`, `src/package.sh`, `completions/`, and
  `man/codex-termux.1.in`; regenerate with `python3 tools/build.py`. `VERSION` is
  authoritative. Never edit generated bin/install/uninstall/man files directly.
- Keep startup independent of npm/network discovery. Help/wrapper version must
  not start Node. Background update checks must not block launching Codex.
- `--version` belongs to Codex. Wrapper flags use `--wrapper-*` before the
  command. Unknown Codex commands/options pass through exactly. `run` bypasses
  wrapper-reserved command names.
- Never auto-select a model, disable TLS verification, weaken approvals/sandbox
  settings, fake bubblewrap, log credentials/prompts, or edit live auth/config.
- No runtime dependencies beyond native Bash/Node and normal Termux utilities.
  npm/pkg are for explicit maintenance. Python is for development only.
- Pin both npm packages to the same exact release; validate before activation.
  Preserve the selected and previous runtime on failure. Do not overwrite the
  existing global npm installation or silently delete old runtimes.
- Setup/update installation requires confirmation or the caller's explicit
  `--yes`. Cached checks never authorize installation.
- `manage update`/`rollback` manage npm runtimes. `manage self-update`/`uninstall`
  manage the wrapper package. Keep these separate and preserve CLI passthrough.
- Package tools must work without Node/npm/Python and when piped into Bash.
  Confirm via /dev/tty, never by consuming the script's standard input. Keep
  HTTPS validation, version-pinned URLs, exact allowed assets, and checksums.
- Back up existing entries, never follow destination symlinks, and switch normal
  upgrades with one current pointer. Refuse modified ownership and surviving
  locks; preserve pending recovery state rather than guessing it is stale.
- Uninstall only owned public entries. Preserve credentials/config, npm runtimes,
  shell startup, package snapshots, and old payloads; no implicit purge.
- Configuration is literal data, never sourced/evaluated. Completion must stay
  static, local, and free of Codex/network execution.
- Only test in owned roots. Tests may use fake credentials, never real accounts.
  Do not install packages globally or rewrite shell startup while verifying.
- Verify foreground streams, Ctrl+C continuation, TERM cleanup, failed update
  preservation, version pairing, cache prompting, and actual shell completion.
- Clearly separate mocked Termux tests, native Linux execution, and actual
  Termux/Android testing. No native phone login/support claims without evidence.
- Update README, CHANGELOG, completion/help, and validation evidence when their
  contracts change. Run focused existing tests to address concrete risks.
- Rebuild the manifest after changing any payload, including README/CHANGELOG.
  Keep `SHA256SUMS` (11 allowed payloads) distinct from `RELEASE-SHA256SUMS`
  (also source archives). Preserve historical evidence under docs/history/.
- Release tooling builds locally; the tag workflow creates a draft. Publishing,
  tagging/pushing, and editing remote releases need task authorization. Do not
  overwrite published versions. Use explicit push source:destination refspecs.

Checks: `python3 tools/build.py --check`, `python3 -B tools/verify.py`,
`git diff --check`. See [RELEASING.md](RELEASING.md).
