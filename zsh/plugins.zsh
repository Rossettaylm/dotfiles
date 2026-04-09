#!/usr/bin/env zsh
# Zsh 插件加载（submodule 手动管理 + OMZ 轻量替代）

# ── submodule 插件 ────────────────────────────────────────

# zsh-defer：先加载，后续非关键插件用它异步初始化
source "$ZSH_PLUGINS/zsh-defer/zsh-defer.plugin.zsh"

# fzf-tab：必须在 compinit 之后、其他 zle 插件之前
source "$ZSH_PLUGINS/fzf-tab/fzf-tab.plugin.zsh"

# 延迟加载：补全增强，不阻塞启动
zsh-defer source "$ZSH_PLUGINS/zsh-autosuggestions/zsh-autosuggestions.plugin.zsh"
zsh-defer source "$ZSH_PLUGINS/zsh-syntax-highlighting/zsh-syntax-highlighting.plugin.zsh"

# ── sudo ─────────────────────────────────────────────────
# 双击 Esc：在当前命令前加/去 sudo
_sudo_maybe() {
  if [[ -z $BUFFER ]]; then
    zle up-history
  elif [[ $BUFFER == sudo\ * ]]; then
    LBUFFER="${LBUFFER#sudo }"
  else
    LBUFFER="sudo $LBUFFER"
  fi
}
zle -N _sudo_maybe
bindkey '\e\e' _sudo_maybe

# ── extract ──────────────────────────────────────────────
# 解压任意常见格式
extract() {
  if [[ -f "$1" ]]; then
    case "$1" in
      *.tar.bz2)  tar xjf "$1"         ;;
      *.tar.gz)   tar xzf "$1"         ;;
      *.tar.xz)   tar xJf "$1"         ;;
      *.tar.zst)  tar --zstd -xf "$1"  ;;
      *.tar)      tar xf  "$1"         ;;
      *.bz2)      bunzip2 "$1"         ;;
      *.gz)       gunzip  "$1"         ;;
      *.zip)      unzip   "$1"         ;;
      *.7z)       7z x    "$1"         ;;
      *.rar)      unrar x "$1"         ;;
      *.xz)       unxz    "$1"         ;;
      *.zst)      zstd -d "$1"         ;;
      *)          echo "'$1' 无法识别的格式" ;;
    esac
  else
    echo "'$1' 不是有效文件"
  fi
}

# ── web-search ───────────────────────────────────────────
# 在默认浏览器中搜索（先清除同名别名，避免 zsh 报 parse error）
unalias google baidu github 2>/dev/null
_web_search() {
  local url="$1"; shift
  local query
  query=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(' '.join(sys.argv[1:])))" "$@")
  open "${url}${query}"
}
google() { _web_search "https://www.google.com/search?q=" "$@" }
baidu()  { _web_search "https://www.baidu.com/s?wd=" "$@" }
github() { _web_search "https://github.com/search?q=" "$@" }
