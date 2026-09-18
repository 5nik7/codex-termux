# codex-termux 0.2.0

A standalone Bash wrapper for running Codex's Linux npm build in **native
Termux**, with Android DNS handled by native Node.js. No proot or persistent
proxy service. This is a candidate update to the supplied, working 0.1.0 wrapper.

The original `chatgpt` launch behavior is preserved. Updates use a private,
versioned npm installation; the existing global installation stays intact.
No credentials, Codex configuration, shell startup files, model selection, or
sandbox/approval settings are rewritten.

## Try it alongside the working wrapper

Extract the ZIP inside Termux's private home, then enter its directory:

```bash
unzip codex-termux-0.2.0.zip
cd codex-termux-0.2.0

bash bin/codex-termux --help
bash bin/codex-termux --wrapper-version
bash bin/codex-termux --wrapper-info --json
bash bin/codex-termux run --version
bash bin/codex-termux --wrapper-no-update test
```

Use the same launch options that already work on your phone:

```bash
bash bin/codex-termux --wrapper-no-update chatgpt \
  --sandbox danger-full-access \
  --ask-for-approval on-request \
  -c 'approvals_reviewer="auto_review"'
```

Those flags are your explicit selection. `danger-full-access` disables Codex's
OS sandbox; approval review does not provide that sandbox. The wrapper neither
adds these flags nor substitutes a fake `bwrap`. Android sandbox support is
unchanged. Omit `--wrapper-no-update` after checking the candidate to enable the
cached update feature.

The candidate can use your existing login. A new login is unnecessary if it
already works. Native Termux interactive use and authentication have **not**
been executed by the author of this candidate; see [VALIDATION.md](VALIDATION.md).

## Install the wrapper after trying it

Only `bin/codex-termux` is required at runtime; the JavaScript helpers and shell
completions are embedded. Keep the source directory for documentation and tests.

For a conventional existing installation at `$PREFIX/bin/codex-termux`, this
backs up the existing entry and atomically replaces that directory entry. A
symlink target is not overwritten:

```bash
target="$PREFIX/bin/codex-termux"
backup_dir="$(mktemp -d "$HOME/codex-termux-wrapper-backup.XXXXXXXX")"
if [ -e "$target" ] || [ -L "$target" ]; then
  cp -P -- "$target" "$backup_dir/codex-termux"
fi
staged="$(mktemp "$PREFIX/bin/.codex-termux.XXXXXXXX")"
install -m 755 bin/codex-termux "$staged" && mv -T -- "$staged" "$target"
hash -r
printf 'Wrapper backup: %s\n' "$backup_dir"
```

First check `type -a codex-termux` if your existing wrapper is installed elsewhere.
Use its actual destination instead of installing a second competing command.
Keep this extracted release and the printed backup directory until native checks
pass. Restoring the backed-up entry restores the old wrapper; it will continue
to use the untouched global Codex installation.

## Fresh Termux setup

With the wrapper downloaded to Termux's private storage:

```bash
bash bin/codex-termux setup
bash bin/codex-termux test
bash bin/codex-termux login
bash bin/codex-termux chatgpt
```

`setup` checks native ARM64/x64, Node.js, npm, curl, Git, a CA certificate bundle,
and a working Codex executable. Missing Termux packages are listed before
confirmation. Current Termux distributes npm separately from Node.js, so both
are checked. It installs Codex only when missing/broken, or when you request an
exact version. A healthy existing installation is left alone.

```bash
codex-termux setup --version 0.153.4
codex-termux setup --yes              # authorize the displayed setup operations
```

Coreutils/Bash are part of the normal Termux base. This wrapper uses GNU `env`
signal options and `timeout` supplied by coreutils. Use current native Termux
Node.js; the candidate was tested with Node 24.19.0, while the supplied working
phone used Node 26.4.0/npm 12.0.2. No minimum Android version is newly claimed.

Setup does not log in for you, upgrade the whole Termux system, uninstall TUR's
Codex, or rewrite PATH/startup files. If repositories or TLS are broken, it
stops with an error. Termux package operations are not rolled back by the npm
runtime rollback feature.

## Updating Codex

```bash
codex-termux manage update --check
codex-termux manage update --check --json
codex-termux manage update
codex-termux manage update --version 0.153.4
codex-termux manage rollback
```

`--check` reads registry metadata and updates only the wrapper's small private
cache. It never installs. `update` resolves an exact version and asks before
installation; `--yes` explicitly authorizes installation in scripts. An explicit
`--version` accepts stable numeric versions only. Review the version shown in
the prompt before authorizing a switch.

Use **`manage update`** for the Termux-aware updater. The plain `update` command
is deliberately passed to Codex, preserving Codex's own command namespace.

Each install:

1. Reads the official npm registry and validates the known package layout.
2. Pins the launcher and its matching native alias to the same release:
   `@openai/codex@X.Y.Z` and, on ARM64,
   `@openai/codex-linux-arm64@npm:@openai/codex@X.Y.Z-linux-arm64`.
3. Installs into a fresh private npm prefix with lifecycle scripts disabled,
   optional dependency auto-selection disabled, and the native alias explicitly
   supplied. `--force` permits the Linux binary package on Android.
4. Verifies installed package identities and the executable's version, then
   moves the runtime and repeats the executable check at its final path.
5. Atomically records the new selection and the previous selection.

Registry/package TLS and npm integrity validation remain enabled. npm user and
global configuration files are bypassed for this managed installation; API keys
and npm auth tokens are removed from the installer environment. Existing
transport proxy/CA environment settings are retained. No third-party registry
is selected by a user's npmrc. This is not an independent publisher-signature
verification system.

Updates change what **codex-termux** selects. A direct global `codex` command is
unchanged. An explicit `CODEX_TERMUX_CODEX_BIN` override disables managed updates;
the selected installation must be managed separately.

### Automatic checks

The default is `auto_update=ask`:

- Eligible interactive `run`/`chatgpt` launches read the local cache.
- When stale/missing, a background check shares the temporary Node proxy process.
  It never delays the launch waiting for a registry response.
- A newer cached version is offered on a later interactive launch. The answer
  defaults to **No**. Installation never happens just because a check succeeded.
- Successful metadata is cached for 24 hours by default. Failed/interrupted
  background attempts back off for one hour. Explicit checks bypass that backoff.
- No prompting or automatic checking occurs for piped/noninteractive invocations,
  `exec`, arbitrary prompts, login, doctor, completion, or machine-readable output.
  Unrecognized launch-option grammar conservatively disables automatic checking.

The eligibility parser recognizes separate-value options such as `--sandbox`,
`--ask-for-approval`, `-c`, `--model`, `--profile`, and `--cd`, plus `--full-auto`
and `--no-alt-screen`. Other valid Codex syntax still passes through; it simply
does not trigger the optional automatic check.

```bash
codex-termux --wrapper-no-update chatgpt  # no background check or update prompt
```

### Storage and rollback

Managed runtimes live at
`${XDG_DATA_HOME:-$HOME/.local/share}/codex-termux/runtimes/`. Each native npm
runtime can occupy hundreds of MiB. Installation needs temporary download/cache
space as well as the new runtime. Temporary npm caches are deleted after a
completed attempt; previously installed runtimes are retained to protect rollback
and still-running sessions. There is **no automatic runtime deletion** in 0.2.0.

`manage rollback` validates the previous executable and swaps selections. After
the first managed install it can return to the original global npm launcher, if
that launcher still exists. A PATH-only/TUR original has no captured npm launcher;
rollback to that entry is refused without changing the selection. The preserved
0.1.0 wrapper remains another way to launch the original installation.

Do not delete runtime directories while sessions may be using them. Retain the
selected and previous runtimes. Older unreferenced versions can be reviewed and
removed after all Codex sessions using them have ended; automated garbage
collection is deliberately deferred.

A crash/forced kill may leave `update.lock`, `check.lock`, or an `.install-*`
directory in the private data/cache location. A normal failure cleans its own
staging directory and lock. The wrapper never guesses that a surviving update
lock is stale: confirm that no update/check is running before removing a leftover
lock. A normal wrapper exit cleans its background check lock. Never remove a
lock to force concurrent updates.

## Shell completion

Generation and completion do not run Codex, launch a proxy, contact a registry,
or read credentials. Completion covers wrapper commands and options; it does not
guess the evolving Codex argument grammar after `run` or `chatgpt`.

For Zsh, after your existing `compinit`, try it in the current shell:

```zsh
source ./completions/_codex-termux
# Or, once installed:
source <(codex-termux completion zsh)
```

If completion has not been initialized in that shell:

```zsh
autoload -Uz compinit
compinit
source ./completions/_codex-termux
```

Try `codex-termux man<Tab>` or `codex-termux manage up<Tab>`. The default section
heading uses cyan, with styled descriptions and plain inserted tokens. Existing
Zsh description styles take precedence; `NO_COLOR` disables the default cyan.
The completion function does not change global `zstyle` settings.

For persistent Zsh autoloading, put `_codex-termux` in a trusted directory already
on your `fpath` **before** `compinit`. The wrapper never edits `.zshrc` for you.

For Bash:

```bash
source ./completions/codex-termux.bash
# Or:
source <(codex-termux completion bash)
```

## Output and configuration

`--help` gets a wide ASCII logo or a compact phone-sized `codex (termux)` header.
Width comes from `COLUMNS`, then the terminal. Color/header default to terminal
output only; machine output and forwarded Codex output are never decorated.

```bash
codex-termux --wrapper-color always --wrapper-banner always --help
codex-termux --wrapper-color never --wrapper-banner never --help
codex-termux --wrapper-version    # wrapper 0.2.0, no Node process
codex-termux --version            # original Codex --version behavior
codex-termux --wrapper-info --json
codex-termux --wrapper-dry-run chatgpt --sandbox danger-full-access
codex-termux manage check --json
codex-termux manage config example
codex-termux manage config show
```

`manage check`/`--wrapper-info` are local prerequisite/version checks, not online
authentication verification. `test` runs DNS, a TLS/HTTP transport check, and
Codex Doctor. An HTTP 403 from the auth root proves an HTTP response was received;
it does not prove device authorization will succeed.

Optional configuration:
`${XDG_CONFIG_HOME:-$HOME/.config}/codex-termux/config`.
Use [config.example](config.example). It is parsed as literal `key=value` data;
it is never sourced or evaluated. Empty/comment lines are supported; no inline
comments, shell quoting, variable expansion, duplicate keys, or unknown keys.
Use absolute literal paths. Regular-file symlinks are accepted for your dotfiles.

Precedence: wrapper prefix options > environment > configuration > defaults.
Wrapper options belong **before** the wrapper command; all arguments after
`run`/`chatgpt` go to Codex unchanged.

| Variable | Default / role |
| --- | --- |
| `CODEX_TERMUX_AUTO_UPDATE` | `ask`; also `notify` or `off` |
| `CODEX_TERMUX_UPDATE_INTERVAL` | `86400`; range 3600–2592000 seconds |
| `CODEX_TERMUX_COLOR` | `auto`; also `always` or `never` |
| `CODEX_TERMUX_BANNER` | `auto`; also `always` or `never` |
| `CODEX_TERMUX_PROXY_CONNECT_TIMEOUT` | `10000`; range 1000–120000 ms |
| `CODEX_TERMUX_PROXY_ALLOW` | Extra allowed hostname trees, comma separated |
| `CODEX_TERMUX_CODEX_BIN` | Explicit executable override, preserved from 0.1.0 |
| `CODEX_TERMUX_CA_BUNDLE` | Optional explicit Codex/curl CA file |
| `CODEX_TERMUX_CONFIG` | Override configuration file location |
| `CODEX_TERMUX_DATA_DIR` | Override private runtime/selection directory |
| `CODEX_TERMUX_CACHE_DIR` | Override private update cache directory |
| `NO_COLOR` | Disable automatic ANSI color |

`--wrapper-no-config` ignores the file. `--wrapper-debug` emits fixed wrapper
events to stderr without echoing prompts, credentials, or argument values.
JSON reports and dry runs omit arbitrary paths and argument values.

## Proxy and process behavior

The per-launch proxy binds only `127.0.0.1` on a random port. It accepts CONNECT
to `openai.com`, `chatgpt.com`, `oaistatic.com`, `oaiusercontent.com`, and their
subdomains, plus explicitly allowed extras. Hostnames are matched on DNS label
boundaries. Other HTTP methods and malformed CONNECT authorities are refused.

TLS remains end to end; no certificate verification is disabled. Node handles
upstream DNS/TCP. The connect deadline covers establishment; established streaming
and WebSocket tunnels have no newly imposed idle/lifetime cutoff. Readiness uses
a pipe instead of the old 100 ms polling loop.

The proxy is a connectivity workaround, not a network sandbox or authentication
boundary against other code running as your Android app user. Trusted local
configuration/state is not defended against concurrent replacement by that user.

Actual stdin/stdout/stderr, argument values/order, working directory, and Codex
exit status are preserved. Console Ctrl+C is delivered by the process group;
the wrapper does not duplicate it. The proxy survives if Codex handles Ctrl+C
and stays open. Wrapper TERM/HUP forwards to its direct child and waits for it.
It does not supervise arbitrary descendants or guarantee cleanup after SIGKILL,
Android killing the app, or a child that ignores termination.

`chatgpt` removes the three API-credential environment variables for the child.
It does not erase the parent shell's environment or transform a stored API login
into a ChatGPT login. `login` uses device authorization by default; `login-api`
passes `OPENAI_API_KEY` on stdin to Codex, without including the key in argv.

## Development and verification

```bash
python3 tools/build.py
bash -n bin/codex-termux
node --check src/runtime.cjs
node --test tests/runtime.test.cjs
python3 -B tests/test_wrapper.py
python3 -B tools/bench.py
```

Python is a developer/test dependency, not a wrapper runtime dependency. Tests
use private roots, mocked package operations, fake credentials, and loopback
servers. Zsh acceptance includes actual Tab completion in a test-owned terminal.
If Zsh is missing its two shell tests are explicitly skipped, not reported as
verified. The Node helper tests require a Node version with `node:test`.

Keep `src/`, `completions/`, and the generated `bin/codex-termux` synchronized.
[AGENTS.md](AGENTS.md) describes the compatibility and safety rules.

References: [npm install options](https://docs.npmjs.com/cli/v12/commands/npm-install/),
[npm package aliases](https://docs.npmjs.com/cli/v12/using-npm/package-spec/),
[Termux Node.js packaging](https://github.com/termux/termux-packages/blob/master/packages/nodejs/build.sh),
[Codex authentication](https://learn.chatgpt.com/docs/auth).
