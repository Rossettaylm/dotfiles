# -*- coding: utf-8 -*-
from pyutils import shell as sh


class BranchResult(object):
    has_cur_branch: bool = False
    cur_branch_name: str = ""
    branch_list: list = []

    def __init__(self, has_cur_branch=False, cur_branch_name="", branch_list=None):
        self.has_cur_branch = has_cur_branch
        self.cur_branch_name = cur_branch_name
        self.branch_list = branch_list if branch_list is not None else []

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
        branches[idx] = br.removeprefix("  ")
        if br.startswith("*"):
            has_cur_branch = True
            cur_branch = br.removeprefix("* ")
            branches[idx] = cur_branch

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


# 必须要使用/$()来包裹命令来保证刷新
def git_branch_fzf_preview_cmd():
    """返回纯预览命令字符串（不含 --preview 标志），传给 build_fzf_cmd 的 preview 参数。"""
    return "git log -n 30 --oneline --graph --color=always --date=short --pretty='format:%C(auto)%cd %an %h%d %s' $(cut -c3- <<< {} | cut -d' ' -f1) --"


# 选中分支
def get_branches(header, use_multi_select=False, show_brs_cmd="git branch"):
    fzf_cmd = sh.build_fzf_cmd(
        border_label=header,
        use_multi_select=use_multi_select,
        sort=False,
        preview=git_branch_fzf_preview_cmd(),
        preview_window="right,border-left,70%",
        preview_label="[ Git Log ]",
        extra_args=["--no-hscroll", "--color", "hl:underline,hl+:underline"],
        as_str=True,
    )

    _, err = sh.run_shell_cmd(show_brs_cmd)
    if err:
        sh.log_err("当前目录不是git仓库!")
        return BranchResult()

    branches, err = sh.run_shell_cmd(
        "{git_cmd} | {fzf_cmd}".format(git_cmd=show_brs_cmd, fzf_cmd=fzf_cmd)
    )
    result = branch_preprocess(branches)
    # result.setCurBranch(get_cur_branch())
    return result


def git_log_cmd(branch=""):
    gitLogCmd = (
        f"git log --oneline --date=short --pretty='format:%C(auto)%cd %h%d %s' {branch}"
    )
    return gitLogCmd
