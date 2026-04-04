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
        if isinstance(br, bytes):
            br = br.decode()
        if br.startswith("*"):
            br = br.removeprefix("* ")
        os.system("echo '{}'".format(br))


if __name__ == "__main__":
    git_show_branches()
