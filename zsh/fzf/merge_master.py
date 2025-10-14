#!/usr/bin/python3
import os
from pyutils import shell
from pyutils import git

# valid_options = ["m", "merge", "rebase", "r", "\n", "\r", "\r\n", ""]


def merge_master():
    cur_branch = git.get_cur_branch()
    if len(cur_branch) <= 0:
        shell.log_err("无法获取当前分支名...")
        return
    if cur_branch == "master":
        shell.log_err("已经处于master分支上...")
        return
    shell.log_plain("git fetch...")
    os.system("git fetch origin master")

    # option = input("rebase(Default) or merge? (r/m)")
    # if option not in valid_options:
    #     shell.log_err("错误的输入:{}".format(option))
    #     return
    # cmd = (
    #     "git merge origin/master"
    #     if option == "m" or option == "merge"
    #     else "git rebase origin/master"
    # )
    # tip = "merging..." if option == "m" or option == "merge" else "rebasing..."
    tip = "merging..."
    cmd = "git merge origin/master"

    shell.log_plain(tip)
    os.system(cmd)


if __name__ == "__main__":
    merge_master()
