# Colored-log regression: 0.4.2

The two added presentation tests failed against the previous generated wrapper
before the fix. Actual ESC styling was displayed as literal `\x1b` text, and
the underscore logger timestamp prevented severity recognition.

Both tests passed after SGR normalization and consecutive timestamp parsing.
The full verifier subsequently passed all 133 tests, including both regressions.
No deadlines were changed. The supplied example was reproduced in an owned log
fixture; no live service log or real credentials were read.

Coverage includes the exact reported two-timestamp ERROR line, empty/reset and
semicolon/colon extended SGR, literal backslash text, Unicode, unknown formats,
continuations, unterminated lines, OSC and cursor controls, explicit monochrome,
NO_COLOR on a real PTY, explicit raw, and redirected auto output. Pretty output
removes actual SGR only; other controls remain visible and inert. Raw output
retains all original bytes. Existing rotation and signal cleanup checks pass.

The visible message is retained:

```text
2026-10-28_21:13:09.25704 2026-10-28T21:13:09.255877Z ERROR codex_core::tools::router: error=write_stdin failed: Unknown process id 71146
```

Both timestamps are dim and ERROR is red when automatic/forced color applies.
The message reports the original Codex tool error; formatting does not change
that underlying event.
