#!/usr/bin/python3
"""
交互式 git log，选中 commit 后将 hash 输出到 stdout（供 glog alias 复制）。
支持选择任意本地/远程分支查看提交记录。

快捷键:
  Ctrl-D → view diff
  Ctrl-R → git reset 到选中 commit (弹出 mode 选择)
  Ctrl-E → git revert 选中 commit

用法: git_log.py [branch]
       git_log.py --reset <hash>
       git_log.py --revert <hash>
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
        preview_window="up,50%,border-bottom",
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


def do_reset(hash_val):
    """弹出二级选择框选择 reset mode，确认后执行 git reset。"""
    modes = ["hard", "soft", "mixed", "keep", "merge"]
    fzf_cmd = shell.build_fzf_cmd(
        border_label="🔄  [Git Reset Mode]",
        header=f"  Commit: {hash_val}",
        prompt="  Mode > ",
        sort=False,
        preview="",
        preview_window="",
        preview_label="",
        extra_args=["--no-hscroll"],
        as_str=False,
    )
    p = subprocess.Popen(fzf_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    out, _ = p.communicate(input="\n".join(modes))
    if p.returncode != 0 or not out.strip():
        shell.log_plain("reset 已取消")
        return
    mode = out.strip()

    shell.log_plain(f"⚠️  即将执行: git reset --{mode} {hash_val}")
    confirm = input("确认? [y/N] ").strip().lower()
    if confirm != "y":
        shell.log_plain("reset 已取消")
        return

    ret = subprocess.run(["git", "reset", f"--{mode}", hash_val])
    if ret.returncode == 0:
        shell.log_success(f"git reset --{mode} {hash_val} ✅")
    else:
        shell.log_err(f"git reset --{mode} {hash_val} 失败 ❌")


def do_revert(hash_val):
    """确认后执行 git revert (--no-edit 使用默认 revert message)。"""
    shell.log_plain(f"⚠️  即将执行: git revert {hash_val}")
    confirm = input("确认? [y/N] ").strip().lower()
    if confirm != "y":
        shell.log_plain("revert 已取消")
        return

    ret = subprocess.run(["git", "revert", "--no-edit", hash_val])
    if ret.returncode == 0:
        shell.log_success(f"git revert {hash_val} ✅")
    else:
        shell.log_err(f"git revert {hash_val} 失败/冲突 ❌")
        shell.log_plain("请手动解决冲突后 git revert --continue")


def main():
    # ── 子命令模式：从 fzf execute 回调 ───────────────────────
    if len(argv) >= 3 and argv[1] == "--reset":
        do_reset(argv[2])
        return
    if len(argv) >= 3 and argv[1] == "--revert":
        do_revert(argv[2])
        return

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
    script_path = os.path.abspath(__file__)
    python_exe = sys.executable

    fzf_cmd = shell.build_fzf_cmd(
        border_label=f"📜  [Git Log: {branch or 'HEAD'}]",
        header="  Enter → copy hash  ·  Ctrl-D → diff  ·  Ctrl-R → reset  ·  Ctrl-E → revert  ·  Esc quit",
        prompt="  Commit > ",
        use_multi_select=True,
        sort=False,
        preview=f"git show --stat --color=always $({hash_extract})",
        preview_window="down,border-top,50%",
        preview_label="[ Modified Files ]",
        extra_args=[
            "--no-hscroll", "--delimiter", " ",
            "--bind", f"ctrl-d:execute(git diff $({hash_extract})~1 $({hash_extract}) | delta --side-by-side --paging always)",
            "--bind", f"ctrl-r:execute({python_exe} {script_path} --reset $({hash_extract}))+abort",
            "--bind", f"ctrl-e:execute({python_exe} {script_path} --revert $({hash_extract}))+abort",
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
