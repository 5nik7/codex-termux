#!/data/data/com.termux/files/usr/bin/bash
# Generated standalone package tool. Source: src/package.sh; format version 1.
set -Eeuo pipefail
umask 077

readonly PACKAGE_TOOL_VERSION=0.3.0
readonly PACKAGE_DEFAULT_ACTION=uninstall
readonly PACKAGE_RELEASES=https://github.com/5nik7/codex-termux/releases
readonly PACKAGE_FORMAT=codex-termux-package-1
readonly PACKAGE_SCRIPT_PATH=${BASH_SOURCE[0]:-}
readonly -a PACKAGE_ASSETS=(codex-termux codex-termux.bash codex-termux.zsh codex-termux.1 install.sh uninstall.sh README.md CHANGELOG.md config.example LICENSE VERSION)
readonly -a PACKAGE_SOURCES=(bin/codex-termux completions/codex-termux.bash completions/_codex-termux man/codex-termux.1 install.sh uninstall.sh README.md CHANGELOG.md config.example LICENSE VERSION)
readonly -a PACKAGE_LINKS=(bin/codex-termux share/bash-completion/completions/codex-termux share/zsh/site-functions/_codex-termux share/man/man1/codex-termux.1 share/doc/codex-termux/README.md share/doc/codex-termux/CHANGELOG.md share/doc/codex-termux/config.example share/doc/codex-termux/LICENSE)
readonly -a PACKAGE_TARGETS=(codex-termux codex-termux.bash codex-termux.zsh codex-termux.1 README.md CHANGELOG.md config.example LICENSE)
package_action=$PACKAGE_DEFAULT_ACTION package_prefix=${PREFIX:-} package_source='' package_remote=0
package_yes=0 package_check=0 package_dry=0 package_repair=0 package_recover=0 package_color=auto
package_requested='' package_version='' package_installed='' package_root='' package_current=''
package_tmp='' package_lock='' package_transaction='' package_active=0 package_owned=0
package_reset='' package_cyan='' package_green='' package_yellow='' package_red='' package_dim=''
declare -A package_hashes=()

package_line() { printf '%s\n' "$*"; }
package_note() { printf '%s[info]%s %s\n' "$package_cyan" "$package_reset" "$*" >&2; }
package_die() { printf '%s[error]%s %s\n' "$package_red" "$package_reset" "$*" >&2; exit 1; }
package_usage_error() { printf 'codex-termux package: %s\n' "$*" >&2; exit 2; }
package_valid_version() { [[ $1 =~ ^(0|[1-9][0-9]{0,7})\.(0|[1-9][0-9]{0,7})\.(0|[1-9][0-9]{0,7})$ ]]; }
package_newer() {
  local -a first second; local i
  IFS=. read -r -a first <<<"$1"; IFS=. read -r -a second <<<"$2"
  for i in 0 1 2; do
    ((10#${first[i]} > 10#${second[i]})) && return 0
    ((10#${first[i]} < 10#${second[i]})) && return 1
  done
  return 1
}
package_style() {
  case $package_color in auto|always|never) ;; *) package_usage_error '--color requires auto, always, or never' ;; esac
  if [[ $package_color == always || ( $package_color == auto && -t 1 && -z ${NO_COLOR+x} && ${TERM:-dumb} != dumb ) ]]; then
    package_reset=$'\e[0m'; package_cyan=$'\e[1;36m'; package_green=$'\e[1;32m'
    package_yellow=$'\e[1;33m'; package_red=$'\e[1;31m'; package_dim=$'\e[2m'
  fi
}
package_heading() { printf '\n%s< codex (termux) >%s\n%s%s%s\n\n' "$package_cyan" "$package_reset" "$package_dim" "$1" "$package_reset"; }
package_row() {
  local label_color=$package_green
  [[ $1 != --* && $1 != -h* ]] || label_color=$package_yellow
  printf '  %s%-15s%s %s\n' "$label_color" "$1" "$package_reset" "$2"
}
package_help() {
  package_heading "Wrapper package manager $PACKAGE_TOOL_VERSION"
  if [[ $package_action == install ]]; then
    package_row 'Install/update' 'bash install.sh [OPTIONS]'
    package_row '--source DIR' 'Install the built local checkout/source bundle.'
    package_row '--remote' 'Use GitHub Releases, even from a checkout.'
    package_row '--version X.Y.Z' 'Select a published stable wrapper release.'
    package_row '--check' 'Compare versions only; do not install.'
    package_row '--repair' 'Recreate missing managed links at the same version.'
    package_row '--recover' 'Restore a pending interrupted package transaction.'
  else
    package_row 'Uninstall' 'bash uninstall.sh [OPTIONS]'
  fi
  package_row '--prefix DIR' 'Existing owned prefix; defaults to Termux $PREFIX.'
  package_row '--dry-run' 'Show the proposed operation without changing the prefix.'
  package_row '--yes' 'Explicitly authorize installation/removal/recovery.'
  package_row '--color MODE' 'auto | always | never (also honors NO_COLOR).'
  package_row '-h, --help' 'Show this help.'
  package_line ''
  if [[ $package_action == install ]]; then
    package_line 'Local checkouts are detected beside install.sh; otherwise use Releases.'
  fi
  package_line 'Prompts read /dev/tty, including curl/wget piped into Bash.'
  package_line 'Codex npm runtimes, credentials, and shell configuration are preserved.'
}
package_confirm() {
  ((package_yes)) && return 0
  local answer fd
  if ! { exec {fd}<>/dev/tty; } 2>/dev/null; then
    package_die 'a terminal is required for confirmation; use --yes only after reviewing the operation'
  fi
  printf '%s%s [y/N]%s ' "$package_yellow" "$1" "$package_reset" >&"$fd"
  IFS= read -r answer <&"$fd" || answer=''
  exec {fd}>&-
  [[ $answer == y || $answer == Y || $answer == yes || $answer == YES ]]
}
package_regular() {
  [[ -f $1 && ! -L $1 && -r $1 ]] || package_die 'expected a readable, nonsymlink regular package file'
  local size; size=$(stat -c %s -- "$1")
  ((size <= ${2:-2097152})) || package_die 'package file exceeds the size limit'
}
package_read_version() {
  local text extra
  package_regular "$1" 64
  { IFS= read -r text && ! IFS= read -r extra && [[ -z $extra ]]; } <"$1" || package_die 'malformed VERSION file'
  package_valid_version "$text" || package_die 'VERSION must contain one stable numeric version'
  package_version=$text
}
package_digest() { local sum; sum=$(sha256sum <"$1"); printf '%s' "${sum%% *}"; }
package_parents() {
  local relative=$1 parent=$package_prefix part
  local -a pieces; IFS=/ read -r -a pieces <<<"${relative%/*}"
  for part in "${pieces[@]}"; do
    parent=$parent/$part
    [[ ! -L $parent ]] || package_die 'refusing a symlink in a destination parent directory'
    [[ ! -e $parent || -d $parent ]] || package_die 'destination parent is not a directory'
  done
}
package_fingerprint() {
  local file=$1 sum
  if [[ -L $file ]]; then sum=$(readlink -- "$file" | sha256sum); printf 'link:%s' "${sum%% *}"
  elif [[ -f $file ]]; then printf 'file:%s' "$(package_digest "$file")"
  elif [[ -e $file ]]; then printf special
  else printf absent; fi
}
package_validate_prefix() {
  [[ $package_prefix == /* && -d $package_prefix && ! $package_prefix =~ [[:cntrl:]] ]] || package_die '--prefix must be an existing absolute directory without control characters'
  package_prefix=$(cd -P -- "$package_prefix" && pwd)
  case $package_prefix in /|/usr|/usr/local|/bin|/etc|/var) package_die 'refusing a shared system prefix; use Termux or a private owned directory' ;; esac
  [[ $(stat -c %u -- "$package_prefix") == "$(id -u)" && -w $package_prefix ]] || package_die 'prefix must be owned and writable by the current user'
  package_root=$package_prefix/libexec/codex-termux
  package_parents libexec/codex-termux/format
  [[ ! -L $package_root && ( ! -e $package_root || -d $package_root ) ]] || package_die 'invalid package state directory'
}
package_load_installed() {
  local candidate_version=$package_version
  package_owned=0; package_installed=''; package_current=''
  if [[ -e $package_root/format || -L $package_root/format ]]; then
    package_regular "$package_root/format" 64
    [[ $(<"$package_root/format") == "$PACKAGE_FORMAT" ]] || package_die 'unknown installation ownership format'
    package_owned=1
    [[ ! -L $package_root/releases && ! -L $package_root/backups ]] || package_die 'invalid state subdirectory'
    if [[ -e $package_root/pending || -L $package_root/pending ]]; then
      ((package_recover)) || package_die 'an interrupted package transaction is retained; review it, then run install.sh --recover'
    fi
    if [[ -L $package_root/current ]]; then
      package_current=$(readlink -- "$package_root/current")
      [[ $package_current =~ ^releases/([0-9]+\.[0-9]+\.[0-9]+)\.[A-Za-z0-9]{8}$ ]] || package_die 'invalid current package pointer'
      package_regular "$package_root/$package_current/VERSION" 64
      package_read_version "$package_root/$package_current/VERSION"; package_installed=$package_version
      [[ $package_current == releases/"$package_installed".* && ! -L $package_root/releases && ! -L $package_root/$package_current ]] || package_die 'package pointer identity mismatch'
    elif [[ -e $package_root/current ]]; then package_die 'current package pointer is not a symlink'; fi
  elif [[ -e $package_root ]]; then
    package_die 'package directory exists without an ownership record; retain it for manual review'
  fi
  if [[ -z $package_installed && -e $package_prefix/bin/codex-termux ]]; then
    # Inspect a known header as text. Never execute an existing candidate to
    # determine its version before the user authorizes an installation.
    local line limit=0 file=$package_prefix/bin/codex-termux
    [[ -f $file ]] || package_die 'existing command is not a regular script'
    while IFS= read -r line; do
      ((limit+=1)); ((limit <= 20)) || break
      if [[ $line =~ ^readonly[[:space:]]WRAPPER_VERSION=([0-9]+\.[0-9]+\.[0-9]+)$ ]]; then package_installed=${BASH_REMATCH[1]}; break; fi
      if [[ $line =~ ^readonly[[:space:]]VERSION=\"([0-9]+\.[0-9]+\.[0-9]+)\"$ ]]; then package_installed=${BASH_REMATCH[1]}; break; fi
    done <"$file"
    [[ -n $package_installed ]] || package_die 'existing codex-termux has an unknown version; keep it and inspect it manually'
    package_valid_version "$package_installed" || package_die 'invalid existing wrapper version'
  fi
  package_version=$candidate_version
}
package_download() {
  local url=$1 destination=$2
  if command -v curl >/dev/null 2>&1; then
    curl -q --fail --location --silent --show-error --globoff --proto '=https' --proto-redir '=https' --max-redirs 5 --max-filesize 2097152 --connect-timeout 10 --max-time 90 --retry 1 --output "$destination" "$url"
  elif command -v wget >/dev/null 2>&1; then
    wget --no-config --no-netrc --no-cookies --hsts-file "$package_tmp/wget-hsts" --https-only --max-redirect=5 --timeout=30 --tries=2 -q -O "$destination" "$url"
  else package_die 'curl or wget is required to download releases'; fi
}
package_manifest() {
  local dir=$1 line hash name i count=0
  local -A allowed=() seen=()
  for name in "${PACKAGE_ASSETS[@]}"; do allowed[$name]=1; done
  package_regular "$dir/SHA256SUMS" 4096
  package_hashes=()
  while IFS= read -r line || [[ -n $line ]]; do
    [[ $line =~ ^([a-f0-9]{64})\ \ ([A-Za-z0-9._-]+)$ ]] || package_die 'malformed checksum manifest'
    hash=${BASH_REMATCH[1]}; name=${BASH_REMATCH[2]}
    [[ -n ${allowed[$name]+yes} && -z ${seen[$name]+yes} ]] || package_die 'unknown or duplicate checksum member'
    seen[$name]=1; package_hashes[$name]=$hash; ((count+=1))
  done <"$dir/SHA256SUMS"
  ((count == ${#PACKAGE_ASSETS[@]})) || package_die 'checksum manifest is incomplete'
  for name in "${PACKAGE_ASSETS[@]}"; do
    package_regular "$dir/$name"
    [[ $(package_digest "$dir/$name") == "${package_hashes[$name]}" ]] || package_die "checksum mismatch: $name"
  done
  local expected=$package_version
  package_read_version "$dir/VERSION"
  [[ $package_version == "$expected" ]] || package_die 'downloaded release version changed during resolution'
  # Bash-only syntax checks: no release file is executed before activation.
  for name in codex-termux install.sh uninstall.sh codex-termux.bash; do bash -n "$dir/$name"; done
  local marker=''; while IFS= read -r line; do
    if [[ $line == readonly\ WRAPPER_VERSION=* ]]; then marker=${line#*=}; break; fi
  done <"$dir/codex-termux"
  [[ $marker == "$package_version" ]] || package_die 'wrapper and package versions disagree'
}
package_fetch_payload() {
  local i asset
  mkdir -- "$package_tmp/payload"
  if [[ -n $package_source ]]; then
    package_regular "$package_source/PACKAGE-SHA256SUMS" 4096
    cp -- "$package_source/PACKAGE-SHA256SUMS" "$package_tmp/payload/SHA256SUMS"
    for i in "${!PACKAGE_ASSETS[@]}"; do
      package_regular "$package_source/${PACKAGE_SOURCES[i]}"
      cp -- "$package_source/${PACKAGE_SOURCES[i]}" "$package_tmp/payload/${PACKAGE_ASSETS[i]}"
    done
  else
    package_download "$PACKAGE_RELEASES/download/v$package_version/SHA256SUMS" "$package_tmp/payload/SHA256SUMS"
    for asset in "${PACKAGE_ASSETS[@]}"; do
      package_download "$PACKAGE_RELEASES/download/v$package_version/$asset" "$package_tmp/payload/$asset"
    done
  fi
  package_manifest "$package_tmp/payload"
}
package_validate_links() {
  local i dest target
  for i in "${!PACKAGE_LINKS[@]}"; do
    package_parents "${PACKAGE_LINKS[i]}"
    dest=$package_prefix/${PACKAGE_LINKS[i]}; target=$package_root/current/${PACKAGE_TARGETS[i]}
    if [[ -e $dest || -L $dest ]]; then
      [[ -f $dest || -L $dest ]] || package_die 'refusing a directory or special file at an installation destination'
      if ((package_owned)) && [[ -n $package_current ]]; then
        [[ -L $dest && $(readlink -- "$dest") == "$target" ]] || package_die "managed entry was changed; retain and review: ${PACKAGE_LINKS[i]}"
      fi
    fi
  done
}
package_acquire() {
  mkdir -p -- "$package_prefix/libexec"
  package_lock=$package_prefix/libexec/.codex-termux-package.lock
  if ! mkdir -m 700 -- "$package_lock" 2>/dev/null; then
    package_lock=''; package_die 'another package operation may be running; do not remove its lock without review'
  fi
  # Revalidate after locking: another invocation may have completed while the
  # user was reading the confirmation prompt.
  local previous=$package_installed previous_current=$package_current
  package_load_installed
  [[ $previous == "$package_installed" && $previous_current == "$package_current" ]] || package_die 'installation changed while awaiting confirmation; run the command again'
  ((package_recover)) || package_validate_links
}
package_begin() {
  [[ ! -L $package_root/backups && ! -L $package_root/releases ]] || package_die 'invalid package state subdirectory'
  mkdir -p -- "$package_root/backups" "$package_root/releases"
  chmod 700 -- "$package_root" "$package_root/backups" "$package_root/releases"
  [[ ! -L $package_root/backups && ! -L $package_root/releases ]] || package_die 'invalid package state subdirectory'
  printf '%s\n' "$PACKAGE_FORMAT" >"$package_root/format"
  package_transaction=$(mktemp -d "$package_root/backups/tx.XXXXXXXX")
  mkdir -- "$package_transaction/links"
  local i dest
  for i in "${!PACKAGE_LINKS[@]}"; do
    dest=$package_prefix/${PACKAGE_LINKS[i]}
    if [[ -e $dest || -L $dest ]]; then cp -aP -- "$dest" "$package_transaction/links/$i"; fi
  done
  if [[ -L $package_root/current ]]; then cp -P -- "$package_root/current" "$package_transaction/current"; fi
  printf '%s\n' "${package_transaction##*/}" >"$package_root/pending"
  package_active=1
}
package_restore() {
  local transaction=$1 i dest before current expected temp
  [[ -d $transaction/links && ! -L $transaction && ! -L $transaction/links ]] || return 1
  # Refuse to overwrite an unrelated edit made after an interrupted operation.
  for i in "${!PACKAGE_LINKS[@]}"; do
    package_parents "${PACKAGE_LINKS[i]}"
    dest=$package_prefix/${PACKAGE_LINKS[i]}; before=$transaction/links/$i
    current=$(package_fingerprint "$dest") || return 1
    if [[ $current != absent && $current != "$(package_fingerprint "$before")" ]]; then
      [[ -L $dest && $(readlink -- "$dest") == "$package_root/current/${PACKAGE_TARGETS[i]}" ]] || return 1
    fi
  done
  for i in "${!PACKAGE_LINKS[@]}"; do
    dest=$package_prefix/${PACKAGE_LINKS[i]}; before=$transaction/links/$i
    if [[ -e $before || -L $before ]]; then
      temp=$(mktemp "${dest%/*}/.codex-termux-restore.XXXXXXXX") || return 1
      cp -aP --remove-destination -- "$before" "$temp" || return 1
      mv -fT -- "$temp" "$dest" || return 1
    else rm -f -- "$dest" || return 1; fi
  done
  if [[ -L $transaction/current ]]; then
    temp=$package_root/.current-restore-$$
    [[ ! -e $temp && ! -L $temp ]] || return 1
    cp -P -- "$transaction/current" "$temp" || return 1
    mv -fT -- "$temp" "$package_root/current" || return 1
  else rm -f -- "$package_root/current" || return 1; fi
  rm -f -- "$package_root/pending" || return 1
  package_active=0
}
package_cleanup() {
  local status=$?
  trap - EXIT INT TERM HUP
  if ((package_active)); then
    if package_restore "$package_transaction"; then
      package_note 'the incomplete operation was rolled back; original entries were restored'
    else
      package_note 'recovery is incomplete; backups and pending state were retained'
      package_note 'review the prefix, then use install.sh --recover'
      status=1
    fi
  fi
  if [[ -n $package_lock ]]; then rmdir -- "$package_lock" 2>/dev/null || true; fi
  if [[ -n $package_tmp ]]; then rm -rf -- "$package_tmp"; fi
  exit "$status"
}
package_apply_install() {
  package_begin
  local version_dir i dest temp
  version_dir=$(mktemp -d "$package_root/releases/$package_version.XXXXXXXX")
  cp -- "$package_tmp/payload/"* "$version_dir/"
  chmod 644 -- "$version_dir/"*
  chmod 755 -- "$version_dir/codex-termux" "$version_dir/install.sh" "$version_dir/uninstall.sh"
  # Existing installations already have all stable links. Initial adoption also
  # snapshots any standalone wrapper/completion/man files before replacement.
  for i in "${!PACKAGE_LINKS[@]}"; do
    dest=$package_prefix/${PACKAGE_LINKS[i]}
    mkdir -p -- "${dest%/*}"
    if [[ -L $dest && $(readlink -- "$dest") == "$package_root/current/${PACKAGE_TARGETS[i]}" ]]; then continue; fi
    temp=$(mktemp "${dest%/*}/.codex-termux-link.XXXXXXXX")
    rm -- "$temp"
    ln -s -- "$package_root/current/${PACKAGE_TARGETS[i]}" "$temp"
    mv -fT -- "$temp" "$dest"
  done
  temp=$(mktemp "$package_root/.current.XXXXXXXX")
  rm -- "$temp"
  ln -s -- "releases/${version_dir##*/}" "$temp"
  mv -fT -- "$temp" "$package_root/current"
  rm -- "$package_root/pending"
  package_active=0
  printf '\n%s[done]%s codex-termux %s installed.\n' "$package_green" "$package_reset" "$package_version"
  package_line "Backups retained: $package_transaction"
  package_line 'Next: codex-termux --help | man codex-termux'
  package_line 'Fresh Termux: codex-termux setup, then codex-termux login'
}
package_apply_uninstall() {
  package_begin
  local relative
  for relative in "${PACKAGE_LINKS[@]}"; do rm -f -- "$package_prefix/$relative"; done
  rm -- "$package_root/current"
  rm -- "$package_root/pending"
  package_active=0
  printf '\n%s[done]%s Wrapper command, completions, manual, and documentation links removed.\n' "$package_green" "$package_reset"
  package_line 'Codex npm runtimes, credentials, configuration, and shell startup are unchanged.'
  package_line "Recovery copies and package history retained: $package_root"
}
package_main() {
  local flag source_explicit=0 prefix_explicit=0 here i
  local -A seen=()
  while (($#)); do
    flag=$1; shift
    case $flag in -h|--help) package_style; package_help; return ;; esac
    [[ $flag =~ ^--[a-z-]+$ && -z ${seen[$flag]+yes} ]] || package_usage_error 'invalid or repeated package option'
    seen[$flag]=1
    case $flag in
      --yes) package_yes=1 ;; --check) package_check=1 ;; --dry-run) package_dry=1 ;;
      --repair) package_repair=1 ;; --recover) package_recover=1 ;; --remote) package_remote=1 ;;
      --source|--prefix|--version|--color)
        (($#)) && [[ -n $1 ]] || package_usage_error "$flag requires a value"
        case $flag in
          --source) package_source=$1; source_explicit=1 ;;
          --prefix) package_prefix=$1; prefix_explicit=1 ;;
          --version) package_requested=$1; package_remote=1 ;;
          --color) package_color=$1 ;;
        esac; shift ;;
      *) package_usage_error 'unknown package option' ;;
    esac
  done
  (( ! source_explicit || ! package_remote )) || package_usage_error '--source cannot be combined with --remote/--version'
  (( ! package_check || (! package_repair && ! package_yes && ! package_recover && ! package_dry) )) || package_usage_error '--check cannot be combined with mutation options'
  if [[ $package_action == uninstall ]]; then
    (( ! source_explicit && ! package_remote && ! package_repair && ! package_check && ! package_recover )) || package_usage_error 'uninstall accepts only --prefix, --dry-run, --yes, and --color'
  fi
  (( ! package_recover || (! source_explicit && ! package_remote && ! package_repair && ! package_check) )) || package_usage_error '--recover cannot install or download a package'
  [[ -z $package_requested ]] || package_valid_version "$package_requested" || package_usage_error '--version must be X.Y.Z'
  package_style
  for flag in sha256sum stat id readlink mktemp cp mv ln rm rmdir mkdir chmod dirname bash; do command -v "$flag" >/dev/null 2>&1 || package_die "required utility missing: $flag"; done
  package_validate_prefix
  local temp_base=${TMPDIR:-${PREFIX:+$PREFIX/tmp}}; temp_base=${temp_base:-/tmp}
  package_tmp=$(mktemp -d "$temp_base/codex-termux-package.XXXXXXXX") || package_die 'cannot create private temporary directory; check TMPDIR'
  trap package_cleanup EXIT
  trap 'exit 130' INT; trap 'exit 143' TERM; trap 'exit 129' HUP
  package_load_installed
  if ((package_recover)); then
    [[ -f $package_root/pending && ! -L $package_root/pending ]] || { package_line 'No interrupted package transaction found.'; return; }
    local transaction; transaction=$(<"$package_root/pending")
    [[ $transaction =~ ^tx\.[A-Za-z0-9]{8}$ ]] || package_die 'invalid recovery record'
    package_heading 'Recover interrupted wrapper operation'
    package_line "Backup: $package_root/backups/$transaction"
    (( ! package_dry )) || return 0
    package_confirm 'Restore the recorded package entries?' || { package_line 'Cancelled. Nothing changed.'; return; }
    package_acquire
    package_restore "$package_root/backups/$transaction" || package_die 'recovery refused a conflicting edit; backups are intact'
    package_line 'Recovery completed.'; return
  fi
  if [[ $package_action == uninstall ]]; then
    [[ -n $package_current ]] || { package_line 'No package-managed installation found. Standalone files were preserved.'; return; }
    package_validate_links
    package_heading "Uninstall codex-termux $package_installed"
    for flag in "${PACKAGE_LINKS[@]}"; do package_row 'remove' "$flag"; done
    package_line 'Credentials, configuration, npm runtimes, and recovery copies stay intact.'
    (( ! package_dry )) || { package_line 'Preview only. Nothing changed.'; return; }
    package_confirm 'Uninstall these wrapper package files?' || { package_line 'Cancelled. Nothing changed.'; return; }
    package_acquire; package_apply_uninstall; return
  fi
  if [[ -z $package_source && -f $PACKAGE_SCRIPT_PATH ]] && (( ! package_remote )); then
    here=$(cd -P -- "$(dirname -- "$PACKAGE_SCRIPT_PATH")" && pwd)
    if [[ -f $here/VERSION && -f $here/bin/codex-termux ]]; then package_source=$here; fi
  fi
  if [[ -n $package_source ]]; then
    [[ -d $package_source ]] || package_die 'source directory is missing'
    package_source=$(cd -P -- "$package_source" && pwd)
    package_read_version "$package_source/VERSION"
  elif [[ -n $package_requested ]]; then package_version=$package_requested
  else
    package_download "$PACKAGE_RELEASES/latest/download/VERSION" "$package_tmp/VERSION"
    package_read_version "$package_tmp/VERSION"
  fi
  package_heading 'Install / update wrapper package'
  package_row Installed "${package_installed:-not installed}"
  package_row Available "$package_version"
  if [[ $package_installed == "$package_version" ]] && (( ! package_repair )); then
    package_line 'Already at this version. Nothing changed. Use --repair for missing managed links.'; return
  fi
  if [[ -n $package_installed && $package_installed != "$package_version" ]] && ! package_newer "$package_version" "$package_installed"; then
    package_line 'Installed version is newer. No downgrade performed.'; return
  fi
  (( ! package_check )) || { package_line 'A wrapper package installation/update is available. Nothing installed.'; return; }
  package_validate_links
  for flag in "${PACKAGE_LINKS[@]}"; do package_row install "$flag"; done
  (( ! package_dry )) || { package_line 'Preview only. Nothing changed.'; return; }
  package_fetch_payload
  package_confirm "Install verified codex-termux $package_version and these files?" || { package_line 'Cancelled. Nothing changed.'; return; }
  package_acquire; package_apply_install
}

# No mutation occurs until this final invocation; download the complete script
# before running it when you want to inspect the bootstrap bytes first.
package_main "$@"
