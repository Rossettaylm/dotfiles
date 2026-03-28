#!/usr/bin/env zsh

alias ls="eza --icons --git"
alias ll="ls -lh"
alias la="ls -a"
# alias setproxy="export http_proxy='http://127.0.0.1:7890' && export https_proxy='https://127.0.0.1:7890'"
# alias unsetproxy="unset http_proxy && unset https_proxy"
alias e="exit"
alias sudo="sudo -E"
alias neo='neofetch'
alias ra='ranger_cd'
alias who="who -H"
alias c="clear"
alias szsh="source $HOME/.zshrc"
alias ezsh="nvim $ZSH_HOME/zshrc"
alias base="conda activate base"
alias sra='sudo -E ranger_cd'
alias vi="nvim"
alias vim='nvim'
alias gg='git clone'
alias up='sudo pacman -Syyu'
alias clip='xclip -selection c'
alias px='proxychains'
alias xm="xmake"
alias xmr="xmake build && xmake run"
alias sdrnow="shutdown -r now"
alias sdnow="shutdown now"
alias cmb="cmake_build"
alias cmr="cmake_run"
alias make="make -j8"
# alias qbuild="./rb -qC"
# 秒编插件 -w 编译失败可选择是否继续编译
# alias qrunq="./centaur.sh guild -w"
alias qguild="./centaur.sh guild -w"
# 带大同插桩的编译
alias qrundt="./rb -qrun -PDTBuild"
alias qrun="./rb -qrun"
alias qc="./rb -qC && cp $(pwd)/AQQLite/AQQLiteApp/build/intermediates/qqLite/compact/signed/compact.apk $HOME/Downloads/apk/"
alias qins="adb install -r $(pwd)/AQQLite/AQQLiteApp/build/intermediates/qqLite/compact/signed/compact.apk"
alias qclone="git clone git@git.woa.com:mobileqq/AndroidQQ.git"
# alias adb="$HOME/.config/scripts/adb.sh"
alias qins="adb install -r AQQLite/AQQLiteApp/build/intermediates/qqLite/compact/signed/compact.apk"
alias qclean="./rb -clean"
alias qhelp="./rb -help"
# scrcpy
alias sp="nohup scrcpy > $HOME/templog/scrcpy.log 2>&1 &"
alias yz="yazi"
# echopath
alias ppath="echo $PATH | tr ':' '\n'"
alias fpath="echo $PATH | tr ':' '\n' | fzf --header='[Find Path]'"

if [[ $(which zoxide) && -f $ZSH_HOME/zoxide.zsh ]]; then 
	alias cd=z
fi

# nvim aliases.zsh
alias na="nvim $ZSH_HOME/aliases.zsh"

# fzf
alias f="fzf"

# brew install/uninstall
alias bins="python3 $ZSH_HOME/fzf/brew_install.py"
alias buins="python3 $ZSH_HOME/fzf/brew_uninstall.py"


#   ____ _ _     ____          _____     __ 
#  / ___(_) |_  | __ ) _   _  |  ___|___/ _|
# | |  _| | __| |  _ \| | | | | |_ |_  / |_ 
# | |_| | | |_  | |_) | |_| | |  _| / /|  _|
#  \____|_|\__| |____/ \__, | |_|  /___|_|  
#                      |___/                
# git checkout by fzf
alias gco="$ZSH_HOME/fzf/gco.sh"
# alias gco="$HOME/.config/zsh/fzf/gco.sh"
# git remove branch by fzf
alias grm="python3 $ZSH_HOME/fzf/git_remove_branch.py"
# git merge by fzf
alias gmg="python3 $ZSH_HOME/fzf/git_merge_branch.py"
alias gcb="git checkout -b"
alias gcbbug="git checkout -b personal/lymanyang_bugfix_$(date -u +%Y%m%d)"
# get_cur_brranch && copy
alias curb="python3 $HOME/.config/zsh/fzf/get_cur_brranch.py | tee >(clipcopy)"
# select branch
alias gb="python3 $HOME/.config/zsh/fzf/git_show_branches.py | tee >(clipcopy)"
# merge_master
alias mma="python3 $HOME/.config/zsh/fzf/merge_master.py"
# git chekcout -b ... origin/... by fzf
alias gcborigin="python3 $HOME/.config/zsh/fzf/git_checkout_from_origin.py"
# git log for fzf
alias glog="$HOME/.config/zsh/fzf/git_log.sh | tee >(clipcopy)"
# git select branch and copy
alias gsb="python3 $HOME/.config/zsh/fzf/git_select_branch.py | tee >(clipcopy)"
# lazygit
alias lg="lazygit"

alias adbid="adb devices | grep -v List | awk '{print \$1}'"

# zellij 终端复用
alias zj="zellij"
alias zja="zellij attach -c"
alias zjs="python3 $HOME/.config/zsh/fzf/zellij_sessions.py"
# git push --set-upstream
alias gpu="$HOME/.config/scripts/gpu"
# 一些rust软件用于替代原来的系统软件
# 系统监控,替代top命令
alias top="btm"
# tldr 命令手册
alias man="tldr"
# dust to du 查看目录文件大小
alias du="dust"
# claude code
# alias cld="claude"
alias cld="claude-internal"

# file_ preview with fzf
alias fp="$HOME/.config/zsh/fzf/file_preview.sh"
alias cr="cargo run"
