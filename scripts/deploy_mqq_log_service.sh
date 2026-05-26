#!/bin/bash
# deploy_mqq_log_service.sh - 一键部署 MQQ 日志捕获后台服务
#
# 用法：
#   chmod +x deploy_mqq_log_service.sh && ./deploy_mqq_log_service.sh
#
# 执行内容：
#   1. 将捕获脚本安装到 ~/.config/scripts/
#   2. 生成 launchd plist（自动适配当前用户和 hdc 路径）
#   3. 加载服务

set -euo pipefail

SCRIPT_DIR="$HOME/.config/scripts"
SCRIPT_NAME="capture_mqq_log.sh"
SCRIPT_PATH="$SCRIPT_DIR/$SCRIPT_NAME"
SERVICE_LABEL="com.lyman.capture-mqq-log"
PLIST_PATH="$HOME/Library/LaunchAgents/${SERVICE_LABEL}.plist"
LOG_DIR="$HOME/harmony_log"

# --- 检测 hdc ---

HDC_PATH=$(which hdc 2>/dev/null || true)
if [ -z "$HDC_PATH" ]; then
  # 常见安装位置
  for candidate in \
    "/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc" \
    "$HOME/Library/OpenHarmony/Sdk/toolchains/hdc" \
    "/usr/local/bin/hdc"; do
    if [ -x "$candidate" ]; then
      HDC_PATH="$candidate"
      break
    fi
  done
fi

if [ -z "$HDC_PATH" ]; then
  echo "❌ 未找到 hdc，请确认 DevEco Studio 已安装"
  echo "   或手动设置: export PATH=\$PATH:/path/to/hdc/dir"
  exit 1
fi

HDC_DIR=$(dirname "$HDC_PATH")
echo "✓ 找到 hdc: $HDC_PATH"

# --- 卸载旧服务（如果存在） ---

if launchctl list 2>/dev/null | grep -q "$SERVICE_LABEL"; then
  echo "→ 卸载旧服务..."
  launchctl unload "$PLIST_PATH" 2>/dev/null || true
fi

# --- 安装脚本 ---

mkdir -p "$SCRIPT_DIR" "$LOG_DIR"

if [ ! -f "$SCRIPT_PATH" ]; then
  echo "❌ 未找到 $SCRIPT_PATH，请确认文件已放置"
  exit 1
fi

chmod +x "$SCRIPT_PATH"
echo "✓ 脚本已安装: $SCRIPT_PATH"

# --- 生成 plist ---

cat > "$PLIST_PATH" << PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${SERVICE_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>${SCRIPT_PATH}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${LOG_DIR}/service.log</string>
    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/service.err</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin:${HDC_DIR}</string>
        <key>HOME</key>
        <string>${HOME}</string>
    </dict>
</dict>
</plist>
PLIST_EOF

echo "✓ plist 已生成: $PLIST_PATH"

# --- 加载服务 ---

launchctl load "$PLIST_PATH"
echo "✓ 服务已加载并启动"

# --- 验证 ---

sleep 1
if launchctl list 2>/dev/null | grep -q "$SERVICE_LABEL"; then
  echo ""
  echo "══════════════════════════════════════════"
  echo "  部署完成！"
  echo "══════════════════════════════════════════"
  echo "  日志目录: $LOG_DIR"
  echo "  服务日志: $LOG_DIR/service.log"
  echo ""
  echo "  常用命令:"
  echo "    查看状态: launchctl list | grep mqq"
  echo "    停止服务: launchctl unload $PLIST_PATH"
  echo "    重启服务: launchctl unload $PLIST_PATH && launchctl load $PLIST_PATH"
  echo "    查看日志: tail -f $LOG_DIR/service.log"
  echo "══════════════════════════════════════════"
else
  echo "⚠️  服务可能未正常启动，检查: launchctl list | grep mqq"
fi
