# CLI maintenance and output style

Use this guide whenever a codex-termux change affects commands, flags, defaults,
configuration, output, help, or completion. The [repository skill](../.agents/skills/codex-termux-cli-consistency/SKILL.md)
provides the workflow; [AGENTS.md](../AGENTS.md) remains the development policy.

## Establish the current interface

Inspect the checkout, its changes, and the relevant parsers before editing.
Identify the installed command's resolved path separately. An installed wrapper
can differ from the checkout even at the same VERSION. Use root help as the
visual reference, but use the current source parser/runtime as the behavior
reference. Do not activate a candidate simply to inspect its help.

Follow each affected operation through accepted arguments, defaults and
precedence, backend restrictions, error paths, output streams, exit status,
and forwarded arguments. Review related controls too: a replacement backend,
changed default, or new workflow can make an older flag misleading or useless.

## Output preferences

The established root-help style uses these semantic roles:

| Element | Style | ANSI SGR |
| --- | --- | --- |
| Branding and banner | Bold cyan | `1;36` |
| Section headings | Bold magenta | `1;35` |
| Command rows | Bold green | `1;32` |
| Option rows | Bold yellow | `1;33` |
| Descriptions | White | `37` |
| Secondary information | Dim when useful | `2` |
| Successful/active state | Bold green, with a status word | `1;32` |
| Warning/inactive state | Bold yellow, with a status word | `1;33` |
| Failure | Bold red, with a status word | `1;31` |

Use two spaces of row indentation and a minimum 27-column label field, followed
by one separator space and the description. Longer labels extend naturally;
do not truncate tokens or descriptions. Keep headings separated by blank lines
and reset styling between labels and descriptions and after each styled span.
The command/option role describes the row label; it is not a shell syntax
highlighter for every bracketed argument within that label.

Root and server help share frontend helpers and banner controls. The banner
uses the existing large artwork at 54+ columns, compact form at 18–53, plain
single-line name at 14–17, and two-line name below 14. These thresholds govern
the banner, not automatic wrapping of the whole help body. Package help uses
the same color roles and row layout with its existing compact branding.
Standalone install/uninstall tools must remain self-contained and work when
piped into Bash, without Node, npm, Python, or another wrapper file.

Color rules are the existing contract:

- `auto` styles eligible terminal output; redirected output, `TERM=dumb`, and
  the presence of `NO_COLOR` suppress automatic ANSI color.
- Explicit `always` forces color, including redirected human help and with
  `NO_COLOR`; explicit `never` disables it.
- Wrapper color options override environment/config. Delegated package help
  inherits the effective wrapper color, and package `--color` can override it.
- Root/server banner mode is independent of color. Package tools retain their
  compact package header and do not expose a separate banner option.

Maintain the [output coverage matrix](OUTPUT.md) for every output route, not
only help. Use compact sections and aligned label/value rows for human reports;
stack rows below 60 columns and retain full values. Green/yellow/red states
must also have meaningful words. Never infer success from color alone.

`output=auto` chooses pretty reports for terminal streams except TERM=dumb;
`pretty` forces layout; `raw` bypasses presentation and overrides wrapper-added
color/banner. Color remains separate: NO_COLOR keeps readable monochrome
layout. Resolve stdout/stderr independently. Existing explicitly forced colors
for redirected help/package text remain available in auto output mode.

Service status and logs may have pretty terminal views. Preserve additional
native details, unknown formats, producer exit codes, rotation, streaming and
interrupt cleanup. Highlight original log lines without filtering or truncating
messages. Strip actual incoming SGR styling before adding the wrapper palette;
recognize consecutive logger/Codex timestamps, including underscore timestamps.
Escape other terminal controls and never decode arbitrary backslash text.
Explicit raw mode and
automatic redirected service/log output preserve original bytes.

JSON, version scalars, configuration examples, emitted completion scripts,
internal token/URL/port exchanges, background workers, and forwarded Codex
streams remain literal in every mode. Config show may use human rows; its raw
key/value summary must reflect current settings. Do not capture prompts or
credentials for styling or validation.

Use shared Bash renderers in `src/ui.sh`, embedded in the frontend and package
tools, and matching Node human helpers. Keep their semantic roles aligned with
focused behavior tests; avoid scattering literal
escape sequences into individual command implementations. New presentation
must not add startup discovery, network requests, or runtime dependencies.

## Change matrix

Review every row for each relevant change. Update affected surfaces in the same
change; record a reason when an apparently related surface stays unchanged.

| Surface | What to reconcile |
| --- | --- |
| Parser/runtime | Accepted arguments, defaults, combinations, precedence, side effects, errors, exit status, forwarding |
| Human output | Semantic colors, spacing, resets, banner behavior, plain/TTY modes, meaningful status text |
| Root and command help | Syntax, scope, descriptions, defaults, restrictions, examples, recovery advice |
| Manual template | Commands, options, configuration/environment, output and exit contracts |
| Bash and Zsh completion | Valid contexts, values, aliases, mutually incompatible and already-used options, descriptions |
| Config examples | Literal keys, defaults, environment equivalents, effective-setting summaries |
| README/current release notes | Current behavior, examples, migration, constraints and limitations |
| Changelog and validation | User-visible changes, compatibility decisions, actual evidence and skips |
| Generated artifacts | Wrapper, install/uninstall, manual and package checksums after all payload edits |
| Repo skill/source archives | Portable guidance, working links, inclusion of new source files and preserved history |

The man page is generated from its template. Completion remains static and
local: never execute Codex, service discovery, network access, or configuration
while completing. Respect explicit backend selection. Without an explicit
backend, offer the applicable union because configuration is unknown; describe
backend-only choices in Zsh. Treat short/long aliases as the same single-use
option. Stop parsing at forwarded commands or wrapper/Codex delimiter boundaries.

Keep stock-service output available unchanged through raw mode. Preserve CLI
boundaries such as Codex-owned `--version`, wrapper-prefixed global flags, and
`run` escaping reserved command names. A removed wrapper command can otherwise
silently become a forwarded Codex argument; review that consequence explicitly.

## Retain, update, deprecate, or remove

For related controls, record a concrete disposition and reason in validation
evidence or the change description. Search callers, examples, tests, completion,
and configuration use before calling an interface obsolete.

- **Retain** when it still supports a distinct workflow. A new default alone
  does not make the previous mode or its options useless.
- **Update** when the behavior remains useful but its implementation,
  applicability, wording, or suggestions no longer match current functionality.
- **Deprecate** a published interface before removal, with a working replacement
  and migration instructions. Keep its behavior through the documented transition;
  any notice must respect machine output and forwarding contracts.
- **Remove** obsolete unreleased/internal controls after checking dependencies,
  or published controls after their documented deprecation period and migration
  conditions are satisfied. Do not invent a deprecation version or schedule;
  establish those details in the specific retirement change.

Update every affected surface when retiring an interface, including negative
tests so rejected or removed syntax does not silently take a different path.
Keep historical release/evidence records intact and label them historical.

## Validation and completion criteria

Use owned fixtures with fake credentials. Test observable contracts: semantic
color spans/resets, plain modes, narrow banners, fast help without dependencies,
argument/exit preservation, valid and rejected combinations, and actual Bash/Zsh
Tab completion. Avoid snapshots that merely duplicate whole help paragraphs.
Use the wrapper, package, runit, and release suites appropriate to the change.

After final payload edits:

```bash
python3 tools/build.py
python3 tools/build.py --check
python3 -B tools/verify.py
git diff --check
```

The verifier checks documentation and repo-skill links. Source-archive tests
cover the guide and skill while the installed package manifest stays at 11
payloads. Validate skill changes with the available skill-creator validator.
Report visual/PTY inspection separately from automated checks, and distinguish
mocked fixtures, real native service execution, real-account acceptance, and
hosted CI. Record missing tools such as groff as skips, not passes.

These checks catch mechanical drift. The functionality review above is still
required to decide whether controls remain useful and descriptions remain true.
See [RELEASING.md](../RELEASING.md) for release and installation boundaries.
