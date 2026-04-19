#!/usr/bin/python3
import sys
from sys import argv
import os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pyutils.shell as shell
import subprocess


def get_sessions() -> list[str]:
    """获取 tmux 会话列表（倒序：最旧在顶，最新在底）"""
    stdout, _ = shell.run_shell_cmd("tmux list-sessions 2>/dev/null")
    sessions = [line for line in stdout if line.strip()]
    return list(reversed(sessions))


def colorize_sessions(sessions: list[str]) -> list[str]:
    """对当前会话（attached）加绿色加粗高亮"""
    colored = []
    for line in sessions:
        if "(attached)" in line:
            colored.append(f"\033[1;32m{line}\033[0m")
        else:
            colored.append(line)
    return colored


def show_tmux_sessions_in_fzf() -> str:
    sessions = get_sessions()
    if not sessions:
        shell.log_err("没有活跃的 tmux session。")
        return ""

    colored = colorize_sessions(sessions)
    input_text = "\n".join(colored)

    fzf_cmd = shell.build_fzf_cmd(
        border_label="🖥️  [Tmux Sessions]",
        header="  ↑↓ navigate  ·  Enter attach  ·  Esc quit",
        prompt="  Attach > ",
        preview=r"echo {} | sed 's/\x1b\[[0-9;]*m//g'",
        preview_window="bottom,4,border-top,wrap",
        preview_label="[ session info ]",
        as_str=False,
    )

    process = subprocess.Popen(
        fzf_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    stdout, _ = process.communicate(input=input_text)
    if process.returncode != 0 or not stdout.strip():
        return ""

    # tmux list-sessions 格式: "name: N windows ..."，取冒号前作为 session 名
    raw = stdout.strip().split(":")[0]
    # 去掉 ANSI 转义
    import re
    return re.sub(r'\x1b\[[0-9;]*m', '', raw).strip()


def attach_session(session: str):
    shell.log_success(f"正在进入 session: {session}")
    if os.environ.get("TMUX"):
        os.system(f"tmux switch-client -t {session}")
    else:
        os.system(f"tmux attach -t {session}")


def main():
    if len(argv) > 1:
        session = argv[1]
        attach_session(session)
        exit(0)

    session = show_tmux_sessions_in_fzf()
    if not session:
        exit(0)
    attach_session(session)


if __name__ == "__main__":
    main()
