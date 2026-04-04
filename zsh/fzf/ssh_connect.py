#!/usr/bin/python3
"""
交互式 SSH 连接：解析 ~/.ssh/config 的 Host 列表，fzf 选择后直接连接。
用法: ssh_connect.py
"""
import os
import re
import subprocess
import pyutils.shell as shell


def parse_ssh_hosts():
    """解析 ~/.ssh/config，返回 (host, hostname, user) 列表。"""
    config_path = os.path.expanduser("~/.ssh/config")
    if not os.path.isfile(config_path):
        return []

    hosts = []
    current = {}
    with open(config_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = re.match(r'^(\w+)\s+(.*)', line)
            if not m:
                continue
            key, value = m.group(1).lower(), m.group(2).strip()
            if key == "host":
                if current and current.get("host") not in ("*", ""):
                    hosts.append(current)
                current = {"host": value}
            elif key == "hostname":
                current["hostname"] = value
            elif key == "user":
                current["user"] = value
            elif key == "port":
                current["port"] = value

    if current and current.get("host") not in ("*", ""):
        hosts.append(current)
    return hosts


def main():
    hosts = parse_ssh_hosts()
    if not hosts:
        shell.log_err("~/.ssh/config 中没有找到任何 Host。")
        exit(0)

    # 格式化行: host -> user@hostname:port
    lines = []
    for h in hosts:
        label = h["host"]
        detail = h.get("hostname", "")
        if h.get("user"):
            detail = f"{h['user']}@{detail}"
        if h.get("port"):
            detail += f":{h['port']}"
        lines.append(f"{label:<25} {detail}")

    fzf_cmd = shell.build_fzf_cmd(
        border_label="🔗  [SSH Connect]",
        header="  Enter → 连接  ·  Esc quit",
        prompt="  Host > ",
        preview="ssh -G {1} 2>/dev/null | grep -E '^(hostname|user|port|identityfile)' | column -t",
        preview_window="right,border-left,40%",
        preview_label="[ SSH Config ]",
        as_str=False,
    )

    process = subprocess.Popen(
        fzf_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    stdout, _ = process.communicate(input="\n".join(lines))
    if process.returncode != 0 or not stdout.strip():
        exit(0)

    host = stdout.strip().split()[0]
    shell.log_success(f"连接到 {host} ...")
    os.execvp("ssh", ["ssh", host])


if __name__ == "__main__":
    main()
