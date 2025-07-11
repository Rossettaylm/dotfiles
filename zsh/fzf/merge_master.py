#!/usr/bin/python3
import os
from pyutils import shell
from pyutils import git


def merge_master():
    cur_branch = git.get_cur_branch()
    if len(cur_branch) <= 0:
        shell.log_err("无法获取当前分支名...")
        return
    if cur_branch == "master":
        shell.log_err("已经处于master分支上...")
        return
    shell.log_plain("git fetch...")
    os.system("git fetch")

    shell.log_plain("merging...")
    os.system("git merge master")

    shell.log_success("merge suscess")


if __name__ == "__main__":
    merge_master()
