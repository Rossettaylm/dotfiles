# -*- coding: utf-8 -*-
"""tmux AI agent 面板扫描与状态解析。

agentd.py / agent_nav.py / fzf_agents.tmux 共用的唯一数据源：
tmux 面板列表 -> agent 类型识别 -> blocked/working/idle 状态解析。

用法:
    python3 agent_lib.py dump    # 缓存新鲜则读缓存，否则实时扫描
    python3 agent_lib.py scan    # 强制实时扫描
"""

import os
import re
import subprocess
import sys
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path

CACHE_DIR = Path.home() / ".cache" / "tmux-agent-radar"
CACHE_FILE = CACHE_DIR / "state.tsv"

# blocked 优先，unknown 垫底；agentd 的排序和 fzf_agents 的分组都依赖这个顺序
STATE_RANK = ("blocked", "working", "idle", "unknown")

ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")

# 只有 claude 和 node 值得进一步识别；node 下面藏着 cursor-agent 和 pi
PANE_FILTER = (
    "#{||:#{==:#{pane_current_command},claude}"
    ",#{==:#{pane_current_command},node}}"
)
PANE_FIELDS = (
    "#D", "#{session_name}", "#{window_id}", "#{pane_current_command}",
    "#{pane_current_path}", "#{pane_pid}", "#T",
)


@dataclass
class AgentPane:
    pane_id: str
    session: str
    window_id: str
    agent: str
    path: str
    state: str
    task: str
    since_ts: float = 0.0

    def to_tsv(self) -> str:
        return "\t".join((
            self.pane_id, self.session, self.window_id, self.agent,
            self.path, self.state, self.task, f"{self.since_ts:.0f}",
        ))

    @classmethod
    def from_tsv(cls, line: str):
        parts = line.split("\t")
        if len(parts) != 8:
            return None
        try:
            since = float(parts[7])
        except ValueError:
            since = 0.0
        return cls(*parts[:7], since_ts=since)


# ── tmux / 进程调用 ──────────────────────────────────────────

def tmux(*args: str) -> str:
    """跑一条 tmux 命令，失败返回空串（tmux server 已退出时不抛异常）。"""
    try:
        r = subprocess.run(
            ("tmux",) + args, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
    except OSError:
        return ""
    return r.stdout if r.returncode == 0 else ""


def server_alive() -> bool:
    try:
        r = subprocess.run(
            ("tmux", "has-session"), capture_output=True, text=True,
        )
    except OSError:
        return False
    return r.returncode == 0


def _ps_snapshot() -> list[tuple[int, int, str]]:
    out = subprocess.run(
        ("ps", "-axo", "pid=,ppid=,command="),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    ).stdout
    rows = []
    for line in out.splitlines():
        parts = line.split(None, 2)
        if len(parts) < 3:
            continue
        try:
            rows.append((int(parts[0]), int(parts[1]), parts[2]))
        except ValueError:
            continue
    return rows


# ── agent 类型识别 ───────────────────────────────────────────
#
# claude 的 pane_current_command 就是 "claude"，直接认。
# cursor-agent 和 pi 都跑在通用的 node 下面，需要第二个信号区分：
#   1. pi 空闲时 OSC title 以自己的 'π' 图标开头 —— 零 fork 快路径
#   2. 否则扫 pane 的进程子树按命令行匹配（memo 到 pane_pid，一个 pane 的
#      agent 身份不会变，所以整个生命周期只付一次 ps 的代价）
#
# 快路径必须配子树兜底：pi 工作时图标是 spinner 而非 'π'，只靠 title 会把
# 正在干活的 pi 面板整个漏掉。

_AGENT_CMD_PATTERNS = (
    ("cursor", re.compile(r"cursor-agent", re.I)),
    ("pi", re.compile(r"(?:^|/)pi(?:\s|$)|pi-coding-agent")),
)

_agent_memo: dict[tuple[str, int], str] = {}


def _probe_process_tree(pane_pid: int) -> str:
    rows = _ps_snapshot()
    children: dict[int, list[tuple[int, str]]] = {}
    own = {pid: cmd for pid, _ppid, cmd in rows}
    for pid, ppid, cmd in rows:
        children.setdefault(ppid, []).append((pid, cmd))

    frontier = [(pane_pid, own.get(pane_pid, ""))]
    depth = 0
    while frontier and depth < 4:
        nxt = []
        for pid, cmd in frontier:
            for agent, pattern in _AGENT_CMD_PATTERNS:
                if pattern.search(cmd):
                    return agent
            nxt.extend(children.get(pid, ()))
        frontier = nxt
        depth += 1
    return ""


def agent_key_for_pane(pane_id: str, pane_pid: str, command: str, title: str) -> str:
    if command == "claude":
        return "claude"
    if command != "node":
        return ""
    if title.split(" ", 1)[0] == "π":
        return "pi"

    try:
        pid = int(pane_pid)
    except ValueError:
        return ""
    key = (pane_id, pid)
    if key not in _agent_memo:
        _agent_memo[key] = _probe_process_tree(pid)
    return _agent_memo[key]


# ── 状态解析：每个 parse_* 返回 (state, task) ────────────────

# claude 的 OSC title 只编码 working/idle；blocked（授权提示）只存在于屏幕内容里
_CLAUDE_PROMPT_RE = re.compile(
    r"do you want to (?:proceed|allow this connection)\?"
    r"|would you like to|waiting for permission"
    r"|tab to amend|ctrl\+e to explain",
    re.I,
)
_CLAUDE_CHOICE_RE = re.compile(
    r"❯?\s*1\.\s*yes|❯\s*yes|2\.\s*(?:yes|no)|3\.\s*no"
    r"|run \(once\)|skip \(esc or n\)",
    re.I,
)


def _after_first_space(text: str) -> str:
    """对齐 bash 的 ${text#* }：没有空格时原样返回。"""
    return text.split(" ", 1)[1] if " " in text else text


def claude_blocked(pane_id: str) -> bool:
    screen = tmux("capture-pane", "-pe", "-S", "-12", "-t", pane_id)
    if not screen:
        return False
    screen = ANSI_RE.sub("", screen)
    return bool(_CLAUDE_PROMPT_RE.search(screen) and _CLAUDE_CHOICE_RE.search(screen))


def parse_claude_title(pane_id: str, title: str, probe_screen: bool = True) -> tuple[str, str]:
    state = "idle" if title.split(" ", 1)[0] == "✳" else "working"
    # idle 的 claude 不可能停在授权提示上，省掉一次 capture-pane
    if state == "working" and probe_screen and claude_blocked(pane_id):
        state = "blocked"
    return state, _after_first_space(title)


def parse_cursor_title(pane_id: str, title: str, probe_screen: bool = True) -> tuple[str, str]:
    # title 形如 "<动作名> - <emoji> <状态短语>"，动作名每次工具调用都变，
    # 只有最后一个 " - " 之后的状态后缀有意义
    suffix = title.rsplit(" - ", 1)[-1].lower()
    state = "working"
    if "ready" in suffix:
        state = "idle"
    elif "waiting for confirmation" in suffix:
        state = "blocked"
    task = title.rsplit(" - ", 1)[0] if " - " in title else title
    return state, task


def parse_pi_title(pane_id: str, title: str, probe_screen: bool = True) -> tuple[str, str]:
    state = "idle" if title.split(" ", 1)[0] == "π" else "working"
    task = title.split("- ", 1)[1] if "- " in title else title
    return state, task


_PARSERS = {
    "claude": parse_claude_title,
    "cursor": parse_cursor_title,
    "pi": parse_pi_title,
}


# ── 扫描 ─────────────────────────────────────────────────────

def scan(probe_screen: bool = True) -> list[AgentPane]:
    raw = tmux("list-panes", "-aF", "\t".join(PANE_FIELDS), "-f", PANE_FILTER)
    panes: list[AgentPane] = []
    for line in raw.splitlines():
        parts = line.split("\t")
        if len(parts) != len(PANE_FIELDS):
            continue
        pane_id, session, window_id, command, path, pane_pid, title = parts

        agent = agent_key_for_pane(pane_id, pane_pid, command, title)
        if agent not in _PARSERS:
            continue

        state, task = _PARSERS[agent](pane_id, title, probe_screen)
        home = os.path.expanduser("~")
        if path.startswith(home):
            path = "~" + path[len(home):]

        # 空字段会被 bash 的 IFS 折叠掉，用占位符保住 TSV 列位
        panes.append(AgentPane(
            pane_id=pane_id, session=session, window_id=window_id,
            agent=agent, path=path, state=state or "unknown",
            task=task.replace("\t", " ").strip() or "-",
        ))
    return panes


def write_cache(panes: list[AgentPane]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CACHE_FILE.with_suffix(".tmp")
    tmp.write_text("".join(p.to_tsv() + "\n" for p in panes), encoding="utf-8")
    os.replace(tmp, CACHE_FILE)


def read_cache(max_age: float) -> list[AgentPane] | None:
    try:
        age = time.time() - CACHE_FILE.stat().st_mtime
    except OSError:
        return None
    if age > max_age:
        return None
    try:
        lines = CACHE_FILE.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    panes = [AgentPane.from_tsv(line) for line in lines if line]
    return [p for p in panes if p is not None]


def load(max_age: float = 3.0) -> list[AgentPane]:
    """优先读 daemon 写的缓存；缓存过期或不存在则同步扫一次。

    这条兜底保证 daemon 没起时所有消费方照常工作 —— 只是没有 since_ts，
    因此看不到「已等待多久」。
    """
    cached = read_cache(max_age)
    if cached is not None:
        return cached
    return scan()


def ensure_daemon() -> None:
    """确保 agentd 在跑。

    client-attached hook 只在 attach 那一刻触发，覆盖不了「已 attach 状态下
    daemon 崩溃」。所以每个交互入口（M-n / M-a / M-e）顺手兜一次底：
    正常情况只多一次 option 读取，daemon 已死才会真的 spawn。
    """
    raw = tmux("show", "-gqv", "@agent_radar_pid").strip()
    try:
        pid = int(raw)
    except ValueError:
        pid = 0
    if pid:
        try:
            os.kill(pid, 0)
            return
        except ProcessLookupError:
            pass
        except PermissionError:
            return
        except OSError:
            return
    daemon = Path(__file__).resolve().parent / "agentd.py"
    try:
        subprocess.Popen(
            (sys.executable, str(daemon)), start_new_session=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except OSError:
        pass


def sort_key(pane: AgentPane) -> tuple[int, float]:
    rank = STATE_RANK.index(pane.state) if pane.state in STATE_RANK else len(STATE_RANK)
    return (rank, pane.since_ts or float("inf"))


# ── 显示宽度（中文任务名占 2 列，不能按字符数算）────────────

def dwidth(text: str) -> int:
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)


def fit(text: str, width: int, tail: bool = False) -> str:
    if dwidth(text) <= width:
        return text + " " * (width - dwidth(text))
    if tail:
        out = ""
        for c in reversed(text):
            if dwidth(out) + dwidth(c) > width - 1:
                break
            out = c + out
        return "…" + out + " " * (width - 1 - dwidth(out))
    out = ""
    for c in text:
        if dwidth(out) + dwidth(c) > width - 1:
            break
        out += c
    return out + "…" + " " * (width - 1 - dwidth(out))


def fmt_duration(since_ts: float, now: float | None = None) -> str:
    if not since_ts:
        return ""
    secs = int((now or time.time()) - since_ts)
    if secs < 0:
        return ""
    if secs < 60:
        return f"{secs}s"
    if secs < 3600:
        return f"{secs // 60}m{secs % 60:02d}s"
    return f"{secs // 3600}h{(secs % 3600) // 60:02d}m"


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "dump"
    if cmd == "dump":
        ensure_daemon()
    if cmd == "scan":
        panes = scan()
    elif cmd == "dump":
        panes = load()
    else:
        sys.exit(f"unknown command: {cmd}")
    for pane in sorted(panes, key=sort_key):
        print(pane.to_tsv())


if __name__ == "__main__":
    main()
