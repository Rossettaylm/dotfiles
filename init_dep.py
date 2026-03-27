#!/usr/bin/env python3
import argparse
import os
import sys
import shutil
import subprocess
from pathlib import Path

REQUIRED_PYTHON = (3, 11)

# 系统基础路径，确保 readlink/dirname 等基础命令可用
SYSTEM_PATHS = ["/usr/bin", "/bin", "/usr/sbin", "/sbin", "/usr/local/bin"]

# Homebrew prefix 和对应的 brew 路径
BREW_PREFIXES = [
    "/opt/homebrew",                # macOS Apple Silicon
    "/usr/local",                   # macOS Intel
    "/home/linuxbrew/.linuxbrew",   # Linux
]


def check_python_version():
    if sys.version_info < REQUIRED_PYTHON:
        sys.exit(
            f"需要 Python {REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]}+，"
            f"当前版本为 {sys.version_info.major}.{sys.version_info.minor}"
        )


def ensure_system_paths():
    """确保系统基础路径在 PATH 中（brew 脚本依赖 readlink/dirname 等）"""
    current = os.environ.get("PATH", "")
    parts = current.split(os.pathsep)
    for p in SYSTEM_PATHS:
        if p not in parts and os.path.isdir(p):
            parts.append(p)
    os.environ["PATH"] = os.pathsep.join(parts)


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
    install_script = "https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh"
    ret = subprocess.run(
        ["/bin/bash", "-c", f"$(curl -fsSL {install_script})"],
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


def resolve_pat(cli_pat: str | None) -> str | None:
    """优先级：命令行 --pat > 环境变量 GITHUB_PAT > GITHUB_TOKEN"""
    if cli_pat:
        return cli_pat
    return os.environ.get("GITHUB_PAT") or os.environ.get("GITHUB_TOKEN") or None


def update_submodules(pat: str | None = None):
    """拉取所有 git submodule。

    若提供 pat，则通过临时 url rewrite 注入 GitHub Personal Access Token，
    仅在本次 git 调用中生效，不修改任何 git 配置文件。
    """
    repo_root = Path(__file__).parent
    print("正在更新 git submodules...")

    cmd = ["git"]
    if pat:
        # 用 -c 临时覆盖，不落盘到 .git/config 或 ~/.gitconfig
        cmd += [
            "-c", f"url.https://{pat}@github.com/.insteadOf=https://github.com/",
        ]
    cmd += ["submodule", "update", "--init", "--recursive"]

    ret = subprocess.run(cmd, cwd=repo_root, check=False)
    if ret.returncode != 0:
        sys.exit("git submodule 更新失败")
    print("git submodules 更新完成")


def init_fzf():
    """初始化 thirdparty/fzf：执行其安装脚本（仅装二进制，不修改 shell 配置）"""
    fzf_dir = Path(__file__).parent / "thirdparty" / "fzf"
    install_script = fzf_dir / "install"

    if not install_script.exists():
        sys.exit(f"fzf 安装脚本不存在: {install_script}，请先执行 submodule 更新")

    print("正在初始化 fzf...")
    ret = subprocess.run(
        [str(install_script), "--bin", "--no-update-rc"],
        cwd=fzf_dir,
        check=False,
    )
    if ret.returncode != 0:
        sys.exit("fzf 初始化失败")
    print("fzf 初始化完成")


def main():
    parser = argparse.ArgumentParser(description="初始化开发环境依赖")
    parser.add_argument(
        "--pat",
        metavar="TOKEN",
        default=None,
        help="GitHub Personal Access Token，用于拉取私有/受限 submodule（也可通过 GITHUB_PAT 或 GITHUB_TOKEN 环境变量传入）",
    )
    args = parser.parse_args()

    check_python_version()
    ensure_system_paths()

    pat = resolve_pat(args.pat)
    update_submodules(pat)
    init_fzf()

    brew = ensure_brew()

    dep_file = Path(__file__).parent / "dep.txt"
    if not dep_file.exists():
        sys.exit(f"依赖文件不存在: {dep_file}")

    deps = [
        line.strip()
        for line in dep_file.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    brew_install(brew, deps)


if __name__ == "__main__":
    main()
