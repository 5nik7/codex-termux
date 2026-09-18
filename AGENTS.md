# codex-termux development rules

Preserve the working native Termux DNS/proxy solution and existing CLI behavior.
This standalone wrapper is separate from the dots CLI and its Go roadmap.

- Edit `src/frontend.sh`, `src/runtime.cjs`, and `completions/`; regenerate the
  standalone `bin/codex-termux` with `python3 tools/build.py`.
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

Checks: `bash -n bin/codex-termux`, `node --check src/runtime.cjs`,
`node --test tests/runtime.test.cjs`, `python3 -B tests/test_wrapper.py`.
