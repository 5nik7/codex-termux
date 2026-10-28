# Width regression investigation

The first correction passed the width to Node, but this run exposed a second
issue in the shared width detector: process substitution replaced stdout before
stty could read its terminal descriptor. The completed fix duplicates the
terminal descriptor before the substitution. Final results are recorded separately.

```text
test_auto_pipes_and_raw_override_preserve_service_bytes (__main__.PresentationTests.test_auto_pipes_and_raw_override_preserve_service_bytes) ... ok
test_interrupt_while_renderer_drains_after_producer_exit (__main__.PresentationTests.test_interrupt_while_renderer_drains_after_producer_exit) ... ok
test_log_highlighting_and_literal_raw_bytes (__main__.PresentationTests.test_log_highlighting_and_literal_raw_bytes) ... ok
test_machine_outputs_and_codex_streams_are_untouched (__main__.PresentationTests.test_machine_outputs_and_codex_streams_are_untouched) ... ok
test_modes_precedence_and_narrow_reports (__main__.PresentationTests.test_modes_precedence_and_narrow_reports) ... ok
test_node_report_uses_actual_terminal_width_without_columns (__main__.PresentationTests.test_node_report_uses_actual_terminal_width_without_columns) ... FAIL
test_output_completion_values_and_boundaries (__main__.PresentationTests.test_output_completion_values_and_boundaries) ... ok
test_pretty_follow_rotation_and_signal_cleanup (__main__.PresentationTests.test_pretty_follow_rotation_and_signal_cleanup) ... ok
test_pretty_service_and_logs_without_node (__main__.PresentationTests.test_pretty_service_and_logs_without_node) ... ok
test_service_fields_unknown_details_and_exit_codes (__main__.PresentationTests.test_service_fields_unknown_details_and_exit_codes) ... ok
test_tty_color_modes_and_independent_stderr (__main__.PresentationTests.test_tty_color_modes_and_independent_stderr) ... ok

======================================================================
FAIL: test_node_report_uses_actual_terminal_width_without_columns (__main__.PresentationTests.test_node_report_uses_actual_terminal_width_without_columns)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/data/data/com.termux/files/home/repos/codex-termux/tests/test_presentation.py", line 247, in test_node_report_uses_actual_terminal_width_without_columns
    self.assertIn('  State\n    Stopped\n',plain)
    ~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: '  State\n    Stopped\n' not found in '\nManaged server\n  State                       Stopped\n  Instance                    /data/data/com.termux/files/usr/tmp/codex-termux-integration-0fp8ccb7/home space 雪/.local/share/codex-termux/servers/bff578e61dce0f1f9e143f84bf4858f3\n'

----------------------------------------------------------------------
Ran 11 tests in 9.539s

FAILED (failures=1)
```
