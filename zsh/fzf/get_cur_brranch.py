#!/usr/bin/python3
from os import system
from pyutils.git import get_cur_branch

if __name__ == "__main__":
    branch = get_cur_branch()
    system("echo {}".format(branch))
