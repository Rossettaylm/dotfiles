"""Tmux 插件初始化：通过 TPM 安装插件，链接手写配置。"""

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path.home() / ".config"
TPM_BIN = REPO_ROOT / "thirdparty" / "tpm" / "bin" / "install_plugins"
PLUGINS_DIR = REPO_ROOT / "tmux" / "plugins"

# (插件名, 插件内配置文件名, repo 中的源文件)
PLUGIN_CONFIGS = [
    ("tmux-which-key", "config.yaml", REPO_ROOT / "tmux" / "which-key-config.yaml"),
]


def init_tmux():
    """通过 TPM 安装 tmux.conf 中声明的插件，并链接手写配置。"""

    if not TPM_BIN.exists():
        raise RuntimeError(f"TPM 未找到: {TPM_BIN}，请先执行 git submodule update --init")

    PLUGINS_DIR.mkdir(parents=True, exist_ok=True)

    # TPM 安装所有 @plugin 声明的插件
    print("  通过 TPM 安装插件...")
    env = os.environ.copy()
    env["TMUX_PLUGIN_MANAGER_PATH"] = str(PLUGINS_DIR) + "/"
    subprocess.run([str(TPM_BIN)], env=env, check=True)

    # 初始化嵌套 submodule + 链接手写配置
    for plugin_name, config_name, config_src in PLUGIN_CONFIGS:
        plugin_dir = PLUGINS_DIR / plugin_name
        if not plugin_dir.exists():
            print(f"  警告: 插件 {plugin_name} 未安装")
            continue

        # 初始化嵌套 submodule（如 tmux-which-key 的 pyyaml）
        if (plugin_dir / ".gitmodules").exists():
            print(f"  初始化 {plugin_name} 的 submodule...")
            subprocess.run(
                ["git", "submodule", "update", "--init", "--recursive"],
                cwd=plugin_dir, check=True,
            )

        # 链接配置文件
        if config_src.exists():
            config_dest = plugin_dir / config_name
            if config_dest.exists() or config_dest.is_symlink():
                config_dest.unlink()
            config_dest.symlink_to(config_src)
            print(f"  {plugin_name}/{config_name} -> {config_src}")
        else:
            print(f"  警告: 配置源文件不存在 {config_src}")
