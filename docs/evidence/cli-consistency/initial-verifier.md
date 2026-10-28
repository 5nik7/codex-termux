# Initial verifier attempt

This attempt stopped at the wrapper suite. Four timing-sensitive fixtures failed;
the same four tests subsequently passed without changes to their deadlines.
The cause of the intermittent failures was not established.

```text
+ /data/data/com.termux/files/usr/bin/python3 -B tools/build.py --check
Generated files and package checksums match source.
+ bash -n bin/codex-termux
+ bash -n install.sh
+ bash -n uninstall.sh
+ zsh -n completions/_codex-termux
+ node --check src/runtime.cjs
+ bash -n completions/codex-termux.bash
+ node --test tests/runtime.test.cjs
✔ auth evidence requires an MCP warning/error, HTTP 401 and the exact expiry code (56.525937ms)
✔ automatic auth scan ignores old bytes and detects new errors without leaking records (48.251927ms)
✔ auth scan supports a newly created log and skips rotation/truncation (16.723698ms)
✔ auth scanner is bounded and separates startup bytes from explicit saved-log tail (37.437031ms)
✔ auth scanner refuses special files, symlinks and auth.json without blocking (71.46776ms)
✔ strict versions and numeric comparison reject injection and prereleases (5.900572ms)
✔ metadata requires an exact platform alias and known launcher layout (20.669844ms)
✔ check updates private cache; a failed check preserves prior cache (95.474167ms)
✔ staged install pins both packages, disables scripts, probes relocated runtime, activates atomically (107.294114ms)
✔ npm failure, corrupt package, and each smoke-test failure preserve active runtime (508.336198ms)
✔ update lock refuses concurrency without changing lock or selection (134.680886ms)
✔ rollback validates the prior selection; a failed probe changes nothing (205.196771ms)
✔ managed paths reject writable dirs, symlinks, and malformed selections (6.754792ms)
✔ installer environment clears auth and npm config; keeps native PATH and transport proxy (6.353854ms)
✔ CONNECT authority parsing preserves explicit ports and rejects URL forms (6.417604ms)
✔ real loopback proxy denies unknown/suffix-confusion hosts and plain HTTP (415.943958ms)
✔ real CONNECT tunnel transports bytes and survives connection timeout after establishment (144.699583ms)
✔ CONNECT handshake timeout is bounded (66.126041ms)
ℹ tests 18
ℹ suites 0
ℹ pass 18
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 3327.434269
+ /data/data/com.termux/files/usr/bin/python3 -B tests/test_wrapper.py
test_auth_check_saved_evidence_json_is_private_and_needs_no_codex_or_ca (__main__.WrapperTests.test_auth_check_saved_evidence_json_is_private_and_needs_no_codex_or_ca) ... ok
test_auth_notice_after_tty_exit_preserves_status_and_filters_old_errors (__main__.WrapperTests.test_auth_notice_after_tty_exit_preserves_status_and_filters_old_errors) ... FAIL
test_auth_notice_honors_codex_home_and_wrapper_log_configuration (__main__.WrapperTests.test_auth_notice_honors_codex_home_and_wrapper_log_configuration) ... FAIL
test_auth_notice_opt_out_passthrough_and_noninteractive_are_quiet (__main__.WrapperTests.test_auth_notice_opt_out_passthrough_and_noninteractive_are_quiet) ... ok
test_bad_args_are_rejected_before_proxy_or_launch (__main__.WrapperTests.test_bad_args_are_rejected_before_proxy_or_launch) ... ok
test_bash_actual_tab_completion_in_owned_pty (__main__.WrapperTests.test_bash_actual_tab_completion_in_owned_pty) ... ok
test_bash_completion_routes_and_passthrough_boundary (__main__.WrapperTests.test_bash_completion_routes_and_passthrough_boundary) ... ok
test_cached_update_prompt_decline_preserves_launch_and_no_update_suppresses_it (__main__.WrapperTests.test_cached_update_prompt_decline_preserves_launch_and_no_update_suppresses_it) ... FAIL
test_chatgpt_preserves_args_cwd_streams_and_status (__main__.WrapperTests.test_chatgpt_preserves_args_cwd_streams_and_status) ... ok
test_configuration_is_literal_and_cli_overrides_env (__main__.WrapperTests.test_configuration_is_literal_and_cli_overrides_env) ... ok
test_console_group_ctrl_c_reaches_child_and_cleans_proxy (__main__.WrapperTests.test_console_group_ctrl_c_reaches_child_and_cleans_proxy) ... FAIL
test_console_interrupt_keeps_proxy_when_codex_stays_open (__main__.WrapperTests.test_console_interrupt_keeps_proxy_when_codex_stays_open) ... ok
test_dry_run_does_not_expose_prompt_or_touch_runtime (__main__.WrapperTests.test_dry_run_does_not_expose_prompt_or_touch_runtime) ... ok
test_dry_run_refuses_maintenance_before_any_install_or_probe (__main__.WrapperTests.test_dry_run_refuses_maintenance_before_any_install_or_probe) ... ok
test_fresh_setup_requests_node_and_npm_separately_then_checks_installation (__main__.WrapperTests.test_fresh_setup_requests_node_and_npm_separately_then_checks_installation) ... ok
test_generated_completions_match_source (__main__.WrapperTests.test_generated_completions_match_source) ... ok
test_help_and_wrapper_version_do_not_need_node_or_termux (__main__.WrapperTests.test_help_and_wrapper_version_do_not_need_node_or_termux) ... ok
test_help_color_modes_in_owned_tty_and_machine_output (__main__.WrapperTests.test_help_color_modes_in_owned_tty_and_machine_output) ... ok
test_help_uses_separate_command_option_and_description_colors (__main__.WrapperTests.test_help_uses_separate_command_option_and_description_colors) ... ok
test_invalid_override_never_triggers_setup_package_repair (__main__.WrapperTests.test_invalid_override_never_triggers_setup_package_repair) ... ok
test_json_info_is_logo_and_color_free (__main__.WrapperTests.test_json_info_is_logo_and_color_free) ... ok
test_local_codex_version_and_status_need_no_proxy_or_ca (__main__.WrapperTests.test_local_codex_version_and_status_need_no_proxy_or_ca) ... ok
test_login_defaults_and_api_secret_via_stdin (__main__.WrapperTests.test_login_defaults_and_api_secret_via_stdin) ... ok
test_no_argument_launch_and_proxy_cleanup (__main__.WrapperTests.test_no_argument_launch_and_proxy_cleanup) ... ok
test_noninteractive_and_exec_never_prompt_or_auto_check (__main__.WrapperTests.test_noninteractive_and_exec_never_prompt_or_auto_check) ... ok
test_responsive_header_and_no_color (__main__.WrapperTests.test_responsive_header_and_no_color) ... ok
test_server_and_connect_completion_contexts (__main__.WrapperTests.test_server_and_connect_completion_contexts) ... ok
test_setup_checks_working_override_without_changes (__main__.WrapperTests.test_setup_checks_working_override_without_changes) ... ok
test_stdin_pipe_passes_through (__main__.WrapperTests.test_stdin_pipe_passes_through) ... ok
test_term_signal_cleans_proxy_and_direct_child (__main__.WrapperTests.test_term_signal_cleans_proxy_and_direct_child) ... ok
test_unknown_commands_are_passthrough_and_run_bypasses_reserved_names (__main__.WrapperTests.test_unknown_commands_are_passthrough_and_run_bypasses_reserved_names) ... ok
test_zsh_actual_tab_completion_in_owned_pty (__main__.WrapperTests.test_zsh_actual_tab_completion_in_owned_pty) ... ok
test_zsh_completion_candidates_with_real_zsh (__main__.WrapperTests.test_zsh_completion_candidates_with_real_zsh) ... ok

======================================================================
FAIL: test_auth_notice_after_tty_exit_preserves_status_and_filters_old_errors (__main__.WrapperTests.test_auth_notice_after_tty_exit_preserves_status_and_filters_old_errors)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/data/data/com.termux/files/home/repos/codex-termux/tests/test_wrapper.py", line 115, in test_auth_notice_after_tty_exit_preserves_status_and_filters_old_errors
    status, output = self.run_tty(args, env)
                     ~~~~~~~~~~~~^^^^^^^^^^^
  File "/data/data/com.termux/files/home/repos/codex-termux/tests/test_wrapper.py", line 101, in run_tty
    self.fail('wrapper TTY fixture did not finish')
    ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: wrapper TTY fixture did not finish

======================================================================
FAIL: test_auth_notice_honors_codex_home_and_wrapper_log_configuration (__main__.WrapperTests.test_auth_notice_honors_codex_home_and_wrapper_log_configuration)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/data/data/com.termux/files/home/repos/codex-termux/tests/test_wrapper.py", line 176, in test_auth_notice_honors_codex_home_and_wrapper_log_configuration
    status, output = self.run_tty(['chatgpt'], {**self.env, 'CODEX_HOME': str(home), 'FIXTURE_AUTH_LOG': str(log)})
                     ~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/data/data/com.termux/files/home/repos/codex-termux/tests/test_wrapper.py", line 101, in run_tty
    self.fail('wrapper TTY fixture did not finish')
    ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: wrapper TTY fixture did not finish

======================================================================
FAIL: test_cached_update_prompt_decline_preserves_launch_and_no_update_suppresses_it (__main__.WrapperTests.test_cached_update_prompt_decline_preserves_launch_and_no_update_suppresses_it)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/data/data/com.termux/files/home/repos/codex-termux/tests/test_wrapper.py", line 561, in test_cached_update_prompt_decline_preserves_launch_and_no_update_suppresses_it
    self.assertIn(b'"args":[]', output)
    ~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^
AssertionError: b'"args":[]' not found in b'codex-termux: Codex 0.999.0 is available (active 0.153.4).\r\nInstall the update before starting Codex? [y/N] n\r\n'

======================================================================
FAIL: test_console_group_ctrl_c_reaches_child_and_cleans_proxy (__main__.WrapperTests.test_console_group_ctrl_c_reaches_child_and_cleans_proxy)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/data/data/com.termux/files/home/repos/codex-termux/tests/test_wrapper.py", line 406, in test_console_group_ctrl_c_reaches_child_and_cleans_proxy
    self.assertTrue(ready.exists())
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^
AssertionError: False is not true

----------------------------------------------------------------------
Ran 33 tests in 107.129s

FAILED (failures=4)
```
