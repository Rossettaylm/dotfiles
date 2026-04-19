#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
from pathlib import Path

REQUIRED_PYTHON = (3, 11)

SYSTEM_PATHS = ["/usr/bin", "/bin", "/usr/sbin", "/sbin", "/usr/local/bin"]

# ── 输出美化 ──────────────────────────────────────────────

BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
RED = "\033[31m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RESET = "\033[0m"

_step_idx = 0


def step_start(title: str):
    global _step_idx
    _step_idx += 1
    print(f"\n{BOLD}{CYAN}[{_step_idx}] {title}{RESET}")
    print(f"{CYAN}{'─' * 48}{RESET}")


def step_ok(msg: str = "done"):
    print(f"  {GREEN}>>> {msg}{RESET}")


def step_fail(msg: str):
    print(f"  {RED}!!! {msg}{RESET}", file=sys.stderr)


def step_info(msg: str):
    print(f"  {DIM}--- {msg}{RESET}")


# ── 前置检查 ──────────────────────────────────────────────

def check_python_version():
    if sys.version_info < REQUIRED_PYTHON:
        step_fail(
            f"需要 Python {REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]}+，"
            f"当前版本为 {sys.version_info.major}.{sys.version_info.minor}"
        )
        sys.exit(1)


def ensure_system_paths():
    current = os.environ.get("PATH", "")
    parts = current.split(os.pathsep)
    for p in SYSTEM_PATHS:
        if p not in parts and os.path.isdir(p):
            parts.append(p)
    os.environ["PATH"] = os.pathsep.join(parts)


# ── 主流程 ────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="初始化开发环境依赖")
    parser.add_argument(
        "--pat",
        metavar="TOKEN",
        default=None,
        help="GitHub Personal Access Token（也可通过 GITHUB_PAT / GITHUB_TOKEN 传入）",
    )
    args = parser.parse_args()

    print(f"\n{BOLD}{YELLOW}  dotfiles 开发环境初始化{RESET}")
    print(f"{DIM}  {'─' * 40}{RESET}")

    check_python_version()
    ensure_system_paths()
    repo_root = Path(__file__).parent

    # ── 1. Git / GitHub ──
    step_start("Git / GitHub 配置")
    try:
        from setup_dep.git_setup import (
            resolve_pat, probe_ssh_github, setup_repo_remote, update_submodules,
        )
        pat = resolve_pat(args.pat)
        use_ssh = probe_ssh_github()
        setup_repo_remote(repo_root, use_ssh, pat)
        step_info("更新 git submodules...")
        update_submodules(repo_root, use_ssh, pat)
        step_ok("Git 配置完成")
    except SystemExit:
        raise
    except Exception as e:
        step_fail(f"Git 配置失败: {e}")
        sys.exit(1)

    # ── 2. FZF ──
    step_start("FZF")
    try:
        from setup_dep.fzf import init_fzf
        init_fzf(repo_root)
        step_ok("FZF 安装完成")
    except SystemExit:
        raise
    except Exception as e:
        step_fail(f"FZF 安装失败: {e}")
        sys.exit(1)

    # ── 3. Zsh 插件（submodule） ──
    step_start("Zsh 插件（submodule）")
    try:
        from setup_dep.plugins import init_plugins
        init_plugins(repo_root)
        step_ok("Zsh 插件初始化完成")
    except SystemExit:
        raise
    except Exception as e:
        step_fail(f"Zsh 插件初始化失败: {e}")
        sys.exit(1)

    # ── 4. Homebrew ──
    step_start("Homebrew 依赖")
    try:
        from setup_dep.brew import ensure_brew, brew_install
        brew = ensure_brew()
        dep_file = repo_root / "dep.txt"
        if not dep_file.exists():
            step_fail(f"依赖文件不存在: {dep_file}")
            sys.exit(1)
        deps = [
            line.strip()
            for line in dep_file.read_text().splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        step_info(f"共 {len(deps)} 个包")
        brew_install(brew, deps)
        step_ok("Homebrew 依赖安装完成")
    except SystemExit:
        raise
    except Exception as e:
        step_fail(f"Homebrew 安装失败: {e}")
        sys.exit(1)

    # ── 5. Shell & Git config ──
    step_start("Shell / Git 全局配置")
    try:
        from setup_dep.shell_config import setup_zshrc
        from setup_dep.git_config import setup_gitconfig
        setup_zshrc()
        setup_gitconfig()
        step_ok("Shell / Git 配置完成")
    except SystemExit:
        raise
    except Exception as e:
        step_fail(f"配置失败: {e}")
        sys.exit(1)

    # ── 6. 定时同步任务 ──
    step_start("定时同步任务")
    try:
        from setup_dep.sync_timer import setup_sync_timer
        setup_sync_timer(repo_root)
        step_ok("同步任务配置完成")
    except SystemExit:
        raise
    except Exception as e:
        step_fail(f"同步任务配置失败: {e}")
        sys.exit(1)

    # ── 7. Claude Code ──
    step_start("Claude Code")
    try:
        from setup_dep.claude_code import init_claude_code
        init_claude_code()
        step_ok("Claude Code 配置完成")
    except SystemExit:
        raise
    except Exception as e:
        step_fail(f"Claude Code 配置失败: {e}")
        sys.exit(1)

    # ── 8. AI 通知 Hooks ──
    step_start("AI 通知 Hooks")
    try:
        from setup_dep.ai_hooks import inject_ai_hooks
        inject_ai_hooks()
        step_ok("AI Hooks 注入完成")
    except SystemExit:
        raise
    except Exception as e:
        step_fail(f"AI Hooks 注入失败: {e}")
        sys.exit(1)

    # ── 9. Yazi 插件 ──
    step_start("Yazi 插件")
    try:
        subprocess.run(["ya", "pkg", "install"], check=True)
        step_ok("Yazi 插件安装完成")
    except FileNotFoundError:
        step_fail("ya 命令不存在，跳过")
    except subprocess.CalledProcessError:
        step_fail("Yazi 插件安装失败")
        sys.exit(1)

    # ── 10. Tmux 插件 ──
    step_start("Tmux 插件")
    try:
        from setup_dep.tmux import init_tmux
        init_tmux()
        step_ok("Tmux 插件安装完成")
    except SystemExit:
        raise
    except Exception as e:
        step_fail(f"Tmux 插件安装失败: {e}")
        sys.exit(1)

    # ── 11. Zellij 插件 ──
    step_start("Zellij 插件")
    try:
        from setup_dep.zellij_plugins import init_zellij_plugins
        init_zellij_plugins()
        step_ok("Zellij 插件安装完成")
    except SystemExit:
        raise
    except Exception as e:
        step_fail(f"Zellij 插件安装失败: {e}")
        sys.exit(1)

    # ── 完成 ──
    print(f"\n{BOLD}{GREEN}{'=' * 48}")
    print("  ALL DONE — 开发环境初始化完成")
    print(f"{'=' * 48}{RESET}\n")


if __name__ == "__main__":
    main()
