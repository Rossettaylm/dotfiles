#!/usr/bin/python3
import os

from pyutils import git


def git_show_branches():
    res = git.get_branches(header="[git:remove branch]", use_multi_select=False)
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
