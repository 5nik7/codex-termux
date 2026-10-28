# Final checks

Commands run after final behavior, help wording, documentation, and archive
assertions were complete:

```bash
python3 tools/build.py --check
python3 /data/data/com.termux/files/home/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/codex-termux-cli-consistency
python3 -B tools/check_docs.py
git diff --check
python3 -B tests/test_release.py
```

All exited 0. Output:

```text
Generated files and package checksums match source.
Skill is valid!
Documentation links passed: 90 local targets (fragments not checked).
test_archive_parity_and_extracted_source_installation (__main__.ReleaseTests.test_archive_parity_and_extracted_source_installation) ... ok
test_rejects_wrong_tag_and_existing_output_without_overwriting (__main__.ReleaseTests.test_rejects_wrong_tag_and_existing_output_without_overwriting) ... ok
test_repeatable_assets_and_both_checksum_manifests (__main__.ReleaseTests.test_repeatable_assets_and_both_checksum_manifests) ... ok
test_repo_skill_links_are_checked (__main__.ReleaseTests.test_repo_skill_links_are_checked) ... ok

----------------------------------------------------------------------
Ran 4 tests in 6.508s

OK
```

Source archive tests include the shared UI, presentation regressions, coverage
matrix, repo skill, and new verification evidence. Extracted-source installation
and reproducible ZIP/tar/checksum parity passed. The installed payload manifest
remains at 11 entries.

The validation sentence, this transcript and JSON metadata/hashes were finalized
after those tests. Final syntax, generated-byte, link, whitespace, source-hash
and preservation checks passed afterward. All 35 earlier evidence/history files
are byte-identical to their pre-task hashes.

groff remains unavailable, so manual rendering is skipped. The full 129-test
run and subsequent 27 focused passes are separate records. Test deadlines were
not relaxed. No live service, account, installation, or publication was used.
