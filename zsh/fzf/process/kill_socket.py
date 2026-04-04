#!/usr/bin/python3
"""
[K]ill [S]erver — 交互式选择 TCP 监听端口并 kill
"""
import subprocess
import sys
import re
import os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pyutils.shell as shell


def get_listen_ports() -> tuple[list[str], dict[str, str]]:
    """返回格式化后的显示行列表，以及 显示行 -> pid 的映射。"""
    raw, _ = shell.run_shell_cmd("lsof -Pwni tcp -sTCP:LISTEN 2>/dev/null | sed 1d")
    if not raw:
        return [], {}

    lines = []
    pid_map = {}
    for row in raw:
        parts = row.split()
        if len(parts) < 9:
            continue
        cmd, pid, name = parts[0], parts[1], parts[8]
        # name 形如 *:8080 或 127.0.0.1:5432
        port = name.split(":")[-1]
        display = f"{port:<8}  {pid:<8}  {cmd}"
        lines.append(display)
        pid_map[display] = pid

    return lines, pid_map


def select_and_kill(sig: str = "9") -> bool:
    lines, pid_map = get_listen_ports()
    if not lines:
        shell.log_err("没有监听中的 TCP 端口。")
        return False

    header_row = f"{'PORT':<8}  {'PID':<8}  COMMAND"
    display_lines = [header_row, "─" * 40] + lines

    fzf_cmd = shell.build_fzf_cmd(
        border_label="🔌  [Kill Server]",
        header="  Tab 多选  ·  Enter kill  ·  Esc quit",
        prompt="  Port > ",
        use_multi_select=True,
        preview="echo {} | awk '{print $2}' | xargs -I% ps -p % -o pid,ppid,user,%cpu,%mem,start,command 2>/dev/null",
        preview_window="right,border-left,50%",
        preview_label="[ Process Info ]",
        extra_args=["--header-lines", "2"],
        as_str=False,
    )

    process = subprocess.Popen(
        fzf_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    stdout, _ = process.communicate(input="\n".join(display_lines))
    if process.returncode != 0 or not stdout.strip():
        return False

    for line in stdout.strip().splitlines():
        line = line.strip()
        pid = pid_map.get(line)
        if not pid:
            continue
        shell.run_shell_cmd(f"kill -{sig} {pid} 2>/dev/null")
        port = line.split()[0]
        shell.log_success(f"killed :{port} (pid {pid})")
    return True


def main():
    sig = sys.argv[1] if len(sys.argv) > 1 else "9"
    while select_and_kill(sig):
        pass


if __name__ == "__main__":
    main()
