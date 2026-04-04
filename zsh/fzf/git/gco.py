#!/usr/bin/python3
import subprocess
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pyutils.git as git
import pyutils.shell as shell


def main():
    res = git.get_branches("🌲 [Git: Checkout]", use_multi_select=False)
    if not res.branch_list:
        exit(0)

    if res.has_cur_branch:
        shell.log_err("不能checkout当前分支!")
        return

    branch = res.branch_list[0]
    branch = branch.lstrip("* ").strip()

    shell.log_success(f"checking out to {branch}...")
    ret = subprocess.run(["git", "checkout", branch])
    if ret.returncode == 0:
        shell.log_success("checkout success ✅")
    else:
        shell.log_err("checkout failed ❌")


if __name__ == "__main__":
    main()
