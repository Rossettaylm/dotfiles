#!/usr/bin/env python3
"""tmux Agent Radar 导航 —— M-n 一键跳转 / M-a 底部 dialog。

用法:
    python3 agent_nav.py jump_next    # 跳到最该处理的 agent（blocked 优先，等最久的先）
    python3 agent_nav.py menu         # 底部弹出原生 display-menu
    python3 agent_nav.py dnd 900      # 免打扰 N 秒（0 = 取消）
"""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import agent_lib as lib

SCRIPTS_DIR = Path(__file__).resolve().parent
FZF_AGENTS = SCRIPTS_DIR / "fzf_agents.tmux"
AGENTD = SCRIPTS_DIR / "agentd.py"

DND_DEFAULT_SECS = 900

STATE_STYLE = {
    "blocked": ("#{@thm_red}", ""),
    "unread": ("#{@thm_sky}", ""),
    "working": ("#{@thm_yellow}", ""),
    "idle": ("#{@thm_green}", ""),
}

COL_AGENT = 7
COL_PATH = 26
COL_DUR = 7


def esc(text: str) -> str:
    return text.replace("#", "##")


def current_client() -> str:
    """定位触发按键的那个 client。

    run-shell 里起的子进程没有「当前 client」上下文，display-menu 需要显式
    指定，否则多 client 时可能挂到错误的终端上。
    """
    pane = os.environ.get("TMUX_PANE", "")
    session = ""
    if pane:
        session = lib.tmux("display-message", "-p", "-t", pane, "#{session_name}").strip()
    clients = []
    for line in lib.tmux("list-clients", "-F", "#{client_name}\t#{client_session}").splitlines():
        parts = line.split("\t")
        if len(parts) == 2:
            clients.append((parts[0], parts[1]))
    if not clients:
        return ""
    for name, sess in clients:
        if sess == session:
            return name
    return clients[0][0]


def notify(message: str) -> None:
    client = current_client()
    args = ["display-message"]
    if client:
        args += ["-c", client]
    args.append(message)
    lib.tmux(*args)


def pick_target(panes: list[lib.AgentPane]) -> lib.AgentPane | None:
    for state in ("blocked", "unread", "working"):
        candidates = [p for p in panes if p.state == state]
        if candidates:
            # 等最久的先处理；无 daemon 时 since_ts 为 0，退化为扫描顺序
            candidates.sort(key=lambda p: p.since_ts or 0.0)
            return candidates[0]
    return None


def jump_next() -> None:
    panes = lib.load()
    if not panes:
        notify("agent radar: no agent panes")
        return
    target = pick_target(panes)
    if target is None:
        notify("agent radar: all agents idle")
        return
    dur = lib.fmt_duration(target.since_ts)
    suffix = f" · {dur}" if dur else ""
    lib.tmux("switch-client", "-t", target.pane_id)
    notify(f"→ {target.agent} [{target.state}] {target.path}{suffix}")


def menu_row(pane: lib.AgentPane) -> str:
    color, icon = STATE_STYLE.get(pane.state, ("#{@thm_overlay_2}", " "))
    dur = lib.fmt_duration(pane.since_ts)
    cells = " ".join((
        icon,
        lib.fit(pane.agent, COL_AGENT),
        lib.fit(pane.path, COL_PATH, tail=True),
        lib.fit(dur, COL_DUR),
    ))
    return f"#[fg={color}]{esc(cells)}#[default]"


def menu() -> None:
    panes = sorted(lib.load(), key=lib.sort_key)
    if not panes:
        notify("agent radar: no agent panes")
        return

    items: list[str] = []
    for idx, pane in enumerate(panes[:9], start=1):
        items += [menu_row(pane), str(idx), f"switch-client -t {pane.pane_id}"]

    items.append("")
    items += [
        lib.fit("  full view (fzf)", COL_AGENT + COL_PATH + COL_DUR + 4),
        "e",
        f"run-shell -b 'bash {FZF_AGENTS} do_action'",
    ]

    dnd_until = lib.tmux("show", "-gqv", "@agent_radar_dnd_until").strip()
    active = False
    try:
        active = float(dnd_until) > time.time()
    except ValueError:
        pass
    dnd_label = "do-not-disturb: off" if active else f"do-not-disturb {DND_DEFAULT_SECS // 60}m"
    dnd_secs = 0 if active else DND_DEFAULT_SECS
    items += [
        lib.fit("  " + dnd_label, COL_AGENT + COL_PATH + COL_DUR + 4),
        "d",
        f"run-shell 'python3 {Path(__file__).resolve()} dnd {dnd_secs}'",
    ]
    items += [
        lib.fit("  restart daemon", COL_AGENT + COL_PATH + COL_DUR + 4),
        "r",
        f"run-shell -b 'python3 {AGENTD} restart'",
    ]

    args = ["display-menu", "-x", "0", "-y", "S", "-T", "#[align=centre] Agents "]
    client = current_client()
    if client:
        args += ["-c", client]
    pane = os.environ.get("TMUX_PANE", "")
    if pane:
        args += ["-t", pane]
    lib.tmux(*(args + items))


def dnd(secs: float) -> None:
    if secs <= 0:
        lib.tmux("set", "-gu", "@agent_radar_dnd_until")
        notify("agent radar: do-not-disturb off")
        return
    lib.tmux("set", "-g", "@agent_radar_dnd_until", f"{time.time() + secs:.0f}")
    notify(f"agent radar: do-not-disturb for {int(secs) // 60}m")


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "menu"
    if cmd in ("jump_next", "menu"):
        lib.ensure_daemon()
    if cmd == "jump_next":
        jump_next()
    elif cmd == "menu":
        menu()
    elif cmd == "dnd":
        secs = float(sys.argv[2]) if len(sys.argv) > 2 else DND_DEFAULT_SECS
        dnd(secs)
    else:
        sys.exit(f"unknown command: {cmd}")


if __name__ == "__main__":
    main()
