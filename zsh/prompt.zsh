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
