#!/usr/bin/python3
"""
交互式 cherry-pick：先选分支，再从该分支 fzf 选 commit(s) 进行 cherry-pick。
用法: git_cherry_pick.py
"""
import re
import subprocess
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pyutils.git as git
import pyutils.shell as shell


def main():
    # 1. 选择源分支
    res = git.get_branches("🍒 [Cherry-Pick: 选择源分支]", use_multi_select=False)
    if not res.branch_list:
        exit(0)
    source_branch = res.branch_list[0].strip()

    # 2. 列出该分支的 commit
    log_cmd = (
        f"git log -n 200 --oneline --date=short "
        f"--pretty='format:%C(auto)%cd %an %h%d %s' {source_branch}"
    )
    log_lines, err = shell.run_shell_cmd(log_cmd)
    if err:
        shell.log_err(err)
        exit(1)
    if not log_lines:
        shell.log_err(f"分支 {source_branch} 没有 commit。")
        exit(0)

    fzf_cmd = shell.build_fzf_cmd(
        border_label=f"🍒  [Cherry-Pick from {source_branch}]",
        header="  Tab 多选  ·  Enter 确认 cherry-pick  ·  Esc quit",
        prompt="  Commit > ",
        use_multi_select=True,
        preview="git show --stat --color=always $(echo {} | grep -oE '[0-9a-f]{7,}' | head -1)",
        preview_window="right,border-left,50%",
        preview_label="[ Commit Detail ]",
        extra_args=["--no-hscroll"],
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

    # 提取 commit hash
    hashes = []
    for line in stdout.strip().splitlines():
        m = re.search(r'\b([0-9a-f]{7,})\b', line)
        if m:
            hashes.append(m.group(1))

    if not hashes:
        shell.log_err("未选中任何 commit。")
        exit(0)

    shell.log_plain(f"即将 cherry-pick: {' '.join(hashes)}")
    confirm = input("确认? [y/N] ").strip().lower()
    if confirm != "y":
        shell.log_plain("已取消。")
        exit(0)

    # 按选择顺序逆序，使 cherry-pick 保持原始提交顺序
    hashes.reverse()
    ret = subprocess.run(["git", "cherry-pick"] + hashes)
    if ret.returncode == 0:
        shell.log_success("cherry-pick 成功 ✅")
    else:
        shell.log_err("cherry-pick 失败/冲突，请手动解决 ❌")


if __name__ == "__main__":
    main()
