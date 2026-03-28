#!/bin/zsh

branch="${1:-}"

# 第一步：选择 commit，预览区右侧显示修改文件列表
commit_hash=$(
  git log --since='1 month ago' --oneline --date=short \
    --pretty='format:%C(auto)%cd %an %h%d %s' $branch |
  fzf -m --no-sort --ansi \
    --border-label=' 📜  [Git Log] ' \
    --border-label-pos=2 \
    --prompt='  Commit > ' \
    --pointer='▶' \
    --header='  Enter → show diff  ·  Esc quit' \
    --delimiter=' ' \
    --preview='noglob git show --stat --color=always {3}' \
    --preview-label='[ Modified Files ]' \
    --preview-window='right,border-left,50%' \
    --no-hscroll |
  cut -d ' ' -f 3
)

if [[ -z "$commit_hash" ]]; then
  exit 0
fi

echo "$commit_hash"
