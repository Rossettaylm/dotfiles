#!/usr/bin/env zsh
#        _ _                     
#   __ _| (_) __ _ ___  ___  ___ 
#  / _` | | |/ _` / __|/ _ \/ __|
# | (_| | | | (_| \__ \  __/\__ \
#  \__,_|_|_|\__,_|___/\___||___/
#

# ── 基础工具 ──────────────────────────────────────────────────
alias ls="eza --icons --git"
alias ll="ls -lh"
alias la="ls -a"
alias e="exit"
alias c="clear"
alias sudo="sudo -E"
alias who="who -H"
alias vi="nvim"
alias vim="nvim"
alias make="make -j8"

# ── 系统替代（rust 工具）─────────────────────────────────────
alias top="btm"
alias man="tldr"
alias du="dust"

# ── 导航 ─────────────────────────────────────────────────────
alias ra="ranger_cd"
alias sra="sudo -E ranger_cd"
alias yz="yazi"

if [[ $(which zoxide) && -f $ZSH_HOME/zoxide.zsh ]]; then
    alias cd=z
fi

# ── Zsh 配置 ──────────────────────────────────────────────────
alias szsh="source $HOME/.zshrc"
alias ezsh="nvim $ZSH_HOME/zshrc"
alias na="nvim $ZSH_HOME/aliases.zsh"

# ── 构建工具 ──────────────────────────────────────────────────
alias xm="xmake"
alias xmr="xmake build && xmake run"
alias cmb="cmake_build"
alias cmr="cmake_run"

# ── 环境 ──────────────────────────────────────────────────────
alias base="conda activate base"
alias neo="neofetch"
alias ppath="echo $PATH | tr ':' '\n'"

# ── Brew（fzf 交互）──────────────────────────────────────────
alias bins="python3 $ZSH_HOME/fzf/brew_install.py"
alias buins="python3 $ZSH_HOME/fzf/brew_uninstall.py"

# ── Git ───────────────────────────────────────────────────────
alias gg="git clone"
alias gcb="git checkout -b"
alias gcbbug="git checkout -b personal/lymanyang_bugfix_$(date -u +%Y%m%d)"
alias lg="lazygit"
alias gpu="$HOME/.config/scripts/gpu"

# git fzf 交互
alias gco="python3 $ZSH_HOME/fzf/gco.py"
alias grm="python3 $ZSH_HOME/fzf/git_remove_branch.py"
alias gmg="python3 $ZSH_HOME/fzf/git_merge_branch.py"
alias mma="python3 $ZSH_HOME/fzf/merge_master.py"
alias gcborigin="python3 $ZSH_HOME/fzf/git_checkout_from_origin.py"
alias glog="python3 $ZSH_HOME/fzf/git_log.py | tee >(clipcopy)"
alias gsb="python3 $ZSH_HOME/fzf/git_select_branch.py | tee >(clipcopy)"
alias gb="python3 $ZSH_HOME/fzf/git_show_branches.py | tee >(clipcopy)"
alias curb="python3 $ZSH_HOME/fzf/get_cur_brranch.py | tee >(clipcopy)"

# ── Zellij ────────────────────────────────────────────────────
alias zj="zellij"
alias zja="zellij attach -c"
alias zjs="python3 $ZSH_HOME/fzf/zellij_sessions.py"

# ── fzf 工具 ──────────────────────────────────────────────────
alias f="fzf"
alias fp="python3 $ZSH_HOME/fzf/file_preview.py"
alias fpath="echo $PATH | tr ':' '\n' | fzf --header='[Find Path]'"
alias kp="python3 $ZSH_HOME/fzf/kp"
alias ks="python3 $ZSH_HOME/fzf/ks"

# ── Android / QQ 工程 ─────────────────────────────────────────
alias adbid="adb devices | grep -v List | awk '{print \$1}'"
alias sp="nohup scrcpy > $HOME/templog/scrcpy.log 2>&1 &"
alias qclone="git clone git@git.woa.com:mobileqq/AndroidQQ.git"
alias qguild="./centaur.sh guild -w"
alias qrundt="./rb -qrun -PDTBuild"
alias qrun="./rb -qrun"
alias qclean="./rb -clean"
alias qhelp="./rb -help"
alias qins="adb install -r AQQLite/AQQLiteApp/build/intermediates/qqLite/compact/signed/compact.apk"

# ── 其他 ──────────────────────────────────────────────────────
alias cr="cargo run"
alias cld="claude"
alias cldi="claude-internal"
