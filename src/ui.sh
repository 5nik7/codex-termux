# Shared human presentation, embedded at build time. Bash and normal utilities only.
ui_output=${CODEX_TERMUX_OUTPUT:-auto} ui_color=${CODEX_TERMUX_COLOR:-auto} ui_width=80
ui_pretty() {
  [[ $ui_output == pretty || ( $ui_output == auto && -t ${1:-1} && ${TERM:-dumb} != dumb ) ]]
}
ui_colored() {
  [[ $ui_output != raw && ( $ui_color == always || ( $ui_color == auto && -t ${1:-1} && -z ${NO_COLOR+x} && ${TERM:-dumb} != dumb ) ) ]]
}
ui_size() {
  local rows tty_fd width=${COLUMNS:-0}
  [[ $width =~ ^[0-9]{1,4}$ ]] || width=0
  if ((width == 0)) && [[ -t ${1:-1} ]] && command -v stty >/dev/null 2>&1; then
    # Save the terminal descriptor before process substitution replaces stdout.
    exec {tty_fd}<&"${1:-1}"
    read -r rows width < <(stty size <&"$tty_fd" 2>/dev/null) || width=0
    exec {tty_fd}<&-
  fi
  ui_width=$((width > 0 ? width : 80))
}
ui_escape() {
  UI_TEXT=$1
  if [[ $UI_TEXT == *[[:cntrl:]]* ]]; then
    local i ch code escaped='' value=$UI_TEXT
    for ((i=0; i<${#value}; i++)); do
      ch=${value:i:1}
      if [[ $ch == [[:cntrl:]] ]]; then
        printf -v code '%d' "'$ch"
        printf -v ch '\\x%02x' "$code"
      fi
      escaped+=$ch
    done
    UI_TEXT=$escaped
  fi
}
ui_span() {
  local fd=$1 role=$2 text=$3 sgr=''
  case $role in
    brand|info) sgr='1;36' ;; heading) sgr='1;35' ;; success|command) sgr='1;32' ;;
    warning|option) sgr='1;33' ;; error) sgr='1;31' ;; muted) sgr=2 ;; *) sgr=37 ;;
  esac
  if ui_colored "$fd"; then printf '\033[%sm%s\033[0m' "$sgr" "$text" >&"$fd"
  else printf '%s' "$text" >&"$fd"; fi
}
ui_section() {
  local fd=$1
  ui_escape "$2"
  printf '\n' >&"$fd"; ui_span "$fd" heading "$UI_TEXT"; printf '\n' >&"$fd"
}
ui_field() {
  local fd=$1 label=$2 value=$3 role=${4:-value} padded
  ui_escape "$label"; label=$UI_TEXT
  ui_escape "$value"; value=$UI_TEXT
  ui_size "$fd"
  if ((ui_width < 60)); then
    printf '  ' >&"$fd"; ui_span "$fd" info "$label"; printf '\n    ' >&"$fd"
  else
    printf -v padded '%-27s' "$label"
    printf '  ' >&"$fd"; ui_span "$fd" info "$padded"; printf ' ' >&"$fd"
  fi
  ui_span "$fd" "$role" "$value"; printf '\n' >&"$fd"
}
ui_message() {
  local fd=$1 role=$2 message=$3 label
  case $role in success) label=Done ;; warning) label=Warning ;; error) label=Error ;; muted) label=Debug ;; *) label=Info ;; esac
  ui_escape "$message"
  ui_span "$fd" "$role" "[$label]"; printf ' ' >&"$fd"
  ui_span "$fd" value "$UI_TEXT"; printf '\n' >&"$fd"
}
ui_log_line() {
  local line=$1 prefix='' rest role=info level suffix
  # Normalize only actual SGR styling. Never interpret backslash text or pass
  # through other terminal controls; ui_escape keeps those visible and inert.
  local sgr=$'\033''\[[0-9;:]*m'
  while [[ $line =~ $sgr ]]; do line=${line/"${BASH_REMATCH[0]}"/}; done
  # Recognize fields only at the start, never severity words inside messages.
  local stamp='^(@[0-9a-fA-F]{24}|[0-9]{4}-[0-9]{2}-[0-9]{2}[T _][0-9:.]+([Zz]|[+-][0-9:]+)?)([[:space:]]+)(.*)$'
  ui_escape "$line"; rest=$UI_TEXT
  while [[ $rest =~ $stamp ]]; do
    prefix=${BASH_REMATCH[1]}${BASH_REMATCH[3]}; rest=${BASH_REMATCH[4]}
    ui_span 1 muted "$prefix"
  done
  if [[ $rest =~ ^(\[?(TRACE|DEBUG|INFO|WARN|WARNING|ERROR|FATAL)\]?)([[:space:]:]+)(.*)$ ]]; then
    level=${BASH_REMATCH[1]}; suffix=${BASH_REMATCH[3]}; rest=${BASH_REMATCH[4]}
    case ${BASH_REMATCH[2]} in TRACE|DEBUG) role=muted ;; WARN|WARNING) role=warning ;; ERROR|FATAL) role=error ;; esac
    ui_span 1 "$role" "$level"; printf '%s' "$suffix"
  fi
  ui_span 1 value "$rest"
}
ui_stream() {
  local kind=$1 fd=$2 row ending state role pid elapsed
  while :; do
    row=''; ending=0
    if IFS= read -r row; then ending=1; elif [[ -z $row ]]; then break; fi
    case $kind in
      logs) ui_log_line "$row"; (( ! ending )) || printf '\n' ;;
      sv)
        if [[ $row =~ ^(ok:\ )?(run|down): ]]; then
          state=${BASH_REMATCH[2]}; role=success
          if [[ $state == down ]]; then state=Stopped; role=warning; else state=Running; fi
          ui_field 1 State "$state" "$role"
          if [[ $row =~ \(pid\ ([0-9]+)\)\ ([0-9]+)s ]]; then
            pid=${BASH_REMATCH[1]}; elapsed=${BASH_REMATCH[2]}
            ui_field 1 PID "$pid"
            ui_field 1 Elapsed "$elapsed seconds"
          fi
        fi
        ui_field 1 Details "$row" ;;
      *)
        role=warning
        case $row in fail:*|fatal:*|timeout:*|error:*) role=error ;; esac
        ui_message "$fd" "$role" "$row" ;;
    esac
    ((ending)) || break
  done
}
# Keep producers and presentation filters separately owned/reaped. No temporary
# recordings; the producer's status is authoritative, including service failures.
ui_stream_signal() {
  ui_signal_status=$1
  trap '' INT TERM HUP
  local pid
  for pid in "$ui_producer" "$ui_out_pid" "$ui_err_pid"; do
    [[ -z $pid ]] || kill -TERM "$pid" 2>/dev/null || true
  done
}
ui_run_stream() {
  local kind=$1; shift
  local ui_out_fd ui_err_fd ui_out_pid='' ui_err_pid='' ui_producer ui_signal_status=0 result=0
  if ui_pretty 1; then exec {ui_out_fd}> >(ui_stream "$kind" 1); ui_out_pid=$!
  else exec {ui_out_fd}>&1; fi
  if ui_pretty 2; then exec {ui_err_fd}> >(ui_stream diagnostic 2); ui_err_pid=$!
  else exec {ui_err_fd}>&2; fi
  "$@" <&0 >&"$ui_out_fd" 2>&"$ui_err_fd" & ui_producer=$!
  exec {ui_out_fd}>&-; exec {ui_err_fd}>&-
  trap 'ui_stream_signal 130' INT
  trap 'ui_stream_signal 143' TERM
  trap 'ui_stream_signal 129' HUP
  wait "$ui_producer" || result=$?
  if ((ui_signal_status)); then wait "$ui_producer" 2>/dev/null || true; fi
  ui_producer=''
  if [[ -n $ui_out_pid ]]; then
    wait "$ui_out_pid" || true
    if ((ui_signal_status)); then wait "$ui_out_pid" 2>/dev/null || true; fi
    ui_out_pid=''
  fi
  if [[ -n $ui_err_pid ]]; then
    wait "$ui_err_pid" || true
    if ((ui_signal_status)); then wait "$ui_err_pid" 2>/dev/null || true; fi
    ui_err_pid=''
  fi
  (( ! ui_signal_status )) || result=$ui_signal_status
  trap - INT TERM HUP
  return "$result"
}
