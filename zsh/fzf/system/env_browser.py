#!/usr/bin/python3
"""
交互式环境变量浏览器：列出所有环境变量，预览值，选中后复制到剪贴板。
用法: env_browser.py
"""
import os
import subprocess
import sys; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pyutils.shell as shell


def main():
    env_lines = sorted(
        [f"{k}={v}" for k, v in os.environ.items()],
        key=lambda x: x.lower(),
    )
    if not env_lines:
        shell.log_err("没有环境变量。")
        exit(0)

    fzf_cmd = shell.build_fzf_cmd(
        border_label="🌍  [Environment Variables]",
        header="  Enter → 复制值到剪贴板  ·  Esc quit",
        prompt="  Env > ",
        use_multi_select=False,
        preview="echo {} | cut -d'=' -f2-",
        preview_window="up,3,border-bottom,wrap",
        preview_label="[ Value ]",
        extra_args=["--delimiter", "=", "--nth", "1"],
        as_str=False,
    )

    process = subprocess.Popen(
        fzf_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    stdout, _ = process.communicate(input="\n".join(env_lines))
    if process.returncode != 0 or not stdout.strip():
        exit(0)

    # 提取值（KEY=VALUE 中 = 之后的部分）
    line = stdout.strip()
    idx = line.find("=")
    if idx < 0:
        exit(0)

    key = line[:idx]
    value = line[idx + 1:]

    # 复制到剪贴板
    subprocess.run(["pbcopy"], input=value, text=True)
    shell.log_success(f"已复制 ${key} 的值到剪贴板")


if __name__ == "__main__":
    main()
