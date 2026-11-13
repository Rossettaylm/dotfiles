#!/usr/bin/env python3
"""Agent Radar 推送入口：agent 的生命周期 hook 调它，把状态写进所在 pane 的 option。

agentd 每轮 scan 时读这些 option（见 agent_lib.PUSH_OPTS），比解析标题、
爬屏幕更早也更准；agent_resurrect.py 保存布局时读 @agent_session 拼恢复命令。

用法:
    agent_hook.py claude            # Claude Code hook：事件 JSON 从 stdin 读
    agent_hook.py <kind> <state> [session]   # 通用：state ∈ blocked/working/idle/end

无论发生什么都 exit 0 且不写 stdout —— hook 的输出和退出码会被 agent 当成
决策（Claude Code 的 exit 2 = 阻断工具调用），这里只能做旁观者。
"""

import json
import os
import subprocess
import sys
import time

KIND = "@agent_kind"
STATE = "@agent_state"
STATE_TS = "@agent_state_ts"
SESSION = "@agent_session"

STATES = ("blocked", "working", "idle")

# 会停下来等人回答的工具：PreToolUse 就是「球到你这边了」
_CLAUDE_ASKING_TOOLS = ("AskUserQuestion", "ExitPlanMode")
_CLAUDE_BLOCKING_NOTIFICATIONS = (
    "permission_prompt", "elicitation_dialog", "elicitation_url_dialog",
)


def claude_state(event: dict) -> str:
    name = event.get("hook_event_name", "")
    if name == "SessionEnd":
        return "end"
    if name in ("SessionStart", "Stop", "StopFailure"):
        return "idle"
    if name == "PermissionRequest":
        return "blocked"
    if name == "Notification":
        return "blocked" if event.get("notification_type") in _CLAUDE_BLOCKING_NOTIFICATIONS else ""
    if name == "PreToolUse" and event.get("tool_name") in _CLAUDE_ASKING_TOOLS:
        return "blocked"
    # PostToolUse 也算 working：授权通过后工具开跑，要把 blocked 翻回来
    if name in ("UserPromptSubmit", "PreToolUse", "PostToolUse", "PostToolUseFailure"):
        return "working"
    return ""


def publish(pane: str, kind: str, state: str, session: str) -> None:
    if state == "end":
        args = []
        for opt in (KIND, STATE, STATE_TS, SESSION):
            args += ["set", "-pu", "-t", pane, opt, ";"]
    else:
        args = [
            "set", "-p", "-t", pane, KIND, kind, ";",
            "set", "-p", "-t", pane, STATE, state, ";",
            "set", "-p", "-t", pane, STATE_TS, f"{time.time():.3f}", ";",
        ]
        if session:
            args += ["set", "-p", "-t", pane, SESSION, session, ";"]
    subprocess.run(("tmux", *args[:-1]), stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, timeout=3)


def main() -> None:
    pane = os.environ.get("TMUX_PANE", "")
    if not pane or len(sys.argv) < 2:
        return
    kind = sys.argv[1]
    if kind == "claude":
        event = json.loads(sys.stdin.read() or "{}")
        # 子 agent 的 Stop 走 SubagentStop，不会误判；但它的工具调用会刷成 working，
        # 这正是主会话的真实状态（主会话在等子 agent）
        state = claude_state(event)
        session = str(event.get("session_id") or "")
    else:
        state = sys.argv[2] if len(sys.argv) > 2 else ""
        session = sys.argv[3] if len(sys.argv) > 3 else ""
    if state in STATES or state == "end":
        publish(pane, kind, state, session)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
