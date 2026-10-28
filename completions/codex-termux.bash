# Static codex-termux completion. Source this file; no runtime discovery.
_codex_termux_complete() {
  local cur=${COMP_WORDS[COMP_CWORD]} prev=${COMP_WORDS[COMP_CWORD-1]:-}
  local word action='' sub='' i=1 j pending backend operation choices canonical
  local -A used=()
  local -a candidates=()
  COMPREPLY=()
  while ((i < COMP_CWORD)); do
    word=${COMP_WORDS[i]}
    case $word in
      --wrapper-color|--wrapper-banner|--wrapper-output|--wrapper-config) i=$((i+2)); continue ;;
      --wrapper-no-config|--wrapper-no-update|--wrapper-debug|--wrapper-dry-run) i=$((i+1)); continue ;;
    esac
    action=$word; i=$((i+1)); break
  done
  case $prev in
    --wrapper-color|--wrapper-banner) [[ -z $action ]] || return 0; COMPREPLY=($(compgen -W 'auto always never' -- "$cur")); return ;;
    --wrapper-output) [[ -z $action ]] || return 0; COMPREPLY=($(compgen -W 'auto pretty raw' -- "$cur")); return ;;
    --wrapper-config) [[ -z $action ]] || return 0; mapfile -t COMPREPLY < <(compgen -f -- "$cur"); return ;;
  esac
  if [[ -z $action ]]; then
    COMPREPLY=($(compgen -W 'run chatgpt connect login login-api status logout doctor test setup manage completion help --help --version --wrapper-version --wrapper-info --wrapper-dry-run --wrapper-no-update --wrapper-color --wrapper-banner --wrapper-output --wrapper-config --wrapper-no-config --wrapper-debug' -- "$cur")); return
  fi
  if [[ $action == manage ]]; then
    if ((i == COMP_CWORD)); then COMPREPLY=($(compgen -W 'check auth-check server update rollback self-update uninstall config help' -- "$cur")); return; fi
    sub=${COMP_WORDS[i]}
    case $sub in
      server)
        if ((i+1 == COMP_CWORD)); then
          COMPREPLY=($(compgen -W 'start status stop restart enable disable is-enabled logs check help' -- "$cur")); return
        fi
        operation=${COMP_WORDS[i+1]}; backend=''; pending=''; j=$((i+2))
        while ((j < COMP_CWORD)); do
          word=${COMP_WORDS[j]}
          case $word in -w) word=--wait ;; -n) word=--lines ;; -f) word=--follow ;; esac
          [[ -n $word ]] || return 0
          [[ -z ${used[$word]+yes} ]] || return 0
          used[$word]=1
          case $word in
            --backend|--auth|--port|--wait|--lines)
              if ((j+1 == COMP_CWORD)); then pending=$word; break; fi
              [[ $word != --backend ]] || backend=${COMP_WORDS[j+1]}
              j=$((j+2)) ;;
            --follow) j=$((j+1)) ;;
            *) return 0 ;;
          esac
        done
        choices='--backend --help'
        case $operation in
          start)
            [[ $backend == managed ]] || choices+=' --wait -w'
            [[ $backend == runit ]] || choices+=' --auth --port' ;;
          stop) [[ $backend == managed ]] || choices+=' --wait -w' ;;
          restart|enable|disable) choices+=' --wait -w' ;;
          logs) choices+=' --follow -f --lines -n' ;;
          status|is-enabled|check) ;;
          *) return 0 ;;
        esac
        if [[ $backend == managed && $operation != start && $operation != status && $operation != stop ]] ||
           [[ -n ${used[--backend]+yes} && $pending != --backend && $backend != managed && $backend != runit ]]; then choices='--help'; fi
        if [[ -n $pending ]]; then
          [[ " $choices " == *" $pending "* ]] || return 0
          case $pending in
            --backend) COMPREPLY=($(compgen -W 'runit managed' -- "$cur")) ;;
            --auth) COMPREPLY=($(compgen -W 'inherited chatgpt' -- "$cur")) ;;
          esac
          return 0
        fi
        for word in $choices; do
          canonical=$word
          case $word in -w) canonical=--wait ;; -n) canonical=--lines ;; -f) canonical=--follow ;; esac
          [[ -n ${used[$canonical]+yes} ]] || candidates+=("$word")
        done
        COMPREPLY=($(compgen -W "${candidates[*]}" -- "$cur")) ;;
      check|auth-check) COMPREPLY=($(compgen -W '--json' -- "$cur")) ;;
      update)
        [[ $prev != --version ]] || return 0
        COMPREPLY=($(compgen -W '--check --json --yes --version' -- "$cur")) ;;
      rollback) COMPREPLY=($(compgen -W '--yes' -- "$cur")) ;;
      self-update|uninstall)
        case $prev in
          --prefix|--source) mapfile -t COMPREPLY < <(compgen -d -- "$cur"); return ;;
          --version) return 0 ;;
          --output) COMPREPLY=($(compgen -W 'auto pretty raw' -- "$cur")); return ;;
          --color) COMPREPLY=($(compgen -W 'auto always never' -- "$cur")); return ;;
        esac
        if [[ $sub == self-update ]]; then
          COMPREPLY=($(compgen -W '--check --dry-run --yes --version --prefix --source --remote --repair --recover --color --output --help' -- "$cur"))
        else COMPREPLY=($(compgen -W '--dry-run --yes --prefix --color --output --help' -- "$cur")); fi ;;
      config) if ((i+1 == COMP_CWORD)); then COMPREPLY=($(compgen -W 'show example' -- "$cur")); fi ;;
    esac
  elif [[ $action == connect ]]; then
    while ((i < COMP_CWORD)); do
      word=${COMP_WORDS[i]}
      [[ -n $word ]] || return 0
      [[ -z ${used[$word]+yes} ]] || return 0
      used[$word]=1
      case $word in
        --chatgpt) i=$((i+1)) ;;
        --backend)
          if ((i+1 == COMP_CWORD)); then COMPREPLY=($(compgen -W 'runit managed' -- "$cur")); return; fi
          case ${COMP_WORDS[i+1]} in runit|managed) ;; *) return 0 ;; esac
          i=$((i+2)) ;;
        *) return 0 ;;
      esac
    done
    [[ -n ${used[--chatgpt]+yes} ]] || candidates+=(--chatgpt)
    [[ -n ${used[--backend]+yes} ]] || candidates+=(--backend)
    candidates+=(-- resume fork)
    COMPREPLY=($(compgen -W "${candidates[*]}" -- "$cur"))
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
