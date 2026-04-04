# -*- coding: utf-8 -*-
import subprocess
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pyutils import git
from pyutils import shell


def git_merge_branch():
    branch_result = git.get_branches(header="🔀 [Git: Merge]", use_multi_select=False)
    if branch_result.isInvalid():
        return
    has_cur_branch = branch_result.has_cur_branch
    cur_branch_name = branch_result.cur_branch_name
    branches = branch_result.branch_list

    if has_cur_branch:
        shell.log_err("不能merge当前分支")
        return

    if len(branches) == 0:
        shell.log_err("取消merge!")
        return

    shell.log_plain("[merge] {} to {}?".format(branches[0], cur_branch_name))
    confirm = input("确认merge?(y/n)").strip()
    if confirm == "y":
        subprocess.run(["git", "merge", branches[0]])
    else:
        shell.log_err("取消merge!")


if __name__ == "__main__":
    git_merge_branch()
