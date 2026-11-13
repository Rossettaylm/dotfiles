#!/usr/bin/env zsh

# yazi exit to $(pwd)
y() {
		local tmp="$(mktemp -t "yazi-cwd.XXXXXX")" cwd
		FZF_DEFAULT_COMMAND="fd --hidden --no-ignore-vcs --exclude .git" yazi "$@" --cwd-file="$tmp"
		if cwd="$(command cat -- "$tmp")" && [ -n "$cwd" ] && [ "$cwd" != "$PWD" ]; then
			builtin cd -- "$cwd"
		fi
		rm -f -- "$tmp"
}

update () {
    echo "update $(pwd) ..."
    git pull
    git status
}

commit () {
    echo "checking $(pwd) status"
    git status
    printf "Commit and Push your changes? [ y / n ]\n"
    read msg
    if [ "${msg}" = "y" ]; then
        printf "\n>>>>>>>>>>add / commit current changes<<<<<<<<<<\n"
        git add .
        git commit -a
        printf "\n>>>>>>>>>> push current changes <<<<<<<<<<\n"
        git push
        git status
    else
        printf "Nothing gonna be changed!\n"
    fi
}

set_proxy () {
    export LOCAL_IP=$(cat /etc/resolv.conf | grep nameserver | cut -d ' ' -f 2)
    export ALL_PROXY="http://${LOCAL_IP}:7890"
		unset LOCAL_IP
    git config --global http.proxy "${ALL_PROXY}"
    git config --global https.proxy "${ALL_PROXY}"
}


unset_proxy () {
    unset all_proxy
    git config --global --unset http.proxy
    git config --global --unset https.proxy 
}

test_proxy() {
    resp=$(curl -I -s --connect-timeout 5 -m 5 -w "%{http_code}" -o /dev/null www.google.com)
    if [ ${resp} = 200 ]; then
        echo "State Code: $resp, Proxy setup succeeded!"
    else
        echo "State Code: $resp, Proxy setup failed!"
    fi
}

# ssh() {
# 	command ssh "$@"
# 	local ret=$?
# 	# SSH 断开后重置终端状态，防止转义序列残留导致乱码
# 	printf '\033[?1000l\033[?1006l\033[?1049l\033[?25h\033c'
# 	stty sane 2>/dev/null
# 	return $ret
# }

cmake_build() {
	# if "build"" is exist or "build" is not empty
	if [[ -f "./CMakeLists.txt" ]]; then
		if [[ -d "./build" ]]; then
			cmake -B ./build && cmake --build "./build"
		else 
			mkdir ./build && cmake -B ./build && cmake --build "./build"
		fi
	fi
}

cmake_run() {
	if [[ -f "./CMakeLists.txt" ]]; then 
		local PROCESS=$(cat "./CMakeLists.txt" | grep add_executable | cut -d '(' -f 2 | cut -d ' ' -f 1)
		if [[ -n ${PROCESS} && -f "./build/${PROCESS}" ]]; then 
			./build/${PROCESS}
		fi
	fi
}

function print_lib_path() {
	gcc -print-search-dirs | awk -F'[:=]' '/libraries/ { for(i=2; i<=NF; i++) print $i }' | bat
}

function print_include_path() {
	gcc -xc++ -E -Wp,-v - </dev/null
}

function print_success_text() {
  local text="$1"
  echo -e "\033[32m${text}\033[0m"
}

function print_fail_text() {
  local text="$1"
  echo -e "\033[31m${text}\033[0m"
}

# fzf 选择 adb 设备
fadb() {
  local s
  s=$(python3 $ZSH_HOME/fzf/system/adb_device.py) && export ANDROID_SERIAL="$s" && echo "ANDROID_SERIAL=$s"
}

# 文本匹配
# $HOME/zsh/fzf/file/file_preview.py 替代
# fzg() {
#   local RG_PREFIX="rg --column --line-number --no-heading --color=always --smart-case --glob '!{.git,node_modules}'"
#   local INITIAL_QUERY="${*:-}"
#   fzf --ansi --disabled --query "$INITIAL_QUERY" \
#       --bind "start:reload:$RG_PREFIX {q} || true" \
#       --bind "change:reload:sleep 0.1; $RG_PREFIX {q} || true" \
#       --color "hl:-1:underline,hl+:-1:underline:reverse" \
#       --delimiter : \
#       --preview 'bat --color=always {1} --highlight-line {2}' \
#       --preview-window 'up,60%,border-bottom,+{2}+3/3,~3' \
#       --bind 'enter:become(nvim {1} +{2})'
# }

# git log
glog() { python3 $ZSH_HOME/fzf/git/git_log.py "$@" | tee >(cb); }

# 交互式浏览命令（alias/function/script），选中后注入 zsh buffer
utils() {
  local cmd
  cmd=$(python3 $ZSH_HOME/fzf/utils.py "$@")
  [[ -n "$cmd" ]] && print -z "$cmd"
}

# 输出倒数第 N 条命令（默认 1=上一条）的输出；依赖 prompt.zsh 的 OSC 133 标记，仅限 tmux
_last_output() {
  local n=${1:-1}
  [[ -n $TMUX ]] || { print -u2 "需要在 tmux 中使用"; return 1 }
  [[ $n == <1-> ]] || { print -u2 "用法: ${funcstack[2]:-$0} [N]"; return 1 }
  local p=$TMUX_PANE pos='#{e|-:#{copy_cursor_y},#{scroll_position}}' cur last i
  tmux copy-mode -H -t $p
  # 第 1 跳落在当前 prompt，再往上 N 跳是目标；send -N 对 previous-prompt 不生效，只能逐跳
  for i in {1..$n}; do
    cur=$(tmux send -t $p -X previous-prompt \; display -p -t $p $pos)
    [[ $cur == $last ]] && { tmux send -t $p -X cancel; print -u2 "scrollback 中找不到第 $n 条命令"; return 1 }
    last=$cur
  done
  # 依次输出：上一跳 prompt、目标 prompt、下一条 prompt、目标输出起点（坐标均为 capture-pane 行号）
  local -a cmd=(display -p -t $p $pos \; send -t $p -X previous-prompt \; display -p -t $p $pos
        \; send -t $p -X next-prompt \; display -p -t $p $pos
        \; send -t $p -X previous-prompt \; send -t $p -X next-prompt -o \; display -p -t $p $pos
        \; send -t $p -X cancel)
  local -a r=(${(f)"$(tmux $cmd)"})
  (( ${#r} == 4 )) || { print -u2 "tmux 坐标获取失败"; return 1 }
  local prev=$r[1] a=$r[2] e=$r[3] c=$r[4]
  (( a < prev )) || { print -u2 "scrollback 中找不到第 $n 条命令"; return 1 }
  (( c > a && c < e )) || { print -u2 "第 $n 条命令无输出"; return 1 }
  tmux capture-pane -p -J -t $p -S $c -E $((e - 1)) | sed -E 's/[[:space:]]+$//'
}

# 全量复制上 N 条命令的输出到剪贴板
cpo() {
  local out
  out=$(_last_output "$@") || return
  print -rn -- "$out" | pbcopy
  local -a lines=("${(@f)out}")
  print "已复制 ${#lines} 行"
}

# 在 nvim scratch 中打开上 N 条命令的输出，自行选择 y 复制，q 退出
cpv() {
  local out
  out=$(_last_output "$@") || return
  print -r -- "$out" | nvim -n \
    -c 'setlocal buftype=nofile bufhidden=wipe noswapfile' \
    -c 'nnoremap <buffer><nowait> q <cmd>q!<CR>' -
}
