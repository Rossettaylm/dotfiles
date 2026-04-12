"""Zellij 插件初始化：下载 wasm 插件文件。"""

import urllib.request
import urllib.error
from pathlib import Path

ZELLIJ_PLUGINS = [
    {
        "name": "zjstatus",
        "version": "v0.22.0",
        "url": "https://github.com/dj95/zjstatus/releases/download/v0.22.0/zjstatus.wasm",
        "filename": "zjstatus.wasm",
    },
]


def init_zellij_plugins():
    """下载缺失的 zellij wasm 插件（已存在则跳过）。"""
    plugins_dir = Path.home() / ".config" / "zellij" / "plugins"
    plugins_dir.mkdir(parents=True, exist_ok=True)

    for plugin in ZELLIJ_PLUGINS:
        dest = plugins_dir / plugin["filename"]
        if dest.exists():
            print(f"  {plugin['name']} 已就绪，跳过")
            continue

        print(f"  正在下载 {plugin['name']} {plugin['version']}...")
        try:
            urllib.request.urlretrieve(plugin["url"], dest)
            print(f"  {plugin['name']} 下载完成 -> {dest}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"下载 {plugin['name']} 失败: {e}") from e
