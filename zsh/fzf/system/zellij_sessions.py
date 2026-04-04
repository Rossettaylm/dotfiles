#!/usr/bin/python3
import sys
from sys import argv
import os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pyutils.shell as shell
import subprocess


def get_sessions() -> list[str]:
    """获取 zellij 会话列表（倒序：最旧在顶，最新在底）"""
    stdout, _ = shell.run_shell_cmd("zellij list-sessions 2>/dev/null")
    # 过滤掉空行和 "No active zellij sessions found" 类提示
    sessions = [line for line in stdout if line.strip() and not line.startswith("No ")]
    return list(reversed(sessions))


def colorize_sessions(sessions: list[str]) -> list[str]:
    """对当前会话加绿色加粗高亮"""
    colored = []
    for line in sessions:
        if "(current)" in line:
            colored.append(f"\033[1;32m{line}\033[0m")
        else:
            colored.append(line)
    return colored


def show_zellij_sessions_in_fzf() -> str:
    sessions = get_sessions()
    if not sessions:
        shell.log_err("没有活跃的 zellij session。")
        return ""

    colored = colorize_sessions(sessions)
    input_text = "\n".join(colored)

    fzf_cmd = shell.build_fzf_cmd(
        border_label="🪟  [Zellij Sessions]",
        header="  ↑↓ navigate  ·  Enter attach  ·  Esc quit",
        prompt="  Attach > ",
        pointer="▶",
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

    # 取第一个词作为 session 名（去掉后续的时间/状态信息）
    return stdout.strip().split()[0]


def main():
    if len(argv) > 1:
        session = argv[1]  # 直接指定 session，跳过选择
        attach_session(session)
        exit(0)

    session = show_zellij_sessions_in_fzf()
    if not session:
        exit(0)
    attach_session(session)


def attach_session(session: str):
    shell.log_success(f"正在进入 session: {session}")
    os.system(f"zellij attach -c {session}")


if __name__ == "__main__":
    main()
