#!/usr/bin/python3
"""
交互式命令浏览器：扫描 $PATH 中所有可执行文件，fzf 选择后复制到剪贴板。
用法: cmd_browser.py [初始搜索词]
"""
import os
import subprocess
import sys; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pyutils.shell as shell


def collect_commands():
    """扫描 PATH 中所有可执行文件，返回去重排序的命令名列表。"""
    cmds = set()
    seen_paths = set()
    for d in os.environ.get("PATH", "").split(os.pathsep):
        d = os.path.realpath(d)
        if d in seen_paths or not os.path.isdir(d):
            continue
        seen_paths.add(d)
        try:
            for entry in os.listdir(d):
                fpath = os.path.join(d, entry)
                if os.path.isfile(fpath) and os.access(fpath, os.X_OK):
                    cmds.add(entry)
        except PermissionError:
            continue
    return sorted(cmds, key=str.lower)


def main():
    initial_query = " ".join(sys.argv[1:])

    cmds = collect_commands()
    if not cmds:
        shell.log_err("未找到任何可执行命令。")
        exit(1)

    preview_script = (
        "echo '── which ──' && which {} 2>/dev/null; "
        "echo ''; "
        "echo '── file ──' && file $(which {} 2>/dev/null) 2>/dev/null; "
        "echo ''; "
        "echo '── tldr ──' && tldr --color {} 2>/dev/null || echo 'No tldr page'"
    )

    fzf_cmd = shell.build_fzf_cmd(
        border_label="🔍  [Command Browser]",
        header="  Enter → 复制命令名  ·  Esc quit",
        prompt="  Cmd > ",
        preview=preview_script,
        preview_window="right,border-left,60%",
        preview_label="[ Info ]",
        sort=True,
        as_str=False,
    )

    if initial_query:
        fzf_cmd += ["--query", initial_query]

    process = subprocess.Popen(
        fzf_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    stdout, _ = process.communicate(input="\n".join(cmds))
    if process.returncode != 0 or not stdout.strip():
        exit(0)

    print(stdout.strip(), end="")


if __name__ == "__main__":
    main()
