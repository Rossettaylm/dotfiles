#!/usr/bin/env zsh

# atuin: 智能历史命令面板
#   - Ctrl-H 呼出搜索面板（vi 模式感知）
#   - ↑ 接管为 atuin-up-search（多行 buffer 自动退化为 up-line）
#   - zsh-autosuggestions 自动走 atuin 历史（通过 ZSH_AUTOSUGGEST_STRATEGY）
#   - 关闭 `?` AI 模式以避免误触

if command -v atuin >/dev/null 2>&1; then
  eval "$(atuin init zsh --disable-up-arrow --disable-ctrl-r)"

  # Ctrl-H → atuin-search
  bindkey -M emacs '^H' atuin-search
  bindkey -M viins '^H' atuin-search-viins
  bindkey -M vicmd '^H' atuin-search-vicmd

  # ↑ → atuin-up-search（覆盖 init --disable-up-arrow 的清空）
  bindkey -M emacs '^[[A' atuin-up-search
  bindkey -M viins '^[[A' atuin-up-search-viins
  bindkey -M vicmd '^[[A' atuin-up-search-vicmd
  # application cursor mode（部分终端 / tmux / ssh 环境）
  bindkey -M emacs '^[OA' atuin-up-search
  bindkey -M viins '^[OA' atuin-up-search-viins
  bindkey -M vicmd '^[OA' atuin-up-search-vicmd

  # 关闭 atuin AI 的 `?` 劫持（init 内强制绑定，手动解绑）
  bindkey -r '?'
fi
