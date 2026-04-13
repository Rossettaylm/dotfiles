#!/usr/bin/python3
import subprocess
import sys
import os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pyutils.shell as shell
from zellij_sessions import get_sessions, colorize_sessions


def select_sessions_in_fzf() -> list[str]:
    sessions = get_sessions()
    if not sessions:
        shell.log_err("没有活跃的 zellij session。")
        return []

    colored = colorize_sessions(sessions)
    input_text = "\n".join(colored)

    fzf_cmd = shell.build_fzf_cmd(
        border_label="🗑️  [Zellij: Delete Session]",
        header="  Tab 多选  ·  Enter 删除  ·  Esc 取消",
        prompt="  Delete > ",
        use_multi_select=True,
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
        return []

    return [line.strip().split()[0] for line in stdout.strip().splitlines() if line.strip()]


def delete_sessions(sessions: list[str]):
    names = ", ".join(sessions)
    confirm = input(f"\033[33m确定要删除 [{names}] 吗？(y/n) \033[0m")
    if confirm.strip().lower() != "y":
        shell.log_err("已取消")
        return

    for session in sessions:
        shell.log_success(f"正在删除 session: {session}")
        os.system(f"zellij delete-session --force {session}")


def main():
    if len(sys.argv) > 1:
        delete_sessions(sys.argv[1:])
        return

    sessions = select_sessions_in_fzf()
    if not sessions:
        return
    delete_sessions(sessions)


if __name__ == "__main__":
    main()
