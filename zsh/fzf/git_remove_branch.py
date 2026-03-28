# -*- coding: utf-8 -*-
from pyutils import git
from pyutils import shell


# 确认删除分支
def confirm_to_remove(branches):
    print("确认remove这些分支吗?")
    for br in branches:
        print(br)
    confirm = input("确认删除? (y/n)")
    if confirm == "y":
        return True
    return False


def git_remove_branch():
    res = git.get_branches(header="🗑️  [Git: Remove Branch]", use_multi_select=True)
    has_cur_branch = res.has_cur_branch
    branches = res.branch_list
    if has_cur_branch:
        shell.log_err("不能remove当前分支!")
        return

    if len(branches) == 0:
        return

    # check
    confirm = confirm_to_remove(branches)
    if confirm == False:
        shell.log_err("取消删除!")
        return

    for br in branches:
        out, err = shell.run_shell_cmd("git branch -D {}".format(br))
        if out:
            shell.log_success(out)
        if err:
            shell.log_err(err)


if __name__ == "__main__":
    git_remove_branch()
