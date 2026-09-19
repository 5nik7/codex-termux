#!/data/data/com.termux/files/usr/bin/bash
# Generated standalone release; edit src/ and run python3 tools/build.py.
set -Eeuo pipefail

readonly PROGRAM=${0##*/}
readonly WRAPPER_VERSION=@@VERSION@@
runtime_dir='' proxy_pid='' child_pid='' proxy_url='' node_bin='' ca_bundle=''
codex_kind='' codex_launcher='' installed_version='' selected_runtime=system previous_runtime=-
color=auto banner=auto auto_update=ask update_interval=86400 proxy_connect_timeout=10000
proxy_allow='' codex_bin='' configured_ca='' debug=0 no_update=0 config_disabled=0
config_file='' data_dir='' cache_dir='' arch='' pending_cache='' original_action=''
config_explicit=0
auth_notice=auto auth_log='' auth_monitor_log=''
declare -a codex_command=() prefix_args=()
reset='' bold='' accent='' muted='' command_color='' option_color='' description_color='' heading_color=''

say() { printf '%s\n' "$*"; }
emit() { local row; while IFS= read -r row; do printf '%s\n' "$row"; done; }
note() { printf '%s: %s\n' "$PROGRAM" "$*" >&2; }
die() { note "error: $*"; exit 1; }
usage_error() { note "error: $*"; exit 2; }
trace() { if ((debug)); then note "debug: $*"; fi; }
is_termux() { [[ -n ${TERMUX_VERSION:-} || ${PREFIX:-} == /data/data/*/files/usr ]]; }
require_termux() {
  is_termux || die 'this command is intended for native Termux'
  [[ -n ${PREFIX:-} && -d $PREFIX/bin ]] || die 'Termux PREFIX is unavailable'
}
stable_version() { [[ $1 =~ ^(0|[1-9][0-9]{0,7})\.(0|[1-9][0-9]{0,7})\.(0|[1-9][0-9]{0,7})$ ]]; }
has_control() { [[ $1 =~ [[:cntrl:]] ]]; }

configure() {
  local line key value count=0
  local -A seen=()
  config_file=${config_file:-${CODEX_TERMUX_CONFIG:-${XDG_CONFIG_HOME:-${HOME:?HOME is required}/.config}/codex-termux/config}}
  if ((config_explicit && ! config_disabled)) && [[ ! -f $config_file ]]; then die 'explicit configuration file is missing or not regular'; fi
  if (( ! config_disabled )) && [[ -e $config_file || -L $config_file ]]; then
    [[ -f $config_file && -r $config_file ]] || die 'configuration must be a readable regular file'
    # Literal data only: no sourcing, expansion, eval, or command substitution.
    while IFS= read -r line || [[ -n $line ]]; do
      count=$((count + ${#line} + 1)); ((count <= 16384)) || die 'configuration exceeds 16 KiB'
      [[ -z $line || $line == \#* ]] && continue
      has_control "$line" && die 'control characters are not permitted in configuration'
      [[ $line == *=* ]] || die 'configuration requires literal key=value lines'
      key=${line%%=*}; value=${line#*=}
      [[ $key =~ ^[a-z_]+$ ]] || die 'invalid configuration key'
      [[ -z ${seen[$key]+yes} ]] || die 'duplicate configuration key'
      seen[$key]=1
      case $key in
        color|banner|auto_update|update_interval|proxy_connect_timeout|proxy_allow|codex_bin|auth_notice|auth_log) printf -v "$key" '%s' "$value" ;;
        ca_bundle) configured_ca=$value ;;
        *) die 'unknown configuration key' ;;
      esac
    done <"$config_file"
  fi
  color=${CODEX_TERMUX_COLOR-$color}; banner=${CODEX_TERMUX_BANNER-$banner}
  auto_update=${CODEX_TERMUX_AUTO_UPDATE-$auto_update}
  update_interval=${CODEX_TERMUX_UPDATE_INTERVAL-$update_interval}
  proxy_connect_timeout=${CODEX_TERMUX_PROXY_CONNECT_TIMEOUT-$proxy_connect_timeout}
  proxy_allow=${CODEX_TERMUX_PROXY_ALLOW-$proxy_allow}
  codex_bin=${CODEX_TERMUX_CODEX_BIN-$codex_bin}
  configured_ca=${CODEX_TERMUX_CA_BUNDLE-$configured_ca}
  auth_notice=${CODEX_TERMUX_AUTH_NOTICE-$auth_notice}
  auth_log=${CODEX_TERMUX_AUTH_LOG-${auth_log:-${CODEX_HOME:-$HOME/.codex}/log/codex-tui.log}}
  data_dir=${CODEX_TERMUX_DATA_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/codex-termux}
  cache_dir=${CODEX_TERMUX_CACHE_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/codex-termux}
  local i=0
  while ((i < ${#prefix_args[@]})); do
    key=${prefix_args[i]}; value=${prefix_args[i+1]}; i=$((i+2))
    case $key in color) color=$value ;; banner) banner=$value ;; esac
  done
  case $color in auto|always|never) ;; *) usage_error 'color must be auto, always, or never' ;; esac
  case $banner in auto|always|never) ;; *) usage_error 'banner must be auto, always, or never' ;; esac
  case $auto_update in ask|notify|off) ;; *) die 'auto_update must be ask, notify, or off' ;; esac
  case $auth_notice in auto|off) ;; *) die 'auth_notice must be auto or off' ;; esac
  [[ $update_interval =~ ^[0-9]{1,7}$ ]] && ((10#$update_interval >= 3600 && 10#$update_interval <= 2592000)) || die 'update_interval must be 3600..2592000 seconds'
  [[ $proxy_connect_timeout =~ ^[0-9]{1,6}$ ]] && ((10#$proxy_connect_timeout >= 1000 && 10#$proxy_connect_timeout <= 120000)) || die 'proxy_connect_timeout must be 1000..120000 milliseconds'
  update_interval=$((10#$update_interval)); proxy_connect_timeout=$((10#$proxy_connect_timeout))
  for value in "$data_dir" "$cache_dir"; do
    [[ $value == /* && $value != / ]] && ! has_control "$value" || die 'data/cache paths must be absolute and contain no control characters'
  done
  for value in "$codex_bin" "$configured_ca"; do
    [[ -z $value || $value == /* ]] && ! has_control "$value" || die 'executable/CA overrides must be absolute literal paths'
  done
  [[ $auth_log == /* && $auth_log != / ]] && ! has_control "$auth_log" || die 'auth_log must be an absolute literal path'
  ((no_update)) && auto_update=off
  if [[ $color == always || ( $color == auto && -t 1 && -z ${NO_COLOR+x} && ${TERM:-dumb} != dumb ) ]]; then
    reset=$'\e[0m'; bold=$'\e[1m'; accent=$'\e[1;36m'; muted=$'\e[2m'
    command_color=$'\e[1;32m'; option_color=$'\e[1;33m'
    description_color=$'\e[37m'; heading_color=$'\e[1;35m'
  fi
}

header() {
  [[ $banner == never ]] && return 0
  [[ $banner == always || -t 1 ]] || return 0
  local width=${COLUMNS:-0} row
  [[ $width =~ ^[0-9]{1,4}$ ]] || width=0
  if ((width == 0)) && [[ -t 1 ]] && command -v stty >/dev/null 2>&1; then
    read -r row width < <(stty size 2>/dev/null) || width=0
  fi
  ((width > 0)) || width=40
  if ((width >= 54)); then
    printf '%s' "$accent"
    printf '%s\n' '                _' '  ___ ___   __| | _____  __' ' / __/ _ \ / _` |/ _ \ \/ /' '| (_| (_) | (_| |  __/>  <' ' \___\___/ \__,_|\___/_/\_\' '             (termux)'
    printf '%s\n\n' "$reset"
  elif ((width >= 18)); then
    printf '%s< codex (termux) >%s\n\n' "$accent" "$reset"
  elif ((width >= 14)); then
    printf '%scodex (termux)%s\n\n' "$accent" "$reset"
  else
    printf '%scodex\n(termux)%s\n\n' "$accent" "$reset"
  fi
}
help_row() {
  local style=$1 label=$2 description=$3
  printf '  %s%-27s%s %s%s%s\n' "$style" "$label" "$reset" "$description_color" "$description" "$reset"
}
usage() {
  header
  printf '%sUsage%s\n' "$heading_color" "$reset"
  printf '  %s%s%s %s[CODEX_ARGUMENTS...]%s\n' "$command_color" "$PROGRAM" "$reset" "$option_color" "$reset"
  printf '  %s%s chatgpt%s [CODEX_ARGUMENTS...]\n' "$command_color" "$PROGRAM" "$reset"
  printf '  %s%s completion%s bash|zsh\n' "$command_color" "$PROGRAM" "$reset"
  printf '\n%sCommands%s\n' "$heading_color" "$reset"
  help_row "$command_color" run 'Launch Codex (default).'
  help_row "$command_color" chatgpt 'Launch without API-key variables.'
  help_row "$command_color" login 'ChatGPT device login by default.'
  help_row "$command_color" login-api 'Use OPENAI_API_KEY on stdin.'
  help_row "$command_color" status 'Show Codex authentication status.'
  help_row "$command_color" logout 'Remove stored Codex credentials.'
  help_row "$command_color" doctor 'Codex doctor --all, or supplied options.'
  help_row "$command_color" test 'Check DNS, proxy/TLS, and Doctor.'
  help_row "$command_color" 'setup [--yes] [--version V]' 'Prepare fresh Termux dependencies.'
  help_row "$command_color" manage 'Check, update, roll back, or uninstall.'
  help_row "$command_color" completion 'Emit Bash or Zsh completion.'
  printf '\n%sWrapper options%s (before the command)\n' "$heading_color" "$reset"
  help_row "$option_color" '-h, --help' 'This help.'
  help_row "$option_color" '--wrapper-version' 'Wrapper version; no Node startup.'
  help_row "$option_color" '--wrapper-info [--json]' 'Local runtime information.'
  help_row "$option_color" '--wrapper-dry-run' 'Describe run/chatgpt; launch nothing.'
  help_row "$option_color" '--wrapper-no-update' 'Disable automatic npm checks/prompts.'
  help_row "$option_color" '--wrapper-color MODE' 'auto | always | never'
  help_row "$option_color" '--wrapper-banner MODE' 'auto | always | never'
  help_row "$option_color" '--wrapper-config PATH' 'Literal key=value configuration.'
  help_row "$option_color" '--wrapper-no-config' 'Ignore the configuration file.'
  help_row "$option_color" '--wrapper-debug' 'Fixed diagnostic events on stderr.'
  printf '\n%sMaintenance%s\n' "$heading_color" "$reset"
  help_row "$command_color" 'manage check [--json]' 'Local prerequisite checks.'
  help_row "$command_color" 'manage auth-check [--json]' 'Inspect saved MCP token-expiry errors.'
  help_row "$command_color" 'manage update [--check]' 'Update the Codex npm runtime.'
  help_row "$option_color" '  --check [--json]' 'Check npm updates without installing.'
  help_row "$option_color" '  [--yes] [--version X.Y.Z]' 'Authorize/pin npm installation.'
  help_row "$command_color" 'manage rollback' 'Restore the previous npm runtime.'
  help_row "$command_color" 'manage self-update [--check]' 'Update this wrapper package.'
  help_row "$command_color" 'manage uninstall [--dry-run]' 'Remove wrapper package files.'
  help_row "$option_color" '  --help' 'Show the package tool options.'
  help_row "$command_color" 'manage config show|example' 'Inspect wrapper configuration.'
  printf '\n%sManual%s\n' "$heading_color" "$reset"
  help_row "$command_color" 'man codex-termux' 'Commands, package tools, and examples.'
  printf '\n%sNotes%s\n' "$heading_color" "$reset"
  say "  --version remains Codex's version (not the wrapper)."
  say '  Unknown commands/options pass through unchanged.'
  say '  Use run COMMAND to bypass wrapper command names.'
  say '  Auto-checks run in the background on eligible TUI launches.'
  say '  A cached update is offered at a later launch; default is No.'
  say '  Eligible TUI exits show hints for newly logged token expiry.'
  say '  Auth hints use existing logs; they never log out for you.'
  say '  No sandbox, approval, model, or auth settings are rewritten.'
}

find_ca_bundle() {
  local candidate
  if [[ -n $configured_ca ]]; then
    [[ -f $configured_ca && -r $configured_ca && -s $configured_ca ]] || return 1
    ca_bundle=$configured_ca; return 0
  fi
  for candidate in "$PREFIX/etc/tls/cert.pem" "$PREFIX/etc/ssl/cert.pem" "$PREFIX/etc/ssl/certs/ca-certificates.crt"; do
    if [[ -f $candidate && -r $candidate && -s $candidate ]]; then ca_bundle=$candidate; return 0; fi
  done
  return 1
}
resolve_node() { node_bin=$(type -P node || true); [[ -n $node_bin && -x $node_bin ]]; }
get_arch() {
  case $(uname -m) in aarch64|arm64) arch=arm64 ;; x86_64|amd64) arch=x64 ;; *) die 'only native ARM64 and x64 are supported' ;; esac
}
read_selection() {
  selected_runtime=system; previous_runtime=-
  local file=$data_dir/selection extra schema
  [[ -e $file || -L $file ]] || return 0
  [[ -f $file && ! -L $file && -r $file ]] || die 'invalid managed selection file'
  { IFS= read -r schema && IFS= read -r selected_runtime && IFS= read -r previous_runtime && ! IFS= read -r extra && [[ -z $extra ]]; } <"$file" || die 'invalid managed selection contents'
  [[ $schema == 1 && ( $selected_runtime == system || $selected_runtime =~ ^v[0-9]+\.[0-9]+\.[0-9]+-[a-f0-9]{16}$ ) &&
     ( $previous_runtime == - || $previous_runtime == system || $previous_runtime =~ ^v[0-9]+\.[0-9]+\.[0-9]+-[a-f0-9]{16}$ ) ]] || die 'invalid managed selection values'
}
resolve_codex() {
  codex_command=(); codex_launcher=''; codex_kind=''; installed_version=''
  if [[ -n $codex_bin ]]; then
    [[ -f $codex_bin && -x $codex_bin ]] || return 1
    codex_command=("$codex_bin"); codex_kind=override; return 0
  fi
  read_selection
  local launcher candidate
  if [[ $selected_runtime != system ]]; then
    launcher=$data_dir/runtimes/$selected_runtime/node_modules/@openai/codex/bin/codex.js
    [[ -f $launcher && -r $launcher ]] || die 'selected managed runtime is missing; use manage rollback'
    codex_launcher=$launcher; codex_command=("$node_bin" "$launcher"); codex_kind=managed
    installed_version=${selected_runtime#v}; installed_version=${installed_version%-*}; return 0
  fi
  launcher=$PREFIX/lib/node_modules/@openai/codex/bin/codex.js
  if [[ -f $launcher && -r $launcher ]]; then
    codex_launcher=$launcher; codex_command=("$node_bin" "$launcher"); codex_kind=system-npm; return 0
  fi
  candidate=$(type -P codex || true)
  [[ -n $candidate && -f $candidate && -x $candidate ]] || return 1
  [[ ! $candidate -ef $0 ]] || return 1
  codex_command=("$candidate"); codex_kind=system-path
}
require_runtime() {
  require_termux
  resolve_node || die "Node.js is required; run: $PROGRAM setup"
  resolve_codex || die "Codex is unavailable; run: $PROGRAM setup"
}
runtime() {
  local -a runner=()
  [[ $1 == proxy ]] && runner=(exec)
  NODE_OPTIONS='' NODE_PATH='' "${runner[@]}" "$node_bin" - "$@" <<'CODEX_TERMUX_NODE'
@@RUNTIME@@
CODEX_TERMUX_NODE
}
completion() {
  case ${1:-} in
    bash) emit <<'CODEX_TERMUX_BASH'
@@BASH_COMPLETION@@
CODEX_TERMUX_BASH
      ;;
    zsh) emit <<'CODEX_TERMUX_ZSH'
@@ZSH_COMPLETION@@
CODEX_TERMUX_ZSH
      ;;
    *) usage_error 'completion requires bash or zsh' ;;
  esac
}
config_example() {
  emit <<'CODEX_TERMUX_CONFIG'
# Literal values; do not quote or use $HOME, ~, or shell expressions.
# Omitted keys use defaults. This file is never sourced.
auto_update=ask
update_interval=86400
color=auto
banner=auto
proxy_connect_timeout=10000
auth_notice=auto
# auth_log=/absolute/path/to/codex-tui.log
# proxy_allow=example.com
# codex_bin=/absolute/path/to/codex
# ca_bundle=/absolute/path/to/cert.pem
CODEX_TERMUX_CONFIG
}
confirm() {
  local answer
  [[ -t 0 && -t 2 ]] || die 'confirmation requires a terminal; inspect the action and pass --yes to authorize it'
  printf '%s [y/N] ' "$1" >&2
  IFS= read -r answer || return 1
  [[ $answer == y || $answer == Y || $answer == yes || $answer == YES ]]
}
probe_version() {
  local result timeout_bin
  # --version is local; it needs no proxy and reads no credentials.
  timeout_bin=$(type -P timeout || true)
  [[ -n $timeout_bin ]] || return 1
  result=$("$timeout_bin" --kill-after=2 15 "${codex_command[@]}" --version 2>/dev/null) || return 1
  [[ $result =~ ^codex-cli[[:space:]]([0-9]+\.[0-9]+\.[0-9]+)$ ]] || return 1
  installed_version=${BASH_REMATCH[1]}
  stable_version "$installed_version"
}
info() {
  local mode=${1:-text} node_status=missing codex_status=missing ca_status=missing
  require_termux
  if resolve_node; then node_status=present; if resolve_codex && probe_version; then codex_status=working; fi; fi
  if find_ca_bundle; then ca_status=present; fi
  if [[ $mode == json ]]; then
    # Values are enums or validated versions; no arbitrary paths or env values.
    printf '{"schema_version":1,"wrapper_version":"%s","node":"%s","codex":"%s","codex_version":' "$WRAPPER_VERSION" "$node_status" "$codex_status"
    if [[ -n $installed_version ]]; then printf '"%s"' "$installed_version"; else printf null; fi
    printf ',"runtime":"%s","ca_bundle":"%s","auto_update":"%s"}\n' "${codex_kind:-none}" "$ca_status" "$auto_update"
  else
    header
    say "Wrapper: $WRAPPER_VERSION"
    say "Node: $node_status | Codex: $codex_status ${installed_version:-}"
    say "Runtime: ${codex_kind:-none} | CA bundle: $ca_status"
    say "Automatic updates: $auto_update (check interval ${update_interval}s)"
    say 'Updates require confirmation. Sandbox/approval settings are passed through.'
  fi
  [[ $node_status == present && $codex_status == working && $ca_status == present ]]
}
maintenance() {
  local action=${1:-help} requested=latest yes=0 check=0 json=0 option
  (($#)) && shift
  if [[ $action != self-update && $action != uninstall && $# == 1 && ( $1 == --help || $1 == -h ) ]]; then usage; return; fi
  case $action in
    help|-h|--help) (($# == 0)) || usage_error 'unexpected maintenance arguments'; usage; return ;;
    config)
      (($# <= 1)) || usage_error 'config accepts show or example'
      case ${1:-show} in
        example) config_example ;;
        show)
          printf 'auto_update=%s\nupdate_interval=%s\ncolor=%s\nbanner=%s\nproxy_connect_timeout=%s\n' "$auto_update" "$update_interval" "$color" "$banner" "$proxy_connect_timeout"
          printf 'auth_notice=%s\n' "$auth_notice"
          say '# Overrides: paths and additional hosts are omitted from this summary.' ;;
        *) usage_error 'config accepts show or example' ;;
      esac
      return ;;
    check)
      (($# == 0)) || [[ $# == 1 && $1 == --json ]] || usage_error 'check accepts only --json'
      info "${1:+json}"; return ;;
    auth-check)
      (($# == 0)) || [[ $# == 1 && $1 == --json ]] || usage_error 'auth-check accepts only --json'
      require_termux
      resolve_node || die "Node.js is required; run: $PROGRAM setup"
      runtime auth-check "$auth_log" "${1:+json}"; return ;;
    self-update|uninstall)
      package_tool "$action" "$@"; return ;;
    update|rollback) ;;
    *) usage_error 'unknown manage command' ;;
  esac
  local -A seen=()
  while (($#)); do
    option=$1; shift
    [[ $option =~ ^--[a-z]+$ ]] || usage_error 'unsupported maintenance option'
    [[ -z ${seen[$option]+yes} ]] || usage_error 'repeated maintenance option'; seen[$option]=1
    case $option in
      --yes) yes=1 ;;
      --check) check=1 ;;
      --json) json=1 ;;
      --version) (($#)) || usage_error '--version requires X.Y.Z'; requested=$1; shift; stable_version "$requested" || usage_error 'expected a stable version X.Y.Z' ;;
      *) usage_error 'unsupported maintenance option' ;;
    esac
  done
  if [[ $action == rollback ]]; then
    (( ! check && ! json )) && [[ $requested == latest ]] || usage_error 'rollback accepts only --yes'
  else
    (( ! json || check )) || usage_error '--json requires --check'
    (( ! check || ! yes )) && { (( ! check )) || [[ $requested == latest ]]; } || usage_error '--check cannot install or pin a version'
  fi
  require_termux
  [[ -z $codex_bin ]] || die 'an explicit Codex override is active; manage that installation separately'
  resolve_node || die "Node.js is required; run: $PROGRAM setup"
  get_arch
  if ((check)); then
    if resolve_codex; then probe_version || installed_version=''; fi
    local latest
    if ((json)); then runtime check-update "$cache_dir" "$arch" json "$installed_version"
    else
      latest=$(runtime check-update "$cache_dir" "$arch" text "$installed_version")
      say "Installed: ${installed_version:-unknown} | Latest: $latest"
      if [[ $installed_version == "$latest" ]]; then say 'Codex is up to date.'
      else say "To install: $PROGRAM manage update"; fi
    fi
    return
  fi
  if [[ $action == rollback ]]; then
    ((yes)) || confirm 'Validate and switch to the previous runtime?' || { note 'unchanged'; return 0; }
    runtime rollback "$data_dir" "$PREFIX/lib/node_modules/@openai/codex/bin/codex.js"
    return
  fi
  local npm_bin
  npm_bin=$(type -P npm || true); [[ -n $npm_bin ]] || die "npm is required; run: $PROGRAM setup"
  if [[ $requested == latest ]]; then
    requested=$(runtime check-update "$cache_dir" "$arch" text '')
  fi
  if resolve_codex && probe_version && [[ $installed_version == "$requested" ]]; then say "Codex $requested is already active."; return; fi
  ((yes)) || confirm "Install and validate Codex $requested in a separate runtime?" || { note 'unchanged'; return 0; }
  note "staging Codex $requested; the current runtime stays available"
  runtime install "$data_dir" "$arch" "$requested" "$npm_bin"
}
package_tool() {
  local operation=$1 helper own folder arg force_remote=1 explicit_color=0
  shift
  for arg in "$@"; do [[ $arg != --color ]] || explicit_color=1; done
  ((explicit_color)) || set -- --color "$color" "$@"
  own=$(readlink -f -- "${BASH_SOURCE[0]}") || die 'cannot locate the wrapper package helper'
  folder=${own%/*}
  if [[ $operation == uninstall ]]; then helper=uninstall.sh; else helper=install.sh; fi
  if [[ -f $folder/$helper ]]; then
    bash "$folder/$helper" "$@"
  elif [[ -f $folder/../$helper ]]; then
    # A development checkout can explicitly install its built source with
    # --source. Self-update itself always targets published releases.
    for arg in "$@"; do
      case $arg in --source|--remote|--version|--recover) force_remote=0 ;; esac
    done
    if [[ $operation == self-update ]] && ((force_remote)); then bash "$folder/../$helper" --remote "$@"
    else bash "$folder/../$helper" "$@"; fi
  else
    die 'package helper is unavailable; use the repository install.sh/uninstall.sh'
  fi
}
setup() {
  local yes=0 requested='' option npm_bin
  local -A seen=()
  local -a packages=()
  if [[ $# == 1 && ( $1 == --help || $1 == -h ) ]]; then usage; return; fi
  while (($#)); do
    option=$1; shift
    [[ $option =~ ^--[a-z]+$ ]] || usage_error 'unsupported setup option'
    [[ -z ${seen[$option]+yes} ]] || usage_error 'repeated setup option'; seen[$option]=1
    case $option in
      --yes) yes=1 ;;
      --version) (($#)) || usage_error '--version requires X.Y.Z'; requested=$1; shift; stable_version "$requested" || usage_error 'expected a stable version X.Y.Z' ;;
      *) usage_error 'setup accepts --yes and --version X.Y.Z' ;;
    esac
  done
  require_termux; get_arch
  # An override is a user-selected installation, never a reason to repair npm.
  if [[ -n $codex_bin ]]; then
    [[ -f $codex_bin && -x $codex_bin ]] || die 'the explicit Codex override is invalid; no packages changed'
    [[ -z $requested ]] || die '--version cannot replace an explicit Codex override'
    resolve_node || die 'Node.js is required with an override; install it explicitly or remove the override'
    resolve_codex && probe_version || die 'the explicit Codex override failed its version check; no packages changed'
    find_ca_bundle || die 'a working CA bundle is required; no packages changed'
    say "Override validated: Codex $installed_version. Nothing installed."; return
  fi
  command -v node >/dev/null 2>&1 || packages+=(nodejs)
  command -v npm >/dev/null 2>&1 || packages+=(npm)
  command -v curl >/dev/null 2>&1 || packages+=(curl)
  command -v git >/dev/null 2>&1 || packages+=(git)
  if ! find_ca_bundle; then
    [[ -z $configured_ca ]] || die 'the configured CA bundle is invalid; no packages changed'
    packages+=(ca-certificates)
  fi
  if ((${#packages[@]})); then
    command -v pkg >/dev/null 2>&1 || die 'Termux pkg is unavailable'
    note "missing Termux packages: ${packages[*]}"
    ((yes)) || confirm 'Install these packages with pkg?' || { note 'unchanged'; return 0; }
    pkg install -y "${packages[@]}"
    hash -r
  fi
  resolve_node || die 'Node.js is still unavailable'
  find_ca_bundle || die 'the CA bundle is still unavailable'
  npm_bin=$(type -P npm || true); [[ -n $npm_bin ]] || die 'npm is still unavailable'
  if [[ -z $requested ]] && resolve_codex && probe_version; then
    say "Setup checked: Codex $installed_version is working. Nothing reinstalled."
  else
    local -a args=(update)
    [[ -z $requested ]] || args+=(--version "$requested")
    (( ! yes )) || args+=(--yes)
    maintenance "${args[@]}"
    resolve_codex && probe_version || die 'setup did not produce a working Codex runtime'
    say "Setup checked: Codex $installed_version is working."
  fi
  say "Next: $PROGRAM test, then $PROGRAM login, then $PROGRAM chatgpt"
}

cleanup() {
  local status=$?
  trap - EXIT INT TERM HUP
  if [[ -n $proxy_pid ]]; then
    kill "$proxy_pid" 2>/dev/null || true
    wait "$proxy_pid" 2>/dev/null || true
  fi
  if [[ -n $runtime_dir ]]; then
    rm -f -- "$runtime_dir/proxy.log" "$runtime_dir/auth-state"
    rmdir -- "$runtime_dir" 2>/dev/null || true
  fi
  exit "$status"
}
interrupted() {
  local signal=$1 code=$2
  trap '' INT TERM HUP
  if [[ -n $child_pid ]]; then
    kill -s "$signal" "$child_pid" 2>/dev/null || true
    # Only the wrapper-owned direct child; no process-tree or PID-scanning kills.
    wait "$child_pid" 2>/dev/null || true
  fi
  exit "$code"
}
start_proxy() {
  local temp_base=${TMPDIR:-$PREFIX/tmp} ready_fd write_fd
  mkdir -p -- "$temp_base"
  runtime_dir=$(mktemp -d "$temp_base/codex-termux.XXXXXXXX") || die 'could not create runtime directory'
  chmod 700 "$runtime_dir"
  : >"$runtime_dir/proxy.log"; chmod 600 "$runtime_dir/proxy.log"
  trap cleanup EXIT
  trap ':' INT
  trap 'interrupted TERM 143' TERM
  trap 'interrupted HUP 129' HUP
  coproc CT_PROXY {
    unset OPENAI_API_KEY CODEX_API_KEY CODEX_ACCESS_TOKEN NODE_OPTIONS NODE_PATH
    runtime proxy "$proxy_allow" "$proxy_connect_timeout" "$pending_cache" "$arch" "$auth_monitor_log" "$runtime_dir/auth-state" 2>"$runtime_dir/proxy.log"
  }
  proxy_pid=$CT_PROXY_PID; ready_fd=${CT_PROXY[0]}; write_fd=${CT_PROXY[1]}
  local port
  if ! IFS= read -r -t 5 -u "$ready_fd" port; then die 'the local proxy did not become ready within five seconds'; fi
  exec {ready_fd}<&-; exec {write_fd}>&-
  [[ $port =~ ^[0-9]{1,5}$ ]] && ((port >= 1 && port <= 65535)) || die 'invalid proxy readiness response'
  proxy_url=http://127.0.0.1:$port
  trace 'private CONNECT proxy ready'
}
run_codex() {
  local auth=$1; shift
  # Termux coreutils env restores SIGINT/QUIT for an asynchronous child.
  # Bash otherwise starts asynchronous commands with those signals ignored.
  local -a environment=(env --default-signal=INT,QUIT)
  [[ $auth != chatgpt ]] || environment+=(-u OPENAI_API_KEY -u CODEX_API_KEY -u CODEX_ACCESS_TOKEN)
  if [[ -n $proxy_url ]]; then
    environment+=("HTTPS_PROXY=$proxy_url" "https_proxy=$proxy_url" 'NO_PROXY=127.0.0.1,localhost' 'no_proxy=127.0.0.1,localhost' "CODEX_CA_CERTIFICATE=$ca_bundle" "SSL_CERT_FILE=$ca_bundle")
  fi
  # Explicit stdin preserves terminal/pipe input for a backgrounded child.
  "${environment[@]}" "${codex_command[@]}" "$@" <&0 &
  child_pid=$!
  local status=0
  while :; do
    status=0
    wait "$child_pid" || status=$?
    # A console Ctrl+C reaches the child directly. Do not forward it twice.
    # If a handler kept Codex alive, resume waiting instead of orphaning it.
    kill -0 "$child_pid" 2>/dev/null || break
  done
  child_pid=''
  return "$status"
}
auth_session() {
  local auth=$1 status=0; shift
  run_codex "$auth" "$@" || status=$?
  # Leave Codex's TTY and streams intact. A notice is emitted only after it exits,
  # even if an MCP failure did not cause a nonzero Codex exit status.
  if [[ -n $auth_monitor_log ]]; then
    runtime auth-notice "$auth_monitor_log" "$runtime_dir/auth-state" || true
  fi
  return "$status"
}
interactive_launch() {
  [[ -t 0 && -t 1 && -t 2 ]] || return 1
  # Do not ask on exec/review/login, prompts, piped stdin, or unknown option grammar.
  while (($#)); do
    case $1 in
      --sandbox|--ask-for-approval|-a|-s|-c|--config|-m|--model|-p|--profile|-C|--cd)
        (($# >= 2)) || return 1; shift 2 ;;
      --full-auto|--no-alt-screen) shift ;;
      *) return 1 ;;
    esac
  done
}
consider_update() {
  [[ $auto_update != off && -z $codex_bin ]] && interactive_launch "$@" || return 0
  get_arch
  local schema stamp latest extra now
  printf -v now '%(%s)T' -1
  local file=$cache_dir/update
  if [[ -f $file && ! -L $file && -r $file ]] &&
    { IFS= read -r schema && IFS= read -r stamp && IFS= read -r latest && ! IFS= read -r extra && [[ -z $extra ]]; } <"$file" &&
    [[ $schema == 1 && $stamp =~ ^[1-9][0-9]{8,10}$ ]] && stable_version "$latest" &&
    ((stamp <= now && now - stamp < update_interval)); then
    # Only a fresh cached check can add a version probe to an interactive launch.
    if [[ -z $installed_version ]]; then probe_version || return 0; fi
    local -a a b
    IFS=. read -r -a a <<<"$latest"; IFS=. read -r -a b <<<"$installed_version"
    local i upgrade=0
    for i in 0 1 2; do
      if ((10#${a[i]} > 10#${b[i]})); then upgrade=1; break; fi
      if ((10#${a[i]} < 10#${b[i]})); then break; fi
    done
    if ((upgrade)); then
      note "Codex $latest is available (active $installed_version)."
      if [[ $auto_update == ask ]]; then
        if confirm 'Install the update before starting Codex?'; then
          maintenance update --version "$latest" --yes
          resolve_codex || die 'updated runtime resolution failed'
        fi
      else note "Update when ready: $PROGRAM manage update"; fi
    fi
  else
    # An offline phone should not retry on every launch. Explicit checks bypass
    # this one-hour backoff; successful results use update_interval instead.
    local attempt_file=$cache_dir/check-attempt attempted=''
    if [[ -f $attempt_file && ! -L $attempt_file && -r $attempt_file ]]; then
      IFS= read -r attempted <"$attempt_file" || attempted=''
    fi
    if [[ $attempted =~ ^[1-9][0-9]{8,10}$ ]] && ((attempted <= now && now - attempted < 3600)); then
      trace 'background check deferred after a recent attempt'
    else pending_cache=$cache_dir; fi
  fi
}
test_connection() {
  note 'testing Android DNS through native Node.js'
  "$node_bin" -e 'const t=setTimeout(()=>{console.error("DNS timed out");process.exit(1)},10000); require("node:dns").lookup("auth.openai.com",(e,a,f)=>{clearTimeout(t);if(e){console.error("DNS failed");process.exitCode=1}else console.log(`DNS OK (IPv${f})`)});'
  command -v curl >/dev/null 2>&1 || die "curl is required; run: $PROGRAM setup"
  local code
  code=$(curl --proxy "$proxy_url" --noproxy '' --cacert "$ca_bundle" --connect-timeout 10 --max-time 20 --silent --show-error --output /dev/null --write-out '%{http_code}' https://auth.openai.com/) || die 'HTTPS transport test failed'
  [[ $code =~ ^[1-5][0-9][0-9]$ ]] || die 'no HTTP response'
  say "HTTPS transport reachable: HTTP $code (not proof of successful login)."
  run_codex normal doctor --summary
}
main() {
  local dry=0 mode='' action
  while (($#)); do
    case $1 in
      --wrapper-version) (($# == 1)) || usage_error '--wrapper-version accepts no arguments'; say "codex-termux $WRAPPER_VERSION"; return ;;
      --wrapper-no-config) config_disabled=1; shift ;;
      --wrapper-config) (($# >= 2)) && [[ -n $2 ]] || usage_error '--wrapper-config requires a path'; config_file=$2; config_explicit=1; shift 2 ;;
      --wrapper-color|--wrapper-banner) (($# >= 2)) || usage_error 'wrapper style option requires a mode'; prefix_args+=("${1#--wrapper-}" "$2"); shift 2 ;;
      --wrapper-no-update) no_update=1; shift ;;
      --wrapper-debug) debug=1; shift ;;
      --wrapper-dry-run) dry=1; shift ;;
      --wrapper-info) mode=info; shift; break ;;
      *) break ;;
    esac
  done
  configure
  if [[ $mode == info ]]; then
    (( ! dry )) || usage_error 'dry-run supports run or chatgpt only'
    (($# == 0)) || [[ $# == 1 && $1 == --json ]] || usage_error '--wrapper-info accepts only --json'
    info "${1:+json}"; return
  fi
  action=${1:-run}; original_action=$action
  if ((dry)) && [[ $action != run && $action != chatgpt ]]; then
    usage_error 'dry-run supports run or chatgpt only'
  fi
  case $action in
    -h|--help|help) (($# <= 1)) || usage_error 'help accepts no arguments'; usage; return ;;
    completion) (($# == 2)) || usage_error 'completion requires bash or zsh'; completion "$2"; return ;;
    manage) shift; maintenance "$@"; return ;;
    setup) shift; setup "$@"; return ;;
  esac
  case $action in
    run|chatgpt) (($# == 0)) || shift ;;
    status|logout|login-api|test) (($# == 1)) || usage_error "$action accepts no arguments"; shift ;;
    login|doctor) shift ;;
  esac
  (( ! dry )) || { [[ $action == run || $action == chatgpt ]] || usage_error 'dry-run supports run or chatgpt only'; }
  require_runtime
  if ((dry)); then
    say "Mode: $action | Runtime: $codex_kind | Forwarded argument count: $#"
    say 'Proxy: per-launch loopback CONNECT | Argument values omitted'
    say 'No launch, update check, temporary directory, or network request performed.'
    return
  fi
  # Known local-only queries skip Node proxy startup and need no CA bundle.
  if [[ $action == status ]]; then run_codex normal login status; return; fi
  if [[ $action == logout ]]; then run_codex chatgpt logout; return; fi
  if [[ ( $action == run || $action == chatgpt ) && $# == 1 && ( $1 == --version || $1 == -V ) ]] ||
     [[ $action == --version || $action == -V ]]; then
    run_codex "$action" "$@"; return
  fi
  find_ca_bundle || die "Termux's CA bundle is missing; run: $PROGRAM setup"
  if [[ $action == run || $action == chatgpt ]]; then
    consider_update "$@"
    if [[ $auth_notice == auto ]] && interactive_launch "$@"; then auth_monitor_log=$auth_log; fi
  fi
  start_proxy
  case $action in
    run) auth_session normal "$@" ;;
    chatgpt) auth_session chatgpt "$@" ;;
    login)
      if (($#)); then run_codex chatgpt login "$@"; else run_codex chatgpt login --device-auth; fi
      if [[ -n ${OPENAI_API_KEY:-}${CODEX_API_KEY:-}${CODEX_ACCESS_TOKEN:-} ]]; then note "API credential variables remain in this shell; use '$PROGRAM chatgpt'."; fi ;;
    login-api)
      [[ -n ${OPENAI_API_KEY:-} ]] || die 'OPENAI_API_KEY is not set'
      printf '%s\n' "$OPENAI_API_KEY" | run_codex normal login --with-api-key ;;
    doctor) if (($#)); then run_codex normal doctor "$@"; else run_codex normal doctor --all; fi ;;
    test) test_connection ;;
    *) run_codex normal "$@" ;;
  esac
}
main "$@"
