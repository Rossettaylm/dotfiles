# -*- coding: utf-8 -*-
from os import system
import os
import pyutils.shell as shell
import pyutils.git as git


def git_checkout_branch():
    res = git.get_branches("🌿 [Git: Checkout]", use_multi_select=False)

    has_cur_branch = res.has_cur_branch
    branches = res.branch_list
    if has_cur_branch:
        shell.log_err("不能checkout当前分支!")
        return
    if len(branches) == 0:
        shell.log_err("取消checkout!")
        return
    cmd = "git checkout {}".format(branches[0])
    shell.log_plain("checkout to {}...".format(branches[0]))
    result = system(cmd)
    if result == 0:
        shell.log_plain("checkout success✅")
    else:
        shell.log_plain("checkout failed❌")


if __name__ == "__main__":
    git_checkout_branch()
