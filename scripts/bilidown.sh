#!/bin/bash

EXE_DIR="$HOME/Downloads/bilidown_Darwin_arm64/"
EXE_PATH="${EXE_DIR}bilidown"

# 检查是否有名为 "bilidown" 的后台任务在运行
if ! pgrep -f bilidown >/dev/null; then
  # 如果没有后台任务，则启动它并重定向日志到 $HOME/templog/open-webui.log
  if [[ ! -d $HOME/templog ]]; then
    mkdir $HOME/templog
  fi
  cd $EXE_DIR
  nohup $EXE_PATH >$HOME/templog/bilidown.log 2>&1 &
else
  open "http://localhost:8098"
fi

unset EXE_PATH
unset EXE_DIR
