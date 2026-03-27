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

# GitHub 仓库信息
GITHUB_HOST  = "github.com"
REPO_OWNER   = "Rossettaylm"
REPO_NAME    = "config"
REPO_SSH_URL   = f"git@{GITHUB_HOST}:{REPO_OWNER}/{REPO_NAME}.git"
REPO_HTTPS_URL = f"https://{GITHUB_HOST}/{REPO_OWNER}/{REPO_NAME}.git"

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


def setup_repo_remote(use_ssh: bool, pat: str | None):
    """按协议偏好设置当前仓库的 origin remote URL。

    - SSH 可用  → git@github.com:owner/repo.git
    - SSH 不可用 → https://<pat>@github.com/owner/repo.git

    若当前 remote URL 已经与目标协议匹配则跳过，避免无必要的写操作及
    在无 PAT 时因无法构造 HTTPS URL 而中断流程。
    """
    repo_root = Path(__file__).parent

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
            print(f"remote origin 已是 SSH URL，跳过")
            return
        url = REPO_SSH_URL
    else:
        # 当前已是合法的 HTTPS URL（不论是否含 token），无需变更
        if current_url.startswith(f"https://{GITHUB_HOST}/") or \
                current_url.startswith(f"https://") and f"@{GITHUB_HOST}/" in current_url:
            print(f"remote origin 已是 HTTPS URL，跳过")
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


def update_submodules(use_ssh: bool, pat: str | None):
    """拉取所有 git submodule。

    - SSH 可用  → 直接执行，submodule 的 git@github.com: URL 原样生效
    - SSH 不可用 → 用 -c insteadOf 临时将 SSH / HTTPS URL 均改写为 HTTPS+PAT，
                   不修改任何 git 配置文件
    """
    repo_root = Path(__file__).parent
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


def init_fzf_tab():
    """安装 fzf-tab oh-my-zsh 插件。

    目标路径：$ZSH/custom/plugins/fzf-tab
    （$ZSH = ~/.config/zsh/oh-my-zsh，与 env.zsh 保持一致）
    若目录已存在且非空则跳过。
    """
    zsh_custom = Path.home() / ".config" / "zsh" / "oh-my-zsh" / "custom"
    plugin_dir = zsh_custom / "plugins" / "fzf-tab"

    if plugin_dir.exists() and any(plugin_dir.iterdir()):
        print(f"fzf-tab 插件已存在，跳过")
        return

    plugin_dir.mkdir(parents=True, exist_ok=True)
    print("正在安装 fzf-tab 插件...")
    ret = subprocess.run(
        ["git", "clone", "https://github.com/Aloxaf/fzf-tab", str(plugin_dir)],
        check=False,
    )
    if ret.returncode != 0:
        sys.exit("fzf-tab 安装失败")
    print("fzf-tab 安装完成")


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


def setup_zshrc():
    """确保 ~/.zshrc 中包含 source ~/.config/zsh/zshrc 一行。

    若已存在则跳过，避免重复追加。
    """
    zshrc = Path.home() / ".zshrc"
    source_line = "source $HOME/.config/zsh/zshrc"

    if zshrc.exists() and source_line in zshrc.read_text():
        print("~/.zshrc 已包含 source 配置，跳过")
        return

    with zshrc.open("a") as f:
        f.write(f"\n{source_line}\n")
    print(f"已向 ~/.zshrc 追加: {source_line}")


# gitconfig 模板：仅保留通用、跨平台内容
# 去除：[user]（隐私）、[credential]（平台相关）、公司内网 LFS 端点、
#       BeyondCompare mergetool/difftool（macOS 路径硬编码）、
#       [protocol] version=1（旧版内网兼容）、[http] postBuffer（内网大仓库专用）
GITCONFIG_TEMPLATE = """\
[core]
    quotepath = false
    longpaths = true
    autocrlf = false
    trustctime = false
    excludesfile = ~/.gitignore_global
    attributesfile = ~/.attributes_global
    ignorecase = true
    untrackedcache = true
    safecrlf = false
    eol = lf
[filter "lfs"]
    clean = git-lfs clean -- %f
    smudge = git-lfs smudge -- %f
    process = git-lfs filter-process
    required = true
[diff "text"]
    textconv = cat
[mergetool]
    keepBackup = false
    writeToTemp = true
[lfs]
    concurrenttransfers = 32
    fetchrecentrefsdays = 0
    pruneoffsetdays = 0
    dialtimeout = 3
    tlstimeout = 3
[lfs "transfer"]
    maxretries = 1
    maxretrydelay = 2
[rebase]
    backend = merge
[pull]
    rebase = false
[safe]
    directory = *
[init]
    defaultBranch = master
[gui]
    encoding = utf-8
[alias]
    st = status
    co = checkout
    ci = commit
    br = branch
"""


def setup_gitconfig():
    """将通用 gitconfig 写入 ~/.gitconfig。

    采用 git config 逐条写入而非直接覆盖文件，
    以便与用户已有的 [user] 等配置安全共存。
    已存在相同 key 时直接覆盖，不会产生重复项。
    """
    import configparser
    import re

    print("正在配置 ~/.gitconfig ...")
    parser = configparser.RawConfigParser()
    parser.read_string(GITCONFIG_TEMPLATE)

    for section in parser.sections():
        # 处理带子节的 section，如 filter "lfs" -> filter.lfs
        m = re.fullmatch(r'(\S+)\s+"([^"]+)"', section)
        if m:
            git_section = f"{m.group(1)}.{m.group(2)}"
        else:
            git_section = section

        for key, value in parser.items(section):
            ret = subprocess.run(
                ["git", "config", "--global", f"{git_section}.{key}", value],
                check=False,
            )
            if ret.returncode != 0:
                print(f"  警告: 设置 [{section}] {key} 失败，跳过")
    print("~/.gitconfig 配置完成")


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
    use_ssh = probe_ssh_github()
    setup_repo_remote(use_ssh, pat)
    update_submodules(use_ssh, pat)
    init_fzf()
    init_fzf_tab()

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

    setup_zshrc()
    setup_gitconfig()


if __name__ == "__main__":
    main()
