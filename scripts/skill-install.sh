#!/bin/bash

# skill-install: 从文件夹、zip 压缩包、URL 安装 Claude Code skill
# 校验准则: 文件夹内包含 skill.md 文件 (大小写不敏感)
# 用法: skill-install <folder|zip|url> [--name <skill-name>]

set -euo pipefail

SKILLS_DIRS=(
  "$HOME/.claude/skills"
  "$HOME/.claude-internal/skills"
)
TMPDIR_BASE="${TMPDIR:-/tmp}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

log_info()  { printf "${GREEN}[✓]${NC} %s\n" "$1"; }
log_warn()  { printf "${YELLOW}[!]${NC} %s\n" "$1"; }
log_error() { printf "${RED}[✗]${NC} %s\n" "$1"; }

cleanup() {
  [[ -n "${WORK_DIR:-}" && -d "${WORK_DIR:-}" ]] && rm -rf "$WORK_DIR"
}
trap cleanup EXIT

usage() {
  cat <<EOF
Usage: skill-install <source> [--name <skill-name>]

Source can be:
  - A local folder containing SKILL.md
  - A .zip file
  - A URL to a .zip file

Options:
  --name    Override the skill name (defaults to folder name)
  --help    Show this help message
EOF
  exit 0
}

has_skill_md() {
  local dir="$1"
  find "$dir" -maxdepth 1 -iname "skill.md" -print -quit | grep -q .
}

find_skill_root() {
  local dir="$1"
  if has_skill_md "$dir"; then
    echo "$dir"
    return 0
  fi
  local subdirs=("$dir"/*/)
  if [[ ${#subdirs[@]} -eq 1 && -d "${subdirs[0]}" ]]; then
    if has_skill_md "${subdirs[0]}"; then
      echo "${subdirs[0]}"
      return 0
    fi
  fi
  return 1
}

# --- 参数解析 ---
[[ $# -eq 0 ]] && usage

SOURCE=""
SKILL_NAME=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --name)
      SKILL_NAME="$2"
      shift 2
      ;;
    --help|-h)
      usage
      ;;
    *)
      SOURCE="$1"
      shift
      ;;
  esac
done

[[ -z "$SOURCE" ]] && { log_error "未指定安装源"; usage; }

WORK_DIR=$(mktemp -d "${TMPDIR_BASE}/skill-install.XXXXXX")

# --- 判断来源类型并获取 skill 文件夹 ---
if [[ "$SOURCE" =~ ^https?:// ]]; then
  log_info "从 URL 下载: $SOURCE"
  ZIP_FILE="$WORK_DIR/skill.zip"
  if ! curl -fsSL -o "$ZIP_FILE" "$SOURCE"; then
    log_error "下载失败: $SOURCE"
    exit 1
  fi
  EXTRACT_DIR="$WORK_DIR/extracted"
  mkdir -p "$EXTRACT_DIR"
  unzip -q "$ZIP_FILE" -d "$EXTRACT_DIR"
  SOURCE_DIR=$(find_skill_root "$EXTRACT_DIR") || {
    log_error "下载的压缩包中未找到 SKILL.md"
    exit 1
  }

elif [[ "$SOURCE" == *.zip ]]; then
  [[ ! -f "$SOURCE" ]] && { log_error "文件不存在: $SOURCE"; exit 1; }
  log_info "从 zip 安装: $SOURCE"
  EXTRACT_DIR="$WORK_DIR/extracted"
  mkdir -p "$EXTRACT_DIR"
  unzip -q "$SOURCE" -d "$EXTRACT_DIR"
  SOURCE_DIR=$(find_skill_root "$EXTRACT_DIR") || {
    log_error "压缩包中未找到 SKILL.md"
    exit 1
  }

elif [[ -d "$SOURCE" ]]; then
  log_info "从文件夹安装: $SOURCE"
  SOURCE_DIR=$(find_skill_root "$SOURCE") || {
    log_error "文件夹中未找到 SKILL.md: $SOURCE"
    exit 1
  }

else
  log_error "无法识别的来源: $SOURCE (需要文件夹、.zip 文件或 URL)"
  exit 1
fi

# --- 确定 skill 名称 ---
if [[ -z "$SKILL_NAME" ]]; then
  SKILL_NAME=$(basename "$SOURCE_DIR")
  # zip 解压的顶层目录可能带 -main 等后缀，清理掉
  SKILL_NAME="${SKILL_NAME%-main}"
  SKILL_NAME="${SKILL_NAME%-master}"
fi

# --- 检查是否已安装，任一目标存在即提示 ---
EXISTING=()
for dir in "${SKILLS_DIRS[@]}"; do
  [[ -d "$dir/$SKILL_NAME" ]] && EXISTING+=("$dir/$SKILL_NAME")
done

if [[ ${#EXISTING[@]} -gt 0 ]]; then
  log_warn "Skill '$SKILL_NAME' 已存在于:"
  printf "  %s\n" "${EXISTING[@]}"
  read -r -p "是否覆盖安装? [y/N] " confirm
  [[ "$confirm" != [yY] ]] && { log_info "已取消"; exit 0; }
  for p in "${EXISTING[@]}"; do rm -rf "$p"; done
fi

# --- 安装到所有目标目录 ---
for dir in "${SKILLS_DIRS[@]}"; do
  dest="$dir/$SKILL_NAME"
  mkdir -p "$dir"
  cp -R "$SOURCE_DIR" "$dest"
  log_info "已安装到 $dest"
done
