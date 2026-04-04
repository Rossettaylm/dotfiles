#!/usr/bin/python3
"""
交互式 git stash 管理：列出 stash，预览 diff，支持 apply/pop/drop。
用法: git_stash.py
"""
import subprocess
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pyutils.shell as shell


def main():
    stash_lines, err = shell.run_shell_cmd("git stash list --color=always")
    if err:
        shell.log_err(err)
        exit(1)
    if not stash_lines:
        shell.log_err("当前没有任何 stash。")
        exit(0)

    fzf_cmd = shell.build_fzf_cmd(
        border_label="📦  [Git Stash]",
        header="  Enter → apply  ·  Ctrl-P → pop  ·  Ctrl-X → drop  ·  Esc quit",
        prompt="  Stash > ",
        preview="git stash show -p --color=always $(echo {} | grep -oE 'stash@\\{{[0-9]+\\}}')",
        preview_window="right,border-left,65%",
        preview_label="[ Stash Diff ]",
        extra_args=[
            "--no-hscroll",
            "--expect", "ctrl-p,ctrl-x",
        ],
        as_str=False,
    )

    process = subprocess.Popen(
        fzf_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    stdout, _ = process.communicate(input="\n".join(stash_lines))
    if process.returncode != 0 or not stdout.strip():
        exit(0)

    lines = stdout.strip().splitlines()
    key = lines[0] if len(lines) > 1 else ""
    selected = lines[1] if len(lines) > 1 else lines[0]

    # 提取 stash@{N}
    import re
    m = re.search(r'stash@\{(\d+)\}', selected)
    if not m:
        shell.log_err("无法解析 stash 编号。")
        exit(1)
    stash_ref = f"stash@{{{m.group(1)}}}"

    if key == "ctrl-x":
        confirm = input(f"确认删除 {stash_ref}? [y/N] ").strip().lower()
        if confirm != "y":
            shell.log_plain("已取消。")
            exit(0)
        cmd = ["git", "stash", "drop", stash_ref]
        action = "drop"
    elif key == "ctrl-p":
        cmd = ["git", "stash", "pop", stash_ref]
        action = "pop"
    else:
        cmd = ["git", "stash", "apply", stash_ref]
        action = "apply"

    ret = subprocess.run(cmd)
    if ret.returncode == 0:
        shell.log_success(f"stash {action} 成功 ✅")
    else:
        shell.log_err(f"stash {action} 失败 ❌")


if __name__ == "__main__":
    main()
