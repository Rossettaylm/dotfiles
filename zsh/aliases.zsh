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
alias yz="yazi"

if (( $+commands[zoxide] )) && [[ -f $ZSH_HOME/zoxide.zsh ]]; then
    alias cd=z
fi

# ── Zsh 配置 ──────────────────────────────────────────────────
alias szsh="source $HOME/.zshrc"
alias ezsh="nvim $ZSH_HOME/zshrc"
alias na="nvim $ZSH_HOME/aliases.zsh"

# ── 构建工具 ──────────────────────────────────────────────────
alias cmb="cmake_build"
alias cmr="cmake_run"

# ── 环境 ──────────────────────────────────────────────────────
alias base="conda activate base"
alias neo="neofetch"
alias ppath='echo $PATH | tr ":" "\n"'

# ── Brew（fzf 交互）──────────────────────────────────────────
alias bins="python3 $ZSH_HOME/fzf/brew/brew_install.py"
alias buins="python3 $ZSH_HOME/fzf/brew/brew_uninstall.py"

# ── Git ───────────────────────────────────────────────────────
alias gl="git pull"
alias gp="git push"
alias gst="git status"
alias gg="git clone"
alias gcb="git checkout -b"
alias gcbbug="git checkout -b personal/lymanyang_bugfix_$(date -u +%Y%m%d)"
alias lg="lazygit"
alias gpu="$HOME/.config/scripts/gpu"

# git fzf 交互
alias gco="python3 $ZSH_HOME/fzf/git/gco.py"
alias grm="python3 $ZSH_HOME/fzf/git/git_remove_branch.py"
alias gmg="python3 $ZSH_HOME/fzf/git/git_merge_branch.py"
alias mma="python3 $ZSH_HOME/fzf/git/merge_master.py"
alias gcborigin="python3 $ZSH_HOME/fzf/git/git_checkout_from_origin.py"
alias glog="python3 $ZSH_HOME/fzf/git/git_log.py | tee >(clipcopy)"
alias fstash="python3 $ZSH_HOME/fzf/git/git_stash.py"
alias gcp="python3 $ZSH_HOME/fzf/git/git_cherry_pick.py"
alias gsb="python3 $ZSH_HOME/fzf/git/git_select_branch.py | tee >(clipcopy)"
alias gb="python3 $ZSH_HOME/fzf/git/git_show_branches.py | tee >(clipcopy)"
alias curb="python3 $ZSH_HOME/fzf/git/get_cur_branch.py | tee >(clipcopy)"

# ── Zellij ────────────────────────────────────────────────────
alias zj="zellij"
alias zja="zellij attach -c"
alias zjr="zellij run -i -- "
alias zjs="python3 $ZSH_HOME/fzf/system/zellij_sessions.py"
alias zjt="python3 $ZSH_HOME/fzf/system/zellij_tabs.py"

# ── fzf 工具 ──────────────────────────────────────────────────
alias f="fzf"
alias fp="python3 $ZSH_HOME/fzf/file/file_preview.py"
alias fpath='echo $PATH | tr ":" "\n" | fzf --header="[Find Path]"'
alias kp="python3 $ZSH_HOME/fzf/process/kill_process.py"
alias ks="python3 $ZSH_HOME/fzf/process/kill_socket.py"
alias cmds="python3 $ZSH_HOME/fzf/utils.py"
alias fssh="python3 $ZSH_HOME/fzf/system/ssh_connect.py"
alias fenv="python3 $ZSH_HOME/fzf/system/env_browser.py"
alias ffile="python3 $ZSH_HOME/fzf/file/recent_files.py"
alias fman="python3 $ZSH_HOME/fzf/system/tldr_browser.py"
alias fapp="python3 $ZSH_HOME/fzf/system/app_launcher.py"

# ── Android / QQ 工程 ─────────────────────────────────────────
alias adbid="adb devices | grep -v List | awk '{print \$1}'"
alias sp="nohup scrcpy > $HOME/templog/scrcpy.log 2>&1 &"
alias qclone="git clone git@git.woa.com:mobileqq/AndroidQQ.git"
alias qguild="./centaur.sh guild -w"
alias qrundt="./rb -qrun -PDTBuild"
alias qrun="./rb -qrun"
alias qc="./rb -qC"
alias qcdt="./rb -qC -PDTBuild"
alias qclean="./rb -clean"
alias qhelp="./rb -help"
alias qins="adb install -r AQQLite/AQQLiteApp/build/intermediates/qqLite/compact/signed/compact.apk"

# ── 其他 ──────────────────────────────────────────────────────
alias cr="cargo run"
alias cld="claude"
alias cldi="claude-internal"

# ── macOS 专属 ────────────────────────────────────────────────
if [[ $(uname) == "Darwin" ]]; then
  alias dislid='sudo pmset -b sleep 0; sudo pmset -b displaysleep 0; sudo pmset -b disablesleep 1'
  alias enlid='sudo pmset -b sleep 15; sudo pmset -b displaysleep 10; sudo pmset -b disablesleep 0'
fi
