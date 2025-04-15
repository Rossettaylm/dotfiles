import os
from pyutils import git


def main():
    result = git.get_branches(
        header="[Checkout-Origin]", use_multi_select=False, show_brs_cmd="git branch -r"
    )
    branch = result.branch_list
    if len(branch) != 1:
        return
    branch = str(branch[0])
    target_branch_name = branch.removeprefix("origin/")
    cmd = "git checkout -b {} {}".format(target_branch_name, branch)
    print(cmd)
    os.system(cmd)


if __name__ == "__main__":
    main()
