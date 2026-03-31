"""FZF 及 fzf-tab 插件初始化。"""

import subprocess
import sys
from pathlib import Path


def init_fzf(repo_root: Path):
    """初始化 thirdparty/fzf：执行其安装脚本（仅装二进制，不修改 shell 配置）"""
    fzf_dir = repo_root / "thirdparty" / "fzf"
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


def init_fzf_tab():
    """安装 fzf-tab oh-my-zsh 插件。

    目标路径：$ZSH/custom/plugins/fzf-tab
    （$ZSH = ~/.config/zsh/oh-my-zsh，与 env.zsh 保持一致）
    若目录已存在且非空则跳过。
    """
    zsh_custom = Path.home() / ".config" / "zsh" / "oh-my-zsh" / "custom"
    plugin_dir = zsh_custom / "plugins" / "fzf-tab"

    if plugin_dir.exists() and any(plugin_dir.iterdir()):
        print("fzf-tab 插件已存在，跳过")
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
