#!/usr/bin/env python3
"""tmux-resurrect 存档改写：把 agent pane 的进程命令换成「恢复原会话」的命令。

resurrect 只记录 pane 里的进程命令行（`claude --dangerously-skip-permissions`），
原样重跑会开一个全新会话。这里在 @resurrect-hook-post-save-layout 阶段
（存档文件已写好、尚未与 last 比对）把命令改写成带会话 ID 的恢复命令：

    claude --resume <session_id> [保留的白名单参数]
    omp --resume <session_file>
    cursor-agent --resume <chat_id> [保留的白名单参数]

`--resume` 紧跟可执行名，tmux.conf 的 @resurrect-processes 用 "~claude --resume"
这类子串规则只放行改写过的行 —— 没拿到会话 ID 的 agent 不会被恢复成新会话。

会话 ID 来源（按优先级）:
    @agent_session        agent_hook.py / omp 扩展上报的 pane option
    ~/.claude/sessions    claude 自报文件（hook 未装之前启动的 claude 也有）
    lsof                  cursor-agent 打开的 chats/<hash>/<chat_id>/store.db

用法:
    agent_resurrect.py save <resurrect_state_file>
"""

import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import agent_lib as lib

# 只保留这些参数：原命令里的位置参数是首条 prompt，重放会把它再发一遍
_BOOL_FLAGS = {
    "claude": {"--dangerously-skip-permissions", "--allow-dangerously-skip-permissions",
               "--verbose", "--chrome", "--no-chrome", "--ide"},
    "omp": {"--yolo", "--auto-approve"},
    "cursor": {"--yolo", "--force", "-f", "--approve-mcps", "--trust", "--auto-review", "--plan"},
}
_VALUE_FLAGS = {
    "claude": {"--model", "--permission-mode", "--effort", "--agent", "--fallback-model"},
    "omp": {"--model", "--thinking", "--approval-mode"},
    "cursor": {"--model", "--sandbox", "--mode", "--workspace"},
}
_BINARY = {"claude": "claude", "omp": "omp", "cursor": "cursor-agent"}

_CURSOR_STORE_RE = re.compile(r"/chats/[^/]+/([0-9a-f-]{36})/store\.db$")


def keep_flags(agent: str, argv: list[str]) -> list[str]:
    kept: list[str] = []
    bools, values = _BOOL_FLAGS[agent], _VALUE_FLAGS[agent]
    i = 0
    while i < len(argv):
        tok = argv[i]
        name = tok.split("=", 1)[0]
        if name in bools:
            kept.append(tok)
        elif name in values:
            if "=" in tok:
                kept.append(tok)
            elif i + 1 < len(argv):
                kept += [tok, argv[i + 1]]
                i += 1
        i += 1
    return kept


def cursor_argv(full_command: str) -> list[str]:
    """cursor-agent 的进程命令行形如 `.../agent --use-system-ca .../index.js <用户参数>`。"""
    argv = full_command.split()
    for i, tok in enumerate(argv):
        if tok.endswith("index.js"):
            return argv[i + 1:]
    return argv[1:]


def cursor_chat_id(pane_pid: int) -> str:
    rows = lib._ps_snapshot()
    children: dict[int, list[tuple[int, str]]] = {}
    for pid, ppid, cmd in rows:
        children.setdefault(ppid, []).append((pid, cmd))
    frontier, pids = [pane_pid], []
    while frontier:
        pid = frontier.pop()
        for child, cmd in children.get(pid, ()):
            if "cursor-agent" in cmd:
                pids.append(child)
            frontier.append(child)
    for pid in pids:
        out = subprocess.run(("lsof", "-p", str(pid), "-Fn"), capture_output=True,
                             text=True, errors="replace").stdout
        for line in out.splitlines():
            match = _CURSOR_STORE_RE.search(line)
            if match:
                return match.group(1)
    return ""


def restore_command(agent: str, session: str, original: str) -> str:
    argv = cursor_argv(original) if agent == "cursor" else original.split()[1:]
    words = [_BINARY[agent], "--resume", session, *keep_flags(agent, argv)]
    return " ".join(shlex.quote(w) for w in words)


def live_panes() -> dict[tuple[str, str, str], dict[str, str]]:
    fields = ("#{session_name}", "#{window_index}", "#{pane_index}", "#D", "#{pane_pid}",
              "#{pane_current_command}", "#T", "#{@agent_kind}", "#{@agent_session}")
    out: dict[tuple[str, str, str], dict[str, str]] = {}
    for line in lib.tmux("list-panes", "-aF", "\t".join(fields)).splitlines():
        parts = line.split("\t")
        if len(parts) != len(fields):
            continue
        session, window, index, pane_id, pane_pid, command, title, kind, ref = parts
        out[(session, window, index)] = {
            "pane_id": pane_id, "pane_pid": pane_pid, "command": command,
            "title": title, "kind": kind, "session": ref,
        }
    return out


def session_for(pane: dict[str, str], agent: str, claude: dict[str, dict]) -> str:
    if pane["kind"] == agent and pane["session"]:
        return pane["session"]
    if agent == "claude":
        return str(claude.get(pane["pane_id"], {}).get("sessionId") or "")
    if agent == "cursor":
        try:
            return cursor_chat_id(int(pane["pane_pid"]))
        except ValueError:
            return ""
    return ""


def rewrite(state_file: Path) -> int:
    panes = live_panes()
    claude = lib.claude_session_records()
    lines = state_file.read_text(encoding="utf-8").splitlines(keepends=True)
    changed = 0
    for i, line in enumerate(lines):
        fields = line.rstrip("\n").split("\t")
        # pane 行: pane session window active flags index title dir pane_active command :full_command
        if fields[0] != "pane" or len(fields) != 11:
            continue
        pane = panes.get((fields[1], fields[2], fields[5]))
        if pane is None:
            continue
        agent = lib.agent_key_for_pane(pane["pane_id"], pane["pane_pid"], pane["command"], pane["title"])
        if agent not in _BINARY:
            continue
        session = session_for(pane, agent, claude)
        if not session:
            continue
        fields[10] = ":" + restore_command(agent, session, fields[10][1:])
        lines[i] = "\t".join(fields) + "\n"
        changed += 1
    if changed:
        tmp = state_file.with_name(state_file.name + ".agent.tmp")
        tmp.write_text("".join(lines), encoding="utf-8")
        os.replace(tmp, state_file)
    return changed


def main() -> None:
    if len(sys.argv) != 3 or sys.argv[1] != "save":
        sys.exit(__doc__)
    rewrite(Path(sys.argv[2]))


if __name__ == "__main__":
    main()
