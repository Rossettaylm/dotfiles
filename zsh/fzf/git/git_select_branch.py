#!/usr/bin/python3
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pyutils.git import get_branches
from pyutils.shell import log_err


def main():
    branchResult = get_branches("🌿 [Git: Branches]", False)
    if not branchResult.branch_list:
        log_err("Cancel Select Branch...")
        return
    branch = branchResult.branch_list[0]
    print(branch)


if __name__ == "__main__":
    main()
