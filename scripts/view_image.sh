#!/bin/bash
# Show an image full-screen via the Kitty graphics protocol (GIFs animate), exit on any key.
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
kitten icat --transfer-mode=file --align center --scale-up "$file"
stty -icanon -echo min 1 time 0
dd bs=1 count=1 >/dev/null 2>&1
