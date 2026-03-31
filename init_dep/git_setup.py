"""Git 仓库与 GitHub 远程配置。"""

import os
import subprocess
import sys
from pathlib import Path

# GitHub 仓库信息
GITHUB_HOST = "github.com"
REPO_OWNER = "Rossettaylm"
REPO_NAME = "config"
REPO_SSH_URL = f"git@{GITHUB_HOST}:{REPO_OWNER}/{REPO_NAME}.git"
REPO_HTTPS_URL = f"https://{GITHUB_HOST}/{REPO_OWNER}/{REPO_NAME}.git"


def resolve_pat(cli_pat: str | None) -> str | None:
    """优先级：命令行 --pat > 环境变量 GITHUB_PAT > GITHUB_TOKEN"""
    if cli_pat:
        return cli_pat
    return os.environ.get("GITHUB_PAT") or os.environ.get("GITHUB_TOKEN") or None


def probe_ssh_github() -> bool:
    """探测 SSH 能否连通 GitHub（不依赖任何 PAT）。

    `ssh -T git@github.com` 在认证成功时返回 exit code 1（Hi <user>! ...），
    鉴权失败时返回 255；两种情况都属于"能不能连上"，只要不是连接失败即可。
    """
    ret = subprocess.run(
        ["ssh", "-T", "-o", "StrictHostKeyChecking=no",
         "-o", "BatchMode=yes",           # 禁止交互，密钥不存在时立即失败
         "-o", "ConnectTimeout=5",
         f"git@{GITHUB_HOST}"],
        capture_output=True,
        check=False,
    )
    # exit 255 = 连接/鉴权彻底失败；exit 1 = 连上了但 GitHub 不开 shell（正常）
    reachable = ret.returncode != 255
    if reachable:
        print("SSH 连通 GitHub，使用 SSH 协议")
    else:
        print("SSH 无法连通 GitHub，回退到 HTTPS + PAT")
    return reachable


def setup_repo_remote(repo_root: Path, use_ssh: bool, pat: str | None):
    """按协议偏好设置当前仓库的 origin remote URL。

    - SSH 可用  → git@github.com:owner/repo.git
    - SSH 不可用 → https://<pat>@github.com/owner/repo.git

    若当前 remote URL 已经与目标协议匹配则跳过，避免无必要的写操作及
    在无 PAT 时因无法构造 HTTPS URL 而中断流程。
    """
    # 读取当前 remote URL
    cur = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    current_url = cur.stdout.strip()

    if use_ssh:
        # 当前已是 SSH URL，无需变更
        if current_url == REPO_SSH_URL:
            print("remote origin 已是 SSH URL，跳过")
            return
        url = REPO_SSH_URL
    else:
        # 当前已是合法的 HTTPS URL（不论是否含 token），无需变更
        if current_url.startswith(f"https://{GITHUB_HOST}/") or \
                current_url.startswith("https://") and f"@{GITHUB_HOST}/" in current_url:
            print("remote origin 已是 HTTPS URL，跳过")
            return
        if not pat:
            print("SSH 不可用且未提供 PAT，跳过设置 remote URL（保留现有配置）")
            return
        url = f"https://{pat}@{GITHUB_HOST}/{REPO_OWNER}/{REPO_NAME}.git"

    subprocess.run(
        ["git", "remote", "set-url", "origin", url],
        cwd=repo_root,
        check=True,
    )
    # 打印时隐藏 token
    display = REPO_SSH_URL if use_ssh else REPO_HTTPS_URL
    print(f"remote origin 已设为: {display}")


def update_submodules(repo_root: Path, use_ssh: bool, pat: str | None):
    """拉取所有 git submodule。

    - SSH 可用  → 直接执行，submodule 的 git@github.com: URL 原样生效
    - SSH 不可用 → 用 -c insteadOf 临时将 SSH / HTTPS URL 均改写为 HTTPS+PAT，
                   不修改任何 git 配置文件
    """
    print("正在更新 git submodules...")

    cmd = ["git"]
    if not use_ssh:
        if not pat:
            sys.exit("SSH 不可用且未提供 PAT，无法拉取 submodule")
        authed = f"https://{pat}@{GITHUB_HOST}/"
        cmd += [
            "-c", f"url.{authed}.insteadOf=https://{GITHUB_HOST}/",
            "-c", f"url.{authed}.insteadOf=git@{GITHUB_HOST}:",
        ]
    cmd += ["submodule", "update", "--init", "--recursive"]

    ret = subprocess.run(cmd, cwd=repo_root, check=False)
    if ret.returncode != 0:
        sys.exit("git submodule 更新失败")
    print("git submodules 更新完成")
