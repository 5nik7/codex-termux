# Static codex-termux completion. Source this file; no runtime discovery.
_codex_termux_complete() {
  local cur=${COMP_WORDS[COMP_CWORD]} prev=${COMP_WORDS[COMP_CWORD-1]:-}
  local word action='' sub='' i=1
  COMPREPLY=()
  while ((i < COMP_CWORD)); do
    word=${COMP_WORDS[i]}
    case $word in
      --wrapper-color|--wrapper-banner|--wrapper-config) i=$((i+2)); continue ;;
      --wrapper-no-config|--wrapper-no-update|--wrapper-debug|--wrapper-dry-run) i=$((i+1)); continue ;;
    esac
    action=$word; i=$((i+1)); break
  done
  case $prev in
    --wrapper-color|--wrapper-banner) [[ -z $action ]] || return 0; COMPREPLY=($(compgen -W 'auto always never' -- "$cur")); return ;;
    --wrapper-config) [[ -z $action ]] || return 0; mapfile -t COMPREPLY < <(compgen -f -- "$cur"); return ;;
  esac
  if [[ -z $action ]]; then
    COMPREPLY=($(compgen -W 'run chatgpt login login-api status logout doctor test setup manage completion help --help --version --wrapper-version --wrapper-info --wrapper-dry-run --wrapper-no-update --wrapper-color --wrapper-banner --wrapper-config --wrapper-no-config --wrapper-debug' -- "$cur")); return
  fi
  if [[ $action == manage ]]; then
    if ((i == COMP_CWORD)); then COMPREPLY=($(compgen -W 'check update rollback self-update uninstall config help' -- "$cur")); return; fi
    sub=${COMP_WORDS[i]}
    case $sub in
      check) COMPREPLY=($(compgen -W '--json' -- "$cur")) ;;
      update)
        [[ $prev != --version ]] || return 0
        COMPREPLY=($(compgen -W '--check --json --yes --version' -- "$cur")) ;;
      rollback) COMPREPLY=($(compgen -W '--yes' -- "$cur")) ;;
      self-update|uninstall)
        case $prev in
          --prefix|--source) mapfile -t COMPREPLY < <(compgen -d -- "$cur"); return ;;
          --version) return 0 ;;
          --color) COMPREPLY=($(compgen -W 'auto always never' -- "$cur")); return ;;
        esac
        if [[ $sub == self-update ]]; then
          COMPREPLY=($(compgen -W '--check --dry-run --yes --version --prefix --source --remote --repair --recover --color --help' -- "$cur"))
        else COMPREPLY=($(compgen -W '--dry-run --yes --prefix --color --help' -- "$cur")); fi ;;
      config) if ((i+1 == COMP_CWORD)); then COMPREPLY=($(compgen -W 'show example' -- "$cur")); fi ;;
    esac
  elif [[ $action == completion && $i == "$COMP_CWORD" ]]; then
    COMPREPLY=($(compgen -W 'bash zsh' -- "$cur"))
  elif [[ $action == setup ]]; then
    [[ $prev != --version ]] || return 0
    COMPREPLY=($(compgen -W '--yes --version' -- "$cur"))
  elif [[ $action == --wrapper-info ]]; then
    COMPREPLY=($(compgen -W '--json' -- "$cur"))
  fi
  return 0
}
complete -F _codex_termux_complete codex-termux
