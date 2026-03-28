# -*- coding: utf-8 -*-
from pyutils import git
from pyutils import shell
import os


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
        cmd = "git merge {}".format(branches[0])
        os.system(cmd)
    else:
        shell.log_err("取消merge!")


if __name__ == "__main__":
    git_merge_branch()
