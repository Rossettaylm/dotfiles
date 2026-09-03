#!/usr/bin/env bash

# invoked by pane-focus-in event
update_mru_pane_ids() {
    o_data=($(tmux show -gqv '@mru_pane_ids'))
    current_pane_id=$(tmux display-message -p '#D')
    n_data=($current_pane_id)
    for i in ${!o_data[@]}; do
        [[ $current_pane_id != ${o_data[i]} ]] && n_data+=(${o_data[i]})
    done
    tmux set -g '@mru_pane_ids' "${n_data[*]}"
}

# Crop the visible pane to the last non-empty line, then take the bottom
# $FZF_PREVIEW_LINES rows. Cursor-agent / pi grow from the top (no alternate
# screen); slicing by pane_height would preview the empty region below.
preview_pane() {
    local pane_id=$1
    local n=${FZF_PREVIEW_LINES:-40}
    tmux capture-pane -pe -t "$pane_id" | awk -v n="$n" -v ESC=$'\033' '
    function visible(s) {
        gsub(ESC "\\[[0-9;?]*[A-Za-z]", "", s)
        return s ~ /[^[:space:]]/
    }
    {
        lines[NR] = $0
        if (visible($0)) last = NR
    }
    END {
        if (last == 0) exit
        start = last - n + 1
        if (start < 1) start = 1
        for (i = start; i <= last; i++) print lines[i]
    }
    '
}

do_action() {
    cmd="bash $0 panes_src"
    preview_cmd="bash $0 preview_pane {1}"
    last_pane_cmd='$(tmux show -gqv "@mru_pane_ids" | cut -d\  -f1)'
    selected=$(bash $0 panes_src | fzf -m --ansi --preview="$preview_cmd" \
        --popup center,90%,85% \
        --border-label ' AI Agents ' \
        --preview-window='bottom:70%' --reverse --info=inline --header-lines=1 \
        --delimiter='\s{2,}' --with-nth=2..-1 \
        --bind="alt-e:abort" \
        --bind="alt-p:toggle-preview" \
        --bind="ctrl-r:reload($cmd)" \
        --bind="ctrl-x:execute-silent(tmux kill-pane -t {1})+reload($cmd)" \
        --bind="ctrl-v:execute(tmux move-pane -h -t $last_pane_cmd -s {1})+accept" \
        --bind="ctrl-s:execute(tmux move-pane -v -t $last_pane_cmd -s {1})+accept" \
        --bind="ctrl-t:execute-silent(tmux swap-pane -t $last_pane_cmd -s {1})+reload($cmd)")
    (($?)) && return

    ids_o=($(tmux show -gqv '@mru_pane_ids'))
    ids=()
    for id in ${ids_o[@]}; do
        while read pane_line; do
            # Strip ANSI escape codes before field parsing
            clean_line=$(printf '%s' "$pane_line" | sed $'s/\033\\[[0-9;]*m//g')
            pane_info=($clean_line)
            pane_id=${pane_info[0]}
            [[ $id == $pane_id ]] && ids+=($id)
        done <<<"$selected"
    done

    # Clear AI pending pane after selection
    tmux set -gu '@ai_pending_pane' 2>/dev/null || true

    id_n=${#ids[@]}
    id1=${ids[0]}
    if ((id_n == 1)); then
        tmux switch-client -t$id1
    elif ((id_n > 1)); then
        tmux break-pane -s$id1
        i=1
        tmux_cmd="tmux "
        while ((i < id_n)); do
            tmux_cmd+="move-pane -t${ids[i-1]} -s${ids[i]} \; select-layout -t$id1 'tiled' \; "
            ((i++))
        done

        # personal preference: for 2 panes, pick split direction by aspect ratio
        if (( id_n == 2 )); then
            w_size=($(tmux display-message -p '#{window_width} #{window_height}'))
            w_wid=${w_size[0]}
            w_hei=${w_size[1]}
            if (( 9*w_wid > 16*w_hei )); then
                layout='even-horizontal'
            else
                layout='even-vertical'
            fi
        else
            layout='titled'
        fi

        tmux_cmd+="switch-client -t$id1 \; select-layout -t$id1 $layout \; "
        eval $tmux_cmd
    fi
}

# Agent registry: process name (+ title/process-tree, for wrapper processes like
# node) -> agent key. To add a new agent: add a branch here, a parse_<agent>_title
# function below, and extend the tmux list-panes -f filter in panes_src.
#
# cursor-agent and pi both run under a generic "node" pane_current_command, so
# node panes need a second signal to tell them apart: pi's title starts with its
# own 'π' icon, cursor-agent's does not, and its real executable (a child of
# #{pane_pid}, since node is the pane's original shell's grandchild) has
# "cursor-agent" in its command line.
agent_key_for_pane() {
    local pane_id=$1 command=$2 title=$3
    case $command in
        claude)
            echo claude
            return
            ;;
        node) ;;
        *) return ;;
    esac

    if [[ ${title%% *} == 'π' ]]; then
        echo pi
        return
    fi

    local pane_pid child
    pane_pid=$(tmux display-message -p -t "$pane_id" '#{pane_pid}' 2>/dev/null)
    [[ -z $pane_pid ]] && return
    for child in $(pgrep -P "$pane_pid" 2>/dev/null); do
        if ps -o command= -p "$child" 2>/dev/null | grep -qi 'cursor-agent'; then
            echo cursor
            return
        fi
    done
}

# Each parse_<agent>_title prints "<state>\t<task>", state is one of
# working|idle|blocked.
parse_claude_title() {
    local pane_id=$1 title=$2 icon
    icon=${title%% *}
    local state='working'
    [[ $icon == '✳' ]] && state='idle'

    # claude's OSC title only ever encodes working/idle; blocked (permission
    # prompts) is screen-content only, simplified from herdr's claude.toml
    # bash_permission_prompt / generic_permission_prompt / legacy_no_prompt_blocker.
    local screen
    screen=$(tmux capture-pane -pe -S -12 -t "$pane_id" 2>/dev/null)
    if printf '%s' "$screen" | grep -qiE 'do you want to (proceed|allow this connection)\?|would you like to|waiting for permission|tab to amend|ctrl\+e to explain'; then
        if printf '%s' "$screen" | grep -qiE '❯?[[:space:]]*1\.[[:space:]]*yes|❯[[:space:]]*yes|2\.[[:space:]]*(yes|no)|3\.[[:space:]]*no|run \(once\)|skip \(esc or n\)'; then
            state='blocked'
        fi
    fi

    printf '%s\t%s' "$state" "${title#* }"
}

parse_cursor_title() {
    local pane_id=$1 title=$2
    # cursor-agent's title is "<action name> - <emoji> <status phrase>"; the
    # action prefix varies per tool call (e.g. "Tmux Command", "Request File
    # Access") so only the status suffix after the last " - " is meaningful.
    local suffix=${title##* - }
    local state='working'
    if printf '%s' "$suffix" | grep -qi 'ready'; then
        state='idle'
    elif printf '%s' "$suffix" | grep -qi 'waiting for confirmation'; then
        state='blocked'
    fi
    printf '%s\t%s' "$state" "${title% - *}"
}

parse_pi_title() {
    local pane_id=$1 title=$2 icon
    icon=${title%% *}
    local state='working'
    [[ $icon == 'π' ]] && state='idle'
    printf '%s\t%s' "$state" "${title#*- }"
}

# Display-column helpers. Widths are character counts (Nerd Font Mono icons = 1).
# Columns are joined with two spaces so fzf --delimiter='\s{2,}' still works.
COL_PANEID=6
COL_SESSION=12
COL_AGENT=10
COL_PATH=32
COL_STATUS=11
COL_TASK=36

fit_col() {
    local text=$1
    local width=$2
    local mode=${3:-head}
    local len=${#text}
    if ((len > width)); then
        local keep=$((width - 1))
        if [[ $mode == tail ]]; then
            text="…${text: -keep}"
        else
            text="${text:0:keep}…"
        fi
        len=$width
    fi
    # bash printf '%-*s' pads by bytes; pad here by character count so
    # 3-byte Nerd Font icons still occupy one column.
    printf '%s%*s' "$text" $((width - len)) ''
}

format_status() {
    local state=$1
    local icon label color
    case $state in
        blocked)
            icon=$'\xef\x81\xb1' # U+F071 nf-fa-warning
            label='blocked'
            color='1;31'
            ;;
        working)
            icon=$'\xef\x84\x90' # U+F110 nf-fa-spinner
            label='working'
            color='1;33'
            ;;
        idle)
            icon=$'\xef\x81\x98' # U+F058 nf-fa-check-circle
            label='idle'
            color='32'
            ;;
        *)
            icon=' '
            label=$state
            color='2'
            ;;
    esac
    local visible
    visible=$(fit_col "$icon $label" "$COL_STATUS")
    printf '\033[%sm%s\033[0m' "$color" "$visible"
}

format_agent() {
    local agent=$1
    local icon color
    case $agent in
        claude)
            icon=$'\xef\x83\xab' # U+F0EB nf-fa-lightbulb
            color='38;5;209'
            ;;
        cursor)
            icon=$'\xef\x89\x85' # U+F245 nf-fa-mouse-pointer
            color='38;5;141'
            ;;
        pi)
            icon=$'\xcf\x80' # U+03C0 π
            color='38;5;80'
            ;;
        *)
            icon=' '
            color='2'
            ;;
    esac
    local visible
    visible=$(fit_col "$icon $agent" "$COL_AGENT")
    printf '\033[%sm%s\033[0m' "$color" "$visible"
}

panes_src() {
    printf '%s  %s  %s  %s  %s  %s\n' \
        "$(fit_col 'PANEID' "$COL_PANEID")" \
        "$(fit_col 'SESSION' "$COL_SESSION")" \
        "$(fit_col 'AGENT' "$COL_AGENT")" \
        "$(fit_col 'PATH' "$COL_PATH")" \
        "$(fit_col 'STATUS' "$COL_STATUS")" \
        'TASK'
    # node covers both pi and cursor-agent; agent_key_for_pane tells them apart
    # (and drops unrelated node processes) once we're past this coarse filter.
    panes_info=$(tmux list-panes -aF \
        '#D #{session_name} #{pane_current_command} #{pane_current_path} #T' \
        -f '#{||:#{==:#{pane_current_command},claude},#{==:#{pane_current_command},node}}')

    c_ids=()
    c_sessions=()
    c_agents=()
    c_paths=()
    c_statuses=()
    c_tasks=()
    c_done=()

    collect_pane() {
        local pane_line=$1
        [[ -z $pane_line ]] && return
        local pane_info=($pane_line)
        local pane_id=${pane_info[0]}
        local session=${pane_info[1]}
        local command=${pane_info[2]}
        local pane_path=${pane_info[3]}
        local title="${pane_info[@]:4}"
        pane_path=${pane_path/#$HOME/\~}

        local agent
        agent=$(agent_key_for_pane "$pane_id" "$command" "$title")
        [[ -z $agent ]] && return

        local parsed status task
        parsed=$(parse_"${agent}"_title "$pane_id" "$title")
        status=${parsed%%$'\t'*}
        task=${parsed#*$'\t'}
        [[ -z $status ]] && status='unknown'

        c_ids+=("$pane_id")
        c_sessions+=("$session")
        c_agents+=("$agent")
        c_paths+=("$pane_path")
        c_statuses+=("$status")
        c_tasks+=("$task")
        c_done+=(0)
    }

    print_collected() {
        local i=$1
        printf '%s  %s  %s  %s  %s  %s\n' \
            "$(fit_col "${c_ids[i]}" "$COL_PANEID")" \
            "$(fit_col "${c_sessions[i]}" "$COL_SESSION")" \
            "$(format_agent "${c_agents[i]}")" \
            "$(fit_col "${c_paths[i]}" "$COL_PATH" tail)" \
            "$(format_status "${c_statuses[i]}")" \
            "$(fit_col "${c_tasks[i]}" "$COL_TASK")"
        c_done[i]=1
    }

    while read pane_line; do
        collect_pane "$pane_line"
    done <<<"$panes_info"

    mru_ids=($(tmux show -gqv '@mru_pane_ids'))
    local rank mid i
    for rank in blocked working idle unknown; do
        for mid in "${mru_ids[@]}"; do
            for i in "${!c_ids[@]}"; do
                ((c_done[i])) && continue
                [[ ${c_ids[i]} == "$mid" && ${c_statuses[i]} == "$rank" ]] || continue
                print_collected "$i"
            done
        done
        for i in "${!c_ids[@]}"; do
            ((c_done[i])) && continue
            [[ ${c_statuses[i]} == "$rank" ]] || continue
            print_collected "$i"
        done
    done

    # Keep existing MRU order; only append newly discovered agent panes.
    local new_mru=("${mru_ids[@]}")
    local id found e
    for id in "${c_ids[@]}"; do
        found=0
        for e in "${new_mru[@]}"; do
            [[ $e == "$id" ]] && found=1 && break
        done
        ((found == 0)) && new_mru+=("$id")
    done
    tmux set -g '@mru_pane_ids' "${new_mru[*]}"
}

$@
