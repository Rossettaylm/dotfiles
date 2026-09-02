#!/usr/bin/env bash
# HarmonyOS hdc 录屏：再执行一次结束。默认最多 60 秒，保存到 ~/Pictures/screenshot，并复制到剪贴板
#
# 用法: hdc_record.sh [-t <sn>] [-d <duration>] [-f <path>] [-o] [-n] [path]
#   -t  指定设备序列号
#   -d  超时时长，默认 60 秒；0 表示不限时。支持 90、90s、2m
#   -f  指定保存路径（也可直接跟位置参数）
#   -o  结束后用默认应用打开
#   -n  只落盘，不复制到剪贴板

set -euo pipefail

SAVE_DIR="${HOME}/Pictures/screenshot"
STATE_FILE="${HOME}/.cache/hdc_record.state"
KNOWN_FILE="${HOME}/.cache/hdc_record.known"
LOCK_DIR="${HOME}/.cache/hdc_record.lock"
SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"

DEVICE=""
REMOTE_NAME=""
OUTFILE=""
OPEN_FILE=0
COPY_CLIPBOARD=1
DURATION=60
AUTO_STOP=0
WATCHER_PID=""
START_TS=""
PHASE="recording"

usage() {
  cat <<'EOF'
用法: hrec [-t <sn>] [-d <duration>] [-f <path>] [-o] [-n] [path]

  第一次执行开始录屏，再次执行结束录屏。
  默认最多录制 60 秒，到时自动结束。
  结束后默认复制到剪贴板，并保存到 ~/Pictures/screenshot

  -t <sn>        指定 hdc 设备
  -d <duration>  超时时长，默认 60 秒；0 不限时。示例: 90、90s、2m
  -f <path>      指定保存路径（文件或目录）
  -o             结束后用默认应用打开
  -n             只保存文件，不复制到剪贴板
EOF
}

parse_duration() {
  local raw="$1"
  if [[ "$raw" =~ ^[0-9]+$ ]]; then
    printf '%s\n' "$raw"
    return
  fi
  if [[ "$raw" =~ ^[0-9]+s$ ]]; then
    printf '%s\n' "${raw%s}"
    return
  fi
  if [[ "$raw" =~ ^[0-9]+m$ ]]; then
    printf '%s\n' $((${raw%m} * 60))
    return
  fi
  echo "无效时长: $raw（示例: 60、90s、2m）" >&2
  exit 1
}

if [[ "${1:-}" == "--auto-stop" ]]; then
  AUTO_STOP=1
  shift
fi

while getopts ":t:f:d:onh" opt; do
  case "$opt" in
    t) DEVICE="$OPTARG" ;;
    f) OUTFILE="$OPTARG" ;;
    d) DURATION="$(parse_duration "$OPTARG")" ;;
    o) OPEN_FILE=1 ;;
    n) COPY_CLIPBOARD=0 ;;
    h)
      usage
      exit 0
      ;;
    :)
      echo "参数 -$OPTARG 需要值" >&2
      exit 1
      ;;
    \?)
      echo "未知参数: -$OPTARG" >&2
      usage
      exit 1
      ;;
  esac
done
shift $((OPTIND - 1))

if [[ -z "$OUTFILE" && $# -ge 1 ]]; then
  OUTFILE="$1"
fi

if [[ "$AUTO_STOP" -eq 1 && ! -f "$STATE_FILE" ]]; then
  exit 0
fi

if ! command -v hdc >/dev/null 2>&1; then
  echo "未找到 hdc，请确认已加入 PATH（DevEco toolchains）" >&2
  exit 1
fi

hdc_cmd() {
  if [[ -n "$DEVICE" ]]; then
    hdc -t "$DEVICE" "$@"
  else
    hdc "$@"
  fi
}

list_devices() {
  hdc list targets 2>/dev/null | awk 'NF && $1 != "[Empty]" && tolower($1) != "empty"'
}

resolve_device() {
  if [[ -n "$DEVICE" ]]; then
    return
  fi
  devices=()
  while IFS= read -r line; do
    [[ -n "$line" ]] && devices+=("$line")
  done < <(list_devices)
  if [[ ${#devices[@]} -eq 0 ]]; then
    echo "未检测到 hdc 设备，请先 USB 连接并开启调试" >&2
    exit 1
  fi
  if [[ ${#devices[@]} -gt 1 ]]; then
    echo "检测到多台设备，请用 -t 指定：" >&2
    printf '  %s\n' "${devices[@]}" >&2
    exit 1
  fi
  DEVICE="${devices[0]}"
}

abs_path() {
  local p="$1"
  local dir base
  dir="$(dirname "$p")"
  base="$(basename "$p")"
  mkdir -p "$dir"
  (cd "$dir" && printf '%s/%s\n' "$(pwd)" "$base")
}

copy_video_clipboard() {
  local file="$1"
  osascript \
    -e 'on run args' \
    -e 'set the clipboard to POSIX file (first item of args)' \
    -e 'end run' \
    "$file" >/dev/null
}

now_ts() {
  date +%s
}

file_mtime() {
  local f="$1"
  if stat -f %m "$f" >/dev/null 2>&1; then
    stat -f %m "$f"
  else
    stat -c %Y "$f"
  fi
}

clear_lock() {
  rmdir "$LOCK_DIR" >/dev/null 2>&1 || true
}

acquire_lock() {
  if mkdir "$LOCK_DIR" 2>/dev/null; then
    trap 'rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT
    return 0
  fi
  if [[ -d "$LOCK_DIR" ]]; then
    local age
    age=$(($(now_ts) - $(file_mtime "$LOCK_DIR")))
    if [[ "$age" -gt 30 ]]; then
      clear_lock
      mkdir "$LOCK_DIR"
      trap 'rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT
      return 0
    fi
  fi
  return 1
}

write_state() {
  mkdir -p "$(dirname "$STATE_FILE")"
  cat >"$STATE_FILE" <<EOF
DEVICE=${DEVICE}
REMOTE_NAME=${REMOTE_NAME}
OUTFILE=${OUTFILE}
COPY_CLIPBOARD=${COPY_CLIPBOARD}
OPEN_FILE=${OPEN_FILE}
WATCHER_PID=${WATCHER_PID}
START_TS=${START_TS}
DURATION=${DURATION}
PHASE=${PHASE}
EOF
}

load_state() {
  local key value
  while IFS='=' read -r key value || [[ -n "${key}" ]]; do
    key="${key%$'\r'}"
    value="${value%$'\r'}"
    case "${key}" in
      DEVICE) DEVICE="${value}" ;;
      REMOTE_NAME) REMOTE_NAME="${value}" ;;
      OUTFILE) OUTFILE="${value}" ;;
      COPY_CLIPBOARD) COPY_CLIPBOARD="${value}" ;;
      OPEN_FILE) OPEN_FILE="${value}" ;;
      WATCHER_PID) WATCHER_PID="${value}" ;;
      START_TS) START_TS="${value}" ;;
      DURATION) DURATION="${value}" ;;
      PHASE) PHASE="${value}" ;;
    esac
  done <"$STATE_FILE"
}

cleanup_state() {
  kill_watcher
  rm -f "$STATE_FILE" "$KNOWN_FILE"
}

notify() {
  local msg="$1"
  if [[ "$(uname)" == "Darwin" ]]; then
    osascript -e "display notification \"$msg\" with title \"hrec\"" >/dev/null 2>&1 || true
  fi
}

start_watcher() {
  if [[ "$DURATION" -le 0 ]]; then
    return
  fi
  DURATION="$DURATION" STATE_FILE="$STATE_FILE" SELF="$SELF" \
    nohup bash -c 'sleep "$DURATION"; [ -f "$STATE_FILE" ] && exec "$SELF" --auto-stop' \
    >/dev/null 2>&1 &
  WATCHER_PID=$!
}

kill_watcher() {
  if [[ -n "${WATCHER_PID:-}" ]]; then
    kill "$WATCHER_PID" >/dev/null 2>&1 || true
  fi
}

recorder_start() {
  hdc_cmd shell aa start \
    -b com.huawei.hmos.screenrecorder \
    -a com.huawei.hmos.screenrecorder.ServiceExtAbility \
    --ps "CustomizedFileName" "$REMOTE_NAME"
}

recorder_stop() {
  hdc_cmd shell aa start \
    -b com.huawei.hmos.screenrecorder \
    -a com.huawei.hmos.screenrecorder.ServiceExtAbility
}

extract_media_ref() {
  awk '
    {
      gsub(/"/, "")
      for (i = 1; i <= NF; i++) {
        if ($i ~ /^file:\/\// || $i ~ /\.(mp4|MP4)$/ || $i ~ /^\/storage\// || $i ~ /^\/mnt\//) {
          print $i
          exit
        }
      }
    }
  '
}

extract_all_mp4() {
  awk '
    {
      gsub(/"/, "")
      for (i = 1; i <= NF; i++) {
        if ($i ~ /\.(mp4|MP4)$/ || $i ~ /^file:\/\/media\/Photo\//) {
          print $i
        }
      }
    }
  ' | awk 'NF && !seen[$0]++'
}

query_media() {
  local name="$1"
  local flag="${2:-}"
  if [[ -n "$flag" ]]; then
    hdc_cmd shell "mediatool query '${name}' ${flag}" 2>/dev/null | extract_media_ref
  else
    hdc_cmd shell "mediatool query '${name}'" 2>/dev/null | extract_media_ref
  fi
}

vid_ts_from_name() {
  printf '%s\n' "$1" | sed -nE 's/.*VID_([0-9]+)_.*/\1/p'
}

list_recent_mp4() {
  local out sub
  out="$(hdc_cmd shell 'ls -1t /mnt/data/100/media_fuse/Photo/*/*.mp4 2>/dev/null' || true)"
  if printf '%s' "$out" | grep -q '\.mp4'; then
    printf '%s\n' "$out" | extract_all_mp4
    return
  fi
  out="$(hdc_cmd shell "mediatool ls -l /storage/media/local/files/Photo" 2>/dev/null || true)"
  printf '%s\n' "$out" | extract_all_mp4
  printf '%s\n' "$out" | awk '{print $NF}' | grep -E '^[0-9]+$' | sort -nr | head -3 | while IFS= read -r sub; do
    hdc_cmd shell "mediatool ls -l /storage/media/local/files/Photo/${sub}" 2>/dev/null | extract_all_mp4 || true
  done
}

filter_since_start() {
  local ref ts min_ts
  min_ts=$((${START_TS:-0} - 5))
  while IFS= read -r ref; do
    [[ -z "$ref" ]] && continue
    case "$ref" in
      *"${REMOTE_NAME}"*) printf '%s\n' "$ref"; continue ;;
    esac
    ts="$(vid_ts_from_name "$ref")"
    if [[ -n "$ts" && "$ts" -ge "$min_ts" ]]; then
      printf '%s\n' "$ref"
    fi
  done
}

path_to_uri() {
  printf '%s\n' "$1" | sed -nE 's|.*/Photo/([0-9]+)/.*|file://media/Photo/\1|p'
}

to_media_path() {
  local p="$1"
  printf '%s\n' "$p" | sed -E \
    -e 's|^/storage/cloud/([0-9]+)/files/|/storage/media/\1/local/files/|' \
    -e 's|^/storage/cloud/[0-9]+/files/|/storage/media/local/files/|'
}

to_fuse_path() {
  local p="$1"
  printf '%s\n' "$p" | sed -E 's|^/storage/cloud/([0-9]+)/files/|/mnt/data/\1/media_fuse/|'
}

shorten_uri() {
  printf '%s\n' "$1" | sed -E 's|(file://media/Photo/[0-9]+).*|\1|'
}

mediatool_export() {
  local src="$1"
  local dst="$2"
  local out result
  hdc_cmd shell "rm -f '${dst}'" >/dev/null 2>&1 || true
  out="$(hdc_cmd shell "mediatool recv '${src}' '${dst}'" 2>&1)" || true
  if printf '%s' "$out" | grep -qiE 'fail|error:|permission denied|not exist|invalid|no such'; then
    return 1
  fi
  result="$(printf '%s\n' "$out" | awk '/^\/data\/local\/tmp/ {print $1}' | tail -1)"
  if [[ -n "$result" ]]; then
    printf '%s\n' "$result"
    return 0
  fi
  printf '%s\n' "$dst"
}

remote_file_ready() {
  local out
  out="$(hdc_cmd shell "test -s \"$1\" && echo HREC_OK" 2>/dev/null || true)"
  printf '%s' "$out" | grep -q HREC_OK
}

try_export() {
  local src="$1"
  local dst="$2"
  local exported
  [[ -z "$src" ]] && return 1
  exported="$(mediatool_export "$src" "$dst" || true)"
  if [[ -n "$exported" ]] && remote_file_ready "$exported"; then
    printf '%s\n' "$exported"
    return 0
  fi
  return 1
}

export_one_ref() {
  local ref="$1"
  local tmp_remote="$2"
  local uri path exported candidate

  [[ -z "$ref" ]] && return 1

  if [[ "$ref" == file://* ]]; then
    exported="$(try_export "$ref" "$tmp_remote" || true)"
    [[ -n "$exported" ]] && { printf '%s\n' "$exported"; return 0; }
    candidate="$(shorten_uri "$ref")"
    exported="$(try_export "$candidate" "$tmp_remote" || true)"
    [[ -n "$exported" ]] && { printf '%s\n' "$exported"; return 0; }
    return 1
  fi

  uri="$(query_media "$(basename "$ref")" -u || true)"
  exported="$(try_export "$uri" "$tmp_remote" || true)"
  [[ -n "$exported" ]] && { printf '%s\n' "$exported"; return 0; }

  exported="$(try_export "$(path_to_uri "$ref")" "$tmp_remote" || true)"
  [[ -n "$exported" ]] && { printf '%s\n' "$exported"; return 0; }

  exported="$(try_export "$(to_media_path "$ref")" "$tmp_remote" || true)"
  [[ -n "$exported" ]] && { printf '%s\n' "$exported"; return 0; }

  exported="$(try_export "$ref" "$tmp_remote" || true)"
  [[ -n "$exported" ]] && { printf '%s\n' "$exported"; return 0; }

  candidate="$(to_fuse_path "$ref")"
  if [[ "$candidate" != "$ref" ]] && remote_file_ready "$candidate"; then
    printf '%s\n' "$candidate"
    return 0
  fi
  return 1
}

collect_export_candidates() {
  local name="$1"
  local ref
  query_media "$name" -u || true
  query_media "$name" || true
  while IFS= read -r ref; do
    [[ -n "$ref" ]] && printf '%s\n' "$ref"
  done < <(list_recent_mp4 | filter_since_start)
}

find_accessible_remote() {
  local name="$1"
  local tmp_remote="$2"
  local ref exported
  local seen=""

  while IFS= read -r ref; do
    [[ -z "$ref" ]] && continue
    case " ${seen} " in
      *" ${ref} "*) continue ;;
    esac
    seen="${seen} ${ref}"
    exported="$(export_one_ref "$ref" "$tmp_remote" || true)"
    if [[ -n "$exported" ]]; then
      printf '%s\n' "$exported"
      return 0
    fi
  done < <(collect_export_candidates "$name")
  return 1
}

is_stale_state() {
  local ts age limit
  ts="${START_TS:-}"
  if [[ -z "$ts" && -f "$STATE_FILE" ]]; then
    ts="$(file_mtime "$STATE_FILE")"
  fi
  [[ -z "$ts" ]] && return 0
  age=$(($(now_ts) - ts))
  limit=$((${DURATION:-60} + 180))
  if [[ "$age" -gt "$limit" ]]; then
    return 0
  fi
  return 1
}

resolve_outfile() {
  local name="$1"
  if [[ -z "$OUTFILE" ]]; then
    mkdir -p "$SAVE_DIR"
    OUTFILE="${SAVE_DIR}/${name}"
  elif [[ -d "$OUTFILE" || "$OUTFILE" == */ ]]; then
    mkdir -p "$OUTFILE"
    OUTFILE="${OUTFILE%/}/${name}"
  fi
  OUTFILE="$(abs_path "$OUTFILE")"
}

finish_local_file() {
  if [[ "$COPY_CLIPBOARD" -eq 1 ]]; then
    if [[ "$(uname)" != "Darwin" ]]; then
      echo "当前系统不支持文件剪贴板，已仅保存文件" >&2
    else
      copy_video_clipboard "$OUTFILE"
    fi
  fi
  if [[ "$OPEN_FILE" -eq 1 ]]; then
    open "$OUTFILE"
  fi
  if [[ "$AUTO_STOP" -eq 1 ]]; then
    notify "录屏已结束，已保存并复制到剪贴板"
  fi
  echo "$OUTFILE"
}

start_record() {
  resolve_device
  mkdir -p "$SAVE_DIR"
  REMOTE_NAME="hdc_$(date +%Y%m%d_%H%M%S).mp4"
  resolve_outfile "$REMOTE_NAME"
  START_TS="$(now_ts)"
  PHASE="recording"

  start_out="$(recorder_start 2>&1)" || true
  if printf '%s' "$start_out" | grep -qiE 'failed|error:|errorCode: *[1-9]|errno'; then
    echo "$start_out" >&2
    echo "启动录屏失败。请解锁手机后再试，锁屏状态下无法拉起录屏。" >&2
    cleanup_state
    exit 1
  fi

  start_watcher
  write_state
  echo "录屏已开始（设备 ${DEVICE}）"
  if [[ "$DURATION" -gt 0 ]]; then
    echo "最多录制 ${DURATION} 秒，到时自动结束；也可再次执行 hrec 提前结束"
  else
    echo "未设置超时，再次执行 hrec 结束录屏"
  fi
  echo "将保存到: ${OUTFILE}"
}

stop_recorder_now() {
  local stop_out
  echo "正在停止录屏..."
  stop_out="$(recorder_stop 2>&1)" || true
  if printf '%s' "$stop_out" | grep -qiE 'failed|error:|errorCode: *[1-9]|errno'; then
    echo "$stop_out" >&2
    echo "停止录屏命令返回错误，仍尝试导出。" >&2
  fi
}

export_recording() {
  local tmp_remote remote_path i
  resolve_outfile "$REMOTE_NAME"
  tmp_remote="/data/local/tmp/hrec_${REMOTE_NAME}"

  echo "正在导出录屏文件..."
  remote_path=""
  i=0
  while [[ $i -lt 3 ]]; do
    remote_path="$(find_accessible_remote "$REMOTE_NAME" "$tmp_remote" || true)"
    if [[ -n "$remote_path" ]]; then
      break
    fi
    i=$((i + 1))
    sleep 1
  done

  if [[ -z "$remote_path" ]]; then
    PHASE="export"
    write_state
    echo "录屏已停止，但还没从图库导出成功。" >&2
    echo "再执行一次 hrec 会重试导出，不会新开录屏。" >&2
    exit 1
  fi

  mkdir -p "$(dirname "$OUTFILE")"
  recv_out="$(hdc_cmd file recv "$remote_path" "$OUTFILE" 2>&1)" || true
  hdc_cmd shell "rm -f '${tmp_remote}'" >/dev/null 2>&1 || true
  if [[ ! -s "$OUTFILE" ]] || printf '%s' "$recv_out" | grep -qiE '\[Fail\]|permission denied|error opening'; then
    PHASE="export"
    write_state
    echo "拉取录屏失败: ${remote_path}" >&2
    echo "$recv_out" >&2
    echo "再执行一次 hrec 会重试导出，不会新开录屏。" >&2
    exit 1
  fi

  cleanup_state
  finish_local_file
}

stop_record() {
  local saved_copy="$COPY_CLIPBOARD"
  local saved_open="$OPEN_FILE"
  local saved_out="$OUTFILE"
  local saved_duration="$DURATION"

  if ! acquire_lock; then
    if [[ "$AUTO_STOP" -eq 1 ]]; then
      exit 0
    fi
    echo "正在结束录屏..." >&2
    exit 0
  fi

  load_state
  if [[ -n "$saved_out" ]]; then
    OUTFILE="$saved_out"
  fi
  if [[ "$saved_copy" -eq 0 ]]; then
    COPY_CLIPBOARD=0
  fi
  if [[ "$saved_open" -eq 1 ]]; then
    OPEN_FILE=1
  fi

  if [[ -z "${DEVICE:-}" || -z "${REMOTE_NAME:-}" ]]; then
    cleanup_state
    echo "录屏状态损坏，已清除。请重新执行 hrec 开始录屏。" >&2
    exit 1
  fi

  if is_stale_state; then
    echo "发现过期录屏状态（${REMOTE_NAME}），已清除。"
    cleanup_state
    DURATION="$saved_duration"
    if [[ "$AUTO_STOP" -eq 1 ]]; then
      exit 0
    fi
    start_record
    return
  fi

  if [[ "${PHASE}" == "export" ]]; then
    kill_watcher
    export_recording
    return
  fi

  kill_watcher
  stop_recorder_now
  sleep 2
  export_recording
}

if [[ -f "$STATE_FILE" ]]; then
  stop_record
else
  start_record
fi
