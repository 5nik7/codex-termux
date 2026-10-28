# Remaining suites and isolated server rerun

The isolated server test and all runit tests passed. The package suite reported
one fixture timeout at its unchanged twelve-second limit.

```text
test_connect_ctrl_c_continuation_term_and_piped_stdin (__main__.ServerTests.test_connect_ctrl_c_continuation_term_and_piped_stdin) ... ok

----------------------------------------------------------------------
Ran 1 test in 13.025s

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
Ran 14 tests in 25.388s

OK
test_adopts_standalone_without_executing_it_and_backs_up_original (__main__.PackageTests.test_adopts_standalone_without_executing_it_and_backs_up_original) ... ok
test_bad_checksums_manifest_and_source_symlinks_never_touch_prefix (__main__.PackageTests.test_bad_checksums_manifest_and_source_symlinks_never_touch_prefix) ... ok
test_check_preview_and_no_tty_do_not_install (__main__.PackageTests.test_check_preview_and_no_tty_do_not_install) ... ok
test_destination_parent_symlink_and_fifo_are_refused_without_opening (__main__.PackageTests.test_destination_parent_symlink_and_fifo_are_refused_without_opening) ... ok
test_equal_version_noop_leaves_every_prefix_entry_unchanged (__main__.PackageTests.test_equal_version_noop_leaves_every_prefix_entry_unchanged) ... ok
test_failed_initial_install_restores_original_entries (__main__.PackageTests.test_failed_initial_install_restores_original_entries) ... ok
test_failed_update_preserves_previous_current_pointer (__main__.PackageTests.test_failed_update_preserves_previous_current_pointer) ... ok
test_fresh_local_install_all_components_without_node (__main__.PackageTests.test_fresh_local_install_all_components_without_node) ... ok
test_installed_wrapper_delegates_uninstall_without_node (__main__.PackageTests.test_installed_wrapper_delegates_uninstall_without_node) ... ok
test_interrupted_install_is_detected_and_can_be_explicitly_recovered (__main__.PackageTests.test_interrupted_install_is_detected_and_can_be_explicitly_recovered) ... ok
test_legacy_symlink_target_is_not_modified (__main__.PackageTests.test_legacy_symlink_target_is_not_modified) ... ok
test_lock_refusal_does_not_change_existing_installation (__main__.PackageTests.test_lock_refusal_does_not_change_existing_installation) ... ok
test_missing_link_can_be_repaired_but_modified_entry_is_retained (__main__.PackageTests.test_missing_link_can_be_repaired_but_modified_entry_is_retained) ... ok
test_newer_version_switches_pointer_and_preserves_previous_payload (__main__.PackageTests.test_newer_version_switches_pointer_and_preserves_previous_payload) ... ok
test_older_version_never_downgrades (__main__.PackageTests.test_older_version_never_downgrades) ... ok
test_package_help_semantic_colors_and_plain_output (__main__.PackageTests.test_package_help_semantic_colors_and_plain_output) ... ok
test_partial_uninstall_failure_restores_all_public_entries (__main__.PackageTests.test_partial_uninstall_failure_restores_all_public_entries) ... ok
test_piped_install_resolves_remote_without_source_filename (__main__.PackageTests.test_piped_install_resolves_remote_without_source_filename) ... ok
test_piped_script_uses_controlling_terminal_for_decline_and_accept (__main__.PackageTests.test_piped_script_uses_controlling_terminal_for_decline_and_accept) ... ok
test_remote_check_fetches_only_version_and_remote_install_pins_all_assets (__main__.PackageTests.test_remote_check_fetches_only_version_and_remote_install_pins_all_assets) ... ERROR
test_remote_corrupt_asset_fails_before_install (__main__.PackageTests.test_remote_corrupt_asset_fails_before_install) ... ok
test_state_subdirectory_symlink_is_refused_before_chmod (__main__.PackageTests.test_state_subdirectory_symlink_is_refused_before_chmod) ... ok
test_uninstall_only_owned_entries_and_keep_user_state (__main__.PackageTests.test_uninstall_only_owned_entries_and_keep_user_state) ... ok
test_uninstall_preview_and_modified_entry_refusal (__main__.PackageTests.test_uninstall_preview_and_modified_entry_refusal) ... ok
test_uninstaller_preserves_unmanaged_standalone (__main__.PackageTests.test_uninstaller_preserves_unmanaged_standalone) ... ok
test_wget_fallback_without_curl (__main__.PackageTests.test_wget_fallback_without_curl) ... ok
test_wrapper_color_is_inherited_and_package_flag_can_override_it (__main__.PackageTests.test_wrapper_color_is_inherited_and_package_flag_can_override_it) ... ok
test_wrapper_package_help_delegates_without_node (__main__.PackageTests.test_wrapper_package_help_delegates_without_node) ... ok

======================================================================
ERROR: test_remote_check_fetches_only_version_and_remote_install_pins_all_assets (__main__.PackageTests.test_remote_check_fetches_only_version_and_remote_install_pins_all_assets)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/data/data/com.termux/files/home/repos/codex-termux/tests/test_package.py", line 322, in test_remote_check_fetches_only_version_and_remote_install_pins_all_assets
    result = self.run_tool('--remote', '--yes')
  File "/data/data/com.termux/files/home/repos/codex-termux/tests/test_package.py", line 72, in run_tool
    result = subprocess.run([BASH, str(ROOT / ('uninstall.sh' if uninstall else 'install.sh')), '--prefix', str(self.prefix), *args], env=env or self.env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=12, start_new_session=True)
  File "/data/data/com.termux/files/usr/lib/python3.14/subprocess.py", line 557, in run
    stdout, stderr = process.communicate(input, timeout=timeout)
                     ~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^
  File "/data/data/com.termux/files/usr/lib/python3.14/subprocess.py", line 1221, in communicate
    stdout, stderr = self._communicate(input, endtime, timeout)
                     ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/data/data/com.termux/files/usr/lib/python3.14/subprocess.py", line 2152, in _communicate
    self._check_timeout(endtime, orig_timeout, stdout, stderr)
    ~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/data/data/com.termux/files/usr/lib/python3.14/subprocess.py", line 1268, in _check_timeout
    raise TimeoutExpired(
    ...<2 lines>...
            stderr=b''.join(stderr_seq) if stderr_seq else None)
subprocess.TimeoutExpired: Command '['/data/data/com.termux/files/usr/bin/bash', '/data/data/com.termux/files/home/repos/codex-termux/install.sh', '--prefix', '/data/data/com.termux/files/usr/tmp/codex-termux-package-test-1re54tv6/prefix space 雪', '--remote', '--yes']' timed out after 12 seconds

----------------------------------------------------------------------
Ran 28 tests in 163.623s

FAILED (errors=1)
```
