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
    header='enter=go  ctrl-v=move-h  ctrl-s=move-v  ctrl-t=swap  ctrl-x=kill  ctrl-r=reload  alt-p=preview'
    # --tiebreak=index：匹配分优先，同分才回退到 panes_src 的
    # blocked/unread/working/idle 分组 + 组内 MRU 顺序。曾经用 --no-sort 保序，但它是
    # 「完全忽略匹配分」，会让语义弱匹配（如路径里顺带带 config）压过强匹配（TASK 里
    # 连续命中 config）。query 为空时所有分数相同，index 回退等价于纯输入顺序，分组不丢。
    # --nth=3,6 只搜 PATH 和 TASK（编号相对 --with-nth 输出：1=SESSION … 3=PATH …
    # 6=TASK），否则输 idle/working 会把整张表都命中。
    selected=$(bash $0 panes_src | fzf -m --ansi --preview="$preview_cmd" \
        --tiebreak=index --nth=3,6 \
        --popup center,100%,85% \
        --border-label ' AI Agents ' \
        --header="$header" \
        --preview-window='bottom:70%' --reverse --info=inline --header-lines=1 \
        --delimiter='\s{2,}' --with-nth=2..-1 \
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

# Display-column helpers. 每列宽度是「显示列数」，不是字符数 —— 见下面 dwidth。
# Columns are joined with two spaces so fzf --delimiter='\s{2,}' still works.
COL_PANEID=6
COL_SESSION=12
COL_AGENT=10
COL_PATH=32
COL_STATUS=11
# 列宽预算：popup 是 -w 100%，可见宽度 = client 宽 - 8（被 --with-nth 藏掉的
# PANEID 列 + 6 个分隔符 + fzf 左侧留白）。client 119 时可见 109 列，正好装下
# 6+12+10+32+11+7+27 + 12 个分隔符 = 117 减去藏掉的 8。改列宽要重算这笔账。
COL_DUR=7
COL_TASK=27

# ── 显示宽度 ─────────────────────────────────────────────────
# 中文任务名/路径占 2 列，Nerd Font 图标占 1 列。按 ${#text} 数「字符数」排版
# 会让含中文的行冲出 popup（实测 27 字符的中文任务渲染 36 列，整行被 fzf 裁掉
# 尾巴）。这里按 East Asian Width 的 W/F 判定算真实列数。
WIDE="4352 4447 8986 8987 9001 9002 9193 9196 9200 9200 9203 9203 9725 9726 9748 9749 9800 9811 9855 9855 9875 9875 9889 9889 9898 9899 9917 9918 9924 9925 9934 9934 9940 9940 9962 9962 9970 9973 9978 9978 9981 9981 9989 9989 9994 9995 10024 10024 10060 10062 10067 10071 10133 10135 10160 10160 10175 10175 11035 11036 11088 11088 11093 11093 11904 12019 12032 12245 12272 12283 12288 12350 12353 12438 12441 12543 12549 12771 12784 12871 12880 19903 19968 42124 42128 42182 43360 43388 44032 55203 63744 64109 64112 64217 65040 65049 65072 65131 65281 65376 65504 65510 94176 94180 94192 94193 94208 100343 100352 101589 101632 101640 110576 110882 110928 110930 110948 110951 110960 111355 126980 126980 127183 127183 127374 127374 127377 127386 127488 127490 127504 127547 127552 127560 127568 127569 127584 127589 127744 127776 127789 127891 127904 127946 127951 127955 127968 127984 127988 127988 127992 128252 128255 128317 128331 128359 128378 128378 128405 128406 128420 128420 128507 128591 128640 128709 128716 128716 128720 128722 128725 128727 128733 128735 128747 128748 128756 128764 128992 129003 129008 129008 129292 129535 129648 129652 129656 129660 129664 129670 129680 129708 129712 129722 129728 129733 129744 129753 129760 129767 129776 129782 131072 173791 173824 177976 177984 178205 178208 183969 183984 191456 194560 195101 196608 201546"
read -r -a WIDE <<<"$WIDE"
WIDE_N=${#WIDE[@]}

# 码点是否落在 W/F 区间里（二分）。只收已分配码点，未分配的和 Python
# unicodedata 的判定一致地算窄 —— 真实文本里不会出现。
cp_wide() {
    local cp=$1
    local lo=0
    local hi=$(( WIDE_N / 2 - 1 ))
    local mid a b
    while (( lo <= hi )); do
        mid=$(( (lo + hi) / 2 ))
        a=${WIDE[mid * 2]}
        b=${WIDE[mid * 2 + 1]}
        if (( cp < a )); then
            hi=$(( mid - 1 ))
        elif (( cp > b )); then
            lo=$(( mid + 1 ))
        else
            return 0
        fi
    done
    return 1
}

# 单个字符占几列。UTF-8 首字节自描述长度，手写解码比 fork python 快两个数量级。
# 结果写进全局 CW 而不是 stdout：$(cwidth ...) 每个字符 fork 一次子 shell，
# 20 个 agent 的表格要 6 秒；改成全局变量后同样输入 0.1 秒。
# LC_ALL=C 让 ${c:i:1} 按字节切片；注意每个 local 单独一行 —— bash 3.2 会先
# 展开整行的所有词再赋值，`local a=$1 b=${#a}` 里的 ${#a} 取到的是调用方的 a。
CW=1
cwidth() {
    local c=$1
    local LC_ALL=C
    local b0 b1 b2 b3 cp
    printf -v b0 '%d' "'${c:0:1}"
    (( b0 < 0 )) && b0=$(( b0 + 256 ))
    if (( b0 < 0x80 )); then
        CW=1
        return
    fi
    printf -v b1 '%d' "'${c:1:1}"
    (( b1 < 0 )) && b1=$(( b1 + 256 ))
    if (( b0 < 0xE0 )); then
        cp=$(( (b0 & 0x1F) << 6 | (b1 & 0x3F) ))
        if cp_wide "$cp"; then CW=2; else CW=1; fi
        return
    fi
    printf -v b2 '%d' "'${c:2:1}"
    (( b2 < 0 )) && b2=$(( b2 + 256 ))
    if (( b0 < 0xF0 )); then
        cp=$(( (b0 & 0x0F) << 12 | (b1 & 0x3F) << 6 | (b2 & 0x3F) ))
        if cp_wide "$cp"; then CW=2; else CW=1; fi
        return
    fi
    printf -v b3 '%d' "'${c:3:1}"
    (( b3 < 0 )) && b3=$(( b3 + 256 ))
    cp=$(( (b0 & 0x07) << 18 | (b1 & 0x3F) << 12 | (b2 & 0x3F) << 6 | (b3 & 0x3F) ))
    if cp_wide "$cp"; then CW=2; else CW=1; fi
}

# 整串的字节数。自带 LC_ALL=C 作用域，不污染调用方 —— 调用方必须保持 UTF-8，
# 否则 ${text:i:1} 会按字节切片，把一个 3 字节的字符劈成三个乱码字节。
byte_len() {
    local text=$1
    local LC_ALL=C
    printf '%s' "${#text}"
}

dwidth() {
    local text=$1
    local i=0
    local w=0
    local n=${#text}
    # 纯 ASCII 时字符数 == 字节数 == 列数。表格里 PATH/SESSION/TASK 多数时候是
    # ASCII，这条快路径省掉整个逐字符解码循环。
    if (( n == $(byte_len "$text") )); then
        printf '%s' "$n"
        return
    fi
    while (( i < n )); do
        cwidth "${text:i:1}"
        w=$(( w + CW ))
        (( i++ ))
    done
    printf '%s' "$w"
}

# 按显示列数裁剪 + 右侧补空格到 width 列。tail 模式从尾部截（路径更关心末端）。
fit_col() {
    local text=$1
    local width=$2
    local mode=${3:-head}
    local len
    len=$(dwidth "$text")
    if (( len > width )); then
        local budget=$(( width - 1 ))
        local acc=0
        local i c
        local out=''
        if [[ $mode == tail ]]; then
            i=${#text}
            while (( i > 0 )); do
                c=${text:i-1:1}
                cwidth "$c"
                (( acc + CW > budget )) && break
                out="$c$out"
                acc=$(( acc + CW ))
                i=$(( i - 1 ))
            done
        else
            i=0
            local n=${#text}
            while (( i < n )); do
                c=${text:i:1}
                cwidth "$c"
                (( acc + CW > budget )) && break
                out="$out$c"
                acc=$(( acc + CW ))
                i=$(( i + 1 ))
            done
        fi
        # 必须写成 "${out}…"：bash 3.2 里 "$out…" 会把 … 的首字节当成变量名
        # 的一部分吃掉，只留下 \x80\xa6 两个残字节
        text="${out}…"
        len=$(( acc + 1 ))
    fi
    printf '%s%*s' "$text" $(( width - len )) ''
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
    local pane_id=$1
    [[ -n $pane_id ]] || return 0
    printf '\033[1;31m kill pane %s? [y/N] \033[0m' "$pane_id" >/dev/tty
    local answer
    read -r answer </dev/tty
    [[ $answer == y || $answer == Y ]] || return 0
    tmux kill-pane -t "$pane_id"
}

panes_src() {
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
