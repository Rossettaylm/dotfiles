#!/usr/bin/python3

import os
import sys


def obtain_git_commits(branch=""):
    gitLogCmd = f"git log --oneline --date=short --pretty='format:%C(auto)%cd %an %h%d %s' {branch}"
    cutCmd = "cut -d ' ' -f 3"
    fzfCmd = (
        r"fzf -m --header='[Git:Log]' --delimiter=' ' --preview='git show --pretty="
        " {3} --color=always' --preview-label='[Git:Files]'"
    )

    os.system("{} | {} | {}".format(gitLogCmd, fzfCmd, cutCmd))


if __name__ == "__main__":
    branch = sys.argv[1] if len(sys.argv) >= 2 else ""
    obtain_git_commits(branch)
