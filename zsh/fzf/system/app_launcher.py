#!/usr/bin/python3
"""
macOS 应用启动器：扫描 /Applications 和 ~/Applications，fzf 选择后 open -a 启动。
用法: app_launcher.py
"""
import os
import subprocess
import sys; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pyutils.shell as shell


def find_apps():
    """扫描常见应用目录，返回 .app 名称列表。"""
    search_dirs = [
        "/Applications",
        "/Applications/Utilities",
        "/System/Applications",
        "/System/Applications/Utilities",
        os.path.expanduser("~/Applications"),
    ]
    apps = set()
    for d in search_dirs:
        if not os.path.isdir(d):
            continue
        for entry in os.listdir(d):
            if entry.endswith(".app"):
                apps.add(entry.removesuffix(".app"))
    return sorted(apps, key=str.lower)


def main():
    apps = find_apps()
    if not apps:
        shell.log_err("没有找到任何应用。")
        exit(0)

    fzf_cmd = shell.build_fzf_cmd(
        border_label="🚀  [App Launcher]",
        header="  Enter → 启动应用  ·  Esc quit",
        prompt="  App > ",
        preview="mdls -name kMDItemVersion -name kMDItemCFBundleIdentifier -name kMDItemCopyright '/Applications/{}.app' 2>/dev/null || echo 'No info'",
        preview_window="right,border-left,40%",
        preview_label="[ App Info ]",
        sort=True,
        as_str=False,
    )

    process = subprocess.Popen(
        fzf_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    stdout, _ = process.communicate(input="\n".join(apps))
    if process.returncode != 0 or not stdout.strip():
        exit(0)

    app_name = stdout.strip()
    shell.log_success(f"启动 {app_name} ...")
    subprocess.run(["open", "-a", app_name])


if __name__ == "__main__":
    main()
