#!/usr/bin/python3
"""
交互式文件内容搜索：rg 实时搜索 + bat 预览 + 选中后用 nvim 打开
用法: file_preview.py [初始搜索词]
"""
import os
import subprocess
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pyutils.shell as shell


def main():
    initial_query = " ".join(sys.argv[1:])
    rg_prefix = "rg --column --line-number --no-heading --color=always --smart-case"

    _fzf_cmd = shell.build_fzf_cmd(
        border_label="🔍  [File Preview]",
        header="  输入关键字实时搜索  ·  Enter 用 nvim 打开  ·  Esc quit",
        prompt="  Search > ",
        preview="bat --color=always {1} --highlight-line {2}",
        preview_window="up,60%,border-bottom,+{2}+3/3,~3",
        preview_label="[ File Content ]",
        extra_args=[
            "--disabled",
            "--delimiter", ":",
            "--bind", f"start:reload:{rg_prefix} {{q}}",
            "--bind", f"change:reload:sleep 0.1; {rg_prefix} {{q}} || true",
        ],
        as_str=False,
    )
    assert isinstance(_fzf_cmd, list)
    fzf_cmd: list[str] = _fzf_cmd

    if initial_query:
        fzf_cmd += ["--query", initial_query]

    process = subprocess.Popen(
        fzf_cmd,
        stdout=subprocess.PIPE,
        text=True,
    )
    stdout, _ = process.communicate()
    if process.returncode != 0 or not stdout.strip():
        exit(0)

    # 格式: filepath:line:col:content
    parts = stdout.strip().split(":")
    if len(parts) < 2:
        exit(0)

    filepath, line = parts[0], parts[1]
    # 用 execvp 替换当前进程打开 nvim（与原 enter:become 等效）
    os.execvp("nvim", ["nvim", filepath, f"+{line}"])


if __name__ == "__main__":
    main()
