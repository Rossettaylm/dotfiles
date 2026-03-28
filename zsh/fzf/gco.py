#!/usr/bin/python3
import os
import pyutils.git as git
import pyutils.shell as shell


def main():
    res = git.get_branches("🌲 [Git: Checkout]", use_multi_select=False)
    if not res.branch_list:
        exit(0)

    branch = res.branch_list[0]
    # strip leading "* " if present
    branch = branch.lstrip("* ").strip()

    shell.log_success(f"checking out to {branch}...")
    ret = os.system(f"git checkout {branch}")
    if ret == 0:
        shell.log_success("checkout success ✅")
    else:
        shell.log_err("checkout failed ❌")


if __name__ == "__main__":
    main()
