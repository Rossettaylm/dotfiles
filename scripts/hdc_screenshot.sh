#!/usr/bin/env bash
# HarmonyOS hdc 截屏：保存到 ~/Pictures/screenshot，并复制到剪贴板
#
# 用法: hdc_screenshot.sh [-t <sn>] [-o] [-n]
#   -t  指定设备序列号
#   -o  用默认应用打开图片
#   -n  只落盘，不复制到剪贴板

set -euo pipefail

SAVE_DIR="${HOME}/Pictures/screenshot"
REMOTE_PNG="/data/local/tmp/hdc_shot.png"
REMOTE_JPG="/data/local/tmp/hdc_shot.jpeg"

DEVICE=""
OPEN_FILE=0
COPY_CLIPBOARD=1

usage() {
  cat <<'EOF'
用法: hshot [-t <sn>] [-o] [-n]

  -t <sn>  指定 hdc 设备
  -o       保存后用默认应用打开
  -n       只保存文件，不复制到剪贴板
EOF
}

while getopts ":t:onh" opt; do
  case "$opt" in
    t) DEVICE="$OPTARG" ;;
    o) OPEN_FILE=1 ;;
    n) COPY_CLIPBOARD=0 ;;
    h)
      usage
      exit 0
      ;;
    \?)
      echo "未知参数: -$OPTARG" >&2
      usage
      exit 1
      ;;
  esac
done

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

if [[ -z "$DEVICE" ]]; then
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
fi

mkdir -p "$SAVE_DIR"
outfile="${SAVE_DIR}/hdc_$(date +%Y%m%d_%H%M%S).png"

cleanup_remote() {
  hdc_cmd shell rm -f "$REMOTE_PNG" "$REMOTE_JPG" >/dev/null 2>&1 || true
}

if hdc_cmd shell uitest screenCap -p "$REMOTE_PNG" >/dev/null 2>&1; then
  hdc_cmd file recv "$REMOTE_PNG" "$outfile" >/dev/null
elif hdc_cmd shell snapshot_display -f "$REMOTE_JPG" >/dev/null 2>&1; then
  tmp_jpg="${outfile%.png}.jpeg"
  hdc_cmd file recv "$REMOTE_JPG" "$tmp_jpg" >/dev/null
  if command -v sips >/dev/null 2>&1; then
    sips -s format png "$tmp_jpg" --out "$outfile" >/dev/null
    rm -f "$tmp_jpg"
  else
    outfile="$tmp_jpg"
  fi
else
  cleanup_remote
  echo "截屏失败：uitest screenCap 与 snapshot_display 均不可用" >&2
  exit 1
fi

cleanup_remote

if [[ ! -s "$outfile" ]]; then
  echo "截屏文件为空: $outfile" >&2
  exit 1
fi

if [[ "$COPY_CLIPBOARD" -eq 1 ]]; then
  if [[ "$(uname)" != "Darwin" ]]; then
    echo "当前系统不支持图片剪贴板，已仅保存文件" >&2
  else
    osascript \
      -e 'on run args' \
      -e 'set the clipboard to (read (POSIX file (first item of args)) as «class PNGf»)' \
      -e 'end run' \
      "$outfile" >/dev/null
  fi
fi

if [[ "$OPEN_FILE" -eq 1 ]]; then
  open "$outfile"
fi

echo "$outfile"
