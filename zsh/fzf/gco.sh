_fzf_git_checkout_branch() {
  local branch=$(_select_branch)
  echo "checking out to $branch..."
  git checkout $branch
  if [[ $? -eq 0 ]]; then
    echo "checkout success✅"
  else
    echo "checkout failed❌"
  fi
}

_select_branch() {
  $(which git) branch |
    $(which fzf) --ansi \
      --border-label '🌲 Branches ' \
      --preview-window down,border-top,60% \
      --color hl:underline,hl+:underline \
      --no-hscroll \
      --bind 'ctrl-/:change-preview-window(down,70%|hidden|)' \
      --bind "ctrl-o:execute-silent:bash \"$__fzf_git\" --list branch {}" \
      --bind "alt-a:change-border-label(🌳 All branches)+reload:bash \"$__fzf_git\" --list all-branches" \
      --bind "alt-h:become:LIST_OPTS=\$(cut -c3- <<< {} | cut -d' ' -f1) $shell \"$__fzf_git\" --run hashes" \
      --bind "alt-enter:become:printf '%s\n' {+} | cut -c3- | sed 's@[^/]*/@@'" \
      --preview "git log --oneline --graph --date=short --color=always --pretty='format:%C(auto)%cd %h%d %s' \$(cut -c3- <<< {} | cut -d' ' -f1) --" "$@" |
    sed 's/^\* //' | awk '{print $1}' # Slightly modified to work with hashes as well
}

_fzf_git_checkout_branch
