_fzf_git_checkout_branch() {
  local BRANCH
  BRANCH=$(_select_branch)
  if [[ -z $BRANCH ]]; then
    echo "cancel checkout⚠️"
    exit 1
  fi
  echo "checking out to $BRANCH..."
  git checkout "$BRANCH" &&
    echo "checkout success✅" ||
    echo "checkout failed❌"
}

_select_branch() {
  $(which git) branch |
    $(which fzf) --ansi \
      --border-label '🌲 Branches ' \
      --preview-window right,border-left,70% \
      --color hl:underline,hl+:underline \
      --no-hscroll \
      --preview "git log --oneline --graph --date=short --color=always --pretty='format:%C(auto)%cd %an %h%d %s' \$(cut -c3- <<< {} | cut -d' ' -f1) --" |
    sed 's/^\* //' | awk '{print $1}' # Slightly modified to work with hashes as well
}

_fzf_git_checkout_branch
