"""Zsh 配置初始化。"""

from pathlib import Path


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
