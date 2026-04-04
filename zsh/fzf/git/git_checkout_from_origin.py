import subprocess
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pyutils import git
from pyutils import shell


def main():
    subprocess.run(["git", "fetch"])

    result = git.get_branches(
        header="🌐 [Git: Checkout from Origin]", use_multi_select=False, show_brs_cmd="git branch -r"
    )
    branch = result.branch_list
    if len(branch) != 1:
        shell.log_err("选择分支数量为{},取消checkout!".format(len(branch)))
        return
    branch = str(branch[0])
    target_branch_name = branch.removeprefix("origin/")
    shell.log_success("checkout ing...\ngit checkout -b {} {}".format(target_branch_name, branch))
    subprocess.run(["git", "checkout", "-b", target_branch_name, branch])


if __name__ == "__main__":
    main()
