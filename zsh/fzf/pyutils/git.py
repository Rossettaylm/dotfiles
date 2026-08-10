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


# git branch 行前缀标记：
# "*" 当前分支 / "+" 被其他 worktree 占用的分支 / "" 普通分支
_BRANCH_PREFIXES = ("*", "+")


def branch_prefix_marker(raw):
    """识别 git branch 输出行的前缀标记，不修改原始内容。"""
    if isinstance(raw, bytes):
        raw = raw.decode()
    stripped = raw.strip()
    for marker in _BRANCH_PREFIXES:
        if stripped.startswith(marker):
            return marker
    return ""


def clean_branch_name(raw):
    """统一清理 git branch/branch -a 输出的行前缀 (* / + / 前导空格)，
    并去掉形如 "HEAD -> origin/master" 的别名后缀，返回纯净分支名。
    所有需要从 git branch 输出中提取分支名的地方都应复用此函数，
    避免各脚本各自维护一套不一致的前缀解析逻辑。
    """
    if raw is None:
        return ""
    if isinstance(raw, bytes):
        raw = raw.decode()
    name = raw.strip()
    marker = branch_prefix_marker(name)
    if marker:
        name = name[len(marker):].strip()
    name = name.split(" -> ")[0]
    return name.strip()


# git branch分支预处理
def branch_preprocess(branches):
    has_cur_branch = False
    cur_branch = ""
    result = []
    for br in branches:
        marker = branch_prefix_marker(br)
        if marker == "+":
            continue  # worktree 占用的分支，跳过不展示
        name = clean_branch_name(br)
        if marker == "*":
            has_cur_branch = True
            cur_branch = name
        result.append(name)

    return BranchResult(has_cur_branch, cur_branch, result)


def get_cur_branch():
    cmd = "git branch"
    out, err = sh.run_shell_cmd(cmd)
    for e in err:
        sh.log_err(e)
    for br in out:
        if branch_prefix_marker(br) == "*":
            return clean_branch_name(br)
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
        preview_window="up,50%,border-bottom",
        preview_label="[ Git Log ]",
        extra_args=["--no-hscroll", "--color", "hl:underline,hl+:underline"],
        as_str=True,
    )

    _, err = sh.run_shell_cmd(show_brs_cmd)
    if err:
        sh.log_err("当前目录不是git仓库!")
        return BranchResult()

    branches, err = sh.run_shell_cmd(
        "{git_cmd} | grep -v '^+ ' | {fzf_cmd}".format(git_cmd=show_brs_cmd, fzf_cmd=fzf_cmd)
    )
    result = branch_preprocess(branches)
    # result.setCurBranch(get_cur_branch())
    return result


def git_log_cmd(branch=""):
    gitLogCmd = (
        f"git log --oneline --date=short --pretty='format:%C(auto)%cd %h%d %s' {branch}"
    )
    return gitLogCmd
