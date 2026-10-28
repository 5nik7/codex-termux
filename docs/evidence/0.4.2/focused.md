# Focused presentation and runit tests: 0.4.2

Native Android ARM64 / Termux, owned roots and fake credentials.

```text
test_auto_pipes_and_raw_override_preserve_service_bytes (__main__.PresentationTests.test_auto_pipes_and_raw_override_preserve_service_bytes) ... ok
test_colored_codex_logs_with_two_timestamps (__main__.PresentationTests.test_colored_codex_logs_with_two_timestamps) ... ok
test_interrupt_while_renderer_drains_after_producer_exit (__main__.PresentationTests.test_interrupt_while_renderer_drains_after_producer_exit) ... ok
test_log_highlighting_and_literal_raw_bytes (__main__.PresentationTests.test_log_highlighting_and_literal_raw_bytes) ... ok
test_log_sgr_normalization_preserves_other_text_and_controls (__main__.PresentationTests.test_log_sgr_normalization_preserves_other_text_and_controls) ... ok
test_machine_outputs_and_codex_streams_are_untouched (__main__.PresentationTests.test_machine_outputs_and_codex_streams_are_untouched) ... ok
test_modes_precedence_and_narrow_reports (__main__.PresentationTests.test_modes_precedence_and_narrow_reports) ... ok
test_node_report_uses_actual_terminal_width_without_columns (__main__.PresentationTests.test_node_report_uses_actual_terminal_width_without_columns) ... ok
test_output_completion_values_and_boundaries (__main__.PresentationTests.test_output_completion_values_and_boundaries) ... ok
test_pretty_follow_rotation_and_signal_cleanup (__main__.PresentationTests.test_pretty_follow_rotation_and_signal_cleanup) ... ok
test_pretty_service_and_logs_without_node (__main__.PresentationTests.test_pretty_service_and_logs_without_node) ... ok
test_service_fields_unknown_details_and_exit_codes (__main__.PresentationTests.test_service_fields_unknown_details_and_exit_codes) ... ok
test_tty_color_modes_and_independent_stderr (__main__.PresentationTests.test_tty_color_modes_and_independent_stderr) ... ok

----------------------------------------------------------------------
Ran 13 tests in 11.134s

OK
test_backend_precedence_and_legacy_stop (__main__.RunitTests.test_backend_precedence_and_legacy_stop) ... ok
test_enable_disable_persistence_and_failures (__main__.RunitTests.test_enable_disable_persistence_and_failures) ... ok
test_existing_logs_without_sv_or_node (__main__.RunitTests.test_existing_logs_without_sv_or_node) ... ok
test_failure_and_timeout_exit_status_preserved (__main__.RunitTests.test_failure_and_timeout_exit_status_preserved) ... ok
test_follow_rotation_and_interrupt (__main__.RunitTests.test_follow_rotation_and_interrupt) ... ok
test_invalid_options_do_not_control_service (__main__.RunitTests.test_invalid_options_do_not_control_service) ... ok
test_lifecycle_mapping_and_native_streams (__main__.RunitTests.test_lifecycle_mapping_and_native_streams) ... ok
test_missing_service_is_not_provisioned (__main__.RunitTests.test_missing_service_is_not_provisioned) ... ok
test_no_node_or_codex_needed_for_lifecycle_and_help (__main__.RunitTests.test_no_node_or_codex_needed_for_lifecycle_and_help) ... ok
test_svdir_is_literal_and_overrides_prefix (__main__.RunitTests.test_svdir_is_literal_and_overrides_prefix) ... ok
test_unsafe_service_and_down_marker_are_not_changed (__main__.RunitTests.test_unsafe_service_and_down_marker_are_not_changed) ... ok
test_real_lifecycle_and_autostart (__main__.NativeRunitTests.test_real_lifecycle_and_autostart) ... ok
test_real_timeout_does_not_kill_service (__main__.NativeRunitTests.test_real_timeout_does_not_kill_service) ... ok
test_real_missing_supervision_reports_failure (__main__.NativeRunitTests.test_real_missing_supervision_reports_failure) ... ok

----------------------------------------------------------------------
Ran 14 tests in 16.677s

OK
```
