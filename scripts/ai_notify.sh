#!/usr/bin/env bash
# AI Assistant 统一通知脚本
# 被 Claude Code / CodeBuddy Code 的 Stop / Notification hook 调用
#
# 用法: ai_notify.sh <event> [message]
#   event: "stop" | "subagent_stop" | "notification"
#   message: 自定义通知内容（可选）
#
# Notification 事件会通过 stdin 传入 JSON（含 .message 字段）

set -uo pipefail

EVENT="${1:-stop}"
MSG="${2:-}"

case "$EVENT" in
  stop)
    TITLE="AI Task Done"
    MSG="${MSG:-任务已完成，等待你的指令}"
    SOUND="Glass"
    ;;
  notification)
    TITLE="AI Notification"
    if [[ -z "$MSG" ]]; then
      MSG=$(jq -r '.message // "需要你的操作"' 2>/dev/null || echo '需要你的操作')
    fi
    SOUND="Ping"
    ;;
  *)
    exit 0
    ;;
esac

# 发送 macOS 通知：Ghostty 不在前台，或用户不在 AI pane 所在的 window
SHOULD_NOTIFY=false
frontmost=$(osascript -e \
  'tell application "System Events" to get name of first application process whose frontmost is true' \
  2>/dev/null || true)
if [[ "$frontmost" != "ghostty" ]]; then
  SHOULD_NOTIFY=true
elif [[ -n "${TMUX:-}" && -n "${TMUX_PANE:-}" ]]; then
  # Ghostty 在前台，检查 client 是否正在看 AI pane 所在的 session:window
  # 注意：display-message -p 不带 -t 会返回 client active pane 而非脚本所在 pane，
  # 必须用 -t "$TMUX_PANE" 获取脚本实际所在的 session/window
  my_session=$(tmux display-message -t "$TMUX_PANE" -p '#{session_name}' 2>/dev/null || true)
  my_window=$(tmux display-message -t "$TMUX_PANE" -p '#{window_index}' 2>/dev/null || true)
  # client 当前 attach 的 session
  client_session=$(tmux list-clients -F '#{client_session}' 2>/dev/null | head -1 || true)
  if [[ "$my_session" != "$client_session" ]]; then
    # 用户在另一个 session
    SHOULD_NOTIFY=true
  else
    # 同一 session，检查 active window
    active_window=$(tmux list-windows -t "${client_session}" -F '#{window_index}' -f '#{window_active}' 2>/dev/null | head -1 || true)
    if [[ "$my_window" != "$active_window" ]]; then
      SHOULD_NOTIFY=true
    fi
  fi
fi
if [[ "$SHOULD_NOTIFY" == "true" ]]; then
  terminal-notifier -title "$TITLE" -message "$MSG" -sound "$SOUND" 2>/dev/null || true
fi

# 标记当前 pane 为 AI 待切换（fzf_panes 会优先展示）
# 仅在 AI pane 不可见时才更新 MRU 和 pending 标记（与系统通知逻辑一致）
if [[ -n "${TMUX:-}" && -n "${TMUX_PANE:-}" && "$SHOULD_NOTIFY" == "true" ]]; then
  ai_pane="$TMUX_PANE"
  if [[ -n "$ai_pane" ]]; then
    tmux set -g '@ai_pending_pane' "$ai_pane" 2>/dev/null || true
    # 更新 MRU，将 AI pane 提到最前
    bash "$(dirname "$0")/../tmux/scripts/fzf_panes.tmux" update_mru_pane_ids 2>/dev/null || true
  fi
fi
