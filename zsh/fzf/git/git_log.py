#!/usr/bin/python3
"""
交互式 git log，选中 commit 后将 hash 输出到 stdout（供 glog alias 复制）。
用法: git_log.py [branch]
"""
import re
import subprocess
import sys
from sys import argv
import os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pyutils.shell as shell


def main():
    branch = argv[1] if len(argv) > 1 else ""

    git_log_cmd = (
        f"git log -n 1000 --oneline --date=short "
        f"--pretty='format:%C(auto)%cd %an %h%d %s' {branch}"
    )
    log_lines, err = shell.run_shell_cmd(git_log_cmd)
    if err:
        shell.log_err(err)
        exit(1)
    if not log_lines:
        shell.log_err("没有找到任何 commit。")
        exit(0)

    fzf_cmd = shell.build_fzf_cmd(
        border_label="📜  [Git Log]",
        header="  Enter → copy hash  ·  Esc quit",
        prompt="  Commit > ",
        use_multi_select=True,
        preview="noglob git show --stat --color=always $(echo {} | grep -oE '[0-9a-f]{7,}'| head -1)",
        preview_window="right,border-left,50%",
        preview_label="[ Modified Files ]",
        extra_args=["--no-hscroll", "--delimiter", " "],
        as_str=False,
    )

    process = subprocess.Popen(
        fzf_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    stdout, _ = process.communicate(input="\n".join(log_lines))
    if process.returncode != 0 or not stdout.strip():
        exit(0)

    # 从每行中用正则提取 7位 commit hash（格式固定为 %h）
    hashes = []
    for line in stdout.strip().splitlines():
        m = re.search(r'\b([0-9a-f]{7,})\b', line)
        if m:
            hashes.append(m.group(1))

    if hashes:
        print(" ".join(hashes))


if __name__ == "__main__":
    main()
