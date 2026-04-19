#!/usr/bin/env bash

new_window() {
    [[ -x $(command -v fzf 2>/dev/null) ]] || return
    pane_id=$(tmux show -gqv '@fzf_pane_id')
    [[ -n $pane_id ]] && tmux kill-pane -t $pane_id >/dev/null 2>&1
    tmux new-window "bash $0 do_action" >/dev/null 2>&1
}

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

do_action() {
    trap 'tmux set -gu @fzf_pane_id' EXIT SIGINT SIGTERM
    current_pane_id=$(tmux display-message -p '#D')
    tmux set -g @fzf_pane_id $current_pane_id

    cmd="bash $0 panes_src"
    set -- 'tmux capture-pane -pe -S' \
        '$(start=$(( $(tmux display-message -t {1} -p "#{pane_height}")' \
        '- $FZF_PREVIEW_LINES ));' \
        '(( start>0 )) && echo $start || echo 0) -t {1}'
    preview_cmd=$*
    last_pane_cmd='$(tmux show -gqv "@mru_pane_ids" | cut -d\  -f1)'
    selected=$(FZF_DEFAULT_COMMAND=$cmd fzf -m --preview="$preview_cmd" \
        --preview-window='right:60%' --reverse --info=inline --header-lines=1 \
        --delimiter='\s{2,}' --with-nth=2..-1 --nth=1,2,3 \
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
            pane_info=($pane_line)
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

        # my personally configuration
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

panes_src() {
    printf "%-6s  %-7s  %5s  %s\n" \
        'PANEID' 'SESSION' 'PANE' 'CMD'
    panes_info=$(tmux list-panes -aF \
        '#D #{=|6|…:session_name} #I.#P #{pane_tty} #T' |
        sed -E "/^$TMUX_PANE /d")
    ttys=$(awk '{printf("%s,", $4)}' <<<"$panes_info" | sed 's/,$//')
    ps_info=$(ps -t$ttys -o stat,tty,command |
        awk '$1~/\+/ {$1="";print $0}')
    ids=()
    hostname=$(hostname)

    print_pane_line() {
        local pane_line=$1
        local prefix=${2:-}
        local pane_info=($pane_line)
        local pane_id=${pane_info[0]}
        local session=${pane_info[1]}
        local pane=${pane_info[2]}
        local tty=${pane_info[3]#/dev/}
        local title=${pane_info[@]:4}
        while read ps_line; do
            local p_info=($ps_line)
            if [[ $tty == ${p_info[0]} ]]; then
                local cmd=${p_info[@]:1}
                if [[ $cmd =~ ^n?vim && $title != $hostname ]]; then
                    local cmd_arr=($cmd)
                    cmd="${cmd_arr[0]} $title"
                fi
                printf "%-6s  %-7s  %5s  %s%s\n" \
                    $pane_id $session $pane "$prefix" "$cmd"
                break
            fi
        done <<<"$ps_info"
    }

    # First: output AI pending pane (if any) at the top
    ai_pending=$(tmux show -gqv '@ai_pending_pane' 2>/dev/null || true)
    if [[ -n $ai_pending ]]; then
        while read pane_line; do
            [[ -z $pane_line ]] && continue
            pane_info=($pane_line)
            pane_id=${pane_info[0]}
            if [[ $ai_pending == $pane_id ]]; then
                ids+=($ai_pending)
                print_pane_line "$pane_line" "* "
            fi
        done <<<"$panes_info"
    fi

    # Then: output panes in MRU order
    for id in $(tmux show -gqv '@mru_pane_ids'); do
        [[ $id == "$ai_pending" ]] && continue
        while read pane_line; do
            pane_info=($pane_line)
            pane_id=${pane_info[0]}
            if [[ $id == $pane_id ]]; then
                ids+=($id)
                print_pane_line "$pane_line"
            fi
        done <<<"$panes_info"
    done

    # Then: output any panes not yet in MRU list
    while read pane_line; do
        [[ -z $pane_line ]] && continue
        pane_info=($pane_line)
        pane_id=${pane_info[0]}
        found=0
        for id in "${ids[@]}"; do
            [[ $id == $pane_id ]] && found=1 && break
        done
        if (( found == 0 )); then
            ids+=($pane_id)
            print_pane_line "$pane_line"
        fi
    done <<<"$panes_info"

    tmux set -g '@mru_pane_ids' "${ids[*]}"
}

$@
