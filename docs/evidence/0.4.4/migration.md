# Published 0.4.3 to 0.4.4 manual migration

Run natively on Termux on 2026-11-18 using owned temporary HOME, PREFIX, and
TMPDIR directories. Reconstructed the 11 payloads and checksum manifest from
the local published `v0.4.3` Git tag, then installed with that version's helper.
No network or real account was used. An unrelated manual ensured an existing
mandoc database, so the old missing-entry warning was observable.

The installed 0.4.3 wrapper ran `manage self-update --source <0.4.4 checkout>
--yes`. Its old helper installed 0.4.4 but retained the old manual layout. The
installed 0.4.4 wrapper then ran `manage self-update --source <0.4.4 checkout>
--repair --yes`. Plain-name manual lookup and whatis used only the fixture's
man directory. All 11 selected payload hashes matched the new source assets.
The original public link, previous payload bytes, and unrelated manual were
preserved, and no pending record or package lock remained.

```text
Published 0.4.3 installer: old warning reproduced.
Installed 0.4.3 helper upgraded to 0.4.4; one-time layout repair is needed.
Installed 0.4.4 helper repair: man/whatis have no warnings; all 11 assets match.
Original public link, old payload, and unrelated manual preserved; no lock/pending state.
```
