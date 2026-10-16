"""Node 生态工具安装（claude-code / Cursor CLI）。

- claude-code：macOS 由 brew cask 安装；Linux 无 cask，改走 npm 全局包
- Cursor CLI：官方分发方式是 curl 安装脚本（npm 上无官方包），装到 ~/.local/bin
"""

import platform
import shutil
import subprocess
import sys

CLAUDE_CODE_NPM_PKG = "@anthropic-ai/claude-code"
CURSOR_INSTALL_URL = "https://cursor.com/install"


def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=False, **kwargs)


def install_claude_code():
    """Linux 专属：macOS 上 claude-code 由 brew cask 提供。"""
    if platform.system() == "Darwin":
        print("macOS 上 claude-code 由 Homebrew cask 安装，跳过")
        return

    if shutil.which("claude"):
        print("claude 已安装，跳过")
        return

    npm = shutil.which("npm")
    if not npm:
        print("未找到 npm，跳过 claude-code 安装（请先安装 Node.js）")
        return

    print(f"正在通过 npm 安装 {CLAUDE_CODE_NPM_PKG} ...")
    ret = _run([npm, "install", "-g", CLAUDE_CODE_NPM_PKG])
    if ret.returncode != 0:
        print("claude-code 安装失败", file=sys.stderr)
        return
    print("claude-code 安装完成")


def install_cursor_cli():
    """安装 Cursor CLI（agent / cursor-agent）。"""
    if shutil.which("cursor-agent"):
        print("cursor-agent 已安装，跳过")
        return

    curl = shutil.which("curl")
    if not curl:
        print("未找到 curl，跳过 Cursor CLI 安装")
        return

    print("正在安装 Cursor CLI ...")
    script = _run([curl, "-fsSL", CURSOR_INSTALL_URL], capture_output=True)
    if script.returncode != 0:
        print("下载 Cursor 安装脚本失败，跳过", file=sys.stderr)
        return

    ret = _run(["/bin/bash"], input=script.stdout)
    if ret.returncode != 0:
        print("Cursor CLI 安装失败", file=sys.stderr)
        return
    print("Cursor CLI 安装完成")


def init_node_tools():
    """安装 Node 生态工具（幂等）。"""
    install_claude_code()
    install_cursor_cli()
