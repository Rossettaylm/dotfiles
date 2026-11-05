#!/bin/bash
# Show an image centered in a box VIEW_IMAGE_RATIO% (default 60) of the terminal width via the
# Kitty graphics protocol (GIFs animate), exit on any key.
# Usage: view_image.sh <file>
#
# `kitten icat --hold` never sees keypresses under tmux, so wait for a key here.
# --transfer-mode=file: Ghostty reads frames from temp files; auto-detection
# falls back to stream under tmux and sends hundreds of MB through the pty.

file="$1"
[ -z "$file" ] && echo "Usage: view_image.sh <file>" && exit 1

delete_all_images() {
  local seq=$'\e_Ga=d,d=A\e\\'
  if [ -n "$TMUX" ]; then
    seq=$'\ePtmux;\e\e_Ga=d,d=A\e\e\\\e\\'
  fi
  printf '%s' "$seq"
}

old_tty=$(stty -g)
restore() {
  stty "$old_tty"
  delete_all_images
  clear
}
trap restore EXIT

clear
read -r rows cols < <(stty size)
ratio=${VIEW_IMAGE_RATIO:-60}
width=$((cols * ratio / 100))
height=$((rows - 1))
left=$(((cols - width) / 2))
kitten icat --transfer-mode=file --scale-up --place "${width}x${height}@${left}x0" "$file"
stty -icanon -echo min 1 time 0
dd bs=1 count=1 >/dev/null 2>&1
