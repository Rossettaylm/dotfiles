#!/usr/bin/python3
"""
交互式 git log，选中 commit 后将 hash 输出到 stdout（供 glog alias 复制）。
支持选择任意本地/远程分支查看提交记录。
用法: git_log.py [branch]
"""
import re
import subprocess
import sys
from sys import argv
import os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pyutils.shell as shell


def select_branch():
    """用 fzf 选择本地或远程分支，直接回车则使用当前分支。"""
    branch_lines, err = shell.run_shell_cmd("git branch -a --color=never")
    if err:
        shell.log_err(err)
        return None

    cleaned = []
    current = ""
    for line in branch_lines:
        line = line.strip()
        if line.startswith("* "):
            current = line[2:]
            cleaned.append(line)
        elif "HEAD ->" not in line:
            cleaned.append(line)

    fzf_cmd = shell.build_fzf_cmd(
        border_label="🌿  [Select Branch]",
        header=f"  当前分支: {current}  ·  Enter 选择  ·  Esc 使用当前分支",
        prompt="  Branch > ",
        sort=False,
        preview="git log -n 20 --oneline --graph --color=always --date=short "
                "--pretty='format:%C(auto)%cd %an %h%d %s' "
                "$(echo {} | sed 's/^[* ]*//' | sed 's| -> .*||' | xargs) --",
        preview_window="right,border-left,60%",
        preview_label="[ Branch Log ]",
        extra_args=["--no-hscroll"],
        as_str=False,
    )

    process = subprocess.Popen(
        fzf_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    stdout, _ = process.communicate(input="\n".join(cleaned))
    if process.returncode != 0 or not stdout.strip():
        return current or ""

    selected = stdout.strip()
    selected = re.sub(r'^\*\s*', '', selected).strip()
    selected = re.sub(r'\s*->.*', '', selected).strip()
    return selected


def main():
    branch = argv[1] if len(argv) > 1 else None

    if branch is None:
        branch = select_branch()
        if branch is None:
            exit(1)

    git_log_cmd = (
        f"git log -n 1000 --oneline --date=short "
        f"--pretty='format:%C(auto)%cd %an %h%d %s' {branch} --"
    )
    log_lines, err = shell.run_shell_cmd(git_log_cmd)
    if err:
        shell.log_err(err)
        exit(1)
    if not log_lines:
        shell.log_err("没有找到任何 commit。")
        exit(0)

    hash_extract = "echo {} | grep -oE '[0-9a-f]{7,}'| head -1"

    fzf_cmd = shell.build_fzf_cmd(
        border_label=f"📜  [Git Log: {branch or 'HEAD'}]",
        header="  Enter → copy hash  ·  Ctrl-D → view diff  ·  Esc quit",
        prompt="  Commit > ",
        use_multi_select=True,
        sort=False,
        preview=f"git show --stat --color=always $({hash_extract})",
        preview_window="down,border-top,50%",
        preview_label="[ Modified Files ]",
        extra_args=[
            "--no-hscroll", "--delimiter", " ",
            "--bind", f"ctrl-d:execute(git diff $({hash_extract})~1 $({hash_extract}) | delta --side-by-side --paging always)",
        ],
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

    hashes = []
    for line in stdout.strip().splitlines():
        m = re.search(r'\b([0-9a-f]{7,})\b', line)
        if m:
            hashes.append(m.group(1))

    if hashes:
        print(" ".join(hashes))


if __name__ == "__main__":
    main()
