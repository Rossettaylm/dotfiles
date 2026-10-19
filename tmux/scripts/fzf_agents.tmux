#!/usr/bin/env bash

source "$(dirname "$0")/fzf_utils.sh"

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
    local pane_id
    pane_id=$(strip_ansi "$1")
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
    local script_dir
    script_dir=$(dirname "$0")
    cmd="bash $0 panes_src"
    # 数据源交给 reload 而不是管道：表宽要按 fzf 的真实几何反推，而管道生产者
    # 在 fzf 起来之前就写完输出，环境里没有 FZF_COLUMNS（实测为 0）。start:transform
    # 在布局完成之后执行，此时尺寸可用。
    last_pane_cmd='$(tmux show -gqv "@mru_pane_ids" | cut -d\  -f1)'
    header='enter=go  ctrl-v=move-h  ctrl-s=move-v  ctrl-t=swap  ctrl-x=kill  ctrl-r=reload  ctrl-/=layout  alt-p=preview'
    # --tiebreak=index：匹配分优先，同分才回退到 panes_src 的
    # blocked/unread/working/idle 分组 + 组内 MRU 顺序。曾经用 --no-sort 保序，但它是
    # 「完全忽略匹配分」，会让语义弱匹配（如路径里顺带带 config）压过强匹配（TASK 里
    # 连续命中 config）。query 为空时所有分数相同，index 回退等价于纯输入顺序，分组不丢。
    # --nth=3,6 只搜 PATH 和 TASK（编号相对 --with-nth 输出：1=SESSION … 3=PATH …
    # 6=TASK），否则输 idle/working 会把整张表都命中。
    selected=$(printf '' | fzf -m "${fzf_popup_opts[@]}" \
        --preview="bash $0 preview_pane {1}" \
        --tiebreak=index --nth=3,6 \
        --border-label ' AI Agents ' \
        --header="$header" \
        --delimiter='\s{2,}' --with-nth=2..-1 \
        --bind="start:transform:bash $script_dir/fzf_utils.sh reload $0 panes_src" \
        --bind="ctrl-_:transform:bash $script_dir/fzf_utils.sh toggle_layout $0 panes_src" \
        --bind="alt-e:abort" \
        --bind="alt-p:toggle-preview" \
        --bind="ctrl-r:reload($cmd)" \
        --bind="ctrl-x:execute(bash $0 confirm_kill {1})+reload($cmd)" \
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
            layout='tiled'
        fi

        tmux_cmd+="switch-client -t$id1 \; select-layout -t$id1 $layout \; "
        eval $tmux_cmd
    fi
}

# 列顺序：PANEID SESSION AGENT PATH STATUS AGE TASK（PANEID 被 --with-nth 藏起来，
# 只供选中后回查 pane id）。宽度不再是常量：agent_cols 按 popup 实际宽度分配，
# 富余空间给 TASK，收窄时依次砍 TASK -> PATH -> SESSION -> AGE，其余列是定长内容。
COL_PANEID=6
COL_SESSION=12
COL_AGENT=10
COL_PATH=32
COL_STATUS=11
COL_DUR=7
COL_TASK=27

AGENT_COL_PREF='6,12,10,24,9,5,20'
AGENT_COL_FLOOR='6,10,8,10,9,5,10'
AGENT_COL_SHRINK='3,1,6,5,4,2,0'
AGENT_COL_GROW=6
agent_cols() {
    local avail
    avail=$(fzf_table_width)
    if (( avail <= 0 )); then
        # 拿不到 fzf 尺寸（直接手工跑数据源）：退回固定宽度
        COL_PANEID=6 COL_SESSION=12 COL_AGENT=10 COL_PATH=32 COL_STATUS=11 COL_DUR=7 COL_TASK=27
        return
    fi
    fit_cols "$avail" "$AGENT_COL_PREF" "$AGENT_COL_FLOOR" "$AGENT_COL_GROW" "$AGENT_COL_SHRINK"
    COL_PANEID=${COLS[0]} COL_SESSION=${COLS[1]} COL_AGENT=${COLS[2]} COL_PATH=${COLS[3]}
    COL_STATUS=${COLS[4]} COL_DUR=${COLS[5]} COL_TASK=${COLS[6]}
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
        unread)
            icon=$'\xef\x83\xb3' # U+F0F3 nf-fa-bell
            label='unread'
            color='38;5;117'      # catppuccin sky，与状态栏 ICON_UNREAD 同色
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

# 等待时长只在「球在你这边」时才有意义：blocked 等授权、unread 跑完没看。
# working 的 since 是「开始干活」时长，idle 是「闲了多久」，都是噪音。
# 格式对齐 agent_lib.fmt_duration，别两处漂移。
fmt_age() {
    local state=$1 since=$2
    [[ $state == blocked || $state == unread ]] || return 0
    [[ -n $since && -n $NOW_SECS ]] || return 0
    local secs=$((NOW_SECS - ${since%.*}))
    ((secs < 0)) && return 0
    if ((secs < 60)); then
        printf '%ds' "$secs"
    elif ((secs < 3600)); then
        printf '%dm%02ds' $((secs / 60)) $((secs % 60))
    else
        printf '%dh%02dm' $((secs / 3600)) $(((secs % 3600) / 60))
    fi
}

# 用 execute（而非 execute-silent）弹 y/n：kill 掉正在跑 agent 的 pane 不可撤销，
# 而这个键紧挨着 ctrl-r，误触代价太大。
confirm_kill() {
    local pane_id
    pane_id=$(strip_ansi "$1")
    [[ -n $pane_id ]] || return 0
    printf '\033[1;31m kill pane %s? [y/N] \033[0m' "$pane_id" >/dev/tty
    local answer
    read -r answer </dev/tty
    [[ $answer == y || $answer == Y ]] || return 0
    tmux kill-pane -t "$pane_id"
}

panes_src() {
    agent_cols
    printf '%s  %s  %s  %s  %s  %s  %s\n' \
        "$(fit_col 'PANEID' "$COL_PANEID")" \
        "$(fit_col 'SESSION' "$COL_SESSION")" \
        "$(fit_col 'AGENT' "$COL_AGENT")" \
        "$(fit_col 'PATH' "$COL_PATH")" \
        "$(fit_col 'STATUS' "$COL_STATUS")" \
        "$(fit_col 'AGE' "$COL_DUR")" \
        'TASK'
    # Agent detection and title parsing live in agent_lib.py (shared with the
    # agentd daemon, so both can't drift). It serves the daemon's cache when
    # fresh and falls back to a synchronous scan when the daemon isn't running.
    panes_info=$(python3 "$(dirname "$0")/agent_lib.py" dump)
    # 取一次时间戳给整张表用：每个 pane 各调一次 date 会在 agent 多时明显变慢
    NOW_SECS=$(date +%s)

    c_ids=()
    c_sessions=()
    c_agents=()
    c_paths=()
    c_statuses=()
    c_durs=()
    c_tasks=()
    c_done=()

    # TSV from agent_lib.py: pane_id, session, window_id, agent, path, state,
    # task, since_ts. since_ts 只在这里换算成等待时长；状态栏自己另外格式化。
    collect_pane() {
        local pane_line=$1
        [[ -z $pane_line ]] && return
        local pane_id session window_id agent pane_path status task since
        IFS=$'\t' read -r pane_id session window_id agent pane_path status task since \
            <<<"$pane_line"
        [[ -z $pane_id || -z $agent ]] && return
        [[ -z $status ]] && status='unknown'
        [[ $task == '-' ]] && task=''

        c_ids+=("$pane_id")
        c_sessions+=("$session")
        c_agents+=("$agent")
        c_paths+=("$pane_path")
        c_statuses+=("$status")
        c_durs+=("$(fmt_age "$status" "$since")")
        c_tasks+=("$task")
        c_done+=(0)
    }

    print_collected() {
        local i=$1
        printf '%s  %s  %s  %s  %s  %s  %s\n' \
            "$(fit_col "${c_ids[i]}" "$COL_PANEID")" \
            "$(fit_col "${c_sessions[i]}" "$COL_SESSION")" \
            "$(format_agent "${c_agents[i]}")" \
            "$(fit_col "${c_paths[i]}" "$COL_PATH" tail)" \
            "$(format_status "${c_statuses[i]}")" \
            "$(fit_col "${c_durs[i]}" "$COL_DUR")" \
            "$(fit_col "${c_tasks[i]}" "$COL_TASK")"
        c_done[i]=1
    }

    while IFS= read -r pane_line; do
        collect_pane "$pane_line"
    done <<<"$panes_info"

    mru_ids=($(tmux show -gqv '@mru_pane_ids'))
    local rank mid i
    for rank in blocked unread working idle unknown; do
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
