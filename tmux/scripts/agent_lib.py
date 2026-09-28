# -*- coding: utf-8 -*-
"""tmux AI agent 面板扫描与状态解析。

agentd.py / agent_nav.py / fzf_agents.tmux 共用的唯一数据源：
tmux 面板列表 -> agent 类型识别 -> blocked/working/idle 状态解析。

用法:
    python3 agent_lib.py dump    # 缓存新鲜则读缓存，否则实时扫描
    python3 agent_lib.py scan    # 强制实时扫描
"""

import json
import os
import re
import subprocess
import sys
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path

CACHE_ROOT = Path.home() / ".cache" / "tmux-agent-radar"


def server_tag() -> str:
    """当前 tmux server 的短名，磁盘状态按它分命名空间。

    TMUX 环境变量形如 <socket_path>,<pid>,<session>，tmux CLI 正是按它选
    server，所以这里跟 CLI 的解析规则天然一致：没有 TMUX 时 CLI 落到默认
    socket，tag 也取 default。

    取 basename 而非全路径 —— macOS 上 /tmp 是 /private/tmp 的软链，同一个
    socket 有这两种写法，按全路径分会裂成两个缓存目录。
    """
    path = os.environ.get("TMUX", "").split(",", 1)[0]
    name = os.path.basename(path) if path else "default"
    return re.sub(r"[^A-Za-z0-9._-]", "_", name) or "default"


def cache_file() -> Path:
    # 不缓存结果：一次 os.environ 读取而已，比为此引入模块级可变状态划算
    return CACHE_ROOT / server_tag() / "state.tsv"


# blocked 优先，unread（跑完没看）次之，unknown 垫底；
# agentd 的排序、agent_nav 的 pick_target 和 fzf_agents 的分组都依赖这个顺序
STATE_RANK = ("blocked", "unread", "working", "idle", "unknown")

ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")

# 只有 claude 和 node 值得进一步识别；node 下面藏着 cursor-agent 和 pi
PANE_FILTER = (
    "#{||:#{==:#{pane_current_command},claude}"
    ",#{==:#{pane_current_command},node}}"
)
PANE_FIELDS = (
    "#D", "#{session_name}", "#{window_id}", "#{pane_current_command}",
    "#{pane_current_path}", "#{pane_pid}", "#T", "#{@agent_seen_ts}",
)

# 「client 正盯着这个 pane」：三层缺一不可 —— session_attached 排掉 detached
# session 的当前 pane，window_active 排掉非当前窗口，pane_active 排掉同窗口的非焦点 pane
FOCUS_FIELDS = (
    "#{&&:#{pane_active},#{&&:#{window_active},#{session_attached}}}",
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
    # 已读水位：pane option @agent_seen_ts。不写进 TSV —— 它是 per-client 的
    # 焦点状态，不该污染 daemon 写的那份缓存
    seen_ts: float = 0.0

    def to_tsv(self) -> str:
        return "\t".join((
            self.pane_id, self.session, self.window_id, self.agent,
            # .3f 必须和 mark_seen 写 pane option 的精度一致：用 .0f 会把
            # since_ts 进位到整秒，变成 > 同一时刻的 seen_ts，把「刚跑完正好
            # 被标记已读」的 pane 全误判成 unread
            self.path, self.state, self.task, f"{self.since_ts:.3f}",
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


# claude >= 2.1.2xx 在 tmux/screen/zellij 下 title 前缀恒为 ✳（远端 flag
# tengu_static_title_under_mux），title 已不能区分 working/idle。改读它自报的
# ~/.claude/sessions/<pid>.json：status ∈ busy/waiting/idle，tmux 字段形如
# "<session>:@<window>.%<pane>"。
CLAUDE_SESSIONS_DIR = Path.home() / ".claude" / "sessions"
_CLAUDE_STATUS = {"busy": "working", "waiting": "blocked", "idle": "idle"}


def _pid_alive(pid) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        return True
    return True


def claude_session_status() -> dict[str, str]:
    """pane_id -> claude 自报的 status。pid 已死的残留文件跳过；
    同一 pane 先后跑过多个 claude 时取 statusUpdatedAt 最新的。"""
    best: dict[str, tuple[float, str]] = {}
    for f in CLAUDE_SESSIONS_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        status = data.get("status")
        pane = str(data.get("tmux") or "").rpartition(".")[2]
        if status not in _CLAUDE_STATUS or not pane.startswith("%"):
            continue
        if not _pid_alive(data.get("pid")):
            continue
        ts = data.get("statusUpdatedAt") or 0
        if pane not in best or ts > best[pane][0]:
            best[pane] = (ts, status)
    return {pane: status for pane, (_ts, status) in best.items()}


def parse_claude_title(pane_id: str, title: str, probe_screen: bool = True,
                       status: str = "") -> tuple[str, str]:
    state = _CLAUDE_STATUS.get(status) or (
        "idle" if title.split(" ", 1)[0] == "✳" else "working"
    )
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


# ── 已读水位 ─────────────────────────────────────────────────
#
# 「跑完但还没看过」不新增状态机，纯派生：idle 且 since_ts > seen_ts。
# since_ts 在 agentd 里于状态变化时置为 now，所以 idle 的 since_ts 正好就是
# 「本轮跑完的时刻」。seen_ts 存 tmux pane option —— pane 一销毁自动回收，
# 不用写 GC，也不像全局 option 那样需要自己清理。

def _parse_ts(raw: str) -> float:
    try:
        return float(raw)
    except ValueError:
        return 0.0


def focused_pane_id() -> str:
    """当前 client 正盯着的 pane。无 attached client 时返回空串。"""
    raw = tmux("list-panes", "-aF", "\t".join(("#D",) + FOCUS_FIELDS))
    for line in raw.splitlines():
        parts = line.split("\t")
        if len(parts) == len(FOCUS_FIELDS) + 1 and parts[1] == "1":
            return parts[0]
    return ""


def mark_seen(pane_id: str, ts: float | None = None) -> None:
    """把 pane 的已读水位推到 ts（默认此刻）。只增不减，重复调用无害。"""
    if not pane_id:
        return
    ts = ts if ts is not None else time.time()
    if _parse_ts(tmux("show", "-pv", "-t", pane_id, "@agent_seen_ts").strip()) >= ts:
        return
    # 存毫秒精度：since_ts 是 float，取整会让「同一秒内跑完 -> 已读」比较错向
    tmux("set", "-p", "-t", pane_id, "@agent_seen_ts", f"{ts:.3f}")


def seen_ts_map() -> dict[str, float]:
    """一次 list-panes 取全量已读水位。"""
    raw = tmux("list-panes", "-aF", "#D\t#{@agent_seen_ts}")
    out: dict[str, float] = {}
    for line in raw.splitlines():
        parts = line.split("\t")
        if len(parts) == 2:
            out[parts[0]] = _parse_ts(parts[1])
    return out


def apply_unread(panes: list[AgentPane], focused: str = "") -> list[AgentPane]:
    """把「跑完但没看过」的 idle 改判成 unread。

    必须在 since_ts 就位之后调用 —— 它不在 PANE_FIELDS 里（由 daemon 的 prev
    持有），scan() 刚出来时恒为 0，那时候判等于把所有 pane 都当已读。

    focused 传当前 client 盯着的 pane：正在你眼皮底下跑完的不算未读。
    """
    for pane in panes:
        if pane.pane_id == focused:
            # 正盯着的那个：idle 是唯一合理值（真要还在跑就会是 working）
            if pane.state == "unread":
                pane.state = "idle"
            continue
        if pane.since_ts <= 0:
            # 拿不到「跑完时刻」就无从判断，保守地留在原状态
            continue
        if pane.since_ts > pane.seen_ts:
            if pane.state == "idle":
                pane.state = "unread"
        elif pane.state == "unread":
            # 双向：cache 里可能存着上一轮派生的 unread，用户之后才看的，
            # 这里要能自己纠正回来，不能是单向闩锁
            pane.state = "idle"
    return panes


# ── 扫描 ─────────────────────────────────────────────────────

def scan(probe_screen: bool = True) -> list[AgentPane]:
    raw = tmux("list-panes", "-aF", "\t".join(PANE_FIELDS), "-f", PANE_FILTER)
    panes: list[AgentPane] = []
    claude_status: dict[str, str] | None = None
    for line in raw.splitlines():
        parts = line.split("\t")
        if len(parts) != len(PANE_FIELDS):
            continue
        pane_id, session, window_id, command, path, pane_pid, title, seen = parts

        agent = agent_key_for_pane(pane_id, pane_pid, command, title)
        if agent not in _PARSERS:
            continue

        if agent == "claude":
            if claude_status is None:
                claude_status = claude_session_status()
            state, task = parse_claude_title(
                pane_id, title, probe_screen, claude_status.get(pane_id, ""),
            )
        else:
            state, task = _PARSERS[agent](pane_id, title, probe_screen)
        home = os.path.expanduser("~")
        if path.startswith(home):
            path = "~" + path[len(home):]

        # 空字段会被 bash 的 IFS 折叠掉，用占位符保住 TSV 列位
        panes.append(AgentPane(
            pane_id=pane_id, session=session, window_id=window_id,
            agent=agent, path=path, state=state or "unknown",
            task=task.replace("\t", " ").strip() or "-",
            seen_ts=_parse_ts(seen),
        ))
    return panes


def write_cache(panes: list[AgentPane]) -> None:
    path = cache_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text("".join(p.to_tsv() + "\n" for p in panes), encoding="utf-8")
    os.replace(tmp, path)


def read_cache(max_age: float) -> list[AgentPane] | None:
    """缓存新鲜才返回，否则 None。空文件当作过期 —— 见 load() 的说明。"""
    path = cache_file()
    try:
        age = time.time() - path.stat().st_mtime
    except OSError:
        return None
    if age > max_age:
        return None
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    panes = [AgentPane.from_tsv(line) for line in lines if line]
    panes = [p for p in panes if p is not None]
    return panes or None


def load(max_age: float = 3.0) -> list[AgentPane]:
    """优先读 daemon 写的缓存；缓存过期或不存在则同步扫一次。

    这条兜底保证 daemon 没起时所有消费方照常工作 —— 只是没有 since_ts，
    因此看不到「已等待多久」。
    """
    cached = read_cache(max_age)
    if cached is None:
        # 无缓存 = 无 daemon，scan() 给不出 since_ts，unread 自然派生不出来。
        # 跟「无 daemon 时看不到等待时长」是同一类降级。
        #
        # 空文件也走这条：write_cache 是 tmp + rename 的原子写，空文件正是
        # 「零个 agent」的合法内容，所以「空」本身无法与「陈旧」区分。宁可让
        # 真无 agent 时多扫一次实时，也不要让写缓存的那一瞬被当成数据。
        return scan()
    # 缓存的 since_ts 来自 daemon；seen_ts 是实时焦点状态，不进 TSV，
    # 所以这里补一次全量读取
    seen = seen_ts_map()
    for pane in cached:
        pane.seen_ts = seen.get(pane.pane_id, 0.0)
    return apply_unread(cached, focused_pane_id())


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
