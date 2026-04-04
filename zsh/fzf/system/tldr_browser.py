#!/usr/bin/python3
"""
交互式 tldr 浏览器：fzf 搜索命令名，预览窗口实时显示 tldr 内容。
用法: tldr_browser.py [初始搜索词]
"""
import re
import subprocess
import sys
import os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pyutils.shell as shell

_ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')


def _strip_ansi(s: str) -> str:
    return _ANSI_RE.sub('', s)


def main():
    initial_query = " ".join(sys.argv[1:])

    # 获取所有可用命令
    result = subprocess.run(
        ["tldr", "--list"],
        capture_output=True, text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        shell.log_err("无法获取 tldr 命令列表，请确认 tldr 已安装。")
        exit(1)

    # 过滤掉 section header（如 "Pages for osx"），先去 ANSI 转义码再判断
    commands = []
    for line in result.stdout.splitlines():
        clean = _strip_ansi(line).strip()
        if clean and not clean.startswith("Pages for"):
            commands.append(clean)
    if not commands:
        shell.log_err("tldr 命令列表为空。")
        exit(0)

    fzf_cmd = shell.build_fzf_cmd(
        border_label="📖  [TLDR Browser]",
        header="  Enter → 复制命令名  ·  Esc quit",
        prompt="  Command > ",
        preview="tldr --color {}",
        preview_window="right,border-left,70%",
        preview_label="[ TLDR ]",
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
    stdout, _ = process.communicate(input="\n".join(commands))
    if process.returncode != 0 or not stdout.strip():
        exit(0)

    selected = stdout.strip()
    # 复制到剪贴板
    subprocess.run(["pbcopy"], input=selected, text=True)
    shell.log_success(f"已复制 '{selected}' 到剪贴板")


if __name__ == "__main__":
    main()
