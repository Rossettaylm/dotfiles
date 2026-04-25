#!/usr/bin/env bash

# Shared utilities for fzf-based tmux scripts (fzf_panes, fzf_sessions, etc.)

# Open a new tmux window for fzf, cleaning up any previous instance.
# $1: tmux global var for pane tracking (e.g. @fzf_pane_id)
# $2: script path (caller's $0)
fzf_new_window() {
    local var=$1 script=$2
    [[ -x $(command -v fzf 2>/dev/null) ]] || return
    local old_id=$(tmux show -gqv "$var")
    [[ -n $old_id ]] && tmux kill-pane -t "$old_id" >/dev/null 2>&1
    tmux new-window "bash $script do_action" >/dev/null 2>&1
}

# Register pane tracking and cleanup trap for the fzf window.
# $1: tmux global var for pane tracking
fzf_guard() {
    local var=$1
    trap "tmux set -gu '$var'" EXIT SIGINT SIGTERM
    local pane_id=$(tmux display-message -p '#D')
    tmux set -g "$var" "$pane_id"
}
