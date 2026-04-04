#!/usr/bin/python3
"""
[K]ill [P]rocess — 交互式选择进程并 kill
"""
import subprocess
import sys
import os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pyutils.shell as shell


def select_and_kill(sig: str = "9") -> bool:
    ps_out, _ = shell.run_shell_cmd("ps -ef | sed 1d")
    if not ps_out:
        return False

    fzf_cmd = shell.build_fzf_cmd(
        border_label="💀  [Kill Process]",
        header="  Tab 多选  ·  Enter kill  ·  Esc quit",
        prompt="  Process > ",
        use_multi_select=True,
        preview="echo {} | awk '{print $2}' | xargs -I% ps -p % -o pid,ppid,user,%cpu,%mem,start,command 2>/dev/null",
        preview_window="right,border-left,50%",
        preview_label="[ Process Info ]",
        as_str=False,
    )

    process = subprocess.Popen(
        fzf_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    stdout, _ = process.communicate(input="\n".join(ps_out))
    if process.returncode != 0 or not stdout.strip():
        return False

    pids = [line.split()[1] for line in stdout.strip().splitlines() if line.strip()]
    for pid in pids:
        shell.run_shell_cmd(f"kill -{sig} {pid} 2>/dev/null")
        shell.log_success(f"killed pid {pid}")
    return True


def main():
    sig = sys.argv[1] if len(sys.argv) > 1 else "9"
    while select_and_kill(sig):
        pass


if __name__ == "__main__":
    main()
