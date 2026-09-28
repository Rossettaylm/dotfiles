#!/usr/bin/env python3
"""tmux Agent Radar daemon —— 把 agent 状态推到状态栏 / tab 角标 / pane 边框。

单例保证沿用仓库惯例（tmux option 当标志位，见 watch_pane.sh 的 @pane_watching）：
@agent_radar_pid 存住 owner pid，循环里校验它仍等于自己，所以
`tmux set -gu @agent_radar_pid` 就是一条干净的「停掉 daemon」指令。
tmux server 一死 option 随之消失，磁盘上不留 pid 文件。

用法:
    python3 agentd.py            # 常驻
    python3 agentd.py --once     # 只跑一轮（调试用）
    python3 agentd.py restart    # 停掉在跑的实例再常驻
"""

import os
import signal
import subprocess
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import agent_lib as lib

LOG_DIR = Path.home() / "templog"

DEFAULT_INTERVAL = 2.0
DEFAULT_TOAST_SECS = 4.0

ICON_BLOCKED = ""  # nf-fa-warning
ICON_WORKING = ""  # nf-fa-spinner
ICON_IDLE = ""     # nf-fa-check-circle
ICON_UNREAD = ""   # nf-fa-bell，跑完但还没看过
ICON_SILENT = ""   # nf-fa-circle，daemon 活着但无 agent

OPT_KEYS = (
    "@agent_summary",
    "@agent_toast",
    "@agent_blocked_windows",
    "@agent_blocked_panes",
    "@agent_unread_windows",
    "@agent_unread_panes",
)


def log(message: str) -> None:
    # 跟缓存一样按 server 分文件 —— 隔离 server 上起的 daemon 崩溃日志不该混进
    # 真实 server 那份，否则排查时被别人的 traceback 误导
    path = LOG_DIR / f"agent_radar.{lib.server_tag()}.log"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with path.open("a", encoding="utf-8") as fh:
            fh.write(f"[{stamp}] {message}\n")
    except OSError:
        pass


def esc(text: str) -> str:
    """tmux format 里 '#' 是转义引导符，字面量要双写。"""
    return text.replace("#", "##")


def opt_float(name: str, fallback: float) -> float:
    raw = lib.tmux("show", "-gqv", name).strip()
    try:
        return float(raw)
    except ValueError:
        return fallback


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def owner_pid() -> int:
    raw = lib.tmux("show", "-gqv", "@agent_radar_pid").strip()
    try:
        return int(raw)
    except ValueError:
        return 0


# ── 渲染 ─────────────────────────────────────────────────────

def render_summary(counts: dict[str, int], oldest_blocked: float, now: float) -> str:
    segs = []
    if counts.get("blocked"):
        segs.append(f"#[fg=#{{@thm_red}},bold]{ICON_BLOCKED} {counts['blocked']}#[nobold]")
    if counts.get("unread"):
        segs.append(f"#[fg=#{{@thm_sky}}]{ICON_UNREAD} {counts['unread']}")
    if counts.get("working"):
        segs.append(f"#[fg=#{{@thm_yellow}}]{ICON_WORKING} {counts['working']}")
    if counts.get("idle"):
        segs.append(f"#[fg=#{{@thm_green}}]{ICON_IDLE} {counts['idle']}")
    if not segs:
        # daemon 活着但一个 agent 都没有。留一个暗色点，好让「安静」和
        # 「daemon 挂了」（整段消失）在视觉上能区分开。
        return f"#[push-default]#[fg=#{{@thm_overlay_0}}]{ICON_SILENT}#[pop-default] "
    # 等待时长只在真有 blocked 时出现，避免常态噪音
    if counts.get("blocked") and oldest_blocked:
        dur = lib.fmt_duration(oldest_blocked, now)
        if dur:
            segs.append(f"#[fg=#{{@thm_overlay_2}}]│#[fg=#{{@thm_red}}]{dur}")
    return "#[push-default]" + " ".join(segs) + "#[pop-default] "


def render_toast(events: list[tuple[str, lib.AgentPane]]) -> str:
    if not events:
        return ""
    kind, pane = events[0]
    label = esc(pane.agent)
    where = esc(os.path.basename(pane.path.rstrip("/")) or pane.path)
    extra = f" +{len(events) - 1}" if len(events) > 1 else ""
    if kind == "blocked":
        body = f"#[fg=#{{@thm_red}},bold]{ICON_BLOCKED} {label} blocked#[nobold] {where}{extra}"
    else:
        body = f"#[fg=#{{@thm_sky}}]{ICON_UNREAD} {label} done#[default] {where}{extra}"
    return "#[push-default]" + body + "#[pop-default] "


def notify_system(events: list[tuple[str, lib.AgentPane]]) -> None:
    blocked = [pane for kind, pane in events if kind == "blocked"]
    if not blocked:
        return
    pane = blocked[0]
    extra = f" (+{len(blocked) - 1})" if len(blocked) > 1 else ""
    title = "tmux · agent blocked"
    body = f"{pane.agent} @ {pane.path}{extra}"
    script = (
        f'display notification {_osa_quote(body)} '
        f'with title {_osa_quote(title)}'
    )
    try:
        subprocess.Popen(
            ("osascript", "-e", script),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except OSError:
        pass


def _osa_quote(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


# ── 主循环 ───────────────────────────────────────────────────

def _settled(state: str) -> bool:
    """idle 和 unread 是同一个底层状态（跑完了），只差用户看没看过。

    两者互转不算状态变化 —— 否则 since_ts 会被重置成「你刚看它的时刻」，
    M-a 菜单里的等待时长就废了。"""
    return state in ("idle", "unread")


class Radar:
    def __init__(self) -> None:
        self.prev: dict[str, lib.AgentPane] = {}
        self.written: dict[str, str] = {}
        self.toast_until = 0.0
        self.toast_value = ""

    def tick(self) -> None:
        now = time.time()
        # 焦点所在 pane 一律算已读：这覆盖了「光标停着不动、agent 自己在后台
        # 跑完」——结果就滚在你眼前，不该再报 unread
        focused = lib.focused_pane_id()
        lib.mark_seen(focused)
        # 在这里派生 unread 而不是 scan() 里：since_ts 由本 daemon 的 prev 持有，
        # scan() 读到它永远是 0
        panes = lib.scan()

        # 第一趟：定 since_ts，并挑出真有状态跃迁的 pane
        moved: list[lib.AgentPane] = []
        for pane in panes:
            old = self.prev.get(pane.pane_id)
            if old is not None and (old.state == pane.state
                                    or (_settled(old.state) and _settled(pane.state))):
                pane.since_ts = old.since_ts or now
                continue
            pane.since_ts = now
            if old is None:
                # daemon 刚起 / 面板刚出现：since_ts 只能伪造成 now，据此派生的
                # unread 会是纯误报（now > 看到过的任何 seen_ts）。跟「不补报历史
                # 状态」同一套约定 —— 首次见到的 pane 一律算已读，代价是 daemon
                # 重启期间跑完的 agent 不会亮铃铛（宁可漏报，不要误报）
                lib.mark_seen(pane.pane_id, now)
                pane.seen_ts = now
            else:
                moved.append(pane)

        # 第二趟：since_ts 就位后才谈得上派生 unread
        lib.apply_unread(panes, focused)

        events: list[tuple[str, lib.AgentPane]] = []
        for pane in moved:
            if pane.state == "blocked":
                events.append(("blocked", pane))
            elif pane.state == "unread" and self.prev[pane.pane_id].state in ("working", "blocked"):
                events.append(("idle", pane))

        lib.write_cache(panes)

        counts: dict[str, int] = {}
        blocked_windows: list[str] = []
        blocked_panes: list[str] = []
        unread_windows: list[str] = []
        unread_panes: list[str] = []
        oldest_blocked = 0.0
        for pane in panes:
            state = pane.state
            counts[state] = counts.get(state, 0) + 1
            if state == "blocked":
                if pane.window_id not in blocked_windows:
                    blocked_windows.append(pane.window_id)
                blocked_panes.append(pane.pane_id)
                if not oldest_blocked or pane.since_ts < oldest_blocked:
                    oldest_blocked = pane.since_ts
            elif state == "unread":
                if pane.window_id not in unread_windows:
                    unread_windows.append(pane.window_id)
                unread_panes.append(pane.pane_id)

        dnd = opt_float("@agent_radar_dnd_until", 0.0) > now
        if events and not dnd:
            self.toast_value = render_toast(events)
            self.toast_until = now + opt_float("@agent_radar_toast_secs", DEFAULT_TOAST_SECS)
            notify_system(events)
        if now >= self.toast_until:
            self.toast_value = ""

        self.publish({
            "@agent_summary": render_summary(counts, oldest_blocked, now),
            "@agent_toast": self.toast_value,
            "@agent_blocked_windows": _joined(blocked_windows),
            "@agent_blocked_panes": _joined(blocked_panes),
            "@agent_unread_windows": _joined(unread_windows),
            "@agent_unread_panes": _joined(unread_panes),
        })

        self.prev = {pane.pane_id: pane for pane in panes}

    def publish(self, values: dict[str, str]) -> None:
        args: list[str] = []
        for key, value in values.items():
            if self.written.get(key) == value:
                continue
            if args:
                args.append(";")
            args += ["set", "-g", key, value]
            self.written[key] = value
        if not args:
            return
        args += [";", "refresh-client", "-S"]
        lib.tmux(*args)

    def clear(self) -> None:
        args: list[str] = []
        for key in OPT_KEYS:
            if args:
                args.append(";")
            args += ["set", "-g", key, ""]
        args += [";", "refresh-client", "-S"]
        lib.tmux(*args)


def stop_running_instance() -> None:
    pid = owner_pid()
    lib.tmux("set", "-gu", "@agent_radar_pid")
    if not pid or pid == os.getpid() or not pid_alive(pid):
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return
    for _ in range(20):
        if not pid_alive(pid):
            return
        time.sleep(0.1)


def acquire() -> bool:
    pid = owner_pid()
    if pid and pid != os.getpid() and pid_alive(pid):
        return False
    lib.tmux("set", "-g", "@agent_radar_pid", str(os.getpid()))
    return True


def run(once: bool = False) -> None:
    radar = Radar()
    me = str(os.getpid())
    try:
        while True:
            if not lib.server_alive():
                return
            radar.tick()
            if once:
                return
            time.sleep(opt_float("@agent_radar_interval", DEFAULT_INTERVAL))
            if lib.tmux("show", "-gqv", "@agent_radar_pid").strip() != me:
                return
    finally:
        if not once and owner_pid() == os.getpid():
            lib.tmux("set", "-gu", "@agent_radar_pid")
            radar.clear()


def _joined(items: list[str]) -> str:
    return "|" + "|".join(items) + "|" if items else ""


def main() -> None:
    args = sys.argv[1:]
    if "restart" in args:
        stop_running_instance()
        args = [a for a in args if a != "restart"]

    once = "--once" in args
    if not once and not acquire():
        return

    def _bail(_signum, _frame):
        sys.exit(0)

    signal.signal(signal.SIGTERM, _bail)
    try:
        run(once=once)
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception:
        log("tick failed:\n" + traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
