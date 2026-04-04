#!/usr/bin/python3
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pyutils.git import get_cur_branch

if __name__ == "__main__":
    branch = get_cur_branch()
    print(branch)
