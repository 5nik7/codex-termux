# Human output and literal-output contracts

The [maintenance guide](CLI_MAINTENANCE.md) owns presentation conventions.
This matrix inventories the current output routes. Update it when adding,
changing, or retiring a command; help alone is not the output surface.

## Selecting presentation

```bash
codex-termux manage server status
codex-termux manage server logs --lines 50 --follow
codex-termux --wrapper-output pretty --wrapper-color always manage check
codex-termux --wrapper-output raw manage server logs > service.log
codex-termux --wrapper-output pretty --wrapper-color never manage config show
bash install.sh --output pretty --color never --help
```

`--wrapper-output auto|pretty|raw` must precede the command. Its environment
equivalent is `CODEX_TERMUX_OUTPUT`, and its literal config key is `output`.
Precedence is CLI, environment, configuration, default `auto`.

- `auto` formats human reports on terminal streams, except `TERM=dumb`.
  Redirected streams retain their existing text or data contracts. Existing
  explicit color forcing for help/package text remains available.
- `pretty` formats human reports even when redirected. It does not force color.
- `raw` bypasses added report formatting and wrapper ANSI/banners, including
  when color/banner are set to `always`. Incoming log/service bytes are untouched;
  this mode does not strip escapes produced by another program.

Color is selected separately with `--wrapper-color auto|always|never`.
`NO_COLOR` suppresses automatic color without removing readable report layout.
stdout and stderr determine terminal/color eligibility independently. Section
headings and status words remain meaningful without color.

Standalone package tools accept `--output` and `CODEX_TERMUX_OUTPUT`. They do
not read wrapper configuration. Delegation supplies the wrapper's effective
mode; explicit package `--output` overrides it. Package `--color` remains separate.

## Coverage matrix

| Route | Pretty presentation | Literal/raw contract |
| --- | --- | --- |
| Root/server/package help | Existing semantic help roles and responsive/compact branding | Plain help with raw mode; no Node/network startup |
| `--wrapper-info`, `manage check` | Runtime, prerequisites, versions and update policy as rows | Existing text; `--json` schema unchanged |
| `manage config show` | Effective nonsecret settings with units | Literal key/value summary; adds the new `output` setting |
| `manage config example` | Always literal | Reusable config data, including `output=auto` |
| `manage auth-check` | Saved-evidence status and recovery advice | Existing text/JSON and exit codes; no account-health claim |
| Post-session auth notices | Warning and command hints on stderr | Existing notice text; no log contents or credentials printed |
| `manage update`, `rollback` | Installed/latest rows, progress notices and activation results | Existing text/JSON, confirmation and runtime preservation |
| `setup` | Checks, notices, prompts, outcomes and next steps | Existing operations; pkg/npm streams remain native |
| `test` | DNS/HTTPS results and wrapper diagnostics | Existing results; delegated Codex Doctor remains native |
| `--wrapper-dry-run` | Launch mode, runtime and argument count | Existing summary; argument values never displayed |
| Runit lifecycle/status/check | Service/backend/autostart rows, recognized state/PID/elapsed fields, native details and result | Native sv streams and producer exit code; check retains account-health caveat |
| `manage server is-enabled` | Enabled/Disabled with service name | `enabled` / `disabled`, exits 0 / 1 |
| `manage server logs` | One header; original lines with timestamp/severity spans | Exact tail bytes; lines/follow/rotation semantics retained |
| Managed server start/status/stop | State, endpoint, auth mode, runtime match and instance | Existing text and ownership/authentication checks |
| Package check/install/repair/recover/uninstall | Summaries, file rows, notices, results and controlling-terminal prompts | Existing ownership/confirmation rules; no added Node/Python dependency |
| Wrapper errors, warnings and debug events | Severity labels on their existing stream | Existing diagnostic information and exit status |
| `--wrapper-version`, Codex `--version` | Always scalar/native | Existing version line |
| `completion bash|zsh` | Always literal | Executable shell source, no presentation escapes |
| Internal URL/token/port/version exchanges and background workers | Always literal | Internal protocols unchanged; no presentation context passed to child processes |
| `run`, `chatgpt`, `connect`, login/logout, top-level `status`/`doctor`, unknown commands | Wrapper notices only | Codex stdin/stdout/stderr and argument boundaries remain native |

## Service and log details

Status is an observation, not a readiness guarantee. Stopped services can return
success from `sv status`. Native details, including logger state and unknown
formats, remain visible in pretty output. Autostart is shown as Unknown if its
marker cannot safely establish a setting; presentation does not repair it.

Pretty logs remove actual ANSI SGR styling before parsing and applying the
wrapper palette. They recognize consecutive leading ISO-style, underscore
logger, or TAI64N timestamps and the following
TRACE/DEBUG/INFO/WARN/WARNING/ERROR/FATAL fields. They do not infer severity from
words in the message. Unknown formats and continuation lines remain visible;
messages are not filtered, truncated, or reordered. Other terminal-control characters
are rendered as visible escapes in pretty views. Literal backslash text is not
decoded; only actual SGR styling is removed. Raw mode preserves original
bytes, including final lines without a newline. Following streams incrementally,
handles rotation, and reaps its producer/formatters on Ctrl+C or TERM without
controlling the service or creating a second log recording.

Report rows stack below 60 columns. Long values are retained for terminal
wrapping. Reports use compact headings; the wrapper's explicit banner `always`
can add its existing banner to frontend reports. Help retains its own banner
behavior. Package tools retain compact branding for help.

See [validation](../VALIDATION.md) for measured coverage and limitations.
