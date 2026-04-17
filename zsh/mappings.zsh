#!/usr/bin/env zsh

# ── Vi 模式 ─────────────────────────────────────────────
bindkey -v
export KEYTIMEOUT=15                          # 150ms，兼顾 jj 连击和 Esc 响应

# -- 光标样式：insert 竖线，normal 方块 --
_vi_cursor_update() {
  case $KEYMAP in
    vicmd)        print -n '\e[2 q' ;; # 方块
    viins|main)   print -n '\e[6 q' ;; # 竖线
  esac
}
zle -N zle-keymap-select _vi_cursor_update
zle -N zle-line-init      _vi_cursor_update

# -- insert 模式 --
bindkey -M viins 'jj' vi-cmd-mode            # jj 退出 insert 模式（同 nvim）
bindkey -M viins 'jk' vi-add-eol             # jk 跳到行尾（同 nvim jk → <esc>A）
bindkey -M viins '^?' backward-delete-char    # backspace 可删除进入 insert 前的字符
bindkey -M viins '^W' backward-kill-word      # ctrl+w 删除前一个词
bindkey -M viins '^U' backward-kill-line      # ctrl+u 清除光标前整行
bindkey -M viins '^A' beginning-of-line       # ctrl+a 跳到行首
bindkey -M viins '^E' end-of-line             # ctrl+e 跳到行尾
bindkey -M viins '^F' autosuggest-accept      # ctrl+f 接受 autosuggestion 补全

# -- normal 模式 --
bindkey -M vicmd '(' beginning-of-line        # ( 跳到行首（同 nvim ( → ^）
bindkey -M vicmd ')' end-of-line              # ) 跳到行尾（同 nvim ) → $）
bindkey -M vicmd 'H' vi-backward-word         # H 按词左移（适配 nvim S-h 快速左移）
bindkey -M vicmd 'L' vi-forward-word          # L 按词右移（适配 nvim S-l 快速右移）

# ── 目录导航 ─────────────────────────────────────────────

# alt+left 返回cd之前的目录
cdUndoKey() {
  popd      > /dev/null
  zle       reset-prompt
  echo
  ls
  echo
}

# alt+up 返回上一级目录
cdParentKey() {
  pushd .. > /dev/null
  zle      reset-prompt
  echo
  ls
  echo 
}


zle -N                 cdParentKey
zle -N                 cdUndoKey
bindkey '^[[1;3A'      cdParentKey # alt + up
bindkey '^[[1;3D'      cdUndoKey   # alt + left

