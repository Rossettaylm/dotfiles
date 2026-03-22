#!/usr/bin/env zsh

# ranger exit to $(pwd)
ranger_cd() {
    temp_file="$(mktemp -t "ranger_cd.XXXXXXXXXX")"
    ranger --choosedir="$temp_file" -- "${@:-$PWD}"
    if chosen_dir="$(cat -- "$temp_file")" && [ -n "$chosen_dir" ] && [ "$chosen_dir" != "$PWD" ]; then
        cd -- "$chosen_dir"
    fi
    rm -f -- "$temp_file"
}

# yazi exit to $(pwd)
y() {
		local tmp="$(mktemp -t "yazi-cwd.XXXXXX")" cwd
		yazi "$@" --cwd-file="$tmp"
		if cwd="$(command cat -- "$tmp")" && [ -n "$cwd" ] && [ "$cwd" != "$PWD" ]; then
			builtin cd -- "$cwd"
		fi
		rm -f -- "$tmp"
}

update () {
    DIR=`dirname $(realpath $0)`
    echo "update $DIR ..."
    git pull 
    git status
}

commit () {
    DIR=`dirname $(realpath $0)`
    echo "checking $DIR status"
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

# 文本匹配
fzg() {
  local RG_PREFIX="rg --column --line-number --no-heading --color=always --smart-case --glob '!{.git,node_modules}'"
  local INITIAL_QUERY="${*:-}"
  fzf --ansi --disabled --query "$INITIAL_QUERY" \
      --bind "start:reload:$RG_PREFIX {q} || true" \
      --bind "change:reload:sleep 0.1; $RG_PREFIX {q} || true" \
      --color "hl:-1:underline,hl+:-1:underline:reverse" \
      --delimiter : \
      --preview 'bat --color=always {1} --highlight-line {2}' \
      --preview-window 'up,60%,border-bottom,+{2}+3/3,~3' \
      --bind 'enter:become(nvim {1} +{2})'
}
