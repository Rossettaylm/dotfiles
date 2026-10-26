#!/usr/bin/env bash

# Shared utilities for fzf-based tmux popups (fzf_agents.tmux, fzf_sessions.tmux):
# popup 布局、布局切换、按显示列数的列宽计算与裁切。

# ── 弹窗布局 ─────────────────────────────────────────────────
# 预览面板位置。布局状态存 tmux 全局选项，重开 popup 保持上次选择；默认左右。
FZF_LAYOUT_OPT='@fzf_popup_layout'
FZF_POPUP_SPEC='center,100%,85%'
FZF_PREVIEW_RIGHT='right,35%,border-left,wrap'
FZF_PREVIEW_DOWN='down,70%,border-top,wrap'

fzf_layout_get() {
    local v
    v=$(tmux show -gqv "$FZF_LAYOUT_OPT" 2>/dev/null)
    [[ $v == down ]] && echo down || echo right
}

fzf_layout_preview_window() {
    [[ $(fzf_layout_get) == down ]] && echo "$FZF_PREVIEW_DOWN" || echo "$FZF_PREVIEW_RIGHT"
}

# 两个 popup 共用的 fzf 参数。--popup 之下 FZF_DEFAULT_OPTS 的 --height/--border 会被忽略。
fzf_popup_opts=(
    --ansi
    --color='bg:-1,bg+:#313244,fg:#a6adc8,fg+:#cdd6f4:bold'
    --color='hl:#f38ba8,hl+:#f38ba8:bold,pointer:#f5c2e7,marker:#a6e3a1'
    --color='prompt:#cba6f7,query:#cdd6f4:bold,info:#6c7086,spinner:#f5c2e7'
    --color='header:#7f849c,border:#585b70,label:#cba6f7:bold,preview-border:#45475a,separator:#45475a'
    --highlight-line
    --reverse
    --info=inline
    --header-lines=1
    --popup "$FZF_POPUP_SPEC"
    --preview-window "$(fzf_layout_preview_window)"
)

# 给 --bind 'start:transform:' / 'ctrl-_:transform:' 用，输出要执行的动作串。
# 初次加载和切布局都走 reload：数据源是 `src | fzf` 的管道生产者，在 fzf 启动前
# 就写完了，环境里没有 FZF_COLUMNS，表宽只能靠 reload 子进程拿到的真实尺寸反推。
# transform 在 fzf 完成布局之后执行，实测此时 FZF_COLUMNS/PREVIEW_COLUMNS 已可用；
# 而 start:reload 直接挂在 start 事件上读到的是 0。
fzf_action_reload() {
    printf 'reload(bash %s %s)' "$1" "$2"
}

fzf_action_toggle_layout() {
    local script=$1 subcmd=$2 next spec
    if [[ $(fzf_layout_get) == down ]]; then next=right; else next=down; fi
    tmux set -g "$FZF_LAYOUT_OPT" "$next"
    spec=$(fzf_layout_preview_window)
    # change-preview-window 先于 reload 生效，reload 子进程读到的已经是新布局尺寸
    printf 'change-preview-window(%s)+%s' "$spec" "$(fzf_action_reload "$script" "$subcmd")"
}

# 一行里真正能放多少列（不含行内分隔符）。0 表示拿不到 fzf 实际尺寸。
# 实测 fzf 0.74.1，client 126 列 → popup 内部 FZF_COLUMNS=122：
#   right 35%: FZF_COLUMNS - PREVIEW_COLUMNS - 5 = 78
#   down 70% : FZF_COLUMNS - 2 = 120
# 实测法：往列表里塞定长行，看多长开始被替换成 ··。right 布局扣掉左侧指针
# 「▌ 」的 2 列 + 右侧 2 列内边距 + 1 列分隔；down 布局只有上下两条边框。
# down 布局下 FZF_PREVIEW_COLUMNS 等于 FZF_COLUMNS，不能拿来做减法，所以分支
# 只能按布局状态走，不能看 PREVIEW_COLUMNS 有没有变小。
fzf_table_width() {
    local cols=${FZF_COLUMNS:-0} prev=${FZF_PREVIEW_COLUMNS:-0}
    if (( cols <= 0 )); then
        echo 0
        return
    fi
    if [[ $(fzf_layout_get) == right ]]; then
        cols=$(( cols - prev - 5 ))
    else
        cols=$(( cols - 2 ))
    fi
    (( cols > 0 )) || cols=0
    echo "$cols"
}

# 按可用列数分配各列宽度。列之间固定两个空格，所以 avail 里先扣掉 2*(n-1)。
# 空间富余时全给 grow 指定的列；不够时按 shrink 顺序把该列压到 floor，压完
# 还不够再压下一个。结果写进全局数组 COLS。
#   fit_cols <avail> <pref_csv> <floor_csv> <grow_idx> <shrink_csv>
fit_cols() {
    local avail=$1 grow=$4 order_csv=$5
    local -a pref floor order
    IFS=, read -r -a pref <<<"$2"
    IFS=, read -r -a floor <<<"$3"
    IFS=, read -r -a order <<<"$order_csv"
    local n=${#pref[@]}
    local sep=$(( 2 * (n - 1) ))
    local sum=0 i
    COLS=()
    for (( i = 0; i < n; i++ )); do
        COLS[i]=${pref[i]}
        sum=$(( sum + COLS[i] ))
    done
    avail=$(( avail - sep ))
    local rest=$(( avail - sum ))
    if (( rest >= 0 )); then
        COLS[grow]=$(( COLS[grow] + rest ))
        return 0
    fi
    local over=$(( -rest )) idx cap
    for idx in "${order[@]}"; do
        (( over <= 0 )) && break
        cap=$(( COLS[idx] - floor[idx] ))
        (( cap <= 0 )) && continue
        if (( cap >= over )); then
            COLS[idx]=$(( COLS[idx] - over ))
            over=0
        else
            COLS[idx]=${floor[idx]}
            over=$(( over - cap ))
        fi
    done
}

# 直接执行时的 CLI，供 fzf --bind 调用：
#   bash fzf_utils.sh reload <script> <subcmd>
#   bash fzf_utils.sh toggle_layout <script> <subcmd>
if [[ ${BASH_SOURCE[0]} == "$0" ]]; then
    case $1 in
        reload)
            shift
            fzf_action_reload "$@"
            ;;
        toggle_layout)
            shift
            fzf_action_toggle_layout "$@"
            ;;
        *)
            echo "usage: $0 reload|toggle_layout <script> <subcmd>" >&2
            exit 1
            ;;
    esac
    exit 0
fi

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

# fzf 的 {1} 保留原始行的 SGR，给 shell 函数用之前必须剥掉。
strip_ansi() {
    printf '%s' "$1" | sed $'s/\033\\[[0-9;]*m//g'
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
