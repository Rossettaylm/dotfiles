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

IS_MACOS=false
[[ "$(uname)" == "Darwin" ]] && IS_MACOS=true

# 脚本所在 pane 是否可见（同一 session 且为 active window）。
# 不在 tmux 中时返回 1（调用方按"不可见"处理）。
pane_visible() {
  [[ -n "${TMUX:-}" && -n "${TMUX_PANE:-}" ]] || return 1

  # 注意：display-message -p 不带 -t 会返回 client active pane 而非脚本所在 pane，
  # 必须用 -t "$TMUX_PANE" 获取脚本实际所在的 session/window
  local my_session my_window client_session active_window
  my_session=$(tmux display-message -t "$TMUX_PANE" -p '#{session_name}' 2>/dev/null || true)
  my_window=$(tmux display-message -t "$TMUX_PANE" -p '#{window_index}' 2>/dev/null || true)
  client_session=$(tmux list-clients -F '#{client_session}' 2>/dev/null | head -1 || true)

  [[ "$my_session" == "$client_session" ]] || return 1

  active_window=$(tmux list-windows -t "$client_session" -F '#{window_index}' -f '#{window_active}' 2>/dev/null | head -1 || true)
  [[ "$my_window" == "$active_window" ]]
}

# ── 判定是否需要通知 ────────────────────────────────────────
SHOULD_NOTIFY=false
IN_TMUX=false
[[ -n "${TMUX:-}" && -n "${TMUX_PANE:-}" ]] && IN_TMUX=true

if [[ "$IS_MACOS" == "true" ]]; then
  # Ghostty 不在前台时直接通知，避免用户切走后错过
  frontmost=$(osascript -e \
    'tell application "System Events" to get name of first application process whose frontmost is true' \
    2>/dev/null || true)
  if [[ "$frontmost" != "ghostty" ]]; then
    SHOULD_NOTIFY=true
  elif [[ "$IN_TMUX" == "true" ]]; then
    # Ghostty 在前台，检查 client 是否正在看 AI pane 所在的 session:window
    pane_visible || SHOULD_NOTIFY=true
  fi
else
  # Linux 无法感知终端是否前台，改以 pane 可见性为准
  if [[ "$IN_TMUX" != "true" ]]; then
    SHOULD_NOTIFY=true
  else
    pane_visible || SHOULD_NOTIFY=true
  fi
fi

# ── 发送系统通知 ────────────────────────────────────────────
if [[ "$SHOULD_NOTIFY" == "true" ]]; then
  if [[ "$IS_MACOS" == "true" ]]; then
    terminal-notifier -title "$TITLE" -message "$MSG" -sound "$SOUND" 2>/dev/null || true
  elif command -v notify-send >/dev/null 2>&1; then
    notify-send -u normal "$TITLE" "$MSG" 2>/dev/null || true
  fi
fi

# 标记当前 pane 为 AI 待切换（fzf_agents 会优先展示）
# 仅在 AI pane 不可见时才更新 MRU 和 pending 标记（与系统通知逻辑一致）
if [[ -n "${TMUX:-}" && -n "${TMUX_PANE:-}" && "$SHOULD_NOTIFY" == "true" ]]; then
  tmux set -g '@ai_pending_pane' "$TMUX_PANE" 2>/dev/null || true
  # 更新 MRU，将 AI pane 提到最前
  bash "$(dirname "$0")/../tmux/scripts/fzf_agents.tmux" update_mru_pane_ids 2>/dev/null || true
fi
