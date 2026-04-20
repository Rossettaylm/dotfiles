#!/usr/bin/env bash

do_action() {
    [[ -x $(command -v fzf 2>/dev/null) ]] || return

    current_session=$(tmux display-message -p '#S')
    cmd="bash $0 sessions_src"

    header="enter=switch  ctrl-r=rename  alt-bspace=kill  ctrl-n=new  ctrl-f=reload"

    selected=$(FZF_DEFAULT_COMMAND="$cmd" fzf \
        --ansi \
        --color='bg:-1,bg+:-1' \
        --reverse \
        --info=inline \
        --header-lines=1 \
        --header="$header" \
        --no-preview \
        --delimiter='\s{2,}' \
        --with-nth=2.. \
        --nth=1,2 \
        --bind="ctrl-f:reload($cmd)" \
        --bind="ctrl-r:execute(bash $0 rename_session {1})+reload($cmd)" \
        --bind="alt-bspace:execute-silent(bash $0 kill_session {1})+reload($cmd)" \
        --bind="ctrl-n:execute(bash $0 new_session)+reload($cmd)" \
    )

    [[ -z $selected ]] && return

    session=$(awk '{print $1}' <<<"$selected")
    [[ -n $session ]] && tmux switch-client -t "$session"
}

rename_session() {
    local session=$1
    printf "Rename [%s] → " "$session" >/dev/tty
    read -r newname </dev/tty
    [[ -n $newname ]] && tmux rename-session -t "$session" "$newname"
}

kill_session() {
    local session=$1
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

sessions_src() {
    local current_session last_session
    current_session=$(tmux display-message -p '#S')
    last_session=$(tmux display-message -p '#{client_last_session}')

    printf "%-20s  %-20s  %-5s  %-5s  %s\n" 'NAME' 'SESSION' 'WINS' 'PANES' 'CREATED'

    print_line() {
        local name=$1
        local wins panes created marker color
        wins=$(tmux list-windows -t "$name" 2>/dev/null | wc -l | tr -d ' ')
        panes=$(tmux list-panes  -t "$name" -s 2>/dev/null | wc -l | tr -d ' ')
        created=$(tmux display-message -t "$name" -p '#{t/f/%m-%d %H:%M:session_created}' 2>/dev/null)

        if [[ $name == "$current_session" ]]; then
            marker=" (current)"; color="1;32"
        elif [[ $name == "$last_session" ]]; then
            marker=" (last)";    color="1;34"
        else
            marker="";           color=""
        fi

        local display
        printf -v display "%-20s  %-5s  %-5s  %s%s" "$name" "$wins" "$panes" "$created" "$marker"
        if [[ -n $color ]]; then
            printf "%-20s  \033[%sm%s\033[0m\n" "$name" "$color" "$display"
        else
            printf "%-20s  %s\n" "$name" "$display"
        fi
    }

    local printed=()

    # last session first (most likely switch target)
    if [[ -n $last_session && $last_session != "$current_session" ]]; then
        print_line "$last_session"
        printed+=("$last_session")
    fi

    # other sessions alphabetically
    while read -r name; do
        local skip=0
        for p in "${printed[@]}" "$current_session"; do [[ $p == "$name" ]] && skip=1 && break; done
        (( skip )) && continue
        print_line "$name"
    done < <(tmux list-sessions -F '#{session_name}' 2>/dev/null | sort)

    # current session last
    print_line "$current_session"
}

$@
