"""Homebrew 安装与包管理。"""

import os
import subprocess
import shutil
import sys
from pathlib import Path

# Homebrew prefix 和对应的 brew 路径
BREW_PREFIXES = [
    "/opt/homebrew",                # macOS Apple Silicon
    "/usr/local",                   # macOS Intel
    "/home/linuxbrew/.linuxbrew",   # Linux
]


def find_brew() -> tuple[str, str] | None:
    """查找 brew 可执行文件，返回 (brew_path, prefix) 或 None"""
    brew = shutil.which("brew")
    if brew:
        # 从 brew 路径推导 prefix: .../bin/brew -> ...
        prefix = str(Path(brew).resolve().parent.parent)
        return brew, prefix
    for prefix in BREW_PREFIXES:
        brew = os.path.join(prefix, "bin", "brew")
        if os.path.isfile(brew) and os.access(brew, os.X_OK):
            return brew, prefix
    return None


def setup_brew_env(prefix: str):
    """根据 brew prefix 直接构造环境变量并注入当前进程。

    不使用 brew shellenv，因为其输出含 ${PATH+:$PATH} 等 bash 表达式，
    Python 无法正确解析会导致 PATH 被破坏。
    """
    os.environ["HOMEBREW_PREFIX"] = prefix
    os.environ["HOMEBREW_CELLAR"] = os.path.join(prefix, "Cellar")
    os.environ["HOMEBREW_REPOSITORY"] = os.path.join(prefix, "Homebrew")
    # 将 brew 的 bin/sbin 加到 PATH 最前面
    brew_dirs = [os.path.join(prefix, "bin"), os.path.join(prefix, "sbin")]
    current = os.environ.get("PATH", "")
    parts = current.split(os.pathsep)
    for p in reversed(brew_dirs):
        if p in parts:
            parts.remove(p)
        parts.insert(0, p)
    os.environ["PATH"] = os.pathsep.join(parts)


def ensure_brew() -> str:
    """确保 brew 已安装并可用，返回 brew 路径"""
    found = find_brew()
    if found:
        brew, prefix = found
        setup_brew_env(prefix)
        return brew

    print("未找到 Homebrew，开始安装...")
    install_url = "https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh"
    # 用两段管道：curl 下载脚本内容写入 bash stdin，避免 $() 展开问题
    curl = subprocess.run(
        ["curl", "-fsSL", install_url],
        capture_output=True,
        check=False,
    )
    if curl.returncode != 0:
        sys.exit("下载 Homebrew 安装脚本失败")
    ret = subprocess.run(
        ["/bin/bash"],
        input=curl.stdout,
        check=False,
    )
    if ret.returncode != 0:
        sys.exit("Homebrew 安装失败")

    found = find_brew()
    if not found:
        sys.exit("Homebrew 安装完成但未找到 brew 可执行文件")

    brew, prefix = found
    setup_brew_env(prefix)
    print(f"Homebrew 已安装: {brew}")
    return brew


def brew_install(brew: str, deps: list[str]):
    """批量安装依赖"""
    if not deps:
        return
    print(f"即将安装 {len(deps)} 个包: {', '.join(deps)}")
    subprocess.run([brew, "install", *deps], check=False)
