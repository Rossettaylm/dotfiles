#!/usr/bin/python3
import subprocess
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

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
    subprocess.run(["git", "fetch", "origin", "master"])

    shell.log_plain("merging...")
    subprocess.run(["git", "merge", "origin/master"])


if __name__ == "__main__":
    merge_master()
