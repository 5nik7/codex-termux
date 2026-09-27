# Release codex-termux

## Current local candidate: 0.4.0

VERSION is now 0.4.0 on `feat/managed-app-server`. Read the
[release notes](docs/releases/v0.4.0.md) and [validation record](VALIDATION.md).
This is an opt-in managed WebSocket workaround; the upstream Unix-socket daemon
is not repaired. Preserve the documented Android process-lifetime and manual
recovery limits.

Owner-run native Termux acceptance used Codex CLI 0.157.1 and the corrected
feature candidate whose wrapper VERSION was still 0.3.1. Its artifact identity
and acceptance are recorded in
[owner acceptance](docs/evidence/managed-server/owner-acceptance.md).
The independent [Linux review report](docs/evidence/managed-server/reviewer-report.md)
is reported evidence, not a local execution log. Later 0.4.0 verification has
its own evidence directory; never relabel the older candidate as 0.4.0.

From the candidate checkout:

```bash
python3 tools/build.py
python3 tools/build.py --check
python3 -B tools/verify.py
git diff --check
# Finalize documentation and evidence before building the distributable assets:
python3 -B tools/release.py --tag v0.4.0
```

The last command validates VERSION and builds local assets. It creates no Git
tag and uploads nothing. The default output is `dist/v0.4.0`; if it already
exists, supply a new `--output dist/v0.4.0-review-N` directory. Never overwrite
previous output or published 0.3.1 assets. From the chosen asset directory, run:

```bash
sha256sum -c SHA256SUMS
sha256sum -c RELEASE-SHA256SUMS
```

Expect 15 files: 11 allowed package payloads, `SHA256SUMS`, both 0.4.0 source
archives, and `RELEASE-SHA256SUMS`. The installer manifest has 11 members; the
release manifest has 14 and also covers both source archives and `SHA256SUMS`.
Verify the source archive includes `tests/test_server.py`, the smoke tool,
`docs/releases/v0.4.0.md`, current evidence, and all historical evidence,
including **both** files in `docs/history/managed-server-2026-09-26/`.
Those history files were omitted from the earlier manually assembled review
archive; that partial archive must not be reused.

For review, copy the generated full source tarball and export tracked changes
with `git diff --binary HEAD --`. That patch includes staged and unstaged tracked
changes but omits untracked new files; the full source archive must contain them.
Include branch, HEAD, status, diff summary, untracked paths, results/skips, output
directory, and archive/patch hashes in the review information file. All intended
new files, including both history files, belong in the eventual commit review.
Leave this candidate uncommitted until separately authorized.

The opt-in `tools/native_server_smoke.py --runtime /absolute/existing/runtime`
uses temporary account/config roots and fake credentials. It does not install or
modify the selected runtime and never sends a model request. It supplements the
offline verifier; it does not replace owner-run account and shell acceptance.
It was not rerun during 0.4.0 release preparation.

Installation, commits, pushing, merging, tagging, publication, and remote release
edits require separate task authorization. The tag workflow creates a draft;
local `--tag v0.4.0` is only validation. Keep the installed wrapper, selected npm
runtime, live authentication/configuration, shell settings, coding session, and
external port 4500 server intact during local preparation.

## Historical 0.3.1 candidate guidance

The following records the earlier candidate procedure and its then-outstanding
checks; it is not the current 0.4.0 release procedure.

The authentication-notice patch is prepared as 0.3.1. Review
`docs/releases/v0.3.1.md` and the new section of `VALIDATION.md` first.
Native Termux recognition of real diagnostic records remains to be checked;
Linux fixtures alone are not sufficient evidence for that claim.

From the reviewed candidate checkout, run:

```bash
python3 tools/build.py --check
python3 -B tools/verify.py
git diff --check
python3 -B tools/release.py --tag v0.3.1
```

The last command builds assets locally; it does not create a tag or publish.
Review and merge the intended commit, then obtain task authorization for tag
push and release publication. Use a new `v0.3.1` tag and all its generated
assets. Preserve the published `v0.3.0` tag and assets. Do not replay the old
patch application or tag commands below.

## Historical 0.3.0 shipping walkthrough

These steps update the repository, test on your phone, and publish the wrapper
package. They do not publish a new OpenAI Codex npm release. Nothing in the
provided changes has been committed, pushed, tagged, or published for you.

## 1. Apply the supplied patch in a fresh checkout

Download `codex-termux-0.3.0-update.patch`. Put it in a known readable location
in Termux. The following example uses `$HOME/storage/downloads`; if Android
saved it somewhere else, change only that path. Work inside Termux private
storage, not shared Android storage.

```bash
mkdir -p "$HOME/repos"
git clone https://github.com/5nik7/codex-termux.git \
  "$HOME/repos/codex-termux-release-0.3.0"
cd "$HOME/repos/codex-termux-release-0.3.0"
git switch -c feat/package-lifecycle

git apply --check "$HOME/storage/downloads/codex-termux-0.3.0-update.patch"
git apply "$HOME/storage/downloads/codex-termux-0.3.0-update.patch"
git diff --check
git status --short
```

Run each block only after the previous command succeeds. The patch was prepared
against `main` commit `1f9e155b8c1e64e7c1ec374cde89a187a96ee5a9`. If the check
fails because the repository has changed, resolve the patch in this new branch;
do not reset another checkout or force it over existing edits. A separate
source ZIP is also supplied for browsing/testing without a Git checkout.

## 2. Verify the source on Termux

```bash
python3 -B tools/verify.py
```

This needs the development tools Bash/coreutils, Node.js, Python 3, and Zsh for
the real Zsh cases. The manual render check additionally uses groff if available.
Missing Zsh/groff are reported as skips; CI installs those test-only tools.
The verifier does not install dependencies, use real credentials, access the npm
registry, or modify the real installed wrapper. It uses disposable fixtures.

Generated files and the package checksum manifest are already included. If you
edit source, completions, the manual template, README, or CHANGELOG, regenerate
and then rerun the relevant checks:

```bash
python3 tools/build.py
python3 -B tools/verify.py
```

## 3. Try the package on your phone

Check which command is currently selected, inspect the proposed paths, and
install with the interactive confirmation:

```bash
type -a codex-termux
bash bin/codex-termux --wrapper-version
bash install.sh --source . --dry-run
bash install.sh --source .
hash -r
codex-termux --wrapper-version
codex-termux --help
codex-termux run --version
man codex-termux
```

The wrapper version should be **0.3.0**. The Codex version need not change. Keep
the printed package backup path. If `man` is not installed, you can still inspect
`man/codex-termux.1`; a pager is optional and is not installed automatically.

In your current Zsh, after the usual completion initialization:

```zsh
source "$PREFIX/share/zsh/site-functions/_codex-termux"
```

Try `codex-termux manage self<Tab>`, then confirm your existing working login:

```bash
codex-termux --wrapper-no-update test
codex-termux --wrapper-no-update chatgpt
```

Reuse your normal explicitly chosen Codex sandbox/approval flags when needed;
the wrapper does not change them. No new login is needed if the stored login
already works. Test interactive input, Ctrl+C handling, and a normal response.

Check the no-op and removal preview without uninstalling your working command:

```bash
bash install.sh --source .
codex-termux manage uninstall --dry-run
```

The second install should say the version is already current. Add the actual
phone results and tool versions to `VALIDATION.md` and
`docs/releases/v0.3.0.md`; distinguish successful checks from skipped ones.
Do not claim fresh-device setup unless tested on a fresh installation.

## 4. Commit, push a feature branch, and merge a PR

From the fresh checkout, which should contain only this reviewed change:

```bash
git diff --check
git add -A
git diff --cached --stat
git commit -m "Add wrapper package lifecycle, manual, and richer help"
git push -u origin HEAD:refs/heads/feat/package-lifecycle
```

The full refspec pins the remote destination. If you already use SSH for GitHub
and HTTPS push authentication is unavailable, set only this checkout's push URL
before pushing:

```bash
git remote set-url --push origin git@github.com:5nik7/codex-termux.git
```

Open the [PR creation page](https://github.com/5nik7/codex-termux/compare/main...feat/package-lifecycle?expand=1).
Use this title:

> Add wrapper package install/update/uninstall and manual

Suggested description:

> Adds colored help, a man page, and local/remote package management for the
> wrapper, Bash/Zsh completions, and manual. Uses version-pinned assets,
> checksum validation, confirmation prompts, backups, and guarded uninstall.
> Keeps Codex npm updates and existing launch/authentication behavior separate.
> Includes offline regressions, reproducible packaging, CI, and a draft-release
> workflow. Native Termux smoke-test results are recorded in VALIDATION.md.

Review the diff and wait for the **Verify** workflow to pass, then merge the PR.
The release workflow is not triggered by merging alone.

## 5. Tag the merged version

```bash
git fetch --no-recurse-submodules --refmap= origin \
  refs/heads/main:refs/remotes/origin/main
git switch main
git merge --ff-only origin/main
git status --short
cat VERSION
python3 tools/build.py --check
```

The tree should be clean and VERSION should contain `0.3.0`. Then:

```bash
git tag -a v0.3.0 -m "codex-termux 0.3.0"
git push origin refs/tags/v0.3.0:refs/tags/v0.3.0
```

Do not reuse an existing published tag or force-push tags. A later correction
gets a new patch version. No `--tags` or direct `main` push is needed here.

## 6. Review and publish the draft

Open the repository's [Actions page](https://github.com/5nik7/codex-termux/actions)
and wait for **Draft release** to finish. It reruns offline tests, checks the
tag against VERSION, builds assets, and creates a **draft**, not a public release.
Only the draft job receives repository write permission. It uses the built-in
GitHub Actions token; no personal token belongs in the repository.

Open [Releases](https://github.com/5nik7/codex-termux/releases). Review the draft
notes and these **15 attached assets**:

```text
codex-termux                codex-termux.bash
codex-termux.zsh            codex-termux.1
install.sh                 uninstall.sh
README.md                  CHANGELOG.md
config.example             LICENSE
VERSION                    SHA256SUMS
codex-termux-0.3.0.zip      codex-termux-0.3.0.tar.gz
RELEASE-SHA256SUMS
```

`SHA256SUMS` is intentionally limited to the 11 runtime/manual/doc assets;
the installer rejects unknown members. `RELEASE-SHA256SUMS` also covers the
source archives and the smaller manifest. Keep those roles distinct.

If you download the assets into one directory, verify there:

```bash
sha256sum -c RELEASE-SHA256SUMS
sha256sum -c SHA256SUMS
```

After reviewing the native phone results and the files, publish the draft as
the latest stable release. Do not mark it as a prerelease. The `/latest/download`
URLs start working for public users only after publication.

## 7. Confirm the published update path

```bash
codex-termux manage self-update --check
codex-termux manage self-update
```

If you installed 0.3.0 locally, both should report that it is current. No payload
needs reinstalling. To validate the actual hosted downloads without touching
your normal command, use a disposable **existing** prefix:

```bash
trial_prefix="$(mktemp -d "${TMPDIR:-$PREFIX/tmp}/codex-termux-release-smoke.XXXXXXXX")"
bash install.sh --remote --version 0.3.0 --prefix "$trial_prefix"
bash "$trial_prefix/bin/codex-termux" --wrapper-version
bash uninstall.sh --prefix "$trial_prefix"
```

This leaves only private package history/backups in the printed trial directory;
review/remove that specific test-owned directory after the checks. Do not delete
your real prefix or a shared temporary directory. The published URL check cannot
be completed before this release exists.

## Manual fallback if Actions release creation is disabled

From the verified, tagged checkout:

```bash
python3 -B tools/release.py --tag v0.3.0
```

The new output directory is `dist/v0.3.0`. Existing output is not overwritten;
use `--output` with a new directory if rebuilding for comparison. Create a draft
release in GitHub for the already-pushed `v0.3.0` tag, paste
`docs/releases/v0.3.0.md`, and attach **all 15 files** from that directory. Do not
upload only GitHub's automatically generated source archive.

If your local GitHub CLI is authenticated, the equivalent is:

```bash
gh release create v0.3.0 dist/v0.3.0/* --verify-tag --draft \
  --title "codex-termux v0.3.0" --notes-file docs/releases/v0.3.0.md
```

This does not require repairing a ChatGPT GitHub connector. Use the GitHub web
interface when `gh` authentication is unavailable.

## Later versions

Update VERSION once, edit changelog/release notes, rebuild, verify, review/merge,
then tag that exact version. Keep the installer manifest and all assets together.
Do not replace files under an already published version: equal-version clients
correctly perform no update. `.github/workflows/release.yml` validates tag/version
agreement and refuses an existing release through `gh release create`.

References: [GitHub CLI release creation](https://cli.github.com/manual/gh_release_create),
[GitHub latest release definition](https://docs.github.com/en/rest/releases/releases#get-the-latest-release),
[pinned checkout action](https://github.com/actions/checkout/tree/d23441a48e516b6c34aea4fa41551a30e30af803).
