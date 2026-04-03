#!/bin/zsh

# 自动同步 .config 文件到 GitHub
# 包含详细的commit信息记录和分支自动检测

set -e # 遇到错误时退出

# 设置变量
CURRENT_DATE=$(date "+%Y-%m-%d %H:%M:%S")
LOG_FILE="./.sync.log"

# 记录日志开始
echo "[$CURRENT_DATE] 开始同步.config" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# 获取当前分支名
CURRENT_BRANCH=$(git branch --show-current)
echo "[$CURRENT_DATE] 当前分支: $CURRENT_BRANCH" >> "$LOG_FILE"

# 检查是否有变更
# if git diff --quiet HEAD 2>/dev/null && git diff --quiet --cached 2>/dev/null; then
#     echo "[$CURRENT_DATE] 没有文件变更，跳过提交" >> "$LOG_FILE"
#     echo "========================================" >> "$LOG_FILE"
#     echo "" >> "$LOG_FILE"
#     exit 0
# fi

# 记录变更的文件
echo "[$CURRENT_DATE] 检测到的变更文件:" >> "$LOG_FILE"
git status --porcelain >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# 更新 fzf submodule 到最新 master
git submodule update --remote thirdparty/fzf

# 添加到 git 暂存区
git add .

# 提交变更
COMMIT_MESSAGE="日常同步.config - $CURRENT_DATE"
git commit -m "$COMMIT_MESSAGE"

# 获取刚才的提交信息并记录到日志
echo "[$CURRENT_DATE] Git 提交完成: $COMMIT_MESSAGE" >> "$LOG_FILE"
echo "[$CURRENT_DATE] 本次提交详细信息:" >> "$LOG_FILE"
git --no-pager show --name-status HEAD >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# 推送到当前分支的远程同名分支
echo "[$CURRENT_DATE] 准备推送到远程分支: origin/$CURRENT_BRANCH" >> "$LOG_FILE"
if git push origin "$CURRENT_BRANCH" 2>&1 | tee -a "$LOG_FILE"; then
    echo "[$CURRENT_DATE] 成功推送到 GitHub (分支: $CURRENT_BRANCH)" >> "$LOG_FILE"
else
    echo "[$CURRENT_DATE] 推送到 GitHub 失败 (分支: $CURRENT_BRANCH)" >> "$LOG_FILE"
    exit 1
fi

echo "========================================" >> "$LOG_FILE"
echo "[$CURRENT_DATE] 同步完成" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
