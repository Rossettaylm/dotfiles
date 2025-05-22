# -*- coding: utf-8 -*-
from os import system
from pyutils import shell as sh


class BranchResult(object):
    has_cur_branch: bool = False
    cur_branch_name: str = ""
    branch_list: list = []

    def __init__(self, has_cur_branch=False, cur_branch_name="", branch_list=[]):
        self.has_cur_branch = has_cur_branch
        self.cur_branch_name = cur_branch_name
        self.branch_list = branch_list

    def setCurBranch(self, name):
        self.cur_branch_name = name

    def isInvalid(self):
        return (
            self.has_cur_branch == False
            and self.cur_branch_name == ""
            and self.branch_list == []
        )


# git branch分支预处理
def branch_preprocess(branches):
    has_cur_branch = False
    cur_branch = ""
    for idx, br in enumerate(branches):
        if isinstance(br, bytes):
            br = br.decode()
        branches[idx] = br.lstrip(" ")
        if br.startswith("*"):
            has_cur_branch = True

    return BranchResult(has_cur_branch, cur_branch, branches)


def get_cur_branch():
    cmd = "git branch"
    out, err = sh.run_shell_cmd(cmd)
    for e in err:
        sh.log_err(e)
    for br in out:
        if isinstance(br, bytes):
            br = br.decode()
        if br.startswith("*"):
            return br.removeprefix("* ")
    return ""


# 选中分支
def get_branches(header, use_multi_select=False, show_brs_cmd="git branch"):
    fzf_cmd = sh.fzf_command(header=header, use_multi_select=use_multi_select)

    _, err = sh.run_shell_cmd(show_brs_cmd)
    if err:
        sh.log_err("当前目录不是git仓库!")
        return BranchResult()

    branches, err = sh.run_shell_cmd(
        "{git_cmd} | {fzf_cmd}".format(git_cmd=show_brs_cmd, fzf_cmd=fzf_cmd)
    )
    result = branch_preprocess(branches)
    result.setCurBranch(get_cur_branch())
    return result
