#!/usr/bin/env bash

source "$(dirname "$0")/fzf_utils.sh"

do_action() {
    local script_dir
    script_dir=$(dirname "$0")
    cmd="bash $0 sessions_src"

    header="enter=switch  ctrl-r=rename  alt-bspace=kill  ctrl-n=new  ctrl-f=reload  ctrl-/=layout"

    selected=$(printf '' | fzf "${fzf_popup_opts[@]}" \
        --border-label ' Sessions ' \
        --header="$header" \
        --preview="bash $0 session_preview {1}" \
        --delimiter='\s{2,}' \
        --nth=1 \
        --bind="start:transform:bash $script_dir/fzf_utils.sh reload $0 sessions_src" \
        --bind="ctrl-_:transform:bash $script_dir/fzf_utils.sh toggle_layout $0 sessions_src" \
        --bind="alt-w:abort" \
        --bind="ctrl-f:reload($cmd)" \
        --bind="ctrl-r:execute(bash $0 rename_session {1})+reload($cmd)" \
        --bind="alt-bspace:execute-silent(bash $0 kill_session {1})+reload($cmd)" \
        --bind="ctrl-n:execute(bash $0 new_session)+reload($cmd)" \
    )

    [[ -z $selected ]] && return

    # 行首带 SGR 颜色，先剥掉再取第一列会话名
    session=$(printf '%s\n' "$selected" | sed $'s/\033\\[[0-9;]*m//g' | awk '{print $1}')
    [[ -n $session ]] && tmux switch-client -t "$session"
}

session_preview() {
    local name
    name=$(strip_ansi "$1")
    [[ -z $name ]] && return

    local created wins panes
    created=$(tmux display-message -t "$name" -p '#{t/f/%Y-%m-%d %H%M:session_created}' 2>/dev/null)
    wins=$(tmux list-windows -t "$name" 2>/dev/null | wc -l | tr -d ' ')
    panes=$(tmux list-panes -t "$name" -s 2>/dev/null | wc -l | tr -d ' ')

    printf "\033[1;36m%s\033[0m\n" "$name"
    printf "Created : %s\n" "$created"
    printf "Windows : %s   Panes: %s\n\n" "$wins" "$panes"

    tmux list-windows -t "$name" \
        -F '#{window_index}|#{window_active}|#{window_name}|#{pane_current_path}' 2>/dev/null | \
    while IFS='|' read -r idx active wname wpath; do
        if [[ $active == "1" ]]; then
            printf "  \033[1;32m● %s  %-15s\033[0m  \033[2m%s\033[0m\n" "$idx" "$wname" "$wpath"
        else
            printf "    %s  %-15s   \033[2m%s\033[0m\n" "$idx" "$wname" "$wpath"
        fi
    done
}

rename_session() {
    local session
    session=$(strip_ansi "$1")
    printf "Rename [%s] → " "$session" >/dev/tty
    read -r newname </dev/tty
    [[ -n $newname ]] && tmux rename-session -t "$session" "$newname"
}

kill_session() {
    local session
    session=$(strip_ansi "$1")
    local current
    current=$(tmux display-message -p '#S')
    if [[ $session == "$current" ]]; then
        tmux display-message "Cannot kill current session: $session"
    else
        tmux kill-session -t "$session"
    fi
}

new_session() {
    printf "New session name: " >/dev/tty
    read -r newname </dev/tty
    [[ -n $newname ]] && tmux new-session -d -s "$newname"
}

# 列顺序：NAME WINS PANES CREATED MARK。宽度由 fit_cols 按 popup 实际宽度分配，
# 富余空间给 CREATED；MARK 固定宽度（"(current)" / "(last)"），这样每行等长。
COL_NAME=20
COL_WINS=5
COL_PANES=5
COL_CREATED=13
COL_MARK=10

SESS_COL_PREF='20,5,5,13,10'
SESS_COL_FLOOR='10,4,5,11,9'
SESS_COL_SHRINK='3,0,1,2,4'
SESS_COL_GROW=4
sess_cols() {
    local avail
    avail=$(fzf_table_width)
    if (( avail <= 0 )); then
        COL_NAME=20 COL_WINS=5 COL_PANES=5 COL_CREATED=13 COL_MARK=10
        return
    fi
    fit_cols "$avail" "$SESS_COL_PREF" "$SESS_COL_FLOOR" "$SESS_COL_GROW" "$SESS_COL_SHRINK"
    COL_NAME=${COLS[0]} COL_WINS=${COLS[1]} COL_PANES=${COLS[2]} COL_CREATED=${COLS[3]}
    COL_MARK=${COLS[4]}
}

sessions_src() {
    local current_session last_session
    current_session=$(tmux display-message -p '#S')
    last_session=$(tmux display-message -p '#{client_last_session}')
    sess_cols

    printf '%s  %s  %s  %s  %s\n' \
        "$(fit_col 'NAME' "$COL_NAME")" \
        "$(fit_col 'WINS' "$COL_WINS")" \
        "$(fit_col 'PANES' "$COL_PANES")" \
        "$(fit_col 'CREATED' "$COL_CREATED")" \
        "$(fit_col '' "$COL_MARK")"

    print_line() {
        local name=$1
        local wins panes created marker color
        wins=$(tmux list-windows -t "$name" 2>/dev/null | wc -l | tr -d ' ')
        panes=$(tmux list-panes  -t "$name" -s 2>/dev/null | wc -l | tr -d ' ')
        created=$(tmux display-message -t "$name" -p '#{t/f/%m-%d %H%M:session_created}' 2>/dev/null)

        if [[ $name == "$current_session" ]]; then
            marker=" (current)"; color="1;32"
        elif [[ $name == "$last_session" ]]; then
            marker=" (last)";    color="1;34"
        else
            marker="";           color=""
        fi

        local tail
        tail="$(fit_col "$wins" "$COL_WINS")  $(fit_col "$panes" "$COL_PANES")  $(fit_col "$created" "$COL_CREATED")  $(fit_col "$marker" "$COL_MARK")"
        # SGR 只包住名字本身：即使锚在行首被 --with-nth 截掉，第一列仍是纯文本
        # 会话名，{1} 预览和选中回查都不会拿到转义字符。
        if [[ -n $color ]]; then
            printf '\033[%sm%s\033[0m  %s\n' "$color" "$(fit_col "$name" "$COL_NAME")" "$tail"
        else
            printf '%s  %s\n' "$(fit_col "$name" "$COL_NAME")" "$tail"
        fi
    }

    local printed=()

    # last session first (most likely switch target)
    if [[ -n $last_session && $last_session != "$current_session" ]]; then
        print_line "$last_session"
        printed+=("$last_session")
    fi

    # other sessions alphabetically
    local name p skip
    while read -r name; do
        skip=0
        for p in "${printed[@]}" "$current_session"; do
            [[ $p == "$name" ]] && skip=1 && break
        done
        (( skip )) && continue
        print_line "$name"
    done < <(tmux list-sessions -F '#{session_name}' 2>/dev/null | sort)

    # current session last
    print_line "$current_session"
}

$@
