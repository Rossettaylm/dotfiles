#!/bin/zsh

branch="${1:-}"

# 第一步：选择 commit，预览区显示修改文件列表
commit_hash=$(
  git log --since='1 month ago' --oneline --date=short \
    --pretty='format:%C(auto)%cd %an %h%d %s' $branch |
  fzf -m --no-sort --ansi \
    --header='[Git:Log] Enter => show diff' \
    --delimiter=' ' \
    --preview='noglob git show --stat --color=always {3}' \
    --preview-label='[Modified Files]' \
    --preview-window='up,40%' |
  cut -d ' ' -f 3
)

if [[ -z "$commit_hash" ]]; then
  exit 0
fi

# # 第二步：列出该 commit 修改的文件，选择后预览该文件的 diff
# git diff-tree --no-commit-id --name-only -r "$commit_hash" |
#   fzf --no-sort \
#     --header="[Commit: $commit_hash]" \
#     --preview="noglob git show $commit_hash --color=always -- {}" \
#     --preview-label='[File Diff]' \
#     --preview-window='up,70%'

echo "$commit_hash"
