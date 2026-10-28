# Final local release checks: 0.4.2

After adding the new validation evidence and source-archive assertions, all four
release tests passed. Production sources were unchanged after the full 133-test
verifier run. Documentation checking passed 90 local targets; generated-file
and package checksum checks and git diff --check passed.

All 42 pre-existing evidence/history files remained byte-identical to their
pre-release snapshot. Historical 0.4.1 notes match the published v0.4.1 tag.
The locally built release contains 15 files, and both sha256sum -c checks passed:
11 package payloads and 14 release-manifest entries. Final evidence is included
in a fresh release build before commit. Hosted verification and publication
are separate from these local results.

```text
test_archive_parity_and_extracted_source_installation (__main__.ReleaseTests.test_archive_parity_and_extracted_source_installation) ... ok
test_rejects_wrong_tag_and_existing_output_without_overwriting (__main__.ReleaseTests.test_rejects_wrong_tag_and_existing_output_without_overwriting) ... ok
test_repeatable_assets_and_both_checksum_manifests (__main__.ReleaseTests.test_repeatable_assets_and_both_checksum_manifests) ... ok
test_repo_skill_links_are_checked (__main__.ReleaseTests.test_repo_skill_links_are_checked) ... ok

----------------------------------------------------------------------
Ran 4 tests in 6.565s

OK
```
