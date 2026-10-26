#!/usr/bin/python3
"""
交互式 git log，选中 commit 后将 hash 输出到 stdout（供 glog alias 复制）。
支持选择任意本地/远程分支查看提交记录。

查询词只筛选当前列表里的提交说明 / 作者 / hash。
文件是另一根轴：Ctrl-F 把列表收成该文件的历史，Ctrl-X 回到分支全量。

快捷键:
  Ctrl-P → 命令面板，搜索并执行下面这些动作
  Ctrl-F → 选择文件，列表改为该文件历史（--follow）
  Ctrl-X → 清除文件范围，回到分支全量
  Ctrl-O → 看当前提交里某个文件的 diff
  Ctrl-D → 当前提交的完整 diff
  Ctrl-R → git reset 到选中 commit (弹出 mode 选择)
  Ctrl-E → git revert 选中 commit

用法: git_log.py [branch]
       git_log.py --reset <hash>
       git_log.py --revert <hash>
"""
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from sys import argv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pyutils.git as git
import pyutils.shell as shell


_HASH_EXPR = "echo {} | grep -oE '[0-9a-f]{7,}' | head -1"
_LOG_PRETTY = "%C(auto)%cd %an %h%d %s"
# id, 面板标题, 对应快捷键。标题用英文，空查询时按这个顺序排列。
_COMMANDS = (
    ("copy", "copy hash", "Enter"),
    ("pick-file", "filter by file", "Ctrl-F"),
    ("clear", "clear scope", "Ctrl-X"),
    ("file-diff", "file diff", "Ctrl-O"),
    ("show-diff", "commit diff", "Ctrl-D"),
    ("reset", "reset", "Ctrl-R"),
    ("revert", "revert", "Ctrl-E"),
)
_HASH_ACTIONS = {"copy", "file-diff", "show-diff", "reset", "revert"}


def _read_text(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def _write_text(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _session_file(session, name):
    return os.path.join(session, name)


def _py_invoke(session, subcommand):
    return " ".join([
        shlex.quote(sys.executable),
        shlex.quote(os.path.abspath(__file__)),
        subcommand,
        shlex.quote(session),
    ])


def _refresh_action(session):
    return (
        f"reload-sync[{_py_invoke(session, '--log')}]"
        f"+transform-border-label[{_py_invoke(session, '--border-label')}]"
        f"+transform-preview-label[{_py_invoke(session, '--preview-label')}]"
    )


def _hash_from_line(line):
    match = re.search(r"\b([0-9a-f]{7,})\b", line or "")
    return match.group(1) if match else ""


def _git_log_cmd(branch, path):
    cmd = [
        "git", "log", "-n", "1000", "--color=always", "--date=short-local",
        f"--pretty=format:{_LOG_PRETTY}",
    ]
    if path:
        cmd.append("--follow")
    if branch:
        cmd.append(branch)
    cmd.append("--")
    if path:
        cmd.append(path)
    return cmd


def _scope_line(branch, path):
    if path:
        return f"FILE  {path}"
    return f"BRANCH  {branch or 'HEAD'}"


def _border_label(branch, path):
    label = f"📜  [Git Log: {branch or 'HEAD'}"
    if path:
        label += f" · {path}"
    return f" {label}] "


def _preview_label(path):
    if path:
        return "[ File Diff ]"
    return "[ Modified Files ]"


def _run_fzf(fzf_cmd, items):
    process = subprocess.Popen(
        fzf_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    stdout, _ = process.communicate(input="\n".join(items))
    if process.returncode != 0 or not stdout or not stdout.strip():
        return None
    return stdout.strip()


def select_branch():
    """用 fzf 选择本地或远程分支，直接回车则使用当前分支。"""
    branch_lines, err = shell.run_shell_cmd("git branch -a --color=never")
    if err:
        shell.log_err(err)
        return None

    cleaned = []
    current = ""
    for line in branch_lines:
        line = line.strip()
        if not line or "HEAD ->" in line:
            continue
        if git.branch_prefix_marker(line) == "*":
            current = git.clean_branch_name(line)
        cleaned.append(line)

    fzf_cmd = shell.build_fzf_cmd(
        border_label="🌿  [Select Branch]",
        header=f"  当前分支: {current}  ·  Enter 选择  ·  Esc 使用当前分支",
        prompt="  Branch > ",
        sort=False,
        preview="git log -n 20 --oneline --graph --color=always --date=short-local "
                "--pretty='format:%C(auto)%cd %an %h%d %s' "
                "$(echo {} | sed -E 's/^[*+ ]+//' | sed 's| -> .*||' | xargs) --",
        preview_window="up,50%,border-bottom",
        preview_label="[ Branch Log ]",
        extra_args=["--no-hscroll"],
        as_str=False,
    )

    selected = _run_fzf(fzf_cmd, cleaned)
    if selected is None:
        return current or ""
    return git.clean_branch_name(selected)


def do_reset(hash_val):
    """弹出二级选择框选择 reset mode，确认后执行 git reset。"""
    modes = ["hard", "soft", "mixed", "keep", "merge"]
    fzf_cmd = shell.build_fzf_cmd(
        border_label="🔄  [Git Reset Mode]",
        header=f"  Commit: {hash_val}",
        prompt="  Mode > ",
        sort=False,
        preview="",
        preview_window="",
        preview_label="",
        extra_args=["--no-hscroll"],
        as_str=False,
    )
    selected = _run_fzf(fzf_cmd, modes)
    if selected is None:
        shell.log_plain("reset 已取消")
        return False
    mode = selected.splitlines()[0].strip()

    shell.log_plain(f"⚠️  即将执行: git reset --{mode} {hash_val}")
    confirm = input("确认? [y/N] ").strip().lower()
    if confirm != "y":
        shell.log_plain("reset 已取消")
        return False

    ret = subprocess.run(["git", "reset", f"--{mode}", hash_val])
    if ret.returncode == 0:
        shell.log_success(f"git reset --{mode} {hash_val} ✅")
        return True
    shell.log_err(f"git reset --{mode} {hash_val} 失败 ❌")
    return False


def do_revert(hash_val):
    """确认后执行 git revert (--no-edit 使用默认 revert message)。"""
    shell.log_plain(f"⚠️  即将执行: git revert {hash_val}")
    confirm = input("确认? [y/N] ").strip().lower()
    if confirm != "y":
        shell.log_plain("revert 已取消")
        return False

    ret = subprocess.run(["git", "revert", "--no-edit", hash_val])
    if ret.returncode == 0:
        shell.log_success(f"git revert {hash_val} ✅")
        return True
    shell.log_err(f"git revert {hash_val} 失败/冲突 ❌")
    shell.log_plain("请手动解决冲突后 git revert --continue")
    return False


def emit_log(session):
    """打印一行范围状态 + git log。供 fzf reload-sync 使用。"""
    branch = _read_text(_session_file(session, "branch"))
    path = _read_text(_session_file(session, "path"))
    print(_scope_line(branch, path))
    result = subprocess.run(
        _git_log_cmd(branch, path),
        capture_output=True,
        text=True,
        errors="replace",
    )
    if result.returncode != 0:
        message = (result.stderr or "git log 失败").strip()
        print(message or "git log 失败")
        return
    sys.stdout.write(result.stdout)
    if result.stdout and not result.stdout.endswith("\n"):
        sys.stdout.write("\n")


def emit_border_label(session):
    branch = _read_text(_session_file(session, "branch"))
    path = _read_text(_session_file(session, "path"))
    print(_border_label(branch, path))


def emit_preview_label(session):
    path = _read_text(_session_file(session, "path"))
    print(_preview_label(path))


def emit_followup(session):
    """文件选择成功后，让外层 fzf 重载列表并刷新标题。取消选择时不输出动作。"""
    flag = _session_file(session, "changed")
    if not os.path.exists(flag):
        return
    os.remove(flag)
    print(_refresh_action(session))


def clear_scope(session):
    _write_text(_session_file(session, "path"), "")


def pick_file(session):
    """选择跟踪文件并写入 session。Esc 不修改当前范围。"""
    result = subprocess.run(
        ["git", "ls-files"],
        capture_output=True,
        text=True,
        errors="replace",
    )
    if result.returncode != 0:
        shell.log_err((result.stderr or "git ls-files 失败").strip())
        return
    files = [line for line in result.stdout.splitlines() if line]
    if not files:
        shell.log_plain("仓库里没有已跟踪文件")
        return

    fzf_cmd = shell.build_fzf_cmd(
        border_label="📄  [Select File]",
        header="  输入文件名模糊匹配  ·  Enter 收窄到该文件历史  ·  Esc 取消",
        prompt="  File > ",
        sort=True,
        preview="git log -n 8 --follow --color=always --date=short-local "
                "--pretty='format:%C(auto)%cd %h %s' -- {}",
        preview_window="up,30%,border-bottom",
        preview_label="[ File History ]",
        extra_args=["--no-hscroll", "--scheme", "path"],
        as_str=False,
    )
    selected = _run_fzf(fzf_cmd, files)
    if selected is None:
        return
    path = selected.splitlines()[0]
    _write_text(_session_file(session, "path"), path)
    _write_text(_session_file(session, "changed"), "1")


def _pipe_delta(git_cmd, delta_args):
    show = subprocess.Popen(git_cmd, stdout=subprocess.PIPE)
    try:
        subprocess.run(delta_args, stdin=show.stdout)
    finally:
        if show.stdout:
            show.stdout.close()
        show.wait()


def show_commit_file_diff(hash_val):
    """列出这次提交改过的文件，选中后用 delta 打开该文件的 diff。"""
    hash_val = (hash_val or "").strip()
    if not hash_val:
        shell.log_plain("没有识别到 commit")
        return

    result = subprocess.run(
        ["git", "show", "--name-only", "--pretty=format:", "--first-parent", hash_val],
        capture_output=True,
        text=True,
        errors="replace",
    )
    if result.returncode != 0:
        shell.log_err((result.stderr or "git show 失败").strip())
        return
    files = [line for line in result.stdout.splitlines() if line.strip()]
    if not files:
        shell.log_plain("这次提交没有文件变更")
        return

    quoted_hash = shlex.quote(hash_val)
    fzf_cmd = shell.build_fzf_cmd(
        border_label=f"📄  [Files in {hash_val[:12]}]",
        header="  Enter 全屏 diff  ·  Esc 返回",
        prompt="  File > ",
        sort=True,
        preview=(
            f"git show --format= --first-parent --color=always {quoted_hash} -- {{}} "
            "| delta --paging never"
        ),
        preview_window="down,border-top,60%",
        preview_label="[ File Diff ]",
        extra_args=["--no-hscroll", "--scheme", "path"],
        as_str=False,
    )
    selected = _run_fzf(fzf_cmd, files)
    if selected is None:
        return
    path = selected.splitlines()[0]
    _pipe_delta(
        ["git", "show", "--format=", "--first-parent", "--color=always", hash_val, "--", path],
        ["delta", "--side-by-side", "--paging", "always"],
    )


def show_commit_diff(hash_val):
    """当前提交相对父提交的完整 diff。"""
    hash_val = (hash_val or "").strip()
    if not hash_val:
        shell.log_plain("没有识别到 commit")
        return
    _pipe_delta(
        ["git", "diff", f"{hash_val}~1", hash_val],
        ["delta", "--side-by-side", "--paging", "always"],
    )


def _command_rows():
    return [
        f"{action_id}\t{title}  ·  {shortcut}"
        for action_id, title, shortcut in _COMMANDS
    ]


def _clear_palette_state(session):
    for name in ("action", "abort"):
        path = _session_file(session, name)
        if os.path.exists(path):
            os.remove(path)


def run_palette(session, line):
    """命令面板。动作记到 session，外层 transform 再决定刷新还是退出。"""
    _clear_palette_state(session)
    hash_val = _hash_from_line(line)
    fzf_cmd = shell.build_fzf_cmd(
        border_label="📋  [命令]",
        header="  输入筛选  ·  Enter 执行  ·  Esc 返回",
        prompt="  Command > ",
        sort=True,
        preview="",
        preview_window="hidden",
        preview_label="",
        extra_args=[
            "--no-hscroll",
            "--delimiter", "\t",
            "--with-nth", "2..",
            "--tiebreak", "index",
        ],
        as_str=False,
    )
    selected = _run_fzf(fzf_cmd, _command_rows())
    if selected is None:
        return
    action_id = selected.splitlines()[0].split("\t", 1)[0].strip()
    if action_id not in {item[0] for item in _COMMANDS}:
        return
    if action_id in _HASH_ACTIONS and not hash_val:
        shell.log_plain("没有识别到 commit")
        return
    _write_text(_session_file(session, "action"), action_id)
    if action_id == "pick-file":
        pick_file(session)
    elif action_id == "clear":
        clear_scope(session)
    elif action_id == "file-diff":
        show_commit_file_diff(hash_val)
    elif action_id == "show-diff":
        show_commit_diff(hash_val)
    elif action_id == "reset" and do_reset(hash_val):
        _write_text(_session_file(session, "abort"), "1")
    elif action_id == "revert" and do_revert(hash_val):
        _write_text(_session_file(session, "abort"), "1")


def emit_palette_followup(session):
    action = _read_text(_session_file(session, "action"))
    abort = os.path.exists(_session_file(session, "abort"))
    _clear_palette_state(session)
    if action == "copy":
        print("accept")
    elif action in ("reset", "revert") and abort:
        print("abort")
    elif action == "pick-file":
        emit_followup(session)
    elif action == "clear":
        print(_refresh_action(session))


def _preview_command(session):
    path_file = shlex.quote(_session_file(session, "path"))
    # zsh 的 path 和 PATH 绑定，赋值会清掉命令搜索路径，预览里随后就找不到 git。
    return (
        f"hash=$({_HASH_EXPR}); "
        '[ -n "$hash" ] || exit 0; '
        f"scope=$(cat {path_file} 2>/dev/null || true); "
        'if [ -n "$scope" ]; then '
        'git show --format= --first-parent --color=always "$hash" -- "$scope" | delta --paging never; '
        'else git show --stat --color=always "$hash"; fi'
    )


def _open_log(branch):
    session = tempfile.mkdtemp(prefix="glog-")
    try:
        _write_text(_session_file(session, "branch"), branch or "")
        _write_text(_session_file(session, "path"), "")

        clear_cmd = _py_invoke(session, "--clear")
        pick_cmd = _py_invoke(session, "--pick-file")
        followup_cmd = _py_invoke(session, "--followup")
        palette_cmd = " ".join([
            shlex.quote(sys.executable),
            shlex.quote(os.path.abspath(__file__)),
            "--palette",
            shlex.quote(session),
            "{}",
        ])
        palette_followup = _py_invoke(session, "--palette-followup")
        file_diff_cmd = " ".join([
            shlex.quote(sys.executable),
            shlex.quote(os.path.abspath(__file__)),
            "--file-diff",
            f"$({_HASH_EXPR})",
        ])
        refresh = _refresh_action(session)

        fzf_cmd = shell.build_fzf_cmd(
            border_label=f"📜  [Git Log: {branch or 'HEAD'}]",
            header=(
                "  Enter 复制 hash  ·  Ctrl-P 命令  ·  输入筛说明  ·  Ctrl-F 按文件"
                "  ·  Ctrl-X 清除  ·  Ctrl-O 本次文件 diff  ·  Ctrl-D 整提交 diff"
                "  ·  Ctrl-R reset  ·  Ctrl-E revert  ·  Esc 退出"
            ),
            prompt="  Commit > ",
            use_multi_select=True,
            sort=False,
            preview=_preview_command(session),
            preview_window="down,border-top,50%",
            preview_label="[ Modified Files ]",
            extra_args=[
                "--no-hscroll",
                "--delimiter", " ",
                "--header-lines=1",
                "--bind", f"start:{refresh}",
                "--bind", f"ctrl-p:execute[{palette_cmd}]+transform[{palette_followup}]",
                "--bind", f"ctrl-f:execute[{pick_cmd}]+transform[{followup_cmd}]",
                "--bind", f"ctrl-x:execute-silent[{clear_cmd}]+{refresh}",
                "--bind", f"ctrl-o:execute[{file_diff_cmd}]",
                "--bind", (
                    "ctrl-d:execute["
                    f"git diff $({_HASH_EXPR})~1 $({_HASH_EXPR}) "
                    "| delta --side-by-side --paging always]"
                ),
                "--bind", (
                    "ctrl-r:execute["
                    f"{shlex.quote(sys.executable)} {shlex.quote(os.path.abspath(__file__))} "
                    f"--reset $({_HASH_EXPR})]+abort"
                ),
                "--bind", (
                    "ctrl-e:execute["
                    f"{shlex.quote(sys.executable)} {shlex.quote(os.path.abspath(__file__))} "
                    f"--revert $({_HASH_EXPR})]+abort"
                ),
            ],
            as_str=False,
        )
        process = subprocess.Popen(
            fzf_cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            text=True,
        )
        stdout, _ = process.communicate()
        if process.returncode != 0 or not stdout or not stdout.strip():
            return

        hashes = []
        for line in stdout.strip().splitlines():
            match = re.search(r"\b([0-9a-f]{7,})\b", line)
            if match:
                hashes.append(match.group(1))
        if hashes:
            print(" ".join(hashes))
    finally:
        shutil.rmtree(session, ignore_errors=True)


def main():
    if len(argv) >= 3 and argv[1] == "--reset":
        do_reset(argv[2])
        return
    if len(argv) >= 3 and argv[1] == "--revert":
        do_revert(argv[2])
        return
    if len(argv) >= 3 and argv[1] == "--log":
        emit_log(argv[2])
        return
    if len(argv) >= 3 and argv[1] == "--border-label":
        emit_border_label(argv[2])
        return
    if len(argv) >= 3 and argv[1] == "--preview-label":
        emit_preview_label(argv[2])
        return
    if len(argv) >= 3 and argv[1] == "--followup":
        emit_followup(argv[2])
        return
    if len(argv) >= 3 and argv[1] == "--clear":
        clear_scope(argv[2])
        return
    if len(argv) >= 3 and argv[1] == "--pick-file":
        pick_file(argv[2])
        return
    if len(argv) >= 3 and argv[1] == "--file-diff":
        show_commit_file_diff(argv[2])
        return
    if len(argv) >= 3 and argv[1] == "--palette":
        run_palette(argv[2], argv[3] if len(argv) >= 4 else "")
        return
    if len(argv) >= 3 and argv[1] == "--palette-followup":
        emit_palette_followup(argv[2])
        return

    branch = argv[1] if len(argv) > 1 else None
    if branch is None:
        branch = select_branch()
        if branch is None:
            exit(1)
    _open_log(branch)


if __name__ == "__main__":
    main()
