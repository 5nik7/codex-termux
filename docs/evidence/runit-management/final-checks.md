# Final checks after documentation and archive assertions

2026-10-28 UTC, native Termux, owned fixtures only.

```text
+ python3 tools/build.py --check
Generated files and package checksums match source.
exit: 0
+ git diff --check

exit: 0
+ zsh -n completions/_codex-termux

exit: 0
+ python3 -B tools/check_docs.py
Documentation links passed: 58 local targets (fragments not checked).
exit: 0
+ python3 -B tests/test_wrapper.py WrapperTests.test_configuration_is_literal_and_cli_overrides_env WrapperTests.test_generated_completions_match_source WrapperTests.test_bash_actual_tab_completion_in_owned_pty WrapperTests.test_zsh_actual_tab_completion_in_owned_pty
test_configuration_is_literal_and_cli_overrides_env (__main__.WrapperTests.test_configuration_is_literal_and_cli_overrides_env) ... ok
test_generated_completions_match_source (__main__.WrapperTests.test_generated_completions_match_source) ... ok
test_bash_actual_tab_completion_in_owned_pty (__main__.WrapperTests.test_bash_actual_tab_completion_in_owned_pty) ... ok
test_zsh_actual_tab_completion_in_owned_pty (__main__.WrapperTests.test_zsh_actual_tab_completion_in_owned_pty) ... ok

----------------------------------------------------------------------
Ran 4 tests in 2.106s

OK
exit: 0
+ python3 -B tests/test_release.py
test_archive_parity_and_extracted_source_installation (__main__.ReleaseTests.test_archive_parity_and_extracted_source_installation) ... ok
test_rejects_wrong_tag_and_existing_output_without_overwriting (__main__.ReleaseTests.test_rejects_wrong_tag_and_existing_output_without_overwriting) ... ok
test_repeatable_assets_and_both_checksum_manifests (__main__.ReleaseTests.test_repeatable_assets_and_both_checksum_manifests) ... ok

----------------------------------------------------------------------
Ran 3 tests in 5.879s

OK
exit: 0
+ python3 /data/data/com.termux/files/home/.codex/skills/.system/skill-creator/scripts/quick_validate.py /data/data/com.termux/files/home/.codex/skills/codex-termux-development
Skill is valid!
exit: 0
+ python3 /data/data/com.termux/files/home/.codex/skills/.system/skill-creator/scripts/quick_validate.py /data/data/com.termux/files/home/.codex/skills/codex-termux-service-management
Skill is valid!
exit: 0
+ git diff --exit-code -- docs/history docs/evidence/0.3.0 docs/evidence/0.3.1 docs/evidence/0.4.0 docs/evidence/managed-server

exit: 0
```
