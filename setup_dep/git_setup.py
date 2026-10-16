"""Git 仓库与 GitHub 远程配置（SSH 交互式引导）。

无浏览器环境（远程 Linux 服务器）下也能完成初始化：脚本负责生成密钥、
预置 known_hosts、探测 22/443 端口，最后把公钥打印出来让用户去 GitHub 粘贴。
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

# GitHub 仓库信息
GITHUB_HOST = "github.com"
SSH_HOST = "ssh.github.com"
SSH_PORT_ALT = "443"
REPO_OWNER = "Rossettaylm"
REPO_NAME = "dotfiles"
REPO_SSH_URL = f"git@{GITHUB_HOST}:{REPO_OWNER}/{REPO_NAME}.git"

KEY_CANDIDATES = ["id_ed25519", "id_rsa", "id_ecdsa"]
KEY_COMMENT = "dotfiles-setup"
MAX_PASTE_ATTEMPTS = 3

SSH_CONFIG_MARKER = "# dotfiles-setup: github over 443"
SSH_CONFIG_BLOCK = f"""{SSH_CONFIG_MARKER}
Host {GITHUB_HOST}
  HostName {SSH_HOST}
  Port {SSH_PORT_ALT}
  User git
"""


# ── SSH 密钥 ──────────────────────────────────────────────

def _ssh_dir() -> Path:
    return Path.home() / ".ssh"


def ensure_ssh_key() -> Path:
    """定位或生成 SSH 私钥，返回私钥路径。"""
    ssh_dir = _ssh_dir()
    ssh_dir.mkdir(mode=0o700, exist_ok=True)

    for name in KEY_CANDIDATES:
        key = ssh_dir / name
        if key.exists():
            if not (ssh_dir / f"{name}.pub").exists():
                _derive_pubkey(key)
            print(f"使用已有 SSH 密钥: {key}")
            return key

    key = ssh_dir / KEY_CANDIDATES[0]
    print(f"未找到 SSH 密钥，正在生成 {key} ...")
    ret = subprocess.run(
        ["ssh-keygen", "-t", "ed25519", "-f", str(key),
         "-N", "", "-C", KEY_COMMENT],
        capture_output=True,
        text=True,
        check=False,
    )
    if ret.returncode != 0:
        sys.exit(f"ssh-keygen 失败: {ret.stderr.strip()}")
    print(f"已生成 SSH 密钥: {key}")
    return key


def _derive_pubkey(key: Path):
    """私钥存在但 .pub 缺失时，用 ssh-keygen -y 重新导出公钥。"""
    ret = subprocess.run(
        ["ssh-keygen", "-y", "-f", str(key)],
        capture_output=True,
        text=True,
        check=False,
    )
    if ret.returncode != 0:
        sys.exit(f"无法从 {key} 导出公钥: {ret.stderr.strip()}")
    pub = key.with_suffix(key.suffix + ".pub")
    pub.write_text(ret.stdout)
    print(f"已从私钥恢复公钥: {pub}")


def fix_permissions(key: Path):
    """修正 .ssh 目录与密钥权限，避免 ssh 因权限过宽拒绝使用。"""
    os.chmod(_ssh_dir(), 0o700)
    os.chmod(key, 0o600)
    pub = key.with_suffix(key.suffix + ".pub")
    if pub.exists():
        os.chmod(pub, 0o644)


def read_pubkey(key: Path) -> str:
    pub = key.with_suffix(key.suffix + ".pub")
    if not pub.exists():
        _derive_pubkey(key)
    return pub.read_text().strip()


# ── known_hosts ───────────────────────────────────────────

def _known_hosts_entries(path: Path) -> set[tuple[str, str]]:
    """解析 known_hosts 的 (host字段, 密钥类型) 集合，用于去重。"""
    entries = set()
    if not path.exists():
        return entries
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "|")):
            continue
        parts = line.split()
        if len(parts) >= 2:
            entries.add((parts[0], parts[1]))
    return entries


def ensure_known_hosts():
    """预置 github.com 与 ssh.github.com 的主机密钥，避免交互式指纹确认。"""
    if not shutil.which("ssh-keyscan"):
        print("未找到 ssh-keyscan，跳过 known_hosts 预置")
        return

    path = _ssh_dir() / "known_hosts"
    existing = _known_hosts_entries(path)
    added = []

    for host, port in ((GITHUB_HOST, "22"), (SSH_HOST, SSH_PORT_ALT)):
        ret = subprocess.run(
            ["ssh-keyscan", "-T", "5", "-p", port, host],
            capture_output=True,
            text=True,
            check=False,
        )
        if ret.returncode != 0 or not ret.stdout.strip():
            continue
        for line in ret.stdout.splitlines():
            line = line.strip()
            # ssh-keyscan 会把 "# host:port SSH-2.0-..." 注释一并输出，需剔除
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 3 or (parts[0], parts[1]) in existing:
                continue
            existing.add((parts[0], parts[1]))
            added.append(line)

    if not added:
        print("known_hosts 已包含 GitHub 主机密钥")
        return

    with path.open("a") as f:
        f.write("\n".join(added) + "\n")
    os.chmod(path, 0o600)
    print(f"已写入 {len(added)} 条 GitHub 主机密钥到 {path}")


# ── 连通性与认证探测 ──────────────────────────────────────

def _ssh_probe(host: str, port: str | None = None) -> tuple[bool, str]:
    """返回 (能否建立连接, 输出)。exit 255 表示连接/认证彻底失败。

    port 为 None 时交给 ssh 自己解析（会应用 ~/.ssh/config 的改写）。
    """
    cmd = ["ssh", "-T"]
    if port:
        cmd += ["-p", port]
    cmd += [
        "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "ConnectTimeout=5",
        f"git@{host}",
    ]
    ret = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return ret.returncode != 255, (ret.stdout + ret.stderr)


def is_authenticated() -> bool:
    """git@github.com 是否已通过认证（含 ~/.ssh/config 的 443 改写）。"""
    _, out = _ssh_probe(GITHUB_HOST)
    return "successfully authenticated" in out


def _ensure_sshd_config_443():
    """22 端口不通时，在 ~/.ssh/config 中把 github.com 改写到 443。"""
    config = _ssh_dir() / "config"
    if config.exists() and SSH_CONFIG_MARKER in config.read_text(errors="replace"):
        print("~/.ssh/config 已存在 443 改写，跳过")
        return

    current = config.read_text(errors="replace") if config.exists() else ""
    with config.open("a") as f:
        if current and not current.endswith("\n"):
            f.write("\n")
        f.write("\n" + SSH_CONFIG_BLOCK)
    os.chmod(config, 0o600)
    print(f"22 端口不可用，已在 {config} 中启用 github.com → {SSH_HOST}:{SSH_PORT_ALT}")


# ── 公钥粘贴引导 ──────────────────────────────────────────

def _print_pubkey_box(pubkey: str, key: Path):
    width = 68
    print(f"\n  ┌{'─' * width}")
    print(f"  │ {'公钥尚未授权，请粘贴到 GitHub：'}")
    print(f"  │")
    for line in [pubkey[i:i + width - 4] for i in range(0, len(pubkey), width - 4)]:
        print(f"  │ {line}")
    print(f"  │")
    print(f"  │ 私钥文件：{key}")
    print(f"  │ 设置地址：https://{GITHUB_HOST}/settings/keys  →  New SSH key")
    print(f"  │ （只读场景可用 Deploy key：仓库 → Settings → Deploy keys）")
    print(f"  └{'─' * width}\n")


def prompt_authorize(pubkey: str, key: Path) -> bool:
    """打印公钥并等待用户在 GitHub 完成粘贴，最多重试 MAX_PASTE_ATTEMPTS 次。"""
    if not sys.stdin.isatty():
        print("当前非交互环境，无法等待公钥粘贴。请先手动授权后重跑。")
        _print_pubkey_box(pubkey, key)
        return False

    for attempt in range(1, MAX_PASTE_ATTEMPTS + 1):
        _print_pubkey_box(pubkey, key)
        if attempt > 1:
            print(f"  第 {attempt}/{MAX_PASTE_ATTEMPTS} 次重试")
        try:
            input("  粘贴完成后按回车重试（Ctrl-C 退出）... ")
        except (KeyboardInterrupt, EOFError):
            print()
            return False

        if is_authenticated():
            print("SSH 认证成功")
            return True
        print("  仍未认证成功，请确认公钥已添加到正确的 GitHub 账号")

    return False


# ── 对外入口 ──────────────────────────────────────────────

def ensure_ssh_ready() -> bool:
    """确保 SSH 可认证 GitHub；必要时引导用户粘贴公钥。"""
    if not shutil.which("ssh-keygen"):
        sys.exit("未找到 ssh-keygen，请先安装 openssh-client")

    key = ensure_ssh_key()
    fix_permissions(key)
    ensure_known_hosts()

    # 22 不通则尝试 443，成功则写入 ~/.ssh/config
    reachable_22, _ = _ssh_probe(GITHUB_HOST, "22")
    if not reachable_22:
        reachable_443, _ = _ssh_probe(SSH_HOST, SSH_PORT_ALT)
        if reachable_443:
            _ensure_sshd_config_443()
        else:
            print("22 与 443 均无法连通 GitHub，请检查网络/代理")

    if is_authenticated():
        print(f"SSH 已认证 GitHub: {GITHUB_HOST}")
        return True

    return prompt_authorize(read_pubkey(key), key)


def setup_repo_remote(repo_root: Path):
    """将当前仓库 origin 设为 SSH URL（已是则跳过）。"""
    cur = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if cur.stdout.strip() == REPO_SSH_URL:
        print("remote origin 已是 SSH URL，跳过")
        return

    subprocess.run(
        ["git", "remote", "set-url", "origin", REPO_SSH_URL],
        cwd=repo_root,
        check=True,
    )
    print(f"remote origin 已设为: {REPO_SSH_URL}")


def update_submodules(repo_root: Path):
    """拉取所有 git submodule（公开仓库走 HTTPS，无需凭证）。"""
    print("正在更新 git submodules...")
    ret = subprocess.run(
        ["git", "submodule", "update", "--init", "--recursive"],
        cwd=repo_root,
        check=False,
    )
    if ret.returncode != 0:
        sys.exit("git submodule 更新失败")
    print("git submodules 更新完成")
