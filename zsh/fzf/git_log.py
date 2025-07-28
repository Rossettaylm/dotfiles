#!/usr/bin/python3

import os
from pyutils.git import git_log_cmd


def obtain_git_commits():
    gitLogCmd = git_log_cmd()
    cutCmd = "cut -d '-' -f 1"
    fzfCmd = (
        r"fzf -m --header='[Git:Log]' --delimiter='-' --preview='git show --pretty="
        " {1} --color=always' --preview-label='[Git:Files]'"
    )

    os.system("{} | {} | {}".format(gitLogCmd, fzfCmd, cutCmd))


if __name__ == "__main__":
    obtain_git_commits()
