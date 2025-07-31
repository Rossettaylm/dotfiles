# -*- coding: utf-8 -*-
from subprocess import CalledProcessError
from pyutils import shell as sh
import os


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
            not self.has_cur_branch
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
            print(br)
        branches[idx] = br.lstrip(" ")
        if br.startswith("*"):
            has_cur_branch = True
            cur_branch = br.removeprefix("* ")

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


def get_branches_v2(header, use_multi_select=False, query=""):
    fzf_cmd = sh.fzf_command_list(header, use_multi_select, query)
    _, err = sh.run_shell_cmd("git branch")
    if err:
        raise CalledProcessError(-1, "git branch", None, "not a git repo")
    out = sh.run_cmd_chain([["git", "branch"], fzf_cmd])
    return out


# 必须要使用/$()来包裹命令来保证刷新
def git_branch_fzf_preview_opt():
    preview_opt = "--preview \"git log --since='4 week ago' --oneline --color=always --date=short --pretty='format:%C(auto)%cd %an %h%d %s' \$(cut -c3- <<< {} | cut -d' ' -f1) --\""
    return preview_opt


# 选中分支
def get_branches(header, use_multi_select=False, show_brs_cmd="git branch"):
    fzf_cmd = sh.fzf_command(
        header,
        use_multi_select,
        preview=git_branch_fzf_preview_opt(),
        preview_window="down,70%",
        preview_label="[Git:Show]",
    )

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


def git_log_cmd(branch=""):
    gitLogCmd = (
        f"git log --oneline --date=short --pretty='format:%C(auto)%cd %h%d %s' {branch}"
    )
    return gitLogCmd
