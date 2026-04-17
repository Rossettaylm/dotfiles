 # _____ __________ 
# |  ___|__  /  ___|
# | |_    / /| |_   
# |  _|  / /_|  _|  
# |_|   /____|_|    
#
#

# config ** completion
_fzf_comprun() {
  local command=$1
  shift

  case "$command" in
    cd)           fzf --preview 'tree -C {} | head -200' --preview-label='Directories'          "$@" ;;
    export|unset) fzf --preview "eval 'echo \$'{}" --preview-label='Environment Variables'      "$@" ;;
    ssh)          fzf --preview 'dig {}' --preview-label='Hosts'                                "$@" ;;
    vi)           fzf --preview 'bat -n --color=always {}' --preview-label='Files'              "$@" ;;
    nvim)         fzf --preview 'bat -n --color=always {}' --preview-label='Files'              "$@" ;;
    kill)         fzf --preview-label='Processes'                                               "$@" ;;
    *)            fzf --preview 'bat -n --color=always {}' --preview-label='Search'             "$@" ;;
  esac
}

export FZF_DEFAULT_COMMAND="fd --hidden --exclude '.git'"
# catppuccin/mocha
export FZF_DEFAULT_OPTS="--height=80% --ansi --layout=reverse --padding=1 --margin=1 --border --style=full \
--color=bg+:#313244,bg:-1,spinner:#F5E0DC,hl:#F38BA8 \
--color=fg:#CDD6F4,header:#F38BA8,info:#CBA6F7,pointer:#F5E0DC \
--color=marker:#B4BEFE,fg+:#CDD6F4,prompt:#CBA6F7,hl+:#F38BA8 \
--color=selected-bg:#45475A \
--color=border:#6C7086,label:#CDD6F4"

export FZF_CTRL_T_COMMAND="fd --type f --hidden --exclude '.git'"
export FZF_ALT_C_COMMAND="fd --type d --hidden --exclude '.git'"

# change to ctrl-p override
export FZF_CTRL_T_OPTS="${FZF_DEFAULT_OPTS} --scheme=path --preview-label='Files' --preview 'bat -n --color=always {}' \
--bind 'ctrl-o:execute(nvim {})+abort'"

# change to ctrl-h override
export FZF_CTRL_R_OPTS="${FZF_DEFAULT_OPTS} --preview-label='History Commands' 
--bind 'ctrl-y:execute-silent(echo -n {2..} | pbcopy)+abort'
--header 'Press CTRL-Y to copy command into clipboard'"

# override preview with tree
export FZF_ALT_C_OPTS="--preview 'tree -C {}' --preview-label='Directories'"

# autoload fzf script in $ZSH_HOME/fzf
_fzf_fpath=${0:h}/fzf
fpath+=$_fzf_fpath
autoload -U $_fzf_fpath/*(.:t)
unset _fzf_fpath
                  
# ---------
# Setup fzf
if [[ ! "$PATH" == *$FZF_HOME/bin* ]]; then
  export PATH="${PATH:+${PATH}:}${FZF_HOME}/bin"
fi

# Auto-completion
# ---------------
[[ $- == *i* ]] && source "${FZF_HOME}/shell/completion.zsh" 2> /dev/null

# Key bindings
# ------------
# 禁用 fzf 对 Ctrl-H 的历史绑定（vendored fzf 已改为 ^H），交给 atuin
FZF_CTRL_R_COMMAND= source "${FZF_HOME}/shell/key-bindings.zsh"
