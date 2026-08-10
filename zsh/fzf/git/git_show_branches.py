#!/usr/bin/python3
import os
import sys; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pyutils import git


def git_show_branches():
    res = git.get_branches(header="🌿 [Git: Show Branches]", use_multi_select=False)
    branches = res.branch_list

    if len(branches) != 1:
        return

    # echo
    for br in branches:
        os.system("echo '{}'".format(git.clean_branch_name(br)))


if __name__ == "__main__":
    git_show_branches()
