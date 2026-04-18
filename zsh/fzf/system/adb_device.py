#!/usr/bin/python3
"""
交互式 ADB 设备选择器：列出已连接设备，fzf 选择后输出 serial 到 stdout。
配合 alias 使用 export ANDROID_SERIAL=$(...) 可设为当前 shell 默认设备。
用法: adb_device.py
"""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import subprocess
import pyutils.shell as shell


def main():
    try:
        result = subprocess.run(
            ["adb", "devices", "-l"],
            capture_output=True, text=True, timeout=5,
        )
    except subprocess.TimeoutExpired:
        shell.log_err("adb 命令超时，请检查 adb server 状态或设备连接。")
        exit(1)
    if result.returncode != 0:
        shell.log_err("adb 命令执行失败，请确认 adb 已安装并在 PATH 中。")
        exit(1)

    # 解析 adb devices -l 输出，跳过首行 "List of devices attached"
    devices = []
    for line in result.stdout.strip().splitlines()[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[1] != "offline":
            serial = parts[0]
            # 提取 model 和 device 信息
            info = {}
            for p in parts[2:]:
                if ":" in p:
                    k, v = p.split(":", 1)
                    info[k] = v
            model = info.get("model", "unknown")
            device = info.get("device", "")
            status = parts[1]
            devices.append(f"{serial:<25} {model:<20} {device:<15} [{status}]")

    if not devices:
        shell.log_err("没有找到已连接的 ADB 设备。")
        exit(1)

    cur_serial = os.environ.get("ANDROID_SERIAL", "")
    header = f"  当前默认: {cur_serial}" if cur_serial else "  未设置默认设备"
    header += "  ·  Enter → 设为默认  ·  Esc quit"

    fzf_cmd = shell.build_fzf_cmd(
        border_label="📱  [ADB Device]",
        header=header,
        prompt="  Device > ",
        preview="adb -s $(echo {} | awk '{print $1}') shell getprop ro.build.display.id 2>/dev/null; "
                "echo '---'; "
                "adb -s $(echo {} | awk '{print $1}') shell getprop ro.product.brand 2>/dev/null; "
                "adb -s $(echo {} | awk '{print $1}') shell getprop ro.build.version.release 2>/dev/null",
        preview_window="right,border-left,35%",
        preview_label="[ Device Info ]",
        as_str=False,
    )

    process = subprocess.Popen(
        fzf_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    stdout, _ = process.communicate(input="\n".join(devices))
    if process.returncode != 0 or not stdout.strip():
        exit(0)

    serial = stdout.strip().split()[0]
    # 输出 serial 到 stdout，供 alias 的 export 捕获
    print(serial)


if __name__ == "__main__":
    main()
