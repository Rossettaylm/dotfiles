_fzf_git_checkout_branch() {
  local branch=$(_select_branch)
  echo "checking out to $branch..."
  git checkout $branch &&
    echo "checkout success✅" ||
    echo "checkout failed❌"
}

_select_branch() {
  $(which git) branch |
    $(which fzf) --ansi \
      --border-label '🌲 Branches ' \
      --preview-window down,border-top,70% \
      --color hl:underline,hl+:underline \
      --no-hscroll \
      --preview "git log --oneline --graph --date=short --color=always --pretty='format:%C(auto)%cd %an %h%d %s' \$(cut -c3- <<< {} | cut -d' ' -f1) --" "$@" |
    sed 's/^\* //' | awk '{print $1}' # Slightly modified to work with hashes as well
}

_fzf_git_checkout_branch
