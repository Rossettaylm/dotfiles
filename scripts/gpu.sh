#!/bin/bash

get_push_upstream() {
  local PREFIX="git push --set-upstream origin "
  local CUR_BRANCH="$(python3 $HOME/.config/zsh/fzf/get_cur_brranch.py)"
  local CMD="${PREFIX}${CUR_BRANCH}"
  eval ${CMD}
}

get_push_upstream
