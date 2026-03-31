#!/usr/bin/env python3
import argparse
import os
import sys
from pathlib import Path

REQUIRED_PYTHON = (3, 11)

# 系统基础路径，确保 readlink/dirname 等基础命令可用
SYSTEM_PATHS = ["/usr/bin", "/bin", "/usr/sbin", "/sbin", "/usr/local/bin"]


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


def main():
    parser = argparse.ArgumentParser(description="初始化开发环境依赖")
    parser.add_argument(
        "--pat",
        metavar="TOKEN",
        default=None,
        help="GitHub Personal Access Token，用于拉取私有/受限 submodule"
             "（也可通过 GITHUB_PAT 或 GITHUB_TOKEN 环境变量传入）",
    )
    args = parser.parse_args()

    check_python_version()
    ensure_system_paths()

    repo_root = Path(__file__).parent

    # ── Git / GitHub ──
    from init_dep.git_setup import (
        resolve_pat, probe_ssh_github, setup_repo_remote, update_submodules,
    )
    pat = resolve_pat(args.pat)
    use_ssh = probe_ssh_github()
    setup_repo_remote(repo_root, use_ssh, pat)
    update_submodules(repo_root, use_ssh, pat)

    # ── FZF ──
    from init_dep.fzf import init_fzf, init_fzf_tab
    init_fzf(repo_root)
    init_fzf_tab()

    # ── Homebrew + deps ──
    from init_dep.brew import ensure_brew, brew_install
    brew = ensure_brew()

    dep_file = repo_root / "dep.txt"
    if not dep_file.exists():
        sys.exit(f"依赖文件不存在: {dep_file}")
    deps = [
        line.strip()
        for line in dep_file.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    brew_install(brew, deps)

    # ── Shell & Git config ──
    from init_dep.shell_config import setup_zshrc
    from init_dep.git_config import setup_gitconfig
    setup_zshrc()
    setup_gitconfig()

    # ── 定时同步任务（macOS: crontab, Linux: systemd timer）──
    from init_dep.sync_timer import setup_sync_timer
    setup_sync_timer(repo_root)

    # ── Claude Code ──
    from init_dep.claude_code import init_claude_code
    init_claude_code()


if __name__ == "__main__":
    main()
