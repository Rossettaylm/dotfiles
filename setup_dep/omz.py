"""oh-my-zsh 自定义插件初始化。"""

import subprocess
import sys
from pathlib import Path

# 需要安装到 $ZSH/custom/plugins/ 的第三方插件
CUSTOM_PLUGINS = {
    "zsh-autosuggestions": "https://github.com/zsh-users/zsh-autosuggestions.git",
    "zsh-syntax-highlighting": "https://github.com/zsh-users/zsh-syntax-highlighting.git",
    "fzf-tab": "https://github.com/Aloxaf/fzf-tab.git",
    "zsh-defer": "https://github.com/romkatv/zsh-defer.git",
}


def init_omz_plugins():
    """克隆 oh-my-zsh 自定义插件到 $ZSH/custom/plugins/。

    目标路径：~/.config/zsh/oh-my-zsh/custom/plugins/<name>
    若目录已存在且非空则跳过。
    """
    custom_plugins_dir = (
        Path.home() / ".config" / "zsh" / "oh-my-zsh" / "custom" / "plugins"
    )
    custom_plugins_dir.mkdir(parents=True, exist_ok=True)

    for name, url in CUSTOM_PLUGINS.items():
        plugin_dir = custom_plugins_dir / name
        if plugin_dir.exists() and any(plugin_dir.iterdir()):
            print(f"{name} 已存在，跳过")
            continue

        print(f"正在安装 {name}...")
        ret = subprocess.run(
            ["git", "clone", url, str(plugin_dir)],
            check=False,
        )
        if ret.returncode != 0:
            sys.exit(f"{name} 安装失败")
        print(f"{name} 安装完成")
