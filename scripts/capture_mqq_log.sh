#!/bin/bash
# capture_mqq_log.sh - 持续捕获 com.tencent.mqq 的 hilog 日志
#
# 特性：
#   - 进程重启自动重连（仅主进程）
#   - 按天建文件夹存储（补零格式 2026-04-30）
#   - 总容量 5GB 上限，两级策略：
#     L1 (80%/4GB): 压缩 3 天前最旧的未压缩日志
#     L2 (仍超限):  删除最旧的日志目录
#   - 维护任务后台子进程执行，不阻塞写入
#   - 单文件 500MB 轮转保护

set -uo pipefail

LOG_BASE="$HOME/harmony_log"
PACKAGE="com.tencent.mqq"
RECONNECT_INTERVAL=3
MAX_SINGLE_FILE_MB=500
MAX_TOTAL_MB=5120            # 5GB
THRESHOLD_PCT=80             # 触发阈值百分比
PROTECT_DAYS=3               # 3 天内不压缩
MAINTENANCE_LOCK="$LOG_BASE/.maintenance.lk"
MAINTENANCE_INTERVAL=10000   # 每 N 行检查一次容量

mkdir -p "$LOG_BASE"

# --- 工具函数 ---

get_today_dir() {
  echo "$LOG_BASE/$(date +%Y-%m-%d)"
}

get_main_pid() {
  local pids
  pids=$(hdc shell pidof "$PACKAGE" 2>/dev/null | tr -d '\r\n')
  echo "${pids%% *}"
}

get_total_size_mb() {
  du -sm "$LOG_BASE" 2>/dev/null | cut -f1
}

check_rotation() {
  local file="$1"
  if [ -f "$file" ]; then
    local size_mb
    size_mb=$(du -m "$file" 2>/dev/null | cut -f1)
    if [ "${size_mb:-0}" -ge "$MAX_SINGLE_FILE_MB" ]; then
      mv "$file" "${file%.log}_$(date +%H%M%S).log"
      echo "[$(date +%H:%M:%S)] 文件轮转: 超过 ${MAX_SINGLE_FILE_MB}MB"
    fi
  fi
}

# --- 后台维护函数（在子进程中执行） ---

run_maintenance() {
  # mkdir 原子操作做互斥锁（macOS 无 flock）
  if ! mkdir "$MAINTENANCE_LOCK" 2>/dev/null; then
    return 0
  fi
  # 确保退出时释放锁
  trap 'rmdir "$MAINTENANCE_LOCK" 2>/dev/null' RETURN

  local total_mb
  total_mb=$(get_total_size_mb)
  local threshold_mb=$(( MAX_TOTAL_MB * THRESHOLD_PCT / 100 ))

  if [ "${total_mb:-0}" -lt "$threshold_mb" ]; then
    return 0
  fi

  echo "[$(date +%H:%M:%S)] [维护] 容量 ${total_mb}MB / ${MAX_TOTAL_MB}MB (阈值 ${threshold_mb}MB)，启动清理"

  # L1: 压缩 3 天前最旧的未压缩 .log 文件
  local compressed_count=0
  local protect_boundary
  protect_boundary=$(date -v-${PROTECT_DAYS}d +%Y-%m-%d 2>/dev/null || date -d "${PROTECT_DAYS} days ago" +%Y-%m-%d)

  # 按目录名排序（日期），从最旧开始压缩
  find "$LOG_BASE" -maxdepth 2 -name "*.log" -not -name "service.*" 2>/dev/null | sort | while read -r f; do
    # 提取目录中的日期
    local dir_name
    dir_name=$(basename "$(dirname "$f")")
    # 跳过保护期内的日志
    if [[ "$dir_name" > "$protect_boundary" || "$dir_name" == "$protect_boundary" ]]; then
      continue
    fi
    # 压缩
    gzip -q "$f" 2>/dev/null && echo "[$(date +%H:%M:%S)] [维护-L1] 已压缩: $f"
    compressed_count=$((compressed_count + 1))
    # 压缩后重新检查容量
    total_mb=$(get_total_size_mb)
    if [ "${total_mb:-0}" -lt "$threshold_mb" ]; then
      echo "[$(date +%H:%M:%S)] [维护-L1] 容量已降至 ${total_mb}MB，停止"
      break
    fi
  done

  # 重新检查：如果仍超限，进入 L2 删除
  total_mb=$(get_total_size_mb)
  if [ "${total_mb:-0}" -ge "$threshold_mb" ]; then
    echo "[$(date +%H:%M:%S)] [维护-L2] 压缩后仍超限 (${total_mb}MB)，开始删除最旧目录"

    # 按目录名排序，从最旧开始删除（跳过今天）
    local today
    today=$(date +%Y-%m-%d)
    find "$LOG_BASE" -maxdepth 1 -type d -name "20*" 2>/dev/null | sort | while read -r d; do
      local dname
      dname=$(basename "$d")
      if [ "$dname" == "$today" ]; then
        continue
      fi
      rm -rf "$d"
      echo "[$(date +%H:%M:%S)] [维护-L2] 已删除: $d"
      total_mb=$(get_total_size_mb)
      if [ "${total_mb:-0}" -lt "$threshold_mb" ]; then
        echo "[$(date +%H:%M:%S)] [维护-L2] 容量已降至 ${total_mb}MB，停止"
        break
      fi
    done
  fi
}

# 触发后台维护（非阻塞）
trigger_maintenance() {
  run_maintenance &
}

# --- 主循环 ---

LINE_COUNT=0

echo "[$(date +%H:%M:%S)] 日志捕获服务启动 | 包=$PACKAGE 存储=$LOG_BASE 上限=${MAX_TOTAL_MB}MB"

while true; do
  PID=$(get_main_pid)

  if [ -z "$PID" ]; then
    sleep "$RECONNECT_INTERVAL"
    continue
  fi

  TODAY_DIR=$(get_today_dir)
  mkdir -p "$TODAY_DIR"
  LOG_FILE="$TODAY_DIR/mqq.log"

  echo "[$(date +%H:%M:%S)] 已连接 PID=$PID -> $LOG_FILE"

  # 连接时触发一次维护检查
  trigger_maintenance

  # 用命名管道传输 hilog 输出，便于 watchdog 杀进程后 read 能 EOF
  FIFO="$LOG_BASE/.hilog_fifo_$$"
  rm -f "$FIFO"
  mkfifo "$FIFO"

  # hilog 写入 FIFO（后台）
  hdc shell hilog -P "$PID" > "$FIFO" 2>/dev/null &
  HILOG_PID=$!

  # watchdog：每 5s 检查目标进程是否仍存活
  (
    while kill -0 $HILOG_PID 2>/dev/null; do
      sleep 5
      CURRENT_PID=$(hdc shell pidof "$PACKAGE" 2>/dev/null | tr -d '\r\n')
      CURRENT_PID="${CURRENT_PID%% *}"
      if [ "$CURRENT_PID" != "$PID" ]; then
        kill $HILOG_PID 2>/dev/null
        break
      fi
    done
  ) &
  WATCHDOG_PID=$!

  # 从 FIFO 读取日志
  while IFS= read -r line; do
    # 日期切换检测
    NEW_DIR=$(get_today_dir)
    if [ "$NEW_DIR" != "$TODAY_DIR" ]; then
      TODAY_DIR="$NEW_DIR"
      mkdir -p "$TODAY_DIR"
      LOG_FILE="$TODAY_DIR/mqq.log"
      echo "[$(date +%H:%M:%S)] 日期切换: $TODAY_DIR"
      trigger_maintenance
    fi

    echo "$line" >> "$LOG_FILE"

    # 定期检查
    LINE_COUNT=$((LINE_COUNT + 1))
    if (( LINE_COUNT % MAINTENANCE_INTERVAL == 0 )); then
      trigger_maintenance
    fi
    if (( LINE_COUNT % 5000 == 0 )); then
      check_rotation "$LOG_FILE"
    fi
  done < "$FIFO"

  # 清理
  kill $WATCHDOG_PID 2>/dev/null
  kill $HILOG_PID 2>/dev/null
  wait $HILOG_PID 2>/dev/null
  wait $WATCHDOG_PID 2>/dev/null
  rm -f "$FIFO"

  echo "[$(date +%H:%M:%S)] 连接中断，${RECONNECT_INTERVAL}s 后重连..."
  sleep "$RECONNECT_INTERVAL"
done
