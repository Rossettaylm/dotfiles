#!/usr/bin/env zsh
# Prompt 配置

# 优先使用 Starship；未安装时退化为内置 prompt
if command -v starship &>/dev/null; then
  eval "$(starship init zsh)"
else
  # fallback：SSH 连接显示主机名，本地只显示路径
  if [[ -n "$SSH_CONNECTION" ]]; then
    PROMPT='%F{cyan}%n@%m%f %F{yellow}%~%f %# '
  else
    PROMPT='%F{green}%~%f %# '
  fi
fi

# OSC 133 语义标记：A=prompt 起点，C=命令输出起点（tmux previous-prompt/next-prompt 依赖，cpo/cpv 用）
PROMPT=$'%{\e]133;A\e\\%}'"$PROMPT"
_osc133_output_start() { [[ -t 1 ]] && print -n '\e]133;C\e\\' }
autoload -Uz add-zsh-hook
add-zsh-hook preexec _osc133_output_start
