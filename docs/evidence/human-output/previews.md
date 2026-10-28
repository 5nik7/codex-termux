# Human output samples

Captured from the generated source wrapper using owned fixtures and fake service
results. ANSI is stripped for Markdown; temporary root paths are replaced with
`<fixture>`. Automated checks separately assert the actual spans and resets:
magenta headings, cyan labels/INFO, green active/success, yellow WARN, red ERROR,
white values/messages, and dim timestamps. No live service or account was read.

## Service status

```text

Service status
  Service                     codex-remote
  Backend                     runit
  Directory                   <fixture>/prefix/var/service/codex-remote
  Autostart                   Enabled
  State                       Running
  PID                         321
  Elapsed                     45 seconds
  Details                     run: fixture (pid 321) 45s; log: down: fixture/log 2s
  Result                      Command completed
```

## Narrow configuration report

```text

Effective wrapper configuration
  Automatic updates
    off
  Check interval
    86400 seconds
  Color
    always
  Banner
    never
  Output
    pretty
  Proxy timeout
    10000 milliseconds
  Server backend
    runit
  Runit port
    4511
  Authentication notices
    auto
[Info] Overrides: paths and additional hosts are omitted from this summary.
```

## Service logs

```text

Service logs
  Service                     codex-remote
  File                        <fixture>/home space 雪/.local/share/codex-remote/log/current
  Lines                       100

2026-10-28T12:34:56Z INFO Service ready
2026-10-28T12:34:57Z WARN Retry pending
2026-10-28T12:34:58Z ERROR Fixture failure
  continuation
```
