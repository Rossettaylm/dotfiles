#!/bin/bash

# 检查是否有名为 "open-webui" 的后台任务在运行
if ! pgrep -f open-webui >/dev/null; then
  # 如果没有后台任务，则启动它并重定向日志到 $HOME/templog/open-webui.log
  if [[ ! -d $HOME/templog ]]; then
    mkdir $HOME/templog
  fi
  nohup open-webui serve >$HOME/templog/open-webui.log 2>&1 &
fi

# 打开网址 http://localhost:8080
while ! nc -z localhost 8080; do
  echo "正在启动open-webui服务，请稍后..."
  sleep 1
done

open "http://localhost:8080"
