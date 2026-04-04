#!/usr/bin/python3
"""
交互式最近文件：从 neovim oldfiles 读取最近打开的文件，fzf 选择后用 nvim 打开。
用法: recent_files.py
"""
import os
import subprocess
import sys; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pyutils.shell as shell


def get_oldfiles():
    """通过 nvim 获取 v:oldfiles 列表。"""
    result = subprocess.run(
        [
            "nvim", "--headless",
            "-c", "redir! > /tmp/_nvim_oldfiles.txt | echo v:oldfiles | redir END | quit",
        ],
        capture_output=True, text=True,
    )
    try:
        content = open("/tmp/_nvim_oldfiles.txt").read()
    except FileNotFoundError:
        return []

    # 输出格式为 python list 的字符串表示，逐行提取路径
    files = []
    for part in content.replace("[", "").replace("]", "").split("', '"):
        path = part.strip().strip("'").strip('"').strip(",").strip()
        if path and os.path.isfile(path):
            files.append(path)
    return files


def main():
    files = get_oldfiles()
    if not files:
        shell.log_err("没有找到最近打开的文件。")
        exit(0)

    fzf_cmd = shell.build_fzf_cmd(
        border_label="🕐  [Recent Files]",
        header="  Enter → nvim 打开  ·  Esc quit",
        prompt="  File > ",
        preview="bat -n --color=always {}",
        preview_window="right,border-left,60%",
        preview_label="[ Preview ]",
        sort=False,
        as_str=False,
    )

    process = subprocess.Popen(
        fzf_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    stdout, _ = process.communicate(input="\n".join(files))
    if process.returncode != 0 or not stdout.strip():
        exit(0)

    filepath = stdout.strip()
    os.execvp("nvim", ["nvim", filepath])


if __name__ == "__main__":
    main()
