"""Zsh 插件初始化（手动管理，git submodule）。"""

import subprocess
import sys
from pathlib import Path

# 插件 submodule 相对路径（相对于 repo_root）
PLUGIN_SUBMODULES = [
    "zsh/plugins/zsh-autosuggestions",
    "zsh/plugins/zsh-syntax-highlighting",
    "zsh/plugins/fzf-tab",
    "zsh/plugins/zsh-defer",
]


def init_plugins(repo_root: Path):
    """确保所有插件 submodule 已初始化并拉取。

    - 若 submodule 目录为空，执行 git submodule update --init
    - 若已存在内容，跳过（幂等）
    """
    for rel_path in PLUGIN_SUBMODULES:
        plugin_dir = repo_root / rel_path
        name = plugin_dir.name

        # 目录非空则视为已初始化
        if plugin_dir.exists() and any(plugin_dir.iterdir()):
            print(f"  {name} 已就绪，跳过")
            continue

        print(f"  正在初始化 {name}...")
        ret = subprocess.run(
            ["git", "submodule", "update", "--init", "--recursive", rel_path],
            cwd=repo_root,
            check=False,
        )
        if ret.returncode != 0:
            sys.exit(f"  {name} 初始化失败")
        print(f"  {name} 初始化完成")
