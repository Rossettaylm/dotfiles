#!/bin/bash
# lazygit edit wrapper: detect if inside neovim or terminal
if [ -n "$NVIM" ] && [ -z "$YAZI_LEVEL" ]; then
    # Inside neovim: close lazygit float and open file in parent nvim
    if [[ "$1" == +* ]]; then
        line="${1#+}"
        file="$2"
        nvim --server "$NVIM" --remote-expr "execute(\"close | edit +${line} ${file}\")"
    else
        nvim --server "$NVIM" --remote-expr "execute(\"close | edit $1\")"
    fi
else
    # Terminal: open nvim directly
    nvim "$@"
fi
