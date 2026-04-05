#!/bin/bash
# FZF application picker for yazi
# Usage: open_with.sh <file>

file="$1"
[ -z "$file" ] && echo "Usage: open_with.sh <file>" && exit 1

app=$(find /Applications /System/Applications ~/Applications -maxdepth 3 -name "*.app" 2>/dev/null \
  | sed 's|.*/||; s|\.app$||' \
  | sort -u \
  | fzf --prompt="Open with > " --height=40% --reverse)

[ -n "$app" ] && open -a "$app" "$file"
