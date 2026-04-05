"""FZF 初始化。"""

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
