#!/usr/bin/env bash
# Usage: join_pane_to_window.sh <window_index>
# Moves the current pane to the target window; creates the window if it doesn't exist.
# join-pane uses -h (horizontal/left-right split) by default.

target="$1"
[ -z "$target" ] && exit 1

current_window=$(tmux display-message -p '#{window_index}')
pane_count=$(tmux display-message -p '#{window_panes}')

# Already in target window, do nothing
if [ "$current_window" = "$target" ]; then
    exit 0
fi

window_exists=$(tmux list-windows -F '#{window_index}' | grep -cx "$target")

# Only pane in current window → use move-window or join-pane
if [ "$pane_count" -eq 1 ]; then
    if [ "$window_exists" -gt 0 ]; then
        tmux join-pane -h -t ":$target"
    else
        tmux move-window -t ":$target"
    fi
    exit 0
fi

# Multiple panes: target doesn't exist → break-pane to new window (no empty shell left behind)
if [ "$window_exists" -eq 0 ]; then
    tmux break-pane -d -t ":$target"
else
    tmux join-pane -h -t ":$target"
fi
